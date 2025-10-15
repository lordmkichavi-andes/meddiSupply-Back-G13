"""Tests unificados para funciones de base de datos."""

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

# Importar funciones de db
db_path = os.path.join(parent_dir, "src", "db.py")
db_module = import_from_file("db", db_path)


class TestGetConnection:
    """Tests para get_connection."""
    
    def test_get_connection_success(self):
        """Test obtener conexión exitosa."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            
            result = db_module.get_connection()
            
            assert result == mock_conn
            mock_connect.assert_called_once()
    
    def test_get_connection_with_env_vars(self):
        """Test obtener conexión con variables de entorno."""
        with patch.dict('os.environ', {
            'DB_HOST': 'test-host',
            'DB_PORT': '5432',
            'DB_NAME': 'test-db',
            'DB_USER': 'test-user',
            'DB_PASSWORD': 'test-password'
        }):
            with patch('psycopg2.connect') as mock_connect:
                mock_conn = Mock()
                mock_connect.return_value = mock_conn
                
                result = db_module.get_connection()
                
                mock_connect.assert_called_once_with(
                    host='test-host',
                    port='5432',
                    database='test-db',
                    user='test-user',
                    password='test-password',
                    sslmode='require'
                )
    
    def test_get_connection_default_values(self):
        """Test obtener conexión con valores por defecto."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_connect.return_value = mock_conn
            
            # Simular variables de entorno vacías
            with patch.dict('os.environ', {}, clear=True):
                result = db_module.get_connection()
            
            assert result == mock_conn
    
    def test_get_connection_failure(self):
        """Test obtener conexión fallida."""
        with patch('psycopg2.connect') as mock_connect:
            mock_connect.side_effect = Exception("Connection failed")
            
            result = db_module.get_connection()
            
            assert result is None


class TestExecuteQuery:
    """Tests para execute_query."""
    
    def test_execute_query_no_connection(self):
        """Test ejecutar query sin conexión."""
        result = db_module.execute_query("SELECT 1")
        assert result is None
    
    def test_execute_query_exception(self):
        """Test ejecutar query con excepción."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor_context = Mock()
            mock_cursor_context.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor_context.__exit__ = Mock(return_value=None)
            mock_conn.cursor.return_value = mock_cursor_context
            mock_cursor.execute.side_effect = Exception("Query failed")
            mock_connect.return_value = mock_conn
            
            result = db_module.execute_query("SELECT 1")
            
            assert result is None
    
    def test_execute_query_fetch_one_success(self):
        """Test ejecutar query con fetch_one exitoso."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor_context = Mock()
            mock_cursor_context.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor_context.__exit__ = Mock(return_value=None)
            mock_conn.cursor.return_value = mock_cursor_context
            mock_cursor.fetchone.return_value = {'id': 'test', 'name': 'Test'}
            mock_connect.return_value = mock_conn
            
            result = db_module.execute_query("SELECT * FROM test", fetch_one=True)
            
            assert result == {'id': 'test', 'name': 'Test'}
            mock_cursor.execute.assert_called_once_with("SELECT * FROM test", None)
            mock_cursor.fetchone.assert_called_once()
    
    def test_execute_query_fetch_all_success(self):
        """Test ejecutar query con fetch_all exitoso."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor_context = Mock()
            mock_cursor_context.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor_context.__exit__ = Mock(return_value=None)
            mock_conn.cursor.return_value = mock_cursor_context
            mock_cursor.fetchall.return_value = [{'id': 'test1'}, {'id': 'test2'}]
            mock_connect.return_value = mock_conn
            
            result = db_module.execute_query("SELECT * FROM test", fetch_all=True)
            
            assert result == [{'id': 'test1'}, {'id': 'test2'}]
            mock_cursor.execute.assert_called_once_with("SELECT * FROM test", None)
            mock_cursor.fetchall.assert_called_once()
    
    def test_execute_query_commit_success(self):
        """Test ejecutar query con commit exitoso."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor_context = Mock()
            mock_cursor_context.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor_context.__exit__ = Mock(return_value=None)
            mock_conn.cursor.return_value = mock_cursor_context
            mock_cursor.rowcount = 3
            mock_connect.return_value = mock_conn
            
            result = db_module.execute_query("INSERT INTO test VALUES (1)")
            
            assert result == 3
            mock_cursor.execute.assert_called_once_with("INSERT INTO test VALUES (1)", None)
            mock_conn.commit.assert_called_once()
    
    def test_execute_query_with_params(self):
        """Test ejecutar query con parámetros."""
        with patch('psycopg2.connect') as mock_connect:
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_cursor_context = Mock()
            mock_cursor_context.__enter__ = Mock(return_value=mock_cursor)
            mock_cursor_context.__exit__ = Mock(return_value=None)
            mock_conn.cursor.return_value = mock_cursor_context
            mock_cursor.fetchone.return_value = {'count': 1}
            mock_connect.return_value = mock_conn
            
            result = db_module.execute_query("SELECT COUNT(*) FROM test WHERE id = %s", ('test_id',), fetch_one=True)
            
            assert result == {'count': 1}
            mock_cursor.execute.assert_called_once_with("SELECT COUNT(*) FROM test WHERE id = %s", ('test_id',))


