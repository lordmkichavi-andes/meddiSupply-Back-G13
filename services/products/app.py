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
import re
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

def validate_products_data(products_data):
    """
    Valida los productos antes de insertarlos en la base de datos.
    
    Args:
        products_data: Lista de diccionarios con productos a validar
        
    Returns:
        Tupla: (is_valid: bool, errors: list, warnings: list, validated_products: list)
        - is_valid: True si pasa todas las validaciones
        - errors: Lista de errores críticos que bloquean la inserción
        - warnings: Lista de advertencias que no bloquean la inserción
        - validated_products: Lista de productos validados (vacía si hay errores)
    """
    errors = []
    warnings = []
    validated_products = []
    required_fields = ['sku', 'name', 'value', 'category_name', 'quantity', 'warehouse_id']
    
    # Validar que sea una lista y no esté vacía
    if not isinstance(products_data, list):
        errors.append("Los datos deben ser un array de productos")
        return False, errors, warnings, validated_products
    
    if not products_data:
        errors.append("No se recibieron productos para procesar")
        return False, errors, warnings, validated_products
    
    # Validar cada producto
    for index, product in enumerate(products_data):
        row_num = index + 1
        
        # Verificar que sea un diccionario
        if not isinstance(product, dict):
            errors.append(f"Fila {row_num}: El producto debe ser un objeto JSON")
            continue
        
        product_errors = []
        product_warnings = []
        
        # Verificar campos obligatorios
        for field in required_fields:
            if field not in product or product[field] is None or str(product[field]).strip() == '':
                product_errors.append(f"Fila {row_num}: {field} es obligatorio")
        
        # Validaciones específicas de SKU
        if 'sku' in product and product['sku']:
            sku_str = str(product['sku']).strip()
            if len(sku_str) < 3:
                product_warnings.append(f"Fila {row_num}: SKU muy corto (mínimo 3 caracteres)")
        
        # Validaciones específicas de value
        if 'value' in product and product['value']:
            try:
                value = float(str(product['value']))
                if value <= 0:
                    product_errors.append(f"Fila {row_num}: El valor debe ser mayor a 0")
            except (ValueError, TypeError):
                product_errors.append(f"Fila {row_num}: El valor debe ser un número válido")
        
        # Validaciones específicas de quantity
        if 'quantity' in product and product['quantity']:
            try:
                quantity = int(str(product['quantity']))
                if quantity < 0:
                    product_errors.append(f"Fila {row_num}: La cantidad no puede ser negativa")
            except (ValueError, TypeError):
                product_errors.append(f"Fila {row_num}: La cantidad debe ser un número entero válido")
        
        # Validaciones específicas de warehouse_id
        if 'warehouse_id' in product and product['warehouse_id']:
            try:
                warehouse_id = int(str(product['warehouse_id']))
                if warehouse_id <= 0:
                    product_errors.append(f"Fila {row_num}: El warehouse_id debe ser mayor a 0")
            except (ValueError, TypeError):
                product_errors.append(f"Fila {row_num}: El warehouse_id debe ser un número entero válido")
        
        # Validaciones de ubicación física (opcionales - si están todos, deben ser válidos)
        location_fields = ['section', 'aisle', 'shelf', 'level']
        location_present = [field for field in location_fields if field in product and product[field] and str(product[field]).strip()]
        
        # Si algunos campos de ubicación están presentes, todos deben estar
        if len(location_present) > 0 and len(location_present) < len(location_fields):
            missing_fields = [field for field in location_fields if field not in location_present]
            product_errors.append(f"Fila {row_num}: Si se especifica ubicación física, todos los campos son requeridos (section, aisle, shelf, level). Faltan: {', '.join(missing_fields)}")
        
        # Si hay errores en este producto, agregarlos a la lista general
        if product_errors:
            errors.extend(product_errors)
        else:
            # Si no hay errores, agregar el producto a la lista de validados
            validated_products.append(product)
        
        # Agregar warnings
        if product_warnings:
            warnings.extend(product_warnings)
    
    # Validar SKUs duplicados en la base de datos
    if validated_products:
        try:
            conn, cursor = product_repository._get_connection()
            
            # Obtener todos los SKUs que ya existen
            skus_to_check = [p['sku'] for p in validated_products]
            placeholders = ','.join(['%s'] * len(skus_to_check))
            cursor.execute(f"SELECT product_id, sku, name FROM products.products WHERE sku IN ({placeholders})", skus_to_check)
            existing_products = cursor.fetchall()
            
            if existing_products:
                # Crear un diccionario de productos existentes por SKU
                existing_by_sku = {row['sku']: row for row in existing_products}
                
                # Validar cada producto validado contra los existentes
                filtered_validated = []
                for product in validated_products:
                    if product['sku'] in existing_by_sku:
                        existing = existing_by_sku[product['sku']]
                        row_num = next((i+1 for i, p in enumerate(products_data) if p.get('sku') == product['sku']), 'N/A')
                        errors.append(
                            f"Fila {row_num} (SKU: {product['sku']}, Nombre: {product.get('name', 'N/A')}): "
                            f"El SKU '{product['sku']}' ya existe en la base de datos "
                            f"(ID: {existing['product_id']}, Nombre: {existing['name']})"
                        )
                    else:
                        filtered_validated.append(product)
                
                validated_products = filtered_validated
            
            cursor.close()
            conn.close()
        except Exception as db_error:
            print(f"Error validando SKUs en la base de datos: {str(db_error)}")
            # Si hay error en la validación de DB, no bloquear pero registrar warning
            warnings.append("No se pudo validar SKUs duplicados en la base de datos. Se validará durante la inserción.")
    
    is_valid = len(errors) == 0 and len(validated_products) > 0
    return is_valid, errors, warnings, validated_products


