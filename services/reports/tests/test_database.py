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
        from datetime import datetime, date
        with patch.object(db_module, 'execute_query') as mock_execute:
            # Configurar mock para las 3 consultas separadas
            def mock_execute_side_effect(query, params=None, fetch_one=False, fetch_all=False):
                # Consulta de ventas básicas (fetch_one=True, tiene COUNT y ventas_totales)
                if fetch_one and 'COUNT(o.order_id)' in query and 'ventas_totales' in query:
                    return {
                        'ventas_totales': 150000.0,
                        'pedidos': 10
                    }
                # Consulta de productos (fetch_all=True, tiene GROUP BY p.name)
                elif fetch_all and 'GROUP BY p.name' in query:
                    return [
                        {'nombre': 'Producto A', 'ventas': 75000.0, 'cantidad': 50},
                        {'nombre': 'Producto B', 'ventas': 75000.0, 'cantidad': 25}
                    ]
                # Consulta del gráfico (fetch_all=True, tiene DATE_TRUNC)
                elif fetch_all and 'DATE_TRUNC' in query:
                    # Retornar fechas como datetime para que fmt_period funcione
                    return [
                        {'periodo': datetime(2024, 10, 1), 'ventas': 50000.0},
                        {'periodo': datetime(2024, 11, 1), 'ventas': 100000.0},
                        {'periodo': datetime(2024, 12, 1), 'ventas': 150000.0}
                    ]
                return None
            
            mock_execute.side_effect = mock_execute_side_effect
            
            result = db_module.get_sales_report_data('v1', 'trimestral')
            
            # Validar que el resultado no es None y tiene la estructura correcta
            assert result is not None
            assert result['ventasTotales'] == 150000.0
            assert result['ventas_totales'] == 150000.0
            assert result['pedidos'] == 10
            assert 'period_start' in result
            assert 'period_end' in result
            assert 'periodo' in result
            assert len(result['grafico']) == 3
            # Validar estructura del gráfico (lista de dicts con periodo y ventas)
            assert result['grafico'][0]['periodo'] == '2024-10'
            assert result['grafico'][0]['ventas'] == 50000.0
            assert result['grafico'][1]['periodo'] == '2024-11'
            assert result['grafico'][1]['ventas'] == 100000.0
            assert result['grafico'][2]['periodo'] == '2024-12'
            assert result['grafico'][2]['ventas'] == 150000.0
            assert len(result['productos']) == 2
            assert result['productos'][0]['nombre'] == 'Producto A'
            assert result['productos'][0]['ventas'] == 75000.0
            assert result['productos'][0]['cantidad'] == 50
            assert result['productos'][1]['nombre'] == 'Producto B'
            assert result['productos'][1]['ventas'] == 75000.0
            assert result['productos'][1]['cantidad'] == 25
    
    def test_get_sales_report_data_no_data(self):
        """Test obtener datos de reporte de ventas sin datos."""
        from datetime import datetime
        with patch.object(db_module, 'execute_query') as mock_execute:
            # Cuando no hay datos, execute_query retorna None o {} o []
            def mock_execute_side_effect(query, params=None, fetch_one=False, fetch_all=False):
                if fetch_one:
                    return {}  # Diccionario vacío cuando no hay datos
                elif fetch_all:
                    return []  # Lista vacía cuando no hay datos
                return None
            
            mock_execute.side_effect = mock_execute_side_effect
            
            result = db_module.get_sales_report_data('v1', 'trimestral')
            
            # La función retorna un diccionario con valores por defecto, no None
            assert result is not None
            assert result['ventas_totales'] == 0.0
            assert result['ventasTotales'] == 0.0
            assert result['pedidos'] == 0
            assert result['productos'] == []
            assert result['grafico'] == []
            assert 'period_start' in result
            assert 'period_end' in result
            assert 'periodo' in result
    
    def test_get_sales_report_data_different_periods(self):
        """Test obtener datos de reporte con diferentes períodos."""
        from datetime import datetime
        with patch.object(db_module, 'execute_query') as mock_execute:
            # Configurar mock para las 3 consultas separadas
            def mock_execute_side_effect(query, params=None, fetch_one=False, fetch_all=False):
                # Consulta de ventas básicas
                if fetch_one and 'COUNT(o.order_id)' in query and 'ventas_totales' in query:
                    return {
                        'ventas_totales': 100000.0,
                        'pedidos': 5
                    }
                # Consulta de productos
                elif fetch_all and 'GROUP BY p.name' in query:
                    return []  # Sin productos
                # Consulta del gráfico
                elif fetch_all and 'DATE_TRUNC' in query:
                    return []  # Sin datos del gráfico
                return None
            
            mock_execute.side_effect = mock_execute_side_effect
            
            # Probar diferentes períodos
            result1 = db_module.get_sales_report_data('v1', 'bimestral')
            result2 = db_module.get_sales_report_data('v1', 'semestral')
            result3 = db_module.get_sales_report_data('v1', 'anual')
            
            # Todos deben retornar un diccionario válido, no None
            assert result1 is not None
            assert result1['ventas_totales'] == 100000.0
            assert result1['pedidos'] == 5
            assert result1['productos'] == []
            assert result1['grafico'] == []
            
            assert result2 is not None
            assert result2['ventas_totales'] == 100000.0
            assert result2['pedidos'] == 5
            assert result2['productos'] == []
            assert result2['grafico'] == []
            
            assert result3 is not None
            assert result3['ventas_totales'] == 100000.0
            assert result3['pedidos'] == 5
            assert result3['productos'] == []
            assert result3['grafico'] == []


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
