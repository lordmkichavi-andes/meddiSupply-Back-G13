from flask import Flask, jsonify, request, make_response, send_file
from flask_cors import CORS
from adapters.sql_adapter import PostgreSQLProductAdapter
from services.product_service import ProductService
from database_setup import setup_database
from flask_caching import Cache
from functools import wraps
import os
import json
import io
import pandas as pd
from datetime import datetime

REDIS_HOST = os.environ.get('CACHE_HOST')
REDIS_PORT = os.environ.get('CACHE_PORT', '6379')
REDIS_DB = os.environ.get('CACHE_DB', '0')

config = {
    "CACHE_TYPE": "SimpleCache",  # Usamos un caché en memoria (Pruebas locales)
    "CACHE_DEFAULT_TIMEOUT": 300  # 5 minutos de duración del caché(Pruebas locales)
}

app = Flask(__name__)

CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
    }
})

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

@app.route('/products/upload3', methods=['POST'])
def upload_products_string():
    print("=== INICIO UPLOAD PRODUCTS STRING ===")
    conn = None
    cursor = None
    
    try:
        # Obtener los datos como cadena de texto
        data_string = request.get_data(as_text=True)

        if not data_string or data_string.strip() == '':
            return jsonify({
                "success": False,
                "message": "No se recibieron datos para procesar",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": ["No se recibieron datos para procesar"],
                "warnings": []
            }), 400

        print(f"Datos recibidos como string: {data_string[:200]}...")

        # Limpiar el string (remover espacios en blanco al inicio y final)
        data_string = data_string.strip()

        # Intentar parsear como JSON
        try:
            products_data = json.loads(data_string)
        except json.JSONDecodeError as e:
            return jsonify({
                "success": False,
                "message": "Error al parsear JSON",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": [f"Error de sintaxis JSON: {str(e)}"],
                "warnings": []
            }), 400

        # Verificar que sea un array
        if not isinstance(products_data, list):
            return jsonify({
                "success": False,
                "message": "Los datos deben ser un array de productos",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": ["Los datos deben ser un array de productos"],
                "warnings": []
            }), 400

        if not products_data:
            return jsonify({
                "success": False,
                "message": "No se recibieron productos para procesar",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": ["No se recibieron productos para procesar"],
                "warnings": []
            }), 400

        print(f"Productos parseados: {len(products_data)}")

        # Validar campos obligatorios
        required_fields = ['sku', 'name', 'value', 'category_name', 'quantity', 'warehouse_id']
        errors = []
        warnings = []

        for index, product in enumerate(products_data):
            row_num = index + 1

            # Verificar que sea un diccionario
            if not isinstance(product, dict):
                errors.append(f"Fila {row_num}: El producto debe ser un objeto JSON")
                continue

            # Verificar campos obligatorios
            for field in required_fields:
                if field not in product or product[field] is None or str(product[field]).strip() == '':
                    errors.append(f"Fila {row_num}: {field} es obligatorio")

            # Validaciones específicas
            if 'sku' in product and product['sku']:
                if len(str(product['sku']).strip()) < 3:
                    warnings.append(f"Fila {row_num}: SKU muy corto (mínimo 3 caracteres)")

            if 'value' in product and product['value']:
                try:
                    value = float(str(product['value']))
                    if value <= 0:
                        errors.append(f"Fila {row_num}: El valor debe ser mayor a 0")
                except (ValueError, TypeError):
                    errors.append(f"Fila {row_num}: El valor debe ser un número válido")

            if 'quantity' in product and product['quantity']:
                try:
                    quantity = int(str(product['quantity']))
                    if quantity < 0:
                        errors.append(f"Fila {row_num}: La cantidad no puede ser negativa")
                except (ValueError, TypeError):
                    errors.append(f"Fila {row_num}: La cantidad debe ser un número entero válido")

            if 'warehouse_id' in product and product['warehouse_id']:
                try:
                    warehouse_id = int(str(product['warehouse_id']))
                    if warehouse_id <= 0:
                        errors.append(f"Fila {row_num}: El warehouse_id debe ser mayor a 0")
                except (ValueError, TypeError):
                    errors.append(f"Fila {row_num}: El warehouse_id debe ser un número entero válido")

        # Si hay errores de validación, retornar error
        if errors:
            return jsonify({
                "success": False,
                "message": "Error en la validación",
                "total_records": len(products_data),
                "successful_records": 0,
                "failed_records": len(products_data),
                "errors": errors,
                "warnings": warnings
            }), 400
        
        # Conectar a la base de datos
        conn, cursor = product_repository._get_connection()
        print("Conexión a BD establecida")
        
        # 1. Crear registro en product_uploads
        upload_insert = """
            INSERT INTO products.product_uploads 
            (file_name, file_type, file_size, total_records, successful_records, failed_records, state, start_date, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            RETURNING id
        """
        
        cursor.execute(upload_insert, (
            'string_upload',
            'string',
            len(data_string),  # file_size basado en la longitud del string
            len(products_data),
            0,  # successful_records
            0,  # failed_records
            'procesando',
            1   # user_id (hardcoded por ahora)
        ))
        
        upload_id = cursor.fetchone()['id']
        print(f"Upload ID creado: {upload_id}")
        
        successful_records = 0
        failed_records = 0
        processed_errors = []

        # 2. Procesar cada producto del JSON
        for index, product in enumerate(products_data):
            row_num = index + 1
            print(f"Procesando producto {row_num}: {product.get('sku', 'N/A')}")
            
            try:
                # Obtener o crear category_id
                cursor.execute("SELECT category_id FROM products.category WHERE name = %s", (product['category_name'],))
                category_result = cursor.fetchone()
                
                if category_result:
                    category_id = category_result['category_id']
                else:
                    # Crear nueva categoría si no existe - obtener el siguiente ID disponible
                    cursor.execute("SELECT COALESCE(MAX(category_id), 0) + 1 FROM products.category")
                    next_category_id = cursor.fetchone()[0]

                    cursor.execute("""
                        INSERT INTO products.category (category_id, name) 
                        VALUES (%s, %s) 
                        RETURNING category_id
                    """, (next_category_id, product['category_name']))
                    category_id = cursor.fetchone()['category_id']
                    print(f"Nueva categoría creada: {product['category_name']} (ID: {category_id})")
                
                # Insertar producto
                product_insert = """
                    INSERT INTO products.products 
                    (sku, name, value, category_id, provider_id, status, objective_profile, unit_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING product_id
                """
                
                cursor.execute(product_insert, (
                    product['sku'],
                    product['name'],
                    float(product['value']),
                    category_id,
                    1,  # provider_id (hardcoded)
                    'activo',
                    '',  # objective_profile
                    1    # unit_id (hardcoded)
                ))
                
                product_id = cursor.fetchone()['product_id']
                print(f"Producto creado: {product['sku']} (ID: {product_id})")
                
                # Insertar stock
                stock_insert = """
                    INSERT INTO products.productstock 
                    (product_id, quantity, lote, warehouse_id, provider_id, country)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(stock_insert, (
                    product_id,
                    int(product['quantity']),
                    f"LOTE-{product['sku']}-{datetime.now().strftime('%Y%m%d')}",  # lote generado
                    int(product['warehouse_id']),
                    1,  # provider_id
                    'COL'  # country (hardcoded)
                ))
                print(f"Stock creado para producto {product_id}")
                
                # Insertar en product_history
                history_insert = """
                    INSERT INTO products.product_history 
                    (product_id, new_value, change_type, user_id, upload_id)
                    VALUES (%s, %s, %s, %s, %s)
                """
                
                cursor.execute(history_insert, (
                    product_id,
                    float(product['value']),
                    'creacion',
                    1,  # user_id
                    upload_id
                ))
                print(f"Historial creado para producto {product_id}")
                
                # Insertar en product_upload_details (éxito)
                details_insert = """
                    INSERT INTO products.product_upload_details 
                    (upload_id, row_id, code, name, price, category, status, product_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(details_insert, (
                    upload_id,
                    row_num,
                    product['sku'],
                    product['name'],
                    float(product['value']),
                    product['category_name'],
                    'exitoso',
                    product_id
                ))
                
                successful_records += 1
                print(f"Producto {row_num} procesado exitosamente")
                
            except Exception as row_error:
                error_msg = f"Fila {row_num}: {str(row_error)}"
                print(f"Error en producto {row_num}: {str(row_error)}")
                processed_errors.append(error_msg)
                
                # Insertar en product_upload_details (fallo)
                details_insert = """
                    INSERT INTO products.product_upload_details 
                    (upload_id, row_id, code, name, price, category, status, errors)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(details_insert, (
                    upload_id,
                    row_num,
                    product.get('sku', 'N/A'),
                    product.get('name', 'N/A'),
                    float(product.get('value', 0)),
                    product.get('category_name', 'N/A'),
                    'fallido',
                    str(row_error)
                ))
                
                failed_records += 1
        
        # 3. Actualizar product_uploads con resultados finales
        update_upload = """
            UPDATE products.product_uploads 
            SET successful_records = %s, failed_records = %s, state = %s, end_date = NOW()
            WHERE id = %s
        """
        
        cursor.execute(update_upload, (
            successful_records,
            failed_records,
            'completado',
            upload_id
        ))
        
        # Commit de la transacción
        conn.commit()
        print(f"Transacción completada. Exitosos: {successful_records}, Fallidos: {failed_records}")

        # Determinar si fue exitoso
        success = failed_records == 0
        
        return jsonify({
            "success": success,
            "message": f"Procesados {len(products_data)} productos" if success else f"Procesados {len(products_data)} productos con {failed_records} errores",
            "total_records": len(products_data),
            "successful_records": successful_records,
            "failed_records": failed_records,
            "upload_id": upload_id,
            "errors": processed_errors,
            "warnings": warnings
        })
        
    except Exception as e:
        print(f"ERROR en upload string: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if conn:
            conn.rollback()
            print("Rollback ejecutado")
        
        return jsonify({
            "success": False,
            "message": "Error interno del servidor",
            "total_records": len(products_data) if 'products_data' in locals() else 0,
            "successful_records": 0,
            "failed_records": len(products_data) if 'products_data' in locals() else 0,
            "errors": [f"Error interno: {str(e)}"],
            "warnings": []
        }), 500
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("Conexiones cerradas")


@app.route('/products/location/warehouses', methods=['GET'])
def get_warehouses():
    """
    Endpoint para obtener la lista de almacenes disponibles.
    Parámetro opcional: city_id - Si se proporciona, filtra almacenes por ciudad.
    """
    try:
        # Obtener parámetro opcional city_id
        city_id = request.args.get('city_id', type=int)

        conn, cursor = product_repository._get_connection()
        
        # Consulta base para obtener almacenes
        if city_id:
            # Si se proporciona city_id, filtrar por ciudad (usando datos de ejemplo)
            # Como no hay relación directa entre warehouse y city en la BD actual,
            # devolvemos almacenes con información de ciudad simulada
            query = """
                SELECT DISTINCT 
                    ps.warehouse_id,
                    ps.warehouse_id as name,
                    'Almacén ' || ps.warehouse_id as description,
                    'Ciudad ' || %s as city_name,
                    ps.country
                FROM products.productstock ps
                WHERE ps.warehouse_id IS NOT NULL
                ORDER BY ps.warehouse_id
            """
            cursor.execute(query, (city_id,))
        else:
            # Si no se proporciona city_id, devolver todos los almacenes
            query = """
                SELECT DISTINCT 
                    warehouse_id,
                    warehouse_id as name,
                    'Almacén ' || warehouse_id as description
                FROM products.productstock 
                WHERE warehouse_id IS NOT NULL
                ORDER BY warehouse_id
            """
            cursor.execute(query)

        warehouses = cursor.fetchall()

        # Si no hay datos en productstock, crear datos de ejemplo
        if not warehouses:
            if city_id:
                warehouses = [
                    {'warehouse_id': 1, 'name': 'Almacén Principal', 'description': 'Almacén Principal - Ciudad ' + str(city_id), 'city_name': 'Ciudad ' + str(city_id), 'country': 'COL'}
                ]
            else:
                warehouses = [
                    {'warehouse_id': 1, 'name': 'Almacén Principal', 'description': 'Almacén Principal - Bogotá'},
                    {'warehouse_id': 2, 'name': 'Almacén Norte', 'description': 'Almacén Norte - Medellín'},
                    {'warehouse_id': 3, 'name': 'Almacén Sur', 'description': 'Almacén Sur - Cali'}
                ]
        
        return jsonify({
            'warehouses': warehouses,
            'total': len(warehouses),
            'city_id': city_id if city_id else None
        }), 200

    except Exception as e:
        print(f"Error en get_warehouses: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/products/location/cities', methods=['GET'])
def get_cities():
    """
    Endpoint para obtener la lista de ciudades disponibles.
    """
    try:
        conn, cursor = product_repository._get_connection()

        # Consulta para obtener ciudades basadas en los datos de productstock
        query = """
            SELECT DISTINCT 
                country,
                CASE 
                    WHEN country = 'COL' THEN 'Colombia'
                    WHEN country = 'MEX' THEN 'México'
                    WHEN country = 'ARG' THEN 'Argentina'
                    ELSE country
                END as country_name
            FROM products.productstock 
            WHERE country IS NOT NULL
            ORDER BY country
        """

        cursor.execute(query)
        countries = cursor.fetchall()

        # Si no hay datos, crear datos de ejemplo
        if not countries:
            countries = [
                {'country': 'COL', 'country_name': 'Colombia'},
                {'country': 'MEX', 'country_name': 'México'},
                {'country': 'ARG', 'country_name': 'Argentina'}
            ]

        # Crear ciudades de ejemplo basadas en países
        cities = []
        for country in countries:
            if country['country'] == 'COL':
                cities.extend([
                    {'city_id': 1, 'name': 'Bogotá', 'country': country['country'], 'country_name': country['country_name']},
                    {'city_id': 2, 'name': 'Medellín', 'country': country['country'], 'country_name': country['country_name']},
                    {'city_id': 3, 'name': 'Cali', 'country': country['country'], 'country_name': country['country_name']}
                ])
            elif country['country'] == 'MEX':
                cities.extend([
                    {'city_id': 4, 'name': 'Ciudad de México', 'country': country['country'], 'country_name': country['country_name']},
                    {'city_id': 5, 'name': 'Guadalajara', 'country': country['country'], 'country_name': country['country_name']}
                ])
            elif country['country'] == 'ARG':
                cities.extend([
                    {'city_id': 6, 'name': 'Buenos Aires', 'country': country['country'], 'country_name': country['country_name']},
                    {'city_id': 7, 'name': 'Córdoba', 'country': country['country'], 'country_name': country['country_name']}
                ])

        return jsonify({
            'cities': cities,
            'total': len(cities)
        }), 200

    except Exception as e:
        print(f"Error en get_cities: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/products/location', methods=['GET'])
def get_location_info():
    """
    Endpoint para obtener información completa de ubicaciones (almacenes y ciudades).
    """
    try:
        # Obtener almacenes
        warehouses_response = get_warehouses()
        warehouses_data = warehouses_response[0].get_json() if warehouses_response[1] == 200 else {'warehouses': []}

        # Obtener ciudades
        cities_response = get_cities()
        cities_data = cities_response[0].get_json() if cities_response[1] == 200 else {'cities': []}

        # Obtener productos disponibles
        products_response = product_service.list_available_products()
        products = products_response if products_response else []

        return jsonify({
            'warehouses': warehouses_data.get('warehouses', []),
            'cities': cities_data.get('cities', []),
            'products': products,
            'summary': {
                'total_warehouses': len(warehouses_data.get('warehouses', [])),
                'total_cities': len(cities_data.get('cities', [])),
                'total_products': len(products),
                'countries': list(set([city.get('country') for city in cities_data.get('cities', [])]))
            }
        }), 200

    except Exception as e:
        print(f"Error en get_location_info: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500


@app.route('/products/warehouse/<int:warehouse_id>', methods=['GET'])
def get_products_by_warehouse(warehouse_id):
    """
    Endpoint para obtener todos los productos de una bodega específica.
    """
    conn = None
    cursor = None
    try:
        print(f"=== INICIO get_products_by_warehouse para warehouse_id: {warehouse_id} ===")

        conn, cursor = product_repository._get_connection()
        print("Conexión a BD establecida")

        # Consulta con campos adicionales para cada producto
        query = """
            SELECT 
                p.product_id,
                p.sku,
                p.name,
                p.value,
                p.image_url,
                p.status as product_status,
                p.creation_date,
                c.name as category_name,
                ps.quantity,
                ps.warehouse_id,
                ps.lote,
                ps.country,
                ps.expiry_date,
                ps.status as stock_status,
                ps.last_movement_date
            FROM products.products p
            JOIN products.productstock ps ON p.product_id = ps.product_id
            JOIN products.category c ON p.category_id = c.category_id
            WHERE ps.warehouse_id = %s
            ORDER BY p.name
            LIMIT 10
        """

        print(f"Ejecutando consulta para warehouse_id: {warehouse_id}")
        cursor.execute(query, (warehouse_id,))
        products = cursor.fetchall()
        print(f"Productos encontrados: {len(products)}")

        if not products:
            return jsonify({
                'warehouse_id': warehouse_id,
                'products': [],
                'total_products': 0,
                'total_quantity': 0,
                'message': f'No se encontraron productos en la bodega {warehouse_id}'
            }), 200

        # Calcular totales
        total_quantity = sum(product['quantity'] for product in products)
        
        return jsonify({
            'warehouse_id': warehouse_id,
            'products': products,
            'total_products': len(products),
            'total_quantity': total_quantity,
            'totalAvailable': total_quantity,
            'hasAvailability': total_quantity > 0,
            'warehouse': warehouse_id,
            'locations': [
                {
                    'id': warehouse_id,
                    'name': f'Almacén {warehouse_id}',
                    'address': f'Dirección del Almacén {warehouse_id}',
                    'city': 'Bogotá',
                    'country': 'Colombia',
                    'coordinates': {
                        'lat': 4.6097,
                        'lng': -74.0817
                    }
                }
            ],
            'summary': {
                'categories': list(set([product['category_name'] for product in products])),
                'countries': list(set([product['country'] for product in products if product.get('country')])),
                'total_lotes': len(set([product['lote'] for product in products if product.get('lote')]))
            }
        }), 200
        
    except Exception as e:
        print(f"Error en get_products_by_warehouse: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error interno del servidor: {str(e)}'}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print("Conexiones cerradas")


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
