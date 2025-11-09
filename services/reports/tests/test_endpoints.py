"""Tests unitarios para endpoints de la API."""

import pytest
import json
from unittest.mock import patch, Mock
from flask import Flask
from src.blueprints.reports import reports_bp


@pytest.fixture
def app():
    """Crear aplicación Flask para testing."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(reports_bp, url_prefix='/reports')
    return app


@pytest.fixture
def client(app):
    """Cliente de prueba."""
    return app.test_client()


class TestVendorsEndpoint:
    """Tests unitarios para endpoint /vendors."""
    
    @patch('src.blueprints.reports.get_vendors')
    def test_get_vendors_success(self, mock_get_vendors, client):
        """Test: GET /vendors exitoso."""
        # Arrange
        mock_vendors_data = [
            {'id': 'v1', 'name': 'Vendor 1', 'email': 'v1@test.com', 'region': 'Norte', 'active': True}
        ]
        mock_get_vendors.return_value = mock_vendors_data
        
        # Act
        response = client.get('/reports/vendors')
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) == 1
        assert data['data'][0]['id'] == 'v1'
    
    @patch('src.blueprints.reports.get_vendors')
    def test_get_vendors_no_data(self, mock_get_vendors, client):
        """Test: GET /vendors sin datos."""
        # Arrange
        mock_get_vendors.return_value = []
        
        # Act
        response = client.get('/reports/vendors')
        
        # Assert
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Error cargando datos de vendedores' in data['message']
    
    @patch('src.blueprints.reports.get_vendors')
    def test_get_vendors_exception(self, mock_get_vendors, client):
        """Test: GET /vendors con excepción."""
        # Arrange
        mock_get_vendors.side_effect = Exception("Database error")
        
        # Act
        response = client.get('/reports/vendors')
        
        # Assert
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Error obteniendo vendedores' in data['message']


class TestPeriodsEndpoint:
    """Tests unitarios para endpoint /periods."""
    
    @patch('src.blueprints.reports.get_periods')
    def test_get_periods_success(self, mock_get_periods, client):
        """Test: GET /periods exitoso."""
        # Arrange
        mock_periods = ['2024-Q1', '2024-Q2', '2024-Q3', '2024-Q4']
        mock_get_periods.return_value = mock_periods
        
        # Act
        response = client.get('/reports/periods')
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data'] == mock_periods
    
    @patch('src.blueprints.reports.get_periods')
    def test_get_periods_exception(self, mock_get_periods, client):
        """Test: GET /periods con excepción."""
        # Arrange
        mock_get_periods.side_effect = Exception("Database error")
        
        # Act
        response = client.get('/reports/periods')
        
        # Assert
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Error obteniendo períodos' in data['message']


class TestSalesReportEndpoint:
    """Tests unitarios para endpoint /sales-report."""
    
    @patch('src.blueprints.reports.get_sales_report_data')
    def test_generate_sales_report_success(self, mock_get_data, client):
        """Test: POST /sales-report exitoso."""
        # Arrange
        # Datos que coinciden con la estructura real del modelo SalesReport
        mock_report_data = {
            'ventasTotales': 150000.0,
            'pedidos': 10,
            'productos': [
                {
                    'nombre': 'Producto A',
                    'ventas': 150000.0,
                    'cantidad': 100
                }
            ],
            'grafico': [50000, 100000, 150000],
            'periodo': '2024-01-01 - 2024-03-31'
        }
        mock_get_data.return_value = mock_report_data
        
        request_data = {'vendor_id': 'v1', 'period': 'trimestral'}
        
        # Act
        response = client.post(
            '/reports/sales-report',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['vendor_id'] == 'v1'
        assert data['data']['period_type'] == 'trimestral'
    
    def test_generate_sales_report_missing_vendor_id(self, client):
        """Test: POST /sales-report sin vendor_id."""
        # Arrange
        request_data = {'period': 'trimestral'}  # Falta vendor_id
        
        # Act
        response = client.post(
            '/reports/sales-report',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['message'] == 'Campo obligatorio'
        assert data['error_type'] == 'validation_error'
    
    def test_generate_sales_report_missing_period(self, client):
        """Test: POST /sales-report sin period."""
        # Arrange
        request_data = {'vendor_id': 'v1'}  # Falta period
        
        # Act
        response = client.post(
            '/reports/sales-report',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['message'] == 'Campo obligatorio'
        assert data['error_type'] == 'validation_error'
    
    @patch('src.blueprints.reports.get_sales_report_data')
    def test_generate_sales_report_no_data(self, mock_get_data, client):
        """Test: POST /sales-report sin datos para el período."""
        # Arrange
        mock_get_data.return_value = None
        
        request_data = {'vendor_id': 'v1', 'period': 'trimestral'}
        
        # Act
        response = client.post(
            '/reports/sales-report',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'No se encontraron datos para este período' in data['message']
        assert data['error_type'] == 'no_data'
    
    @patch('src.blueprints.reports.get_sales_report_data')
    def test_generate_sales_report_exception(self, mock_get_data, client):
        """Test: POST /sales-report con excepción."""
        # Arrange
        mock_get_data.side_effect = Exception("Database error")
        
        request_data = {'vendor_id': 'v1', 'period': 'trimestral'}
        
        # Act
        response = client.post(
            '/reports/sales-report',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Hubo un error al generar el reporte' in data['message']
        assert data['error_type'] == 'server_error'
    
    # def test_generate_sales_report_invalid_json(self, client):
    #     """Test: POST /sales-report con JSON inválido."""
    #     # Act
    #     response = client.post(
    #         '/reports/sales-report',
    #         data='invalid json',
    #         content_type='application/json'
    #     )
    #     
    #     # Assert
    #     assert response.status_code == 500


class TestValidateSalesDataEndpoint:
    """Tests unitarios para endpoint /sales-report/validate."""
    
    @patch('src.blueprints.reports.validate_sales_data_availability')
    def test_validate_sales_data_available(self, mock_validate, client):
        """Test: POST /sales-report/validate con datos disponibles."""
        # Arrange
        mock_validate.return_value = True
        
        request_data = {'vendor_id': 'v1', 'period': 'trimestral'}
        
        # Act
        response = client.post(
            '/reports/sales-report/validate',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['has_data'] is True
        assert data['message'] == 'Datos disponibles'
    
    @patch('src.blueprints.reports.validate_sales_data_availability')
    def test_validate_sales_data_not_available(self, mock_validate, client):
        """Test: POST /sales-report/validate sin datos."""
        # Arrange
        mock_validate.return_value = False
        
        request_data = {'vendor_id': 'v1', 'period': 'trimestral'}
        
        # Act
        response = client.post(
            '/reports/sales-report/validate',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['has_data'] is False
        assert data['message'] == 'No hay datos para este período'
    
    def test_validate_sales_data_missing_fields(self, client):
        """Test: POST /sales-report/validate con campos faltantes."""
        # Arrange
        request_data = {'vendor_id': 'v1'}  # Falta period
        
        # Act
        response = client.post(
            '/reports/sales-report/validate',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['has_data'] is False
        assert 'Campos requeridos no proporcionados' in data['message']


class TestSalesComplianceEndpoint:
    """Tests unitarios para endpoint /sales-compliance."""
    
    @patch('src.blueprints.reports.get_sales_compliance')
    def test_get_sales_compliance_success_by_plan_id(self, mock_compliance, client):
        """Test: POST /sales-compliance exitoso con plan_id."""
        # Arrange
        mock_compliance_data = {
            'vendor_id': 1,
            'period_start': '2024-01-01',
            'period_end': '2024-03-31',
            'pedidos': 10,
            'ventasTotales': 150000.0,
            'total_goal': 150000.0,
            'cumplimiento_total_pct': 1.0,
            'status': 'verde',
            'detalle_productos': []
        }
        mock_compliance.return_value = mock_compliance_data
        
        request_data = {'vendor_id': 1, 'plan_id': 1}
        
        # Act
        response = client.post(
            '/reports/sales-compliance',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['vendor_id'] == 1
        assert data['data']['status'] == 'verde'
    
    @patch('src.blueprints.reports.get_sales_compliance')
    def test_get_sales_compliance_success_by_quarter_year(self, mock_compliance, client):
        """Test: POST /sales-compliance exitoso con quarter/year."""
        # Arrange
        mock_compliance_data = {
            'vendor_id': 1,
            'period_start': '2024-01-01',
            'period_end': '2024-03-31',
            'pedidos': 5,
            'ventasTotales': 60000.0,
            'total_goal': 100000.0,
            'cumplimiento_total_pct': 0.6,
            'status': 'amarillo',
            'detalle_productos': []
        }
        mock_compliance.return_value = mock_compliance_data
        
        request_data = {'vendor_id': 1, 'quarter': 'Q1', 'year': 2024}
        
        # Act
        response = client.post(
            '/reports/sales-compliance',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['vendor_id'] == 1
        assert data['data']['status'] == 'amarillo'
    
    def test_get_sales_compliance_missing_vendor_id(self, client):
        """Test: POST /sales-compliance sin vendor_id."""
        # Arrange
        request_data = {'plan_id': 1}
        
        # Act
        response = client.post(
            '/reports/sales-compliance',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'vendor_id' in data['message']
        assert data['error_type'] == 'validation_error'
    
    def test_get_sales_compliance_missing_plan_and_quarter(self, client):
        """Test: POST /sales-compliance sin plan_id ni quarter/year."""
        # Arrange
        request_data = {'vendor_id': 1}
        
        # Act
        response = client.post(
            '/reports/sales-compliance',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'plan_id' in data['message'] or 'quarter' in data['message']
        assert data['error_type'] == 'validation_error'
    
    @patch('src.blueprints.reports.get_sales_compliance')
    def test_get_sales_compliance_not_found(self, mock_compliance, client):
        """Test: POST /sales-compliance cuando no se encuentra el plan."""
        # Arrange
        mock_compliance.return_value = None
        
        request_data = {'vendor_id': 1, 'quarter': 'Q1', 'year': 2024}
        
        # Act
        response = client.post(
            '/reports/sales-compliance',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'No se encontró el plan' in data['message']
        assert data['error_type'] == 'not_found'
    
    @patch('src.blueprints.reports.get_sales_compliance')
    def test_get_sales_compliance_region_mismatch(self, mock_compliance, client):
        """Test: POST /sales-compliance con error de región no coincidente."""
        # Arrange
        from src.db import RegionMismatchError
        mock_compliance.side_effect = RegionMismatchError("Región no coincide")
        
        request_data = {'vendor_id': 1, 'plan_id': 1}
        
        # Act
        response = client.post(
            '/reports/sales-compliance',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error_type'] == 'region_mismatch'
    
    @patch('src.blueprints.reports.get_sales_compliance')
    def test_get_sales_compliance_value_error(self, mock_compliance, client):
        """Test: POST /sales-compliance con error de formato de datos."""
        # Arrange
        mock_compliance.side_effect = ValueError("Formato inválido")
        
        request_data = {'vendor_id': 'invalid', 'plan_id': 1}
        
        # Act
        response = client.post(
            '/reports/sales-compliance',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error_type'] == 'validation_error'
    
    @patch('src.blueprints.reports.get_sales_compliance')
    def test_get_sales_compliance_exception(self, mock_compliance, client):
        """Test: POST /sales-compliance con excepción general."""
        # Arrange
        mock_compliance.side_effect = Exception("Database error")
        
        request_data = {'vendor_id': 1, 'plan_id': 1}
        
        # Act
        response = client.post(
            '/reports/sales-compliance',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        # Assert
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Hubo un error al generar el reporte de cumplimiento' in data['message']
        assert data['error_type'] == 'server_error'


class TestHealthEndpoint:
    """Tests unitarios para endpoint /health."""
    
    def test_health_check_success(self, client):
        """Test: GET /health exitoso."""
        # Act
        response = client.get('/reports/health')
        
        # Assert
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Servidor funcionando correctamente'
        assert 'timestamp' in data
