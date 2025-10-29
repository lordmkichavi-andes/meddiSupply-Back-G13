from flask import Flask, jsonify, request, make_response
from adapters.sql_adapter import PostgreSQLProductAdapter
from services.product_service import ProductService
from database_setup import setup_database
from flask_caching import Cache
from functools import wraps
import os
import json

REDIS_HOST = os.environ.get('CACHE_HOST')
REDIS_PORT = os.environ.get('CACHE_PORT', '6379')
REDIS_DB = os.environ.get('CACHE_DB', '0')

config = {
    "CACHE_TYPE": "SimpleCache",  # Usamos un caché en memoria (Pruebas locales)
    "CACHE_DEFAULT_TIMEOUT": 300  # 5 minutos de duración del caché(Pruebas locales)
}

app = Flask(__name__)
app.config.from_mapping(config)
cache = Cache(app)


def cache_control_header(timeout=None, key = ""):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = key if key != "" else  request.full_path
            # Intenta obtener la respuesta del caché
            cached_response = cache.get(cache_key)

            if cached_response is not None:
                # Si la respuesta está en caché, la devolvemos con el encabezado HIT
                response = make_response(cached_response)
                response.headers['X-Cache'] = 'HIT'
                return response
            else:
                # Si no está en caché, generamos la respuesta
                response = make_response(f(*args, **kwargs))
                response.headers['X-Cache'] = 'MISS'

                # Guardamos la respuesta en la caché antes de devolverla
                cache.set(cache_key, response.data, timeout=timeout)

                return response

        return decorated_function

    return decorator


# Dependencia: inyección del repositorio en el servicio
product_repository = PostgreSQLProductAdapter()
product_service = ProductService(repository=product_repository)
setup_database()


@app.route('/products/available', methods=['GET'])
@cache_control_header(timeout=180, key="products")
def get_products():
    """Endpoint para listar productos disponibles."""
    products = product_service.list_available_products()
    # Convertir la lista de objetos Product en un formato serializable (dict)
    products_list = [p.__dict__ for p in products]
    return jsonify(products_list)


@app.route('/products/update/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """
    Endpoint para actualizar un producto y forzar la invalidación de la caché.
    """
    data = request.get_json()
    price = data.get('price')
    warehouse = data.get('warehouse')
    stock = data.get('stock')

    if price is None or stock is None:
        return jsonify({"error": "Price and stock are required"}), 400

    # Actualiza el producto en la base de datos
    product_service.update_product(product_id, price=price, stock=stock, warehouse= warehouse)

    # ⚠️ Invalida la caché del endpoint de productos disponibles y del producto individual
    cache_key_to_invalidate = 'products'
    cache.delete(cache_key_to_invalidate)
    cache.delete(product_id)

    cache_key_to_invalidate_single = f'/products/{product_id}'
    cache.delete(cache_key_to_invalidate_single)

    return jsonify({"status": "Product updated and cache invalidated"}), 200


@app.route('/products/<int:product_id>', methods=['GET'])
@cache_control_header(timeout=180)
def get_product_by_id(product_id):
    """
    Endpoint para obtener un producto por su ID.
    """
    product = product_service.get_product_by_id(product_id)
    if product:
        return jsonify(product.__dict__)
    else:
        return jsonify({"error": "Product not found"}), 404


@app.route('/products/active', methods=['GET'])
@cache_control_header(timeout=300, key="products_active")
def get_active_products():
    """
    Endpoint para obtener todos los productos activos con información completa.
    Incluye información de unidades y categorías para planes de venta.
    """
    conn, cursor = product_repository._get_connection()
    
    try:
        query = '''
        SELECT 
            p.product_id,
            p.sku,
            p.name,
            p.value,
            p.objective_profile,
            u.name as unit_name,
            u.symbol as unit_symbol,
            c.name as category_name,
            COALESCE(ps.total_quantity, 0) as max_quantity
        FROM 
            products.products p
        JOIN 
            products.units u ON p.unit_id = u.unit_id
        JOIN 
            products.category c ON p.category_id = c.category_id
        LEFT JOIN (
            SELECT product_id, SUM(quantity) as total_quantity
            FROM products.productstock 
            WHERE quantity > 0
            GROUP BY product_id
        ) ps ON p.product_id = ps.product_id
        WHERE
            p.status = 'activo'
        ORDER BY
            p.name;
        '''
        
        cursor.execute(query)
        results = cursor.fetchall()
        products = [dict(row) for row in results]
        return jsonify(products), 200
        
    finally:
        cursor.close()
        conn.close()


@app.route('/products/search', methods=['GET'])
@cache_control_header(timeout=180, key="products_search")
def search_products():
    """
    Endpoint para buscar productos por nombre (para el selector con búsqueda).
    Parámetros:
    - q: término de búsqueda (opcional)
    """
    search_term = request.args.get('q', '').strip()
    
    conn, cursor = product_repository._get_connection()
    
    try:
        if not search_term:
            # Si no hay término de búsqueda, devolver todos los activos
            query = '''
            SELECT 
                p.product_id,
                p.sku,
                p.name,
                p.value,
                p.objective_profile,
                u.name as unit_name,
                u.symbol as unit_symbol,
                c.name as category_name,
                COALESCE(ps.total_quantity, 0) as max_quantity
            FROM 
                products.products p
            JOIN 
                products.units u ON p.unit_id = u.unit_id
            JOIN 
                products.category c ON p.category_id = c.category_id
            LEFT JOIN (
                SELECT product_id, SUM(quantity) as total_quantity
                FROM products.productstock 
                WHERE quantity > 0
                GROUP BY product_id
            ) ps ON p.product_id = ps.product_id
            WHERE
                p.status = 'activo'
            ORDER BY
                p.name;
            '''
            cursor.execute(query)
        else:
            # Buscar por nombre
            query = '''
            SELECT 
                p.product_id,
                p.sku,
                p.name,
                p.value,
                p.objective_profile,
                u.name as unit_name,
                u.symbol as unit_symbol,
                c.name as category_name,
                COALESCE(ps.total_quantity, 0) as max_quantity
            FROM 
                products.products p
            JOIN 
                products.units u ON p.unit_id = u.unit_id
            JOIN 
                products.category c ON p.category_id = c.category_id
            LEFT JOIN (
                SELECT product_id, SUM(quantity) as total_quantity
                FROM products.productstock 
                WHERE quantity > 0
                GROUP BY product_id
            ) ps ON p.product_id = ps.product_id
            WHERE
                p.status = 'activo'
                AND LOWER(p.name) LIKE LOWER(%s)
            ORDER BY
                p.name;
            '''
            cursor.execute(query, (f'%{search_term}%',))
        
        results = cursor.fetchall()
        products = [dict(row) for row in results]
        return jsonify(products), 200
        
    finally:
        cursor.close()
        conn.close()


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
