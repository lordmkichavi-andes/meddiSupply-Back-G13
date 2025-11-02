import json
import pytest
from unittest.mock import patch, MagicMock
from io import BytesIO

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
    
    @patch('src.blueprints.offers.Product')
    @patch('src.blueprints.offers.get_products')
    def test_get_products_success(self, mock_get_products, mock_product_cls, client):
        mock_get_products.return_value = [
            {
                'product_id': 1,
                'sku': 'TEST-001',
                'name': 'Producto Test',
                'value': 10.0,
                'unit_name': 'Caja',
                'unit_symbol': 'Cj',
                'category_name': 'MEDICATION'
            }
        ]
        mock_instance = MagicMock()
        mock_instance.to_dict.return_value = {'product_id': 1, 'sku': 'TEST-001'}
        mock_product_cls.from_dict.return_value = mock_instance

        resp = client.get('/offers/products')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert data[0]['sku'] == 'TEST-001'
    
    @patch('src.blueprints.offers.get_products')
    def test_get_products_empty_response(self, mock_get_products, client):
        mock_get_products.return_value = []
        resp = client.get('/offers/products')
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 0


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

class TestVisitEvidencesEndpoint:
    """Tests para el endpoint POST /offers/visits/<int:visit_id>/evidences"""

    # --- Test de Subida Exitosa ---
    @patch('src.blueprints.offers.db_get_visit_by_id')
    @patch('src.blueprints.offers.StorageService')
    @patch('src.blueprints.offers.db_save_evidence')
    def test_upload_evidences_success(self, mock_db_save, mock_storage, mock_db_get_visit, client):
        # 1. Configurar Mocks
        # La visita existe
        mock_db_get_visit.return_value = {'visit_id': 101, 'exists': True}
        # La subida a S3 es exitosa
        mock_storage.upload_file.return_value = 'http://s3.url/test.jpg'
        # El guardado en DB retorna el registro
        mock_db_save.return_value = {'evidence_id': 5, 'visit_id': 101, 'url_file': 'http://s3.url/test.jpg'}

        # 2. Preparar archivo (usando io.BytesIO para simular un archivo real)
        from io import BytesIO
        file_data = BytesIO(b"file content")
        file_data.name = 'test_photo.jpg'
        
        # 3. Llamar al endpoint con un archivo
        data = {
            'files': (file_data, 'test_photo.jpg')
        }
        resp = client.post('/offers/visits/101/evidences', data=data, content_type='multipart/form-data')

        # 4. Asertos
        assert resp.status_code == 201
        data = resp.get_json()
        assert "evidences" in data
        assert len(data['evidences']) == 1
        assert data['evidences'][0]['evidence_id'] == 5
        
        # Verificar que la lógica se ejecutó
        mock_db_get_visit.assert_called_once_with(101)
        mock_storage.upload_file.assert_called_once()
        mock_db_save.assert_called_once()


    # --- Test de Visita No Encontrada (404) ---
    @patch('src.blueprints.offers.db_get_visit_by_id')
    @patch('src.blueprints.offers.StorageService')
    def test_upload_evidences_visit_not_found(self, mock_storage, mock_db_get_visit, client):
        # 1. Configurar Mocks
        # La visita NO existe
        mock_db_get_visit.return_value = None
        
        from io import BytesIO
        file_data = BytesIO(b"file content")
        data = {'files': (file_data, 'test.jpg')}

        # 2. Llamar al endpoint para una visita inexistente
        resp = client.post('/offers/visits/999/evidences', data=data, content_type='multipart/form-data')

        # 3. Asertos
        assert resp.status_code == 404
        assert 'no existe en el sistema' in resp.get_json()['message']
        # La subida a S3 y el guardado en DB NUNCA deben ser llamados
        mock_storage.upload_file.assert_not_called()


    # --- Test de Falta de Archivos (400) ---
    @patch('src.blueprints.offers.db_get_visit_by_id')
    def test_upload_evidences_no_files(self, mock_db_get_visit, client):
        # Simular que la visita existe, aunque no debería importar si el chequeo de archivos es primero.
        mock_db_get_visit.return_value = {'visit_id': 101, 'exists': True}
        
        # Llamar al endpoint SIN archivos adjuntos
        resp = client.post('/offers/visits/101/evidences', data={}, content_type='multipart/form-data')

        # Asertos
        assert resp.status_code == 400
        assert 'No se adjuntaron archivos' in resp.get_json()['message']


    # --- Test de Error de Credenciales/S3 (500) ---
    @patch('src.blueprints.offers.db_get_visit_by_id')
    @patch('src.blueprints.offers.StorageService')
    def test_upload_evidences_storage_error(self, mock_storage, mock_db_get_visit, client):
        # La visita existe
        mock_db_get_visit.return_value = {'visit_id': 101, 'exists': True}
        # Simular el error que genera 'Unable to locate credentials'
        mock_storage.upload_file.side_effect = Exception("Unable to locate credentials")
        
        from io import BytesIO
        file_data = BytesIO(b"file content")
        data = {'files': (file_data, 'test.jpg')}

        # Llamar al endpoint
        resp = client.post('/offers/visits/101/evidences', data=data, content_type='multipart/form-data')

        # Asertos
        assert resp.status_code == 500
        assert 'Fallo en el procesamiento de la evidencia' in resp.get_json()['message']

class TestRecommendationsEndpoint:
    """Tests para el endpoint POST /offers/recommendations"""
    
    def get_valid_data(self):
        return {'client_id': 123, 'regional_setting': 'CO'}

    def test_post_recommendations_missing_client_id(self, client):
        resp = client.post('/offers/recommendations', json={'regional_setting': 'CO'})
        assert resp.status_code == 400
        assert "Falta el 'client_id'" in resp.get_json()['message']

    @patch('src.blueprints.offers.recommendation_agent')
    def test_post_recommendations_agent_failure(self, mock_agent, client):
        mock_agent.generate_recommendations.return_value = None
        resp = client.post('/offers/recommendations', json=self.get_valid_data())
        assert resp.status_code == 503
        assert "Fallo en el Agente de Razonamiento (LLM)" in resp.get_json()['message']

    @patch('src.blueprints.offers.recommendation_agent')
    def test_post_recommendations_success(self, mock_agent, client):
        mock_recommendations = [
            {"product_sku": "SKU-A", "product_name": "A", "score": 0.9, "reasoning": "Test"}
        ]
        mock_agent.generate_recommendations.return_value = {
            "recommendations": mock_recommendations
        }
        resp = client.post('/offers/recommendations', json=self.get_valid_data())
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'success'
        assert data['recommendations'][0]['product_sku'] == 'SKU-A'