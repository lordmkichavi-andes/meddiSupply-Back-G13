import pytest
import json
from unittest.mock import MagicMock, patch, Mock
from flask import Flask

# Importar la app con manejo de errores de sintaxis
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mockear setup_database antes de importar app para evitar conexión a BD durante import
import sys
from unittest.mock import patch, MagicMock

# Mockear setup_database antes de importar app
with patch('database_setup.setup_database'):
    with patch('database_setup.init_db_pool'):
        from app import app


@pytest.fixture
def client():
    """Fixture para crear un cliente de pruebas Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_db_connection():
    """Fixture que simula una conexión a la base de datos."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit = MagicMock()
    mock_conn.rollback = MagicMock()
    mock_conn.close = MagicMock()
    mock_cursor.close = MagicMock()
    mock_cursor.fetchone = MagicMock()
    mock_cursor.fetchall = MagicMock()
    return mock_conn, mock_cursor


class TestUploadProductsString:
    """Tests para el endpoint /products/upload3 (upload_products_string)"""

    def test_upload3_empty_request(self, client):
        """Test: Debe retornar error cuando no se reciben datos."""
        response = client.post('/products/upload3', 
                              data='',
                              content_type='text/plain')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['total_records'] == 0
        assert 'No se recibieron datos' in data['message']

    def test_upload3_invalid_json(self, client):
        """Test: Debe retornar error cuando el JSON es inválido."""
        response = client.post('/products/upload3',
                              data='{invalid json}',
                              content_type='text/plain')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Error al parsear JSON' in data['message']

    def test_upload3_not_array(self, client):
        """Test: Debe retornar error cuando los datos no son un array."""
        response = client.post('/products/upload3',
                              data='{"sku": "TEST-001"}',
                              content_type='text/plain')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'deben ser un array' in data['message']

    def test_upload3_empty_array(self, client):
        """Test: Debe retornar error cuando el array está vacío."""
        response = client.post('/products/upload3',
                              data='[]',
                              content_type='text/plain')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'No se recibieron productos' in data['message']

    def test_upload3_missing_required_fields(self, client):
        """Test: Debe retornar error cuando faltan campos obligatorios."""
        product_data = [
            {
                "sku": "TEST-001",
                "name": "Producto Test"
                # Faltan: value, category_name, quantity, warehouse_id
            }
        ]
        response = client.post('/products/upload3',
                              data=json.dumps(product_data),
                              content_type='text/plain')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert len(data['errors']) > 0
        assert any('value' in error.lower() for error in data['errors'])

    def test_upload3_invalid_value(self, client):
        """Test: Debe retornar error cuando el valor es inválido."""
        product_data = [
            {
                "sku": "TEST-001",
                "name": "Producto Test",
                "value": -100,  # Valor negativo
                "category_name": "MEDICATION",
                "quantity": "10",
                "warehouse_id": "1"
            }
        ]
        response = client.post('/products/upload3',
                              data=json.dumps(product_data),
                              content_type='text/plain')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert any('valor debe ser mayor a 0' in error.lower() for error in data['errors'])

    def test_upload3_invalid_quantity(self, client):
        """Test: Debe retornar error cuando la cantidad es negativa."""
        product_data = [
            {
                "sku": "TEST-001",
                "name": "Producto Test",
                "value": "100",
                "category_name": "MEDICATION",
                "quantity": "-10",  # Cantidad negativa
                "warehouse_id": "1"
            }
        ]
        response = client.post('/products/upload3',
                              data=json.dumps(product_data),
                              content_type='text/plain')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert any('cantidad no puede ser negativa' in error.lower() for error in data['errors'])

    @patch('app.product_repository._get_connection')
    def test_upload3_success_single_product(self, mock_get_conn, client, mock_db_connection):
        """Test: Debe insertar un producto exitosamente."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = (mock_conn, mock_cursor)

        # Orden correcto de fetchone() según el flujo en app.py:
        mock_cursor.fetchone.side_effect = [
            {'id': 1},        # 1. upload_id (línea 267)
            None,             # 2. category no existe (línea 282)
            [6],              # 3. MAX(category_id) + 1 (línea 289) - retorna lista/tupla
            {'category_id': 6},  # 4. categoria creada (línea 296)
            {'product_id': 100}  # 5. producto creado (línea 318)
        ]

        product_data = [
            {
                "sku": "TEST-001",
                "name": "Producto Test",
                "value": "100",
                "category_name": "MEDICATION",
                "quantity": "10",
                "warehouse_id": "1"
            }
        ]

        response = client.post('/products/upload3',
                              data=json.dumps(product_data),
                              content_type='text/plain')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['total_records'] == 1
        assert data['successful_records'] == 1
        assert data['failed_records'] == 0
        assert 'upload_id' in data

    @patch('app.product_repository._get_connection')
    def test_upload3_duplicate_sku(self, mock_get_conn, client, mock_db_connection):
        """Test: Debe manejar SKU duplicado correctamente."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = (mock_conn, mock_cursor)

        # Crear un mock del error UniqueViolation con pgcode configurado
        # Usamos una clase mock personalizada para simular psycopg2.errors.UniqueViolation
        class MockUniqueViolation(Exception):
            pgcode = '23505'
            def __init__(self):
                super().__init__("duplicate key value violates unique constraint")
        
        duplicate_error = MockUniqueViolation()
        
        # Mock: orden correcto de fetchone()
        mock_cursor.fetchone.side_effect = [
            {'id': 1},        # upload_id (línea 267)
            {'category_id': 1},  # categoria existe (línea 282)
        ]
        
        # Configurar execute para que falle en el INSERT del producto
        call_count = {'count': 0}
        def execute_side_effect(*args, **kwargs):
            call_count['count'] += 1
            if call_count['count'] == 3:  # El tercer execute es el INSERT del producto
                raise duplicate_error
        mock_cursor.execute.side_effect = execute_side_effect

        product_data = [
            {
                "sku": "DUPLICATE-001",
                "name": "Producto Duplicado",
                "value": "100",
                "category_name": "MEDICATION",
                "quantity": "10",
                "warehouse_id": "1"
            }
        ]

        response = client.post('/products/upload3',
                              data=json.dumps(product_data),
                              content_type='text/plain')
        
        # Debe procesar pero con error en el producto
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['failed_records'] == 1
        assert len(data['errors']) > 0