def insert_products(products_data, conn, cursor, data_string, file_name='json_upload', file_type='csv'):
    """
    Inserta los productos validados en la base de datos.
    
    Args:
        products_data: Lista de productos validados a insertar
        conn: Conexión a la base de datos
        cursor: Cursor de la conexión
        data_string: String original de los datos (para file_size)
        file_name: Nombre del archivo (default: 'json_upload')
        file_type: Tipo de archivo - debe ser 'csv', 'xlsx' o 'xls' (default: 'csv')
        
    Returns:
        Tupla: (successful_records: int, failed_records: int, errors: list, upload_id: int, warnings: list)
        - successful_records: Número de productos insertados exitosamente
        - failed_records: Número de productos que fallaron
        - errors: Lista de errores de inserción
        - upload_id: ID del registro de upload creado
        - warnings: Lista de advertencias (vacía, pero se mantiene para compatibilidad)
    """
    successful_records = 0
    failed_records = 0
    processed_errors = []
    warnings = []
    
    # Validar file_type contra el constraint (solo permite 'csv', 'xlsx', 'xls')
    allowed_file_types = ['csv', 'xlsx', 'xls']
    if file_type.lower() not in allowed_file_types:
        file_type = 'csv'  # Default a 'csv' si no es válido
    
    # Truncar file_type a 10 caracteres (límite de la columna VARCHAR(10))
    file_type = file_type[:10]
    
    # 1. Crear registro en product_uploads
    upload_insert = """
        INSERT INTO products.product_uploads 
        (file_name, file_type, file_size, total_records, successful_records, failed_records, state, start_date, user_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), %s)
        RETURNING id
    """
    
    cursor.execute(upload_insert, (
        file_name,
        file_type,
        len(data_string),
        len(products_data),
        0,  # successful_records
        0,  # failed_records
        'procesando',
        1   # user_id (hardcoded por ahora)
    ))
    
    upload_id = cursor.fetchone()['id']
    print(f"Upload ID creado: {upload_id}")
    
    # 2. Procesar cada producto del JSON
    for index, product in enumerate(products_data):
        row_num = index + 1
        print(f"Procesando producto {row_num}: {product.get('sku', 'N/A')}")
        
        # Crear un savepoint antes de procesar cada producto
        savepoint_name = f"sp_product_{row_num}"
        try:
            cursor.execute(f"SAVEPOINT {savepoint_name}")
        except Exception as sp_error:
            # Si hay un error creando el savepoint, puede ser que la transacción ya esté abortada
            error_msg = f"Fila {row_num}: No se pudo crear savepoint - {str(sp_error)}"
            print(f"Error creando savepoint para producto {row_num}: {str(sp_error)}")
            processed_errors.append(error_msg)
            failed_records += 1
            
            # Intentar hacer rollback de la transacción completa
            try:
                conn.rollback()
                print("Rollback completo ejecutado debido a error en savepoint")
                # Reinsertar el upload_id después del rollback si es necesario
                cursor.execute(upload_insert, (
                    file_name,
                    file_type,
                    len(data_string),
                    len(products_data),
                    0,
                    0,
                    'procesando',
                    1
                ))
                upload_id = cursor.fetchone()['id']
                print(f"Upload ID recreado: {upload_id}")
            except Exception as rollback_err:
                print(f"Error en rollback/recreación de upload: {str(rollback_err)}")
                # Si no podemos recuperar, marcar todos los productos restantes como fallidos y salir
                for remaining_index in range(index, len(products_data)):
                    remaining_row = remaining_index + 1
                    processed_errors.append(f"Fila {remaining_row}: No procesado debido a error de transacción")
                    failed_records += 1
                break
            continue
        
        try:
            # Validar si el SKU ya existe antes de intentar insertar (validación adicional)
            cursor.execute("SELECT product_id, sku, name FROM products.products WHERE sku = %s", (product['sku'],))
            existing_product = cursor.fetchone()
            
            if existing_product:
                raise Exception(
                    f"SKU duplicado: El producto con SKU '{product['sku']}' ya existe en la base de datos "
                    f"(ID: {existing_product['product_id']}, Nombre: {existing_product['name']})"
                )
            
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
            
            # Obtener o crear location_id si se proporciona ubicación física
            location_id = None
            if all(field in product and product[field] and str(product[field]).strip() 
                   for field in ['section', 'aisle', 'shelf', 'level']):
                section = str(product['section']).strip()
                aisle = str(product['aisle']).strip()
                shelf = str(product['shelf']).strip()
                level = str(product['level']).strip()
                warehouse_id = int(product['warehouse_id'])
                
                # Buscar ubicación existente
                cursor.execute("""
                    SELECT location_id FROM products.warehouse_locations
                    WHERE warehouse_id = %s AND section = %s AND aisle = %s 
                    AND shelf = %s AND level = %s
                """, (warehouse_id, section, aisle, shelf, level))
                
                location_result = cursor.fetchone()
                
                if location_result:
                    location_id = location_result['location_id']
                    print(f"Ubicación encontrada: {section}-{aisle}-{shelf}-{level} (ID: {location_id})")
                else:
                    # Crear nueva ubicación
                    cursor.execute("""
                        INSERT INTO products.warehouse_locations 
                        (warehouse_id, section, aisle, shelf, level, active)
                        VALUES (%s, %s, %s, %s, %s, true)
                        RETURNING location_id
                    """, (warehouse_id, section, aisle, shelf, level))
                    location_id = cursor.fetchone()['location_id']
                    print(f"Nueva ubicación creada: {section}-{aisle}-{shelf}-{level} (ID: {location_id})")
            
            # Insertar stock
            if location_id:
                stock_insert = """
                    INSERT INTO products.productstock 
                    (product_id, quantity, lote, warehouse_id, provider_id, country, location_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(stock_insert, (
                    product_id,
                    int(product['quantity']),
                    f"LOTE-{product['sku']}-{datetime.now().strftime('%Y%m%d')}",  # lote generado
                    int(product['warehouse_id']),
                    1,  # provider_id
                    'COL',  # country (hardcoded)
                    location_id
                ))
            else:
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
            
            # Liberar el savepoint al completar exitosamente
            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            
            successful_records += 1
            print(f"Producto {row_num} procesado exitosamente")
            
        except Exception as row_error:
            # Extraer información más específica del error
            error_str = str(row_error)
            product_sku = product.get('sku', 'N/A')
            product_name = product.get('name', 'N/A')
            
            # Mejorar el mensaje de error para SKUs duplicados
            if 'duplicate key' in error_str.lower() and 'sku' in error_str.lower():
                # Extraer el SKU del mensaje de error si es posible
                sku_match = re.search(r"\(sku\)=\(([^)]+)\)", error_str)
                if sku_match:
                    duplicate_sku = sku_match.group(1)
                    error_msg = f"Fila {row_num} (SKU: {product_sku}, Nombre: {product_name}): El SKU '{duplicate_sku}' ya existe en la base de datos"
                else:
                    error_msg = f"Fila {row_num} (SKU: {product_sku}, Nombre: {product_name}): SKU duplicado - el producto ya existe en la base de datos"
            # Detectar errores de FOREIGN KEY para warehouse_id inexistente
            elif 'foreign key' in error_str.lower() and 'warehouse' in error_str.lower():
                warehouse_id = product.get('warehouse_id', 'N/A')
                error_msg = f"Fila {row_num} (SKU: {product_sku}, Nombre: {product_name}): El warehouse_id '{warehouse_id}' no existe en la base de datos"
            else:
                # Para otros errores, incluir información del producto
                error_msg = f"Fila {row_num} (SKU: {product_sku}, Nombre: {product_name}): {error_str}"
            
            print(f"Error en producto {row_num} (SKU: {product_sku}): {error_str}")
            processed_errors.append(error_msg)
            
            # Hacer rollback al savepoint para restaurar el estado antes del procesamiento de este producto
            try:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                print(f"Rollback a savepoint {savepoint_name} ejecutado")
            except Exception as rollback_error:
                print(f"Error en rollback a savepoint: {str(rollback_error)}")
            
            # Ahora intentar insertar el registro de error en product_upload_details
            try:
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
                print(f"Registro de error insertado para producto {row_num}")
            except Exception as details_error:
                # Si aún falla, hacer rollback completo y reinsertar upload
                print(f"Error insertando detalles de error: {str(details_error)}")
                try:
                    conn.rollback()
                    cursor.execute(upload_insert, (
                        file_name,
                        file_type,
                        len(data_string),
                        len(products_data),
                        0,
                        0,
                        'procesando',
                        1
                    ))
                    upload_id = cursor.fetchone()['id']
                except:
                    pass
            
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
    
    print(f"Transacción completada. Exitosos: {successful_records}, Fallidos: {failed_records}")
    
    return successful_records, failed_records, processed_errors, upload_id, warnings


@app.route('/products/upload3/validate', methods=['POST'])
def validate_products_endpoint():
    """
    Endpoint para validar productos sin insertarlos en la base de datos.
    Solo realiza la validación y retorna el resultado.
    """
    print("=== INICIO VALIDACIÓN DE PRODUCTOS ===")
    
    try:
        # 1. Obtener y parsear datos del request
        data_string = request.get_data(as_text=True)

        if not data_string or data_string.strip() == '':
            return jsonify({
                "success": False,
                "message": "No se recibieron datos para procesar",
                "total_records": 0,
                "valid_records": 0,
                "invalid_records": 0,
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
                "valid_records": 0,
                "invalid_records": 0,
                "errors": [f"Error de sintaxis JSON: {str(e)}"],
                "warnings": []
            }), 400

        print(f"Productos parseados: {len(products_data)}")

        # 2. Validar productos
        is_valid, errors, warnings, validated_products = validate_products_data(products_data)

        # Preparar respuesta
        valid_records = len(validated_products)
        invalid_records = len(products_data) - valid_records
        
        response_data = {
            "success": is_valid,
            "message": f"Validación completada: {valid_records} productos válidos de {len(products_data)} totales" if is_valid else f"Validación fallida: {invalid_records} productos con errores",
            "total_records": len(products_data),
            "valid_records": valid_records,
            "invalid_records": invalid_records,
            "errors": errors,
            "warnings": warnings,
            "validated_products": validated_products if is_valid else []  # Incluir productos validados si todo está bien
        }
        
        # Retornar 200 con resultado de validación (éxito o fallo en los datos)
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"ERROR en validación: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "message": "Error interno del servidor durante la validación",
            "total_records": len(products_data) if 'products_data' in locals() else 0,
            "valid_records": 0,
            "invalid_records": len(products_data) if 'products_data' in locals() else 0,
            "errors": [f"Error interno: {str(e)}"],
            "warnings": []
        }), 500


@app.route('/products/upload3/insert', methods=['POST'])
def insert_products_endpoint():
    """
    Endpoint para insertar productos validados en la base de datos.
    Asume que los productos ya fueron validados previamente.
    """
    print("=== INICIO INSERCIÓN DE PRODUCTOS ===")
    conn = None
    cursor = None
    
    try:
        # 1. Obtener y parsear datos del request
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

        print(f"Productos parseados para inserción: {len(products_data)}")

        # 2. Validación rápida básica (estructura mínima)
        if not isinstance(products_data, list) or not products_data:
            return jsonify({
                "success": False,
                "message": "Los datos deben ser un array de productos no vacío",
                "total_records": 0,
                "successful_records": 0,
                "failed_records": 0,
                "errors": ["Los datos deben ser un array de productos no vacío"],
                "warnings": []
            }), 400
        
        # 3. Determinar file_name y file_type desde headers o usar defaults
        # Si viene del frontend con headers, usarlos; si no, usar defaults
        file_name = request.headers.get('X-File-Name')
        file_type = request.headers.get('X-File-Type', 'csv')
        
        # Validar que file_type sea uno de los valores permitidos por el constraint
        # Constraint permite: 'csv', 'xlsx', 'xls'
        allowed_file_types = ['csv', 'xlsx', 'xls']
        if file_type.lower() not in allowed_file_types:
            file_type = 'csv'  # Default a 'csv' si no es válido
        else:
            file_type = file_type.lower()
        
        # Si no hay file_name, usar uno basado en timestamp
        if not file_name:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_name = f'json_upload_{timestamp}'
        
        # 4. Conectar a la base de datos e insertar
        conn, cursor = product_repository._get_connection()
        print("Conexión a BD establecida")
        
        # Insertar productos
        successful_records, failed_records, processed_errors, upload_id, insert_warnings = insert_products(
            products_data, conn, cursor, data_string, file_name=file_name, file_type=file_type
        )
        
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
            "warnings": insert_warnings
        })
        
    except Exception as e:
        print(f"ERROR en inserción: {str(e)}")
        import traceback
        traceback.print_exc()
        
        if conn:
            conn.rollback()
            print("Rollback ejecutado")
        
        return jsonify({
            "success": False,
            "message": "Error interno del servidor durante la inserción",
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


@app.route('/products/insert', methods=['POST'])
def insert_single_product_endpoint():
    """
    Endpoint para insertar un solo producto con validación.
    Reutiliza validate_products_data e insert_products.
    Soporta ubicación física (section, aisle, shelf, level) opcional.
    """
    print("=== INICIO INSERCIÓN DE PRODUCTO INDIVIDUAL ===")
    conn = None
    cursor = None
    
    try:
        # 1. Obtener datos del producto
        product_data = request.get_json()
        
        if not product_data:
            return jsonify({
                "success": False,
                "message": "No se recibieron datos del producto",
                "errors": ["Datos del producto requeridos"]
            }), 400
        
        # Convertir a lista para reutilizar las funciones existentes
        products_list = [product_data]
        data_string = json.dumps(products_list)
        
        # 2. Validar producto
        is_valid, errors, warnings, validated_products = validate_products_data(products_list)
        
        if not is_valid:
            return jsonify({
                "success": False,
                "message": "Error de validación",
                "errors": errors,
                "warnings": warnings
            }), 400
        
        # 3. Insertar producto
        conn, cursor = product_repository._get_connection()
        
        successful, failed, insert_errors, upload_id, insert_warnings = insert_products(
            validated_products,
            conn,
            cursor,
            data_string,
            file_name='single_product_insert',
            file_type='json'
        )
        
        conn.commit()
        
        if successful > 0:
            # Obtener el product_id del producto insertado
            cursor.execute("SELECT product_id FROM products.products WHERE sku = %s", (product_data['sku'],))
            result = cursor.fetchone()
            product_id = result['product_id'] if result else None
            
            # Obtener información de ubicación si se proporcionó
            location_info = None
            if all(field in product_data and product_data[field] and str(product_data[field]).strip() 
                   for field in ['section', 'aisle', 'shelf', 'level']):
                cursor.execute("""
                    SELECT location_id, section, aisle, shelf, level 
                    FROM products.warehouse_locations
                    WHERE warehouse_id = %s AND section = %s AND aisle = %s 
                    AND shelf = %s AND level = %s
                """, (
                    int(product_data['warehouse_id']),
                    str(product_data['section']).strip(),
                    str(product_data['aisle']).strip(),
                    str(product_data['shelf']).strip(),
                    str(product_data['level']).strip()
                ))
                location = cursor.fetchone()
                if location:
                    location_info = {
                        "location_id": location['location_id'],
                        "section": location['section'],
                        "aisle": location['aisle'],
                        "shelf": location['shelf'],
                        "level": location['level']
                    }
            
            cursor.close()
            conn.close()
            
            response = {
                "success": True,
                "message": "Producto insertado exitosamente",
                "product_id": product_id,
                "warnings": warnings + insert_warnings
            }
            
            if location_info:
                response["location"] = location_info
            
            return jsonify(response), 201
        else:
            cursor.close()
            conn.close()
            
            return jsonify({
                "success": False,
                "message": "Error al insertar producto",
                "errors": insert_errors,
                "warnings": warnings + insert_warnings
            }), 400
            
    except Exception as e:
        if conn:
            conn.rollback()
            if cursor:
                cursor.close()
            conn.close()
        
        print(f"ERROR en inserción individual: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "message": "Error interno del servidor",
            "errors": [f"Error interno: {str(e)}"]
        }), 500


## Endpoint /products/upload3 eliminado


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

## Endpoint /test-db eliminado

## Endpoint /debug-upload eliminado

@app.route('/products/cities', methods=['GET'])
def get_all_cities():
    """Obtener todas las ciudades"""
    try:
        conn, cursor = product_repository._get_connection()

        cursor.execute("""
            SELECT city_id, name, country, active, created_at
            FROM products.cities 
            WHERE active = true
            ORDER BY name
        """)

        cities = cursor.fetchall()

        return jsonify({
            "success": True,
            "cities": cities
        })

    except Exception as e:
        print(f"Error getting cities: {str(e)}")
        return jsonify({"error": f"Error getting cities: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/products/warehouses', methods=['GET'])
def get_all_warehouses():
    """Obtener todas las bodegas con información de ciudad"""
    try:
        conn, cursor = product_repository._get_connection()

        cursor.execute("""
            SELECT 
                w.warehouse_id,
                w.name,
                w.location,
                w.phone,
                w.manager_name,
                w.active,
                w.created_at,
                c.name as city_name,
                c.country
            FROM products.warehouses w
            LEFT JOIN products.cities c ON w.city_id = c.city_id
            WHERE w.active = true
            ORDER BY c.name, w.name
        """)

        warehouses = cursor.fetchall()

        return jsonify({
            "success": True,
            "warehouses": warehouses
        })

    except Exception as e:
        print(f"Error getting warehouses: {str(e)}")
        return jsonify({"error": f"Error getting warehouses: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/products/warehouses/by-city/<int:city_id>', methods=['GET'])
def get_warehouses_by_city(city_id):
    """Obtener bodegas por ciudad"""
    try:
        conn, cursor = product_repository._get_connection()

        cursor.execute("""
            SELECT 
                w.warehouse_id,
                w.name,
                w.location,
                w.phone,
                w.manager_name,
                w.active,
                c.name as city_name,
                c.country
            FROM products.warehouses w
            LEFT JOIN products.cities c ON w.city_id = c.city_id
            WHERE w.city_id = %s AND w.active = true
            ORDER BY w.name
        """, (city_id,))

        warehouses = cursor.fetchall()

        return jsonify({
            "success": True,
            "city_id": city_id,
            "warehouses": warehouses
        })

    except Exception as e:
        print(f"Error getting warehouses by city: {str(e)}")
        return jsonify({"error": f"Error getting warehouses by city: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/products/by-city/<int:city_id>', methods=['GET'])
def get_products_by_city_id(city_id):
    """Obtener productos disponibles por ciudad (con stock)"""
    try:
        conn, cursor = product_repository._get_connection()

        cursor.execute("""
            SELECT 
                p.product_id,
                p.sku,
                p.name,
                p.value,
                p.status,
                c.name as category_name,
                ci.name as city_name,
                ci.city_id,
                ci.country,
                w.name as warehouse_name,
                w.warehouse_id,
                ps.quantity,
                ps.lote,
                ps.expiry_date,
                ps.reserved_quantity,
                wl.section,
                wl.aisle,
                wl.shelf,
                wl."level"
            FROM products.products p
            JOIN products.productstock ps ON p.product_id = ps.product_id
            JOIN products.warehouses w ON ps.warehouse_id = w.warehouse_id
            JOIN products.cities ci ON w.city_id = ci.city_id
            JOIN products.category c ON p.category_id = c.category_id
            LEFT JOIN products.warehouse_locations wl ON ps.location_id = wl.location_id
            WHERE ci.city_id = %s AND p.status = 'activo' AND ps.quantity > 0
            ORDER BY ps.quantity DESC
        """, (city_id,))

        products = cursor.fetchall()

        return jsonify({
            "success": True,
            "city_id": city_id,
            "products": products
        })

    except Exception as e:
        print(f"Error getting products by city: {str(e)}")
        return jsonify({"error": f"Error getting products by city: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/products/by-warehouse/<int:warehouse_id>', methods=['GET'])
@cache_control_header(timeout=120, key="")
def get_products_by_warehouse_id(warehouse_id):
    """Obtener productos disponibles por bodega (con stock o sin stock según parámetro)"""
    try:
        conn, cursor = product_repository._get_connection()

        # Verificar si se quiere incluir productos con stock = 0
        include_zero = request.args.get('include_zero', 'false').lower() == 'true'
        include_locations = request.args.get('include_locations', 'false').lower() == 'true'

        # Construir la query según si se incluyen productos con stock = 0
        if include_zero:
            quantity_filter = ""
        else:
            quantity_filter = "AND ps.quantity > 0"

        # OPTIMIZACIÓN: Si include_locations=true, traer todo en una sola query para evitar N+1
        if include_locations:
            # Query única optimizada que trae todo en un solo query
            query = f"""
                SELECT 
                    p.product_id,
                    p.sku,
                    p.name,
                    p.value,
                    p.status,
                    c.name as category_name,
                    w.name as warehouse_name,
                    ci.name as city_name,
                    ci.city_id,
                    ci.country,
                    ps.quantity,
                    ps.lote,
                    ps.country as stock_country,
                    ps.expiry_date,
                    ps.reserved_quantity,
                    wl.section,
                    wl.aisle,
                    wl.shelf,
                    wl."level"
                FROM products.products p
                JOIN products.productstock ps ON p.product_id = ps.product_id
                JOIN products.warehouses w ON ps.warehouse_id = w.warehouse_id
                JOIN products.cities ci ON w.city_id = ci.city_id
                JOIN products.category c ON p.category_id = c.category_id
                LEFT JOIN products.warehouse_locations wl ON ps.location_id = wl.location_id
                WHERE ps.warehouse_id = %s AND p.status = 'activo' {quantity_filter}
                ORDER BY p.product_id, ps.quantity DESC
            """

            cursor.execute(query, (warehouse_id,))
            all_rows = cursor.fetchall()

            # Agrupar por producto y construir locations
            products_dict = {}
            for row in all_rows:
                product_id = row['product_id']
                
                if product_id not in products_dict:
                    products_dict[product_id] = {
                        'product_id': row['product_id'],
                        'sku': row['sku'],
                        'name': row['name'],
                        'value': row['value'],
                        'status': row['status'],
                        'category_name': row['category_name'],
                        'warehouse_name': row['warehouse_name'],
                        'city_name': row['city_name'],
                        'city_id': row['city_id'],
                        'country': row['country'],
                        'stock_country': row['stock_country'],
                        'total_quantity': 0,
                        'locations': []
                    }
                
                # Sumar la cantidad
                products_dict[product_id]['total_quantity'] += row['quantity']
                
                # Agregar location si tiene datos
                location_data = {
                    'warehouse_id': warehouse_id,
                    'warehouse_name': row['warehouse_name'],
                    'city_id': row['city_id'],
                    'city_name': row['city_name'],
                    'country': row['country'],
                    'quantity': row['quantity'],
                    'lote': row['lote'],
                    'expiry_date': str(row['expiry_date']) if row['expiry_date'] else None,
                    'reserved_quantity': row['reserved_quantity'],
                    'section': row['section'],
                    'aisle': row['aisle'],
                    'shelf': row['shelf'],
                    'level': row['level']
                }
                products_dict[product_id]['locations'].append(location_data)

            # Convertir a lista y agregar total_quantity como quantity
            products_list = []
            for product_id, product_info in products_dict.items():
                product_info['quantity'] = product_info['total_quantity']
                products_list.append(product_info)

            return jsonify({
                "success": True,
                "warehouse_id": warehouse_id,
                "products": products_list
            })
        else:
            # Sin locations: query más simple
            query = f"""
                SELECT 
                    p.product_id,
                    p.sku,
                    p.name,
                    p.value,
                    p.status,
                    c.name as category_name,
                    w.name as warehouse_name,
                    ci.name as city_name,
                    ci.city_id,
                    ci.country,
                    ps.quantity,
                    ps.lote,
                    ps.country as stock_country,
                    ps.expiry_date,
                    ps.reserved_quantity
                FROM products.products p
                JOIN products.productstock ps ON p.product_id = ps.product_id
                JOIN products.warehouses w ON ps.warehouse_id = w.warehouse_id
                JOIN products.cities ci ON w.city_id = ci.city_id
                JOIN products.category c ON p.category_id = c.category_id
                WHERE ps.warehouse_id = %s AND p.status = 'activo' {quantity_filter}
                ORDER BY ps.quantity DESC
            """

            cursor.execute(query, (warehouse_id,))
            products = cursor.fetchall()

            # Agrupar por producto y sumar cantidades
            products_dict = {}
            for product in products:
                product_id = product['product_id']
                if product_id not in products_dict:
                    products_dict[product_id] = dict(product)
                    products_dict[product_id]['quantity'] = 0
                products_dict[product_id]['quantity'] += product['quantity']

            return jsonify({
                "success": True,
                "warehouse_id": warehouse_id,
                "products": list(products_dict.values())
            })

    except Exception as e:
        print(f"Error getting products by warehouse: {str(e)}")
        return jsonify({"error": f"Error getting products by warehouse: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/products/stock-summary', methods=['GET'])
def get_stock_summary():
    """Obtener resumen de stock por ciudad y bodega"""
    try:
        conn, cursor = product_repository._get_connection()

        # Resumen por ciudad
        cursor.execute("""
            SELECT 
                ci.city_id,
                ci.name as city_name,
                ci.country,
                COUNT(DISTINCT w.warehouse_id) as total_warehouses,
                COUNT(DISTINCT ps.product_id) as total_products,
                SUM(ps.quantity) as total_stock
            FROM products.cities ci
            LEFT JOIN products.warehouses w ON ci.city_id = w.city_id AND w.active = true
            LEFT JOIN products.productstock ps ON w.warehouse_id = ps.warehouse_id
            WHERE ci.active = true
            GROUP BY ci.city_id, ci.name, ci.country
            ORDER BY total_stock DESC
        """)

        cities_summary = cursor.fetchall()

        # Resumen por bodega
        cursor.execute("""
            SELECT 
                w.warehouse_id,
                w.name as warehouse_name,
                ci.name as city_name,
                COUNT(DISTINCT ps.product_id) as total_products,
                SUM(ps.quantity) as total_stock
            FROM products.warehouses w
            LEFT JOIN products.cities ci ON w.city_id = ci.city_id
            LEFT JOIN products.productstock ps ON w.warehouse_id = ps.warehouse_id
            WHERE w.active = true
            GROUP BY w.warehouse_id, w.name, ci.name
            ORDER BY total_stock DESC
        """)

        warehouses_summary = cursor.fetchall()

        return jsonify({
            "success": True,
            "cities_summary": cities_summary,
            "warehouses_summary": warehouses_summary
        })

    except Exception as e:
        print(f"Error getting stock summary: {str(e)}")
        return jsonify({"error": f"Error getting stock summary: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/products/without-stock', methods=['GET'])
def get_products_without_stock():
    """Obtener productos sin stock"""
    try:
        conn, cursor = product_repository._get_connection()

        cursor.execute("""
            SELECT 
                p.product_id,
                p.sku,
                p.name,
                p.value,
                p.status,
                c.name as category_name
            FROM products.products p
            JOIN products.category c ON p.category_id = c.category_id
            LEFT JOIN products.productstock ps ON p.product_id = ps.product_id
            WHERE ps.product_id IS NULL AND p.status = 'activo'
            ORDER BY p.name
        """)

        products = cursor.fetchall()

        return jsonify({
            "success": True,
            "products_without_stock": products
        })

    except Exception as e:
        print(f"Error getting products without stock: {str(e)}")
        return jsonify({"error": f"Error getting products without stock: {str(e)}"}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
