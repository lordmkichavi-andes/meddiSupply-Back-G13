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


class TestQuarterToDates:
    """Tests para _quarter_to_dates."""
    
    def test_quarter_to_dates_q1(self):
        """Test convertir Q1 a fechas."""
        result = db_module._quarter_to_dates('Q1', 2024)
        assert result is not None
        assert result['start'] == db_module.date(2024, 1, 1)
        assert result['end'] == db_module.date(2024, 3, 31)
    
    def test_quarter_to_dates_q2(self):
        """Test convertir Q2 a fechas."""
        result = db_module._quarter_to_dates('Q2', 2024)
        assert result is not None
        assert result['start'] == db_module.date(2024, 4, 1)
        assert result['end'] == db_module.date(2024, 6, 30)
    
    def test_quarter_to_dates_q3(self):
        """Test convertir Q3 a fechas."""
        result = db_module._quarter_to_dates('Q3', 2024)
        assert result is not None
        assert result['start'] == db_module.date(2024, 7, 1)
        assert result['end'] == db_module.date(2024, 9, 30)
    
    def test_quarter_to_dates_q4(self):
        """Test convertir Q4 a fechas."""
        result = db_module._quarter_to_dates('Q4', 2024)
        assert result is not None
        assert result['start'] == db_module.date(2024, 10, 1)
        assert result['end'] == db_module.date(2024, 12, 31)
    
    def test_quarter_to_dates_invalid(self):
        """Test convertir quarter inválido."""
        result = db_module._quarter_to_dates('Q5', 2024)
        assert result is None
    
    def test_quarter_to_dates_lowercase(self):
        """Test convertir quarter en minúsculas."""
        result = db_module._quarter_to_dates('q1', 2024)
        assert result is not None
        assert result['start'] == db_module.date(2024, 1, 1)


class TestStatusFromPct:
    """Tests para _status_from_pct."""
    
    def test_status_from_pct_verde(self):
        """Test status verde (>= 100%)."""
        assert db_module._status_from_pct(1.0) == 'verde'
        assert db_module._status_from_pct(1.5) == 'verde'
        assert db_module._status_from_pct(2.0) == 'verde'
    
    def test_status_from_pct_amarillo(self):
        """Test status amarillo (>= 60% y < 100%)."""
        assert db_module._status_from_pct(0.6) == 'amarillo'
        assert db_module._status_from_pct(0.8) == 'amarillo'
        assert db_module._status_from_pct(0.99) == 'amarillo'
    
    def test_status_from_pct_rojo(self):
        """Test status rojo (< 60%)."""
        assert db_module._status_from_pct(0.0) == 'rojo'
        assert db_module._status_from_pct(0.5) == 'rojo'
        assert db_module._status_from_pct(0.59) == 'rojo'


