"""Tests completos para alcanzar 80% de cobertura."""

import pytest
import sys
import os
import importlib.util
from unittest.mock import Mock, patch

# Función para importar módulo desde archivo
def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Importar módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Importar Vehiculo y Cliente
vehiculo_path = os.path.join(parent_dir, "src", "models", "vehiculo.py")
Vehiculo = import_from_file("vehiculo", vehiculo_path).Vehiculo

cliente_path = os.path.join(parent_dir, "src", "models", "cliente.py")
Cliente = import_from_file("cliente", cliente_path).Cliente

# Importar __init__.py de models
models_init_path = os.path.join(parent_dir, "src", "models", "__init__.py")
models_init = import_from_file("models_init", models_init_path)

# Importar funciones de db
db_path = os.path.join(parent_dir, "src", "db.py")
db_module = import_from_file("db", db_path)


class TestModelsInit:
    """Tests para src/models/__init__.py - cubre las 3 líneas faltantes."""

    def test_models_init_imports(self):
        """Test que los imports en __init__.py funcionen."""
        # Verificar que Vehiculo y Cliente estén disponibles
        assert hasattr(models_init, 'Vehiculo')
        assert hasattr(models_init, 'Cliente')
        
        # Verificar que __all__ esté definido
        assert hasattr(models_init, '__all__')
        assert 'Vehiculo' in models_init.__all__
        assert 'Cliente' in models_init.__all__

    def test_models_init_all_list(self):
        """Test que __all__ contenga los elementos correctos."""
        expected_all = ['Vehiculo', 'Cliente']
        assert models_init.__all__ == expected_all