class TestGetWarehouses:
    """Tests para el endpoint /products/location/warehouses"""

    @patch('app.product_repository._get_connection')
    def test_get_warehouses_success(self, mock_get_conn, client, mock_db_connection):
        """Test: Debe retornar lista de almacenes."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = (mock_conn, mock_cursor)

        mock_cursor.fetchall.return_value = [
            {'warehouse_id': 1, 'name': 1, 'description': 'Almacén 1'},
            {'warehouse_id': 2, 'name': 2, 'description': 'Almacén 2'}
        ]

        response = client.get('/products/location/warehouses')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'warehouses' in data
        assert data['total'] == 2

    @patch('app.product_repository._get_connection')
    def test_get_warehouses_with_city_id(self, mock_get_conn, client, mock_db_connection):
        """Test: Debe filtrar almacenes por city_id."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = (mock_conn, mock_cursor)

        mock_cursor.fetchall.return_value = [
            {'warehouse_id': 1, 'name': 1, 'description': 'Almacén 1', 'city_name': 'Ciudad 1', 'country': 'COL'}
        ]

        response = client.get('/products/location/warehouses?city_id=1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['city_id'] == 1
        assert len(data['warehouses']) == 1

    @patch('app.product_repository._get_connection')
    def test_get_warehouses_no_data(self, mock_get_conn, client, mock_db_connection):
        """Test: Debe retornar datos de ejemplo cuando no hay almacenes."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = (mock_conn, mock_cursor)

        mock_cursor.fetchall.return_value = []

        response = client.get('/products/location/warehouses')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'warehouses' in data
        assert len(data['warehouses']) > 0  # Debe tener datos de ejemplo


class TestGetCities:
    """Tests para el endpoint /products/location/cities"""

    @patch('app.product_repository._get_connection')
    def test_get_cities_success(self, mock_get_conn, client, mock_db_connection):
        """Test: Debe retornar lista de ciudades."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = (mock_conn, mock_cursor)

        mock_cursor.fetchall.return_value = [
            {'country': 'COL', 'country_name': 'Colombia'}
        ]

        response = client.get('/products/location/cities')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'cities' in data
        assert data['total'] > 0
        # Debe crear ciudades basadas en países
        assert any(city['country'] == 'COL' for city in data['cities'])

    @patch('app.product_repository._get_connection')
    def test_get_cities_no_data(self, mock_get_conn, client, mock_db_connection):
        """Test: Debe retornar ciudades de ejemplo cuando no hay datos."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = (mock_conn, mock_cursor)

        mock_cursor.fetchall.return_value = []

        response = client.get('/products/location/cities')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'cities' in data
        assert len(data['cities']) > 0


class TestGetLocationInfo:
    """Tests para el endpoint /products/location"""

    @patch('app.get_warehouses')
    @patch('app.get_cities')
    @patch('app.product_service.list_available_products')
    def test_get_location_info_success(self, mock_products, mock_cities, mock_warehouses, client):
        """Test: Debe retornar información completa de ubicaciones."""
        # Mock responses - get_warehouses y get_cities retornan tuplas (response, status_code)
        mock_warehouse_response = Mock()
        mock_warehouse_response.get_json.return_value = {'warehouses': [{'warehouse_id': 1, 'name': 'Bodega 1'}]}
        mock_warehouses.return_value = (mock_warehouse_response, 200)
        
        mock_city_response = Mock()
        mock_city_response.get_json.return_value = {'cities': [{'city_id': 1, 'name': 'Bogotá', 'country': 'Colombia'}]}
        mock_cities.return_value = (mock_city_response, 200)
        
        # list_available_products retorna una lista de objetos Product
        # Necesitamos objetos que puedan ser serializados por Flask
        # Usamos un objeto simple con atributos serializables
        from domain.models import Product
        test_product = Product(
            product_id=1,
            sku='TEST-001',
            value=100.0,
            name='Producto Test',
            image_url=None,
            category_name='MEDICATION',
            total_quantity=10
        )
        mock_products.return_value = [test_product]

        response = client.get('/products/location')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'warehouses' in data
        assert 'cities' in data
        assert 'products' in data
        assert 'summary' in data


class TestGetProductsByWarehouse:
    """Tests para el endpoint /products/warehouse/<warehouse_id>"""

    @patch('app.product_repository._get_connection')
    def test_get_products_by_warehouse_success(self, mock_get_conn, client, mock_db_connection):
        """Test: Debe retornar productos de una bodega específica."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = (mock_conn, mock_cursor)

        mock_cursor.fetchall.return_value = [
            {
                'product_id': 1,
                'sku': 'TEST-001',
                'name': 'Producto Test',
                'value': 100.0,
                'quantity': 50,
                'category_name': 'MEDICATION',
                'warehouse_id': 1,
                'lote': 'LOTE-001',
                'country': 'COL'
            }
        ]

        response = client.get('/products/warehouse/1')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['warehouse_id'] == 1
        assert 'products' in data
        assert len(data['products']) == 1
        assert data['total_products'] == 1
        assert data['total_quantity'] == 50

    @patch('app.product_repository._get_connection')
    def test_get_products_by_warehouse_not_found(self, mock_get_conn, client, mock_db_connection):
        """Test: Debe retornar lista vacía cuando no hay productos."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = (mock_conn, mock_cursor)

        mock_cursor.fetchall.return_value = []

        response = client.get('/products/warehouse/999')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['warehouse_id'] == 999
        assert data['total_products'] == 0
        assert data['total_quantity'] == 0
        assert 'No se encontraron productos' in data['message']

    @patch('app.product_repository._get_connection')
    def test_get_products_by_warehouse_db_error(self, mock_get_conn, client, mock_db_connection):
        """Test: Debe manejar errores de base de datos."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = (mock_conn, mock_cursor)

        # Simular error en la consulta
        mock_cursor.execute.side_effect = Exception("Database error")

        response = client.get('/products/warehouse/1')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data


class TestProductsAvailable:
    """Tests para el endpoint /products/available"""

    @patch('app.cache')
    @patch('app.product_service.list_available_products')
    def test_get_products_available_success(self, mock_list_products, mock_cache, client):
        """Test: Debe retornar lista de productos disponibles."""
        from domain.models import Product
        test_products = [
            Product(
                product_id=1,
                sku='TEST-001',
                value=100.0,
                name='Producto Test 1',
                image_url=None,
                category_name='MEDICATION',
                total_quantity=10
            )
        ]
        mock_list_products.return_value = test_products
        mock_cache.get.return_value = None  # Cache MISS

        response = client.get('/products/available')
        
        assert response.status_code == 200
        assert response.headers.get('X-Cache') == 'MISS'
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]['sku'] == 'TEST-001'

    @patch('app.cache')
    @patch('app.product_service.list_available_products')
    def test_get_products_available_cache_hit(self, mock_list_products, mock_cache, client):
        """Test: Debe retornar desde caché cuando existe (HIT)."""
        cached_data = b'[{"product_id": 1, "sku": "TEST-001"}]'
        mock_cache.get.return_value = cached_data

        response = client.get('/products/available')
        
        assert response.status_code == 200
        assert response.headers.get('X-Cache') == 'HIT'
        # No se debe llamar a list_available_products cuando hay cache hit
        mock_list_products.assert_not_called()