class TestGetVendors:
    """Tests para get_vendors."""
    
    def test_get_vendors_success(self):
        """Test obtener vendedores exitoso."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = [
                {"id": "v1", "name": "Juan", "email": "juan@test.com", "region": "Norte", "active": True}
            ]
            
            result = db_module.get_vendors()
            
            assert len(result) == 1
            assert result[0]["id"] == "v1"
            assert result[0]["name"] == "Juan"
    
    def test_get_vendors_no_results(self):
        """Test obtener vendedores sin resultados."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = None
            
            result = db_module.get_vendors()
            
            assert result == []
    
    def test_get_vendors_empty_results(self):
        """Test obtener vendedores con resultados vacíos."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = []
            
            result = db_module.get_vendors()
            
            assert result == []


class TestGetPeriods:
    """Tests para get_periods."""
    
    def test_get_periods_success(self):
        """Test obtener períodos exitoso."""
        result = db_module.get_periods()
        
        assert len(result) == 4
        assert result[0]["value"] == "bimestral"
        assert result[1]["value"] == "trimestral"
        assert result[2]["value"] == "semestral"
        assert result[3]["value"] == "anual"


class TestGetProducts:
    """Tests para get_products."""
    
    def test_get_products_success(self):
        """Test obtener productos exitoso."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = [
                {"id": "p1", "name": "Producto A", "category": "Electrónicos", "price": 1500.0, "unit": "unidad"}
            ]
            
            result = db_module.get_products()
            
            assert len(result) == 1
            assert result[0]["id"] == "p1"
            assert result[0]["name"] == "Producto A"
    
    def test_get_products_no_results(self):
        """Test obtener productos sin resultados."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = None
            
            result = db_module.get_products()
            
            assert result == []
    
    def test_get_products_empty_results(self):
        """Test obtener productos con resultados vacíos."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = []
            
            result = db_module.get_products()
            
            assert result == []


class TestGetSalesReportData:
    """Tests para get_sales_report_data."""
    
    def test_get_sales_report_data_success(self):
        """Test obtener datos de reporte de ventas exitoso."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            # Configurar mock para las 3 consultas separadas
            def mock_execute_side_effect(query, params=None, fetch_one=False, fetch_all=False):
                if 'LIMIT 1' in query:  # Consulta de ventas básicas
                    return {
                        'ventas_totales': 150000.0,
                        'pedidos': 10,
                        'period_start': '2024-01-01',
                        'period_end': '2024-03-31'
                    }
                elif 'GROUP BY p.name' in query:  # Consulta de productos
                    return [
                        {'nombre': 'Producto A', 'ventas': 75000.0, 'cantidad': 50},
                        {'nombre': 'Producto B', 'ventas': 75000.0, 'cantidad': 25}
                    ]
                elif 'DISTINCT' in query:  # Consulta del gráfico
                    return [
                        {'idx': 1, 'value': 50000},
                        {'idx': 2, 'value': 100000},
                        {'idx': 3, 'value': 150000}
                    ]
                return None
            
            mock_execute.side_effect = mock_execute_side_effect
            
            result = db_module.get_sales_report_data('v1', 'trimestral')
            
            assert result is not None
            assert result['ventasTotales'] == 150000.0
            assert result['pedidos'] == 10
            assert result['periodo'] == '2024-01-01 - 2024-03-31'
            assert len(result['grafico']) == 3
            assert result['grafico'] == [50000, 100000, 150000]
            assert len(result['productos']) == 2
            assert result['productos'][0]['nombre'] == 'Producto A'
            assert result['productos'][1]['nombre'] == 'Producto B'
    
    def test_get_sales_report_data_no_data(self):
        """Test obtener datos de reporte de ventas sin datos."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = None
            
            result = db_module.get_sales_report_data('v1', 'trimestral')
            
            assert result is None
    
    def test_get_sales_report_data_different_periods(self):
        """Test obtener datos de reporte con diferentes períodos."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            # Configurar mock para las 3 consultas separadas
            def mock_execute_side_effect(query, params=None, fetch_one=False, fetch_all=False):
                if 'LIMIT 1' in query:  # Consulta de ventas básicas
                    return {
                        'ventas_totales': 100000.0,
                        'pedidos': 5,
                        'period_start': '2024-01-01',
                        'period_end': '2024-02-29'
                    }
                elif 'GROUP BY p.name' in query:  # Consulta de productos
                    return []  # Sin productos
                elif 'DISTINCT' in query:  # Consulta del gráfico
                    return []  # Sin datos del gráfico
                return None
            
            mock_execute.side_effect = mock_execute_side_effect
            
            # Probar diferentes períodos
            result1 = db_module.get_sales_report_data('v1', 'bimestral')
            result2 = db_module.get_sales_report_data('v1', 'semestral')
            result3 = db_module.get_sales_report_data('v1', 'anual')
            
            assert result1 is not None
            assert result2 is not None
            assert result3 is not None


class TestValidateSalesDataAvailability:
    """Tests para validate_sales_data_availability."""
    
    def test_validate_sales_data_availability_true(self):
        """Test validar disponibilidad de datos - datos disponibles."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = {'count': 5}
            
            result = db_module.validate_sales_data_availability('v1', 'trimestral')
            
            assert result is True
    
    def test_validate_sales_data_availability_false(self):
        """Test validar disponibilidad de datos - sin datos."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = {'count': 0}
            
            result = db_module.validate_sales_data_availability('v1', 'trimestral')
            
            assert result is False
    
    def test_validate_sales_data_availability_no_result(self):
        """Test validar disponibilidad de datos - sin resultado."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = None
            
            result = db_module.validate_sales_data_availability('v1', 'trimestral')
            
            assert result is False
