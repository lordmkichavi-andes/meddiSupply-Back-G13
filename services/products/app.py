from flask import Flask, jsonify, request, make_response, send_file
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


@app.route('/products/upload', methods=['POST'])
def upload_products():
    print("=== INICIO UPLOAD PRODUCTS SIMPLIFICADO ===")
    try:
        files = request.files.getlist('files')
        print(f"Archivos recibidos: {len(files)}")
        
        if not files:
            return jsonify({"error": "No files received"}), 400
        
        file = files[0]
        print(f"Procesando archivo: {file.filename}")
        
        # Leer el archivo
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(file)
            print(f"CSV leído con {len(df)} filas")
        else:
            return jsonify({"error": "Only CSV files are supported"}), 400
        
        # Verificar columnas requeridas
        required_columns = ['sku', 'name', 'value', 'category_name', 'quantity', 'warehouse_id']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return jsonify({"error": f"Missing columns: {missing_columns}"}), 400
        
        # Mostrar primera fila
        first_row = df.iloc[0].to_dict()
        print(f"Primera fila: {first_row}")
        
        return jsonify({
            "message": "Upload test successful",
            "rows": len(df),
            "columns": list(df.columns),
            "first_row": first_row
        })
        
    except Exception as e:
        print(f"ERROR en upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})

@app.route('/test', methods=['GET'])
def test():
    print("=== TEST ENDPOINT CALLED - VERSION 4 ===")
    return jsonify({'message': 'Test endpoint working - VERSION 4', 'version': '4.0', 'status': 'SUCCESS'})

@app.route('/test3', methods=['GET'])
def test3():
    return jsonify({'message': 'Test3 working'})

@app.route('/test2', methods=['GET'])
def test2():
    print("=== TEST2 ENDPOINT CALLED ===")
    return jsonify({'message': 'Test2 endpoint working'})

@app.route('/test-db', methods=['GET'])
def test_db():
    print("=== TEST DB ENDPOINT CALLED ===")
    try:
        conn, cursor = product_repository._get_connection()
        
        # Obtener productos
        cursor.execute("SELECT * FROM products.products")
        products = cursor.fetchall()
        
        # Obtener categorías
        cursor.execute("SELECT * FROM products.category")
        categories = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'message': 'DB test successful',
            'products': [dict(row) for row in products],
            'categories': [dict(row) for row in categories],
            'products_count': len(products),
            'categories_count': len(categories)
        })
    except Exception as e:
        print(f"ERROR en test-db: {str(e)}")
        return jsonify({'error': f'DB test failed: {str(e)}'}), 500

@app.route('/test-simple', methods=['GET'])
def test_simple():
    print("=== TEST SIMPLE ENDPOINT CALLED ===")
    return jsonify({'message': 'Simple test successful'})

@app.route('/debug', methods=['GET'])
def debug():
    print("=== DEBUG ENDPOINT CALLED ===")
    return jsonify({'status': 'debug working', 'timestamp': str(datetime.now())})

@app.route('/test-upload', methods=['POST'])
def test_upload():
    print("=== TEST UPLOAD ENDPOINT CALLED ===")
    files = request.files.getlist('files')
    print(f"Archivos recibidos: {len(files)}")
    
    try:
        for file in files:
            print(f"Procesando archivo: {file.filename}")
            if file.filename.lower().endswith('.csv'):
                df = pd.read_csv(file)
                print(f"CSV leído con {len(df)} filas")
                print(f"Columnas: {list(df.columns)}")
                print(f"Primera fila: {df.iloc[0].to_dict()}")
        
        return jsonify({"message": "Test upload successful", "files_processed": len(files)})
    except Exception as e:
        print(f"ERROR en test upload: {str(e)}")
        return jsonify({"error": f"Test upload failed: {str(e)}"}), 500

@app.route('/debug-upload', methods=['POST'])
def debug_upload():
    print("=== DEBUG UPLOAD ENDPOINT CALLED ===")
    try:
        files = request.files.getlist('files')
        print(f"Archivos recibidos: {len(files)}")
        
        if not files:
            return jsonify({"error": "No files received"}), 400
        
        file = files[0]
        print(f"Procesando archivo: {file.filename}")
        
        # Leer el archivo
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(file)
            print(f"CSV leído con {len(df)} filas")
            print(f"Columnas: {list(df.columns)}")
            
            # Verificar columnas requeridas
            required_columns = ['sku', 'name', 'value', 'category_name', 'quantity', 'warehouse_id']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                return jsonify({"error": f"Missing columns: {missing_columns}"}), 400
            
            # Mostrar primera fila
            first_row = df.iloc[0].to_dict()
            print(f"Primera fila: {first_row}")
            
            return jsonify({
                "message": "Debug upload successful",
                "rows": len(df),
                "columns": list(df.columns),
                "first_row": first_row
            })
        else:
            return jsonify({"error": "Only CSV files are supported"}), 400
            
    except Exception as e:
        print(f"ERROR en debug upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Debug upload failed: {str(e)}"}), 500

@app.route('/simple-upload', methods=['POST'])
def simple_upload():
    print("=== SIMPLE UPLOAD ENDPOINT CALLED ===")
    try:
        # Verificar conexión a BD
        print("Probando conexión a BD...")
        conn, cursor = product_repository._get_connection()
        print("Conexión a BD exitosa")
        
        # Probar query simple
        cursor.execute("SELECT COUNT(*) FROM products.Products")
        count = cursor.fetchone()['count']
        print(f"Productos en BD: {count}")
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "message": "Simple upload test successful",
            "db_connection": "OK",
            "products_count": count
        })
        
    except Exception as e:
        print(f"ERROR en simple upload: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Simple upload failed: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