class TestUpdateProduct:
    """Tests para el endpoint /products/update/<product_id>"""

    @patch('app.product_service.update_product')
    @patch('app.cache')
    def test_update_product_success(self, mock_cache, mock_update, client):
        """Test: Debe actualizar un producto y limpiar caché."""
        product_data = {
            'price': 150.0,
            'stock': 20,
            'warehouse': 1
        }

        response = client.put('/products/update/1',
                            data=json.dumps(product_data),
                            content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'Product updated and cache invalidated'
        mock_update.assert_called_once_with(1, price=150.0, stock=20, warehouse=1)
        assert mock_cache.delete.call_count == 3  # Se invalida caché 3 veces

    def test_update_product_missing_price(self, client):
        """Test: Debe retornar error cuando falta price."""
        product_data = {
            'stock': 20
            # Falta price
        }

        response = client.put('/products/update/1',
                            data=json.dumps(product_data),
                            content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
        assert 'required' in data['error'].lower()

    def test_update_product_missing_stock(self, client):
        """Test: Debe retornar error cuando falta stock."""
        product_data = {
            'price': 150.0
            # Falta stock
        }

        response = client.put('/products/update/1',
                            data=json.dumps(product_data),
                            content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data


class TestGetProductById:
    """Tests para el endpoint /products/<product_id>"""

    @patch('app.cache')
    @patch('app.product_service')
    def test_get_product_by_id_success(self, mock_service, mock_cache, client):
        """Test: Debe retornar un producto cuando existe."""
        from domain.models import Product
        test_product = Product(
            product_id=1,
            sku='TEST-001',
            value=100.0,
            name='Producto Test',
            image_url=None,
            category_name='MEDICATION',
            total_quantity=10
        )
        mock_service.get_product_by_id.return_value = test_product
        mock_cache.get.return_value = None  # Cache MISS

        response = client.get('/products/1')
        
        assert response.status_code == 200
        assert response.headers.get('X-Cache') == 'MISS'
        data = json.loads(response.data)
        assert data['sku'] == 'TEST-001'
        assert data['product_id'] == 1

    @patch('app.cache')
    @patch('app.product_service')
    def test_get_product_by_id_not_found(self, mock_service, mock_cache, client):
        """Test: Debe retornar 404 cuando el producto no existe."""
        mock_service.get_product_by_id.return_value = None
        mock_cache.get.return_value = None  # Cache MISS

        response = client.get('/products/999')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data
        assert 'not found' in data['error'].lower()


class TestHealthEndpoint:
    """Tests para el endpoint /health"""

    def test_health_check(self, client):
        """Test: Debe retornar status ok."""
        response = client.get('/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'ok'


class TestUpload3Validations:
    """Tests para validaciones adicionales de upload3"""

    def test_upload3_product_not_dict(self, client):
        """Test: Debe validar que cada producto sea un diccionario."""
        product_data = [
            "esto no es un objeto",
            {"sku": "TEST-001", "name": "Test", "value": "100", 
             "category_name": "MEDICATION", "quantity": "10", "warehouse_id": "1"}
        ]

        response = client.post('/products/upload3',
                             data=json.dumps(product_data),
                             content_type='text/plain')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert any('objeto JSON' in error for error in data['errors'])

    def test_upload3_sku_too_short(self, client):
        """Test: Debe validar que SKU tenga mínimo 3 caracteres."""
        product_data = [
            {
                "sku": "AB",  # Muy corto
                "name": "Test",
                "value": "100",
                "category_name": "MEDICATION",
                "quantity": "10",
                "warehouse_id": "1"
            }
        ]

        response = client.post('/products/upload3',
                             data=json.dumps(product_data),
                             content_type='text/plain')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert any('SKU muy corto' in warning for warning in data.get('warnings', []))

    def test_upload3_invalid_value_type(self, client):
        """Test: Debe validar que value sea un número válido."""
        product_data = [
            {
                "sku": "TEST-001",
                "name": "Test",
                "value": "no es un numero",
                "category_name": "MEDICATION",
                "quantity": "10",
                "warehouse_id": "1"
            }
        ]

        response = client.post('/products/upload3',
                             data=json.dumps(product_data),
                             content_type='text/plain')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert any('número válido' in error for error in data['errors'])

    def test_upload3_invalid_quantity_type(self, client):
        """Test: Debe validar que quantity sea un entero válido."""
        product_data = [
            {
                "sku": "TEST-001",
                "name": "Test",
                "value": "100",
                "category_name": "MEDICATION",
                "quantity": "no es numero",
                "warehouse_id": "1"
            }
        ]

        response = client.post('/products/upload3',
                             data=json.dumps(product_data),
                             content_type='text/plain')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert any('número entero válido' in error for error in data['errors'])

    def test_upload3_invalid_warehouse_id_zero(self, client):
        """Test: Debe validar que warehouse_id sea mayor a 0."""
        product_data = [
            {
                "sku": "TEST-001",
                "name": "Test",
                "value": "100",
                "category_name": "MEDICATION",
                "quantity": "10",
                "warehouse_id": "0"
            }
        ]

        response = client.post('/products/upload3',
                             data=json.dumps(product_data),
                             content_type='text/plain')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert any('warehouse_id debe ser mayor a 0' in error for error in data['errors'])

    def test_upload3_invalid_warehouse_id_type(self, client):
        """Test: Debe validar que warehouse_id sea un entero válido."""
        product_data = [
            {
                "sku": "TEST-001",
                "name": "Test",
                "value": "100",
                "category_name": "MEDICATION",
                "quantity": "10",
                "warehouse_id": "no es numero"
            }
        ]

        response = client.post('/products/upload3',
                             data=json.dumps(product_data),
                             content_type='text/plain')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert any('warehouse_id debe ser un número entero válido' in error for error in data['errors'])


class TestErrorHandlers:
    """Tests para manejadores de errores en varios endpoints"""

    @patch('app.product_repository._get_connection')
    def test_upload3_exception_handler(self, mock_get_conn, client):
        """Test: Debe manejar excepciones en upload_products_string."""
        # Simular error al obtener conexión
        mock_get_conn.side_effect = Exception("Database connection failed")

        product_data = [{"sku": "TEST-001", "name": "Test", "value": "100", 
                        "category_name": "MEDICATION", "quantity": "10", "warehouse_id": "1"}]

        response = client.post('/products/upload3',
                             data=json.dumps(product_data),
                             content_type='text/plain')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'error' in data['message'].lower() or 'interno' in data['message'].lower()

    @patch('app.product_repository._get_connection')
    def test_get_warehouses_exception_handler(self, mock_get_conn, client):
        """Test: Debe manejar excepciones en get_warehouses."""
        # Simular error al obtener conexión
        mock_get_conn.side_effect = Exception("Database error")

        response = client.get('/products/location/warehouses')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data

    @patch('app.product_repository._get_connection')
    def test_get_warehouses_no_data_with_city_id(self, mock_get_conn, client, mock_db_connection):
        """Test: Debe retornar datos de ejemplo cuando no hay datos y se filtra por city_id."""
        mock_conn, mock_cursor = mock_db_connection
        mock_get_conn.return_value = (mock_conn, mock_cursor)
        mock_cursor.fetchall.return_value = []

        response = client.get('/products/location/warehouses?city_id=5')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'warehouses' in data
        assert data['city_id'] == 5
        assert len(data['warehouses']) > 0

    @patch('app.product_repository._get_connection')
    def test_get_cities_exception_handler(self, mock_get_conn, client):
        """Test: Debe manejar excepciones en get_cities."""
        # Simular error al obtener conexión - esto hace que cursor y conn no estén definidos
        mock_get_conn.side_effect = Exception("Database error")

        response = client.get('/products/location/cities')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data

    @patch('app.get_warehouses')
    def test_get_location_info_exception_handler(self, mock_warehouses, client):
        """Test: Debe manejar excepciones en get_location_info."""
        # Simular error en get_warehouses
        mock_warehouses.side_effect = Exception("Internal error")

        response = client.get('/products/location')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data


class TestCacheControlHeader:
    """Tests para el decorador cache_control_header"""

    @patch('app.cache')
    def test_cache_hit_with_custom_key(self, mock_cache, client):
        """Test: Debe usar clave personalizada cuando se proporciona."""
        cached_data = b'[{"product_id": 1}]'
        mock_cache.get.return_value = cached_data

        # El endpoint /products/available usa key="products"
        response = client.get('/products/available')
        
        assert response.status_code == 200
        assert response.headers.get('X-Cache') == 'HIT'
        # Verificar que se usa la clave correcta
        mock_cache.get.assert_called_with('products')

    @patch('app.cache')
    @patch('app.product_service')
    def test_cache_miss_saves_to_cache(self, mock_service, mock_cache, client):
        """Test: Debe guardar en caché cuando hay MISS."""
        from domain.models import Product
        test_product = Product(
            product_id=1,
            sku='TEST-001',
            value=100.0,
            name='Producto Test',
            image_url=None,
            category_name='MEDICATION',
            total_quantity=10
        )
        mock_service.get_product_by_id.return_value = test_product
        mock_cache.get.return_value = None  # No hay caché

        response = client.get('/products/1?param=test')  # Con parámetro para usar request.full_path
        
        assert response.status_code == 200
        assert response.headers.get('X-Cache') == 'MISS'
        # Verificar que se guarda en caché (se llama con request.full_path cuando key está vacío)
        assert mock_cache.set.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