class TestDatabaseFunctions:
    """Tests para src/db.py - cubre las 42 líneas faltantes."""

    def test_get_connection_success(self):
        """Test conexión exitosa a la base de datos."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            
            # Configurar variables de entorno
            with patch.dict(os.environ, {
                'DB_HOST': 'localhost',
                'DB_PORT': '5432',
                'DB_NAME': 'test_db',
                'DB_USER': 'test_user',
                'DB_PASSWORD': 'test_pass'
            }):
                result = db_module.get_connection()
                
                assert result == mock_conn
                mock_connect.assert_called_once_with(
                    host='localhost',
                    port='5432',
                    database='test_db',
                    user='test_user',
                    password='test_pass',
                    sslmode='require'
                )

    def test_get_connection_default_values(self):
        """Test conexión con valores por defecto."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            
            with patch.dict(os.environ, {
                'DB_HOST': 'localhost',
                'DB_PASSWORD': 'test_pass'
            }, clear=True):
                result = db_module.get_connection()
                
                assert result == mock_conn
                mock_connect.assert_called_once_with(
                    host='localhost',
                    port=5432,  # Valor por defecto
                    database='postgres',  # Valor por defecto
                    user='postgres',  # Valor por defecto
                    password='test_pass',
                    sslmode='require'
                )

    def test_get_connection_failure(self):
        """Test fallo en la conexión."""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            result = db_module.get_connection()
            assert result is None


    def test_execute_query_no_connection(self):
        """Test execute_query sin conexión."""
        with patch.object(db_module, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value = None
            
            result = db_module.execute_query("SELECT * FROM test")
            assert result is None

    def test_execute_query_exception(self):
        """Test execute_query con excepción."""
        with patch.object(db_module, 'get_connection') as mock_get_conn:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor.execute.side_effect = Exception("Query failed")
            mock_get_conn.return_value = mock_conn
            
            result = db_module.execute_query("SELECT * FROM test")
            assert result is None
            mock_conn.rollback.assert_called_once()

    def test_get_vehiculos_success(self):
        """Test get_vehiculos exitoso."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_data = [
                {'vehicle_id': 'V001', 'capacity': 100, 'color': 'rojo', 'label': 'refrigerado'},
                {'vehicle_id': 'V002', 'capacity': 50, 'color': 'azul', 'label': None}
            ]
            mock_execute.return_value = mock_data
            
            result = db_module.get_vehiculos()
            
            assert result == mock_data
            expected_query = "SELECT vehicle_id, capacity, color, label FROM routes.vehicles ORDER BY vehicle_id"
            mock_execute.assert_called_once_with(expected_query, fetch_all=True)

    def test_get_vehiculos_no_results(self):
        """Test get_vehiculos sin resultados."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = None
            
            result = db_module.get_vehiculos()
            assert result == []

    def test_get_vehiculos_empty_results(self):
        """Test get_vehiculos con resultados vacíos."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = []
            
            result = db_module.get_vehiculos()
            assert result == []

    def test_get_clientes_success(self):
        """Test get_clientes exitoso."""
        # Mock de respuesta del servicio de users (incluye client_id)
        mock_users_response = Mock()
        mock_users_response.status_code = 200
        mock_users_response.json.return_value = {
            'clients': [
                {
                    'user_id': 1,
                    'client_id': 1,  # client_id ahora viene del MS
                    'name': 'Hospital',
                    'last_name': 'Central',
                    'address': 'Calle 123 #45-67',
                    'latitude': 4.6097100,
                    'longitude': -74.0817500
                }
            ]
        }
        
        # Mock de datos de demanda desde orders.Orders
        mock_demanda_data = [
            {
                'client_id': 1,
                'demanda': 50
            }
        ]
        
        expected_result = [
            {
                'id': 1,  # client_id del MS
                'nombre': 'Hospital Central',
                'direccion': 'Calle 123 #45-67',
                'latitud': 4.6097100,
                'longitud': -74.0817500,
                'demanda': 50
            }
        ]
        
        with patch.object(db_module, 'execute_query') as mock_execute, \
             patch.object(db_module, 'requests') as mock_requests:
            
            # Configurar mock para que devuelva demanda cuando se consulta orders.Orders
            def execute_query_side_effect(query, params=None, **kwargs):
                if 'orders.Orders' in query and 'client_id' in query:
                    return mock_demanda_data
                return []
            
            mock_execute.side_effect = execute_query_side_effect
            mock_requests.get.return_value = mock_users_response

            result = db_module.get_clientes()

            assert result == expected_result
            # Verificar que se llamó requests.get al servicio de users
            mock_requests.get.assert_called_once()
            # Verificar que se llamó execute_query para calcular demanda
            assert mock_execute.called

    def test_get_clientes_no_results(self):
        """Test get_clientes sin resultados."""
        with patch.object(db_module, 'execute_query') as mock_execute, \
             patch.object(db_module, 'requests'):
            mock_execute.return_value = None
            
            result = db_module.get_clientes()
            assert result == []

    def test_get_clientes_empty_results(self):
        """Test get_clientes con resultados vacíos."""
        with patch.object(db_module, 'execute_query') as mock_execute, \
             patch.object(db_module, 'requests'):
            mock_execute.return_value = []
            
            result = db_module.get_clientes()
            assert result == []


class TestAdditionalCoverage:
    """Tests adicionales para completar cobertura."""

    def test_vehiculo_edge_cases(self):
        """Test casos edge para Vehiculo."""
        # Test con etiqueta vacía
        vehiculo = Vehiculo(id="V001", capacidad=0, color="", etiqueta="")
        assert vehiculo.etiqueta == ""
        
        # Test from_dict con etiqueta vacía
        data = {"vehicle_id": "V002", "capacity": 0, "color": "", "label": ""}
        vehiculo2 = Vehiculo.from_dict(data)
        assert vehiculo2.etiqueta == ""

    def test_cliente_edge_cases(self):
        """Test casos edge para Cliente."""
        # Test con coordenadas 0
        cliente = Cliente(
            id="C001",
            nombre="Test",
            direccion="Test",
            latitud=0.0,
            longitud=0.0,
            demanda=0
        )
        assert cliente.latitud == 0.0
        assert cliente.longitud == 0.0
        assert cliente.demanda == 0
        
        # Test to_stop con order_id vacío (debe usar el id del cliente)
        result = cliente.to_stop("")
        assert result["orderId"] == "C001"  # Usa el id del cliente cuando order_id es vacío

    def test_logging_functionality(self):
        """Test que el logging esté configurado."""
        # Verificar que el logger esté disponible en db_module
        assert hasattr(db_module, 'logger')
        assert db_module.logger is not None