class TestGetVendorRegion:
    """Tests para _get_vendor_region."""
    
    def test_get_vendor_region_success(self):
        """Test obtener región del vendedor exitoso."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = {'region': 'Norte'}
            
            result = db_module._get_vendor_region(1)
            
            assert result == 'Norte'
    
    def test_get_vendor_region_not_found(self):
        """Test obtener región cuando vendedor no existe."""
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = None
            
            result = db_module._get_vendor_region(999)
            
            assert result is None
    
    def test_get_vendor_region_empty_result(self):
        """Test obtener región con resultado vacío."""
        with patch.object(db_module, '_http_get') as mock_http_get:
            mock_http_get.return_value = None
            
            result = db_module._get_vendor_region(1)
            
            assert result is None


class TestHttpGet:
    """Tests para _http_get."""
    
    def test_http_get_success(self):
        """Test HTTP GET exitoso."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': 'test'}
            mock_get.return_value = mock_response
            
            result = db_module._http_get('http://test.com/api')
            
            assert result == {'data': 'test'}
            mock_get.assert_called_once_with('http://test.com/api', params=None, timeout=10)
    
    def test_http_get_with_params(self):
        """Test HTTP GET con parámetros."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'data': 'test'}
            mock_get.return_value = mock_response
            
            result = db_module._http_get('http://test.com/api', params={'key': 'value'})
            
            assert result == {'data': 'test'}
            mock_get.assert_called_once_with('http://test.com/api', params={'key': 'value'}, timeout=10)
    
    def test_http_get_error_status(self):
        """Test HTTP GET con error de status."""
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            result = db_module._http_get('http://test.com/api')
            
            assert result is None
    
    def test_http_get_exception(self):
        """Test HTTP GET con excepción."""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Connection error")
            
            result = db_module._http_get('http://test.com/api')
            
            assert result is None


class TestGetPlanById:
    """Tests para _get_plan_by_id."""
    
    def test_get_plan_by_id_success(self):
        """Test obtener plan por ID exitoso."""
        with patch.object(db_module, '_http_get') as mock_http_get:
            mock_http_get.return_value = {'plan_id': 1, 'region': 'Norte', 'quarter': 'Q1', 'year': 2024}
            
            result = db_module._get_plan_by_id(1)
            
            assert result is not None
            assert result['plan_id'] == 1
            mock_http_get.assert_called_once()
    
    def test_get_plan_by_id_not_found(self):
        """Test obtener plan por ID no encontrado."""
        with patch.object(db_module, '_http_get') as mock_http_get:
            mock_http_get.return_value = None
            
            result = db_module._get_plan_by_id(999)
            
            assert result is None


class TestGetPlanByParams:
    """Tests para _get_plan_by_params."""
    
    def test_get_plan_by_params_success_dict(self):
        """Test obtener plan por parámetros exitoso (dict)."""
        with patch.object(db_module, '_http_get') as mock_http_get:
            # Primera llamada: obtener lista de planes, segunda: obtener plan completo
            def side_effect(url, params=None, timeout=10):
                if params is not None:
                    # Llamada a _get_plan_by_params (tiene params)
                    return {'plan_id': 1, 'region': 'Norte', 'quarter': 'Q1', 'year': 2024, 'is_active': True}
                else:
                    # Llamada a _get_plan_by_id (no tiene params, URL contiene /plans/{id})
                    return {'plan_id': 1, 'region': 'Norte', 'quarter': 'Q1', 'year': 2024, 'products': []}
            
            mock_http_get.side_effect = side_effect
            
            result = db_module._get_plan_by_params('Norte', 'Q1', 2024)
            
            assert result is not None
            assert result['plan_id'] == 1
    
    def test_get_plan_by_params_success_list_active(self):
        """Test obtener plan por parámetros exitoso (lista con activo)."""
        with patch.object(db_module, '_http_get') as mock_http_get:
            # Primera llamada: obtener lista de planes, segunda: obtener plan completo
            def side_effect(url, params=None, timeout=10):
                if params is not None:
                    # Llamada a _get_plan_by_params (tiene params)
                    return [
                        {'plan_id': 1, 'region': 'Norte', 'quarter': 'Q1', 'year': 2024, 'is_active': True},
                        {'plan_id': 2, 'region': 'Norte', 'quarter': 'Q1', 'year': 2024, 'is_active': False}
                    ]
                else:
                    # Llamada a _get_plan_by_id (no tiene params, URL contiene /plans/{id})
                    return {'plan_id': 1, 'region': 'Norte', 'quarter': 'Q1', 'year': 2024, 'is_active': True, 'products': []}
            
            mock_http_get.side_effect = side_effect
            
            result = db_module._get_plan_by_params('Norte', 'Q1', 2024)
            
            assert result is not None
            assert result['plan_id'] == 1
            assert result['is_active'] is True
    
    def test_get_plan_by_params_success_list_filtered(self):
        """Test obtener plan por parámetros exitoso (lista filtrada)."""
        with patch.object(db_module, '_http_get') as mock_http_get:
            # Primera llamada: obtener lista de planes, segunda: obtener plan completo
            def side_effect(url, params=None, timeout=10):
                if params is not None:
                    # Llamada a _get_plan_by_params (tiene params)
                    return [
                        {'plan_id': 1, 'region': 'Norte', 'quarter': 'Q1', 'year': 2024, 'is_active': True},
                        {'plan_id': 2, 'region': 'Norte', 'quarter': 'Q2', 'year': 2024, 'is_active': False}
                    ]
                else:
                    # Llamada a _get_plan_by_id (no tiene params, URL contiene /plans/{id})
                    return {'plan_id': 1, 'region': 'Norte', 'quarter': 'Q1', 'year': 2024, 'is_active': True, 'products': []}
            
            mock_http_get.side_effect = side_effect
            
            result = db_module._get_plan_by_params('Norte', 'Q1', 2024)
            
            assert result is not None
            assert result['plan_id'] == 1
    
    def test_get_plan_by_params_no_data(self):
        """Test obtener plan por parámetros sin datos."""
        with patch.object(db_module, '_http_get') as mock_http_get:
            mock_http_get.return_value = None
            
            result = db_module._get_plan_by_params('Norte', 'Q1', 2024)
            
            assert result is None
    
    def test_get_plan_by_params_empty_list(self):
        """Test obtener plan por parámetros con lista vacía."""
        with patch.object(db_module, '_http_get') as mock_http_get:
            mock_http_get.return_value = []
            
            result = db_module._get_plan_by_params('Norte', 'Q1', 2024)
            
            assert result is None


class TestQuerySalesTotals:
    """Tests para _query_sales_totals."""
    
    def test_query_sales_totals_success(self):
        """Test consultar totales de ventas exitoso."""
        from datetime import date
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = {'pedidos': 10, 'ventas_totales': 150000.0}
            
            result = db_module._query_sales_totals(1, date(2024, 1, 1), date(2024, 3, 31))
            
            assert result is not None
            assert result['pedidos'] == 10
            assert result['ventas_totales'] == 150000.0
    
    def test_query_sales_totals_no_data(self):
        """Test consultar totales de ventas sin datos."""
        from datetime import date
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = None
            
            result = db_module._query_sales_totals(1, date(2024, 1, 1), date(2024, 3, 31))
            
            assert result is None


class TestQuerySalesByProduct:
    """Tests para _query_sales_by_product."""
    
    def test_query_sales_by_product_success(self):
        """Test consultar ventas por producto exitoso."""
        from datetime import date
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = [
                {'product_id': 1, 'cantidad': 50, 'ventas': 75000.0},
                {'product_id': 2, 'cantidad': 25, 'ventas': 50000.0}
            ]
            
            result = db_module._query_sales_by_product(1, date(2024, 1, 1), date(2024, 3, 31))
            
            assert len(result) == 2
            assert result[0]['product_id'] == 1
    
    def test_query_sales_by_product_no_data(self):
        """Test consultar ventas por producto sin datos."""
        from datetime import date
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = None
            
            result = db_module._query_sales_by_product(1, date(2024, 1, 1), date(2024, 3, 31))
            
            assert result == []
    
    def test_query_sales_by_product_empty_list(self):
        """Test consultar ventas por producto con lista vacía."""
        from datetime import date
        with patch.object(db_module, 'execute_query') as mock_execute:
            mock_execute.return_value = []
            
            result = db_module._query_sales_by_product(1, date(2024, 1, 1), date(2024, 3, 31))
            
            assert result == []


class TestGetSalesCompliance:
    """Tests para get_sales_compliance."""
    
    def test_get_sales_compliance_by_plan_id_success(self):
        """Test obtener cumplimiento por plan_id exitoso."""
        from datetime import date
        with patch.object(db_module, '_get_vendor_region') as mock_region:
            with patch.object(db_module, '_get_plan_by_id') as mock_plan:
                with patch.object(db_module, '_get_sellers_by_region') as mock_sellers:
                    with patch.object(db_module, '_query_sales_totals') as mock_totals:
                        with patch.object(db_module, '_query_sales_by_product') as mock_by_product:
                            with patch.object(db_module, '_query_sales_by_region') as mock_region_sales:
                                mock_region.return_value = 'Norte'
                                mock_sellers.return_value = [1]  # 1 seller en la región
                                mock_plan.return_value = {
                                    'plan_id': 1,
                                    'region': 'Norte',
                                    'quarter': 'Q1',
                                    'year': 2024,
                                    'products': [
                                        {'product_id': 1, 'individual_goal': 100000.0},
                                        {'product_id': 2, 'individual_goal': 50000.0}
                                    ],
                                    'total_goal': 150000.0
                                }
                                # Para que sea verde: ventasTotales >= total_goal_vendor * 100
                                # total_goal_vendor = 150000.0 / 1 = 150000.0
                                # total_goal_vendor_monetario = 150000.0 * 100 = 15,000,000
                                # Para verde: ventasTotales >= 15,000,000
                                mock_totals.return_value = {'pedidos': 10, 'ventas_totales': 15000000.0}
                                mock_region_sales.return_value = {'pedidos': 10, 'ventas_totales': 15000000.0}
                                mock_by_product.return_value = [
                                    {'product_id': 1, 'ventas': 10000000.0, 'cantidad': 50},
                                    {'product_id': 2, 'ventas': 5000000.0, 'cantidad': 25}
                                ]
                                
                                result = db_module.get_sales_compliance(vendor_id=1, plan_id=1)
                                
                                assert result is not None
                                assert result['vendor_id'] == 1
                                assert result['total_goal'] == 150000.0
                                assert result['ventasTotales'] == 15000000.0
                                assert result['status'] == 'verde'
                                assert len(result['detalle_productos']) == 2
    
    def test_get_sales_compliance_by_quarter_year_success(self):
        """Test obtener cumplimiento por quarter/year exitoso."""
        from datetime import date
        with patch.object(db_module, '_get_vendor_region') as mock_region:
            with patch.object(db_module, '_get_plan_by_params') as mock_plan:
                with patch.object(db_module, '_get_sellers_by_region') as mock_sellers:
                    with patch.object(db_module, '_query_sales_totals') as mock_totals:
                        with patch.object(db_module, '_query_sales_by_product') as mock_by_product:
                            with patch.object(db_module, '_query_sales_by_region') as mock_region_sales:
                                mock_region.return_value = 'Norte'
                                mock_sellers.return_value = [1]  # 1 seller en la región
                                mock_plan.return_value = {
                                    'plan_id': 1,
                                    'region': 'Norte',
                                    'quarter': 'Q1',
                                    'year': 2024,
                                    'products': [
                                        {'product_id': 1, 'individual_goal': 100000.0}
                                    ],
                                    'total_goal': 100000.0
                                }
                                # Para que sea amarillo (60-100%): ventasTotales >= 0.6 * total_goal_vendor * 100
                                # total_goal_vendor = 100000.0 / 1 = 100000.0
                                # total_goal_vendor_monetario = 100000.0 * 100 = 10,000,000
                                # Para amarillo: 6,000,000 <= ventasTotales < 10,000,000
                                mock_totals.return_value = {'pedidos': 5, 'ventas_totales': 6000000.0}
                                mock_region_sales.return_value = {'pedidos': 5, 'ventas_totales': 6000000.0}
                                mock_by_product.return_value = [
                                    {'product_id': 1, 'ventas': 6000000.0, 'cantidad': 30}
                                ]
                                
                                result = db_module.get_sales_compliance(vendor_id=1, quarter='Q1', year=2024)
                                
                                assert result is not None
                                assert result['vendor_id'] == 1
                                assert result['status'] == 'amarillo'
    
    def test_get_sales_compliance_vendor_not_found(self):
        """Test obtener cumplimiento cuando vendedor no existe."""
        with patch.object(db_module, '_get_vendor_region') as mock_region:
            mock_region.return_value = None
            
            result = db_module.get_sales_compliance(vendor_id=999, quarter='Q1', year=2024)
            
            assert result is None
    
    def test_get_sales_compliance_plan_not_found(self):
        """Test obtener cumplimiento cuando plan no existe."""
        with patch.object(db_module, '_get_vendor_region') as mock_region:
            with patch.object(db_module, '_get_plan_by_params') as mock_plan:
                mock_region.return_value = 'Norte'
                mock_plan.return_value = None
                
                result = db_module.get_sales_compliance(vendor_id=1, quarter='Q1', year=2024)
                
                assert result is None
    
    def test_get_sales_compliance_region_mismatch_by_plan_id(self):
        """Test obtener cumplimiento con región no coincidente por plan_id."""
        with patch.object(db_module, '_get_vendor_region') as mock_region:
            with patch.object(db_module, '_get_plan_by_id') as mock_plan:
                mock_region.return_value = 'Norte'
                mock_plan.return_value = {
                    'plan_id': 1,
                    'region': 'Sur',
                    'quarter': 'Q1',
                    'year': 2024
                }
                
                with pytest.raises(db_module.RegionMismatchError):
                    db_module.get_sales_compliance(vendor_id=1, plan_id=1)
    
    def test_get_sales_compliance_region_mismatch_by_params(self):
        """Test obtener cumplimiento con región no coincidente por parámetros."""
        with patch.object(db_module, '_get_vendor_region') as mock_region:
            mock_region.return_value = 'Norte'
            
            with pytest.raises(db_module.RegionMismatchError):
                db_module.get_sales_compliance(vendor_id=1, region='Sur', quarter='Q1', year=2024)
    
    def test_get_sales_compliance_invalid_quarter(self):
        """Test obtener cumplimiento con quarter inválido en el plan."""
        with patch.object(db_module, '_get_vendor_region') as mock_region:
            with patch.object(db_module, '_get_plan_by_id') as mock_plan:
                mock_region.return_value = 'Norte'
                # Plan sin quarter válido
                mock_plan.return_value = {
                    'plan_id': 1,
                    'region': 'Norte',
                    'quarter': None,  # Quarter inválido
                    'year': None  # Year también None
                }
                
                result = db_module.get_sales_compliance(vendor_id=1, plan_id=1)
                
                # Como el plan no tiene quarter válido, _quarter_to_dates retornará None
                # y get_sales_compliance debería retornar None
                assert result is None
    
    def test_get_sales_compliance_status_rojo(self):
        """Test obtener cumplimiento con status rojo."""
        from datetime import date
        with patch.object(db_module, '_get_vendor_region') as mock_region:
            with patch.object(db_module, '_get_plan_by_params') as mock_plan:
                with patch.object(db_module, '_get_sellers_by_region') as mock_sellers:
                    with patch.object(db_module, '_query_sales_totals') as mock_totals:
                        with patch.object(db_module, '_query_sales_by_product') as mock_by_product:
                            with patch.object(db_module, '_query_sales_by_region') as mock_region_sales:
                                mock_region.return_value = 'Norte'
                                mock_sellers.return_value = [1]  # 1 seller en la región
                                mock_plan.return_value = {
                                    'plan_id': 1,
                                    'region': 'Norte',
                                    'quarter': 'Q1',
                                    'year': 2024,
                                    'products': [
                                        {'product_id': 1, 'individual_goal': 100000.0}
                                    ],
                                    'total_goal': 100000.0
                                }
                                # Para que sea rojo (< 60%): ventasTotales < 0.6 * total_goal_vendor * 100
                                # total_goal_vendor = 100000.0 / 1 = 100000.0
                                # total_goal_vendor_monetario = 100000.0 * 100 = 10,000,000
                                # Para 0.3%: ventasTotales = 0.003 * 10,000,000 = 30,000
                                mock_totals.return_value = {'pedidos': 2, 'ventas_totales': 30000.0}
                                mock_region_sales.return_value = {'pedidos': 2, 'ventas_totales': 30000.0}
                                mock_by_product.return_value = [
                                    {'product_id': 1, 'ventas': 30000.0, 'cantidad': 15}
                                ]
                                
                                result = db_module.get_sales_compliance(vendor_id=1, quarter='Q1', year=2024)
                                
                                assert result is not None
                                assert result['status'] == 'rojo'
                                assert result['cumplimiento_total_pct'] == 0.3
