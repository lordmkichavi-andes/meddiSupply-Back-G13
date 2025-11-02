import json
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO
from datetime import datetime, timedelta

@pytest.fixture
def client():
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


class TestHealthEndpoint:
    """Tests para el endpoint /health"""
    
    def test_health_ok(self, client):
        resp = client.get('/health')
        assert resp.status_code == 200
        assert resp.get_json()['status'] == 'ok'


class TestProductsEndpoint:
    """Tests para el endpoint /products"""
    
    @patch('src.blueprints.offers.get_products')
    def test_get_products_empty_response(self, mock_get_products, client):
        mock_get_products.return_value = []
        resp = client.get('/offers/products')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 0

    @patch('src.blueprints.offers.get_products')
    def test_get_products_exception(self, mock_get_products, client):
        """Cubre el bloque catch del endpoint /products (Línea 41 en offers.py)."""

        MOCK_ERROR_MESSAGE = "Fallo de conexión de base de datos simulado"
        mock_get_products.side_effect = Exception(MOCK_ERROR_MESSAGE)
        
        resp = client.get('/offers/products')

        assert resp.status_code == 500
        data = resp.get_json()
        assert "Error obteniendo productos" in data['message']
        assert MOCK_ERROR_MESSAGE in data['message']


class TestVisitRegistration:
    def get_valid_data(self):
        return {
            'client_id': 1,
            'seller_id': 10,
            'date': datetime.now().strftime('%Y-%m-%d'), 
            'findings': 'Todo en orden con la mercancía y el cliente.'
        }

    @patch('src.blueprints.offers.save_visit')
    def test_register_visit_success(self, mock_save_visit, client):
        mock_save_visit.return_value = {'visit_id': 50}
        resp = client.post('/offers/visit', json=self.get_valid_data())
        assert resp.status_code == 201
        assert resp.get_json()['visit']['visit_id'] == 50
        mock_save_visit.assert_called_once()
    
    def test_register_visit_missing_fields(self, client):
        data = self.get_valid_data()
        del data['findings'] 
        resp = client.post('/offers/visit', json=data)
        assert resp.status_code == 400
        assert "Faltan campos requeridos" in resp.get_json()['message']
        assert "findings" in resp.get_json()['missing']

    def test_register_visit_empty_field_value(self, client):
        data = self.get_valid_data()
        data['findings'] = "" # Campo vacío
        resp = client.post('/offers/visit', json=data)
        assert resp.status_code == 400
        assert "Ningún campo puede estar vacío" in resp.get_json()['message']

    def test_register_visit_invalid_date_format(self, client):
        data = self.get_valid_data()
        data['date'] = '2025/13/45' 
        resp = client.post('/offers/visit', json=data)
        assert resp.status_code == 400
        assert "no corresponde a un formato de fecha válido" in resp.get_json()['message']

    def test_register_visit_future_date(self, client):
        data = self.get_valid_data()
        data['date'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        resp = client.post('/offers/visit', json=data)
        assert resp.status_code == 400
        assert "posterior a la fecha actual" in resp.get_json()['message']

    def test_register_visit_old_date(self, client):
        data = self.get_valid_data()
        data['date'] = (datetime.now() - timedelta(days=31)).strftime('%Y-%m-%d')
        resp = client.post('/offers/visit', json=data)
        assert resp.status_code == 400
        assert "anterior a 30 días" in resp.get_json()['message']

    @patch('src.blueprints.offers.save_visit')
    def test_register_visit_db_exception(self, mock_save_visit, client):
        mock_save_visit.side_effect = Exception("Fallo de conexión a DB")
        resp = client.post('/offers/visit', json=self.get_valid_data())
        assert resp.status_code == 500
        assert "No se pudo registrar la visita" in resp.get_json()['message']

class TestSalesPlansEndpoint:
    """Tests para los endpoints /plans"""
    
    @patch('src.db.execute_query')
    def test_create_plan_success(self, mock_exec, client):
        mock_exec.side_effect = [
            {'plan_id': 123},
            1,
            1,
        ]

        payload = {
            'region': 'Centro',
            'quarter': 'Q4',
            'year': 2025,
            'total_goal': 100,
            'created_by': 1,
            'products': [
                {'product_id': 1, 'individual_goal': 60},
                {'product_id': 2, 'individual_goal': 40}
            ]
        }
        with patch('src.services.sales_plan_service.products_client.get_all_active_products', return_value=[
            {'product_id': 1}, {'product_id': 2}
        ]):
            resp = client.post('/offers/plans', data=json.dumps(payload), content_type='application/json')
        assert resp.status_code == 201
        data = resp.get_json()
        assert data['plan_id'] == 123
    
    def test_create_plan_missing_fields(self, client):
        payload = {'region': 'Centro'}  # Falta quarter, year, etc.
        resp = client.post('/offers/plans', data=json.dumps(payload), content_type='application/json')
        assert resp.status_code == 400
    
    @patch('src.db.execute_query')
    def test_get_plans_success(self, mock_exec, client):
        mock_exec.return_value = [
            {
                'plan_id': 1,
                'region': 'Norte',
                'quarter': 'Q1',
                'year': 2025,
                'total_goal': 50,
                'is_active': True,
                'creation_date': '2025-01-01'
            }
        ]
        resp = client.get('/offers/plans')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert data[0]['plan_id'] == 1
    
    @patch('src.db.execute_query')
    def test_get_plans_empty(self, mock_exec, client):
        mock_exec.return_value = []
        resp = client.get('/offers/plans')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    @patch('src.blueprints.offers.get_sales_plan_by_id')
    @patch('src.blueprints.offers.get_sales_plan_products')
    def test_get_plan_detail_success(self, mock_get_products, mock_get_by_id, client):
        mock_get_by_id.return_value = {
            'plan_id': 9,
            'region': 'Centro',
            'quarter': 'Q4',
            'year': 2025,
            'total_goal': 100,
            'is_active': True,
            'creation_date': '2025-01-01',
            'created_by': 1
        }
        mock_get_products.return_value = [
            {
                'plan_product_id': 1,
                'product_id': 1,
                'individual_goal': 60.0,
                'sku': 'SKU-1',
                'product_name': 'Prod 1',
                'product_value': 10.0,
                'unit_name': 'Caja',
                'unit_symbol': 'Cj'
            }
        ]
        resp = client.get('/offers/plans/9')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['plan_id'] == 9
        assert len(data['products']) == 1
    
    @patch('src.blueprints.offers.get_sales_plan_by_id')
    def test_get_plan_detail_not_found(self, mock_get_by_id, client):
        mock_get_by_id.return_value = None
        resp = client.get('/offers/plans/999')
        assert resp.status_code == 404


class TestOptionsEndpoints:
    """Tests para endpoints de opciones /regions y /quarters"""
    
    def test_get_regions(self, client):
        resp = client.get('/offers/regions')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0
    
    def test_get_quarters(self, client):
        resp = client.get('/offers/quarters')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert any(item['value'] == 'Q1' for item in data)
        assert len(data) == 4
