import pytest
import json
from app import app

@pytest.fixture
def client():
    """Crear cliente de prueba para la aplicación Flask"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_endpoint(client):
    """Probar endpoint home"""
    response = client.get('/')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert 'mensaje' in data
    assert 'version' in data
    assert 'endpoints_disponibles' in data

def test_datos_endpoint_post(client):
    """Probar endpoint de datos con POST"""
    response = client.post('/datos')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'datos' in data
    assert 'usuarios' in data['datos']
    assert 'productos' in data['datos']
    assert 'estadisticas' in data['datos']

def test_usuarios_endpoint_post(client):
    """Probar endpoint de usuarios con POST"""
    response = client.post('/usuarios')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'usuarios' in data
    assert isinstance(data['usuarios'], list)
    assert len(data['usuarios']) > 0

def test_productos_endpoint_post(client):
    """Probar endpoint de productos con POST"""
    response = client.post('/productos')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] == True
    assert 'productos' in data
    assert isinstance(data['productos'], list)
    assert len(data['productos']) > 0

def test_endpoints_with_json_data(client):
    """Probar endpoints enviando datos JSON"""
    test_data = {"test": "data", "id": 123}
    
    # Probar /datos con datos JSON
    response = client.post('/datos', 
                          data=json.dumps(test_data),
                          content_type='application/json')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] == True
    assert data['peticion_recibida'] == test_data

def test_invalid_endpoint(client):
    """Probar endpoint que no existe"""
    response = client.get('/endpoint-que-no-existe')
    assert response.status_code == 404

def test_usuarios_endpoint_with_json(client):
    """Probar endpoint usuarios con datos JSON"""
    test_data = {"filter": "active", "limit": 10}
    response = client.post('/usuarios', 
                          data=json.dumps(test_data),
                          content_type='application/json')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] == True

def test_productos_endpoint_with_json(client):
    """Probar endpoint productos con datos JSON"""
    test_data = {"category": "electronics", "sort": "price"}
    response = client.post('/productos', 
                          data=json.dumps(test_data),
                          content_type='application/json')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] == True

def test_datos_endpoint_error_handling(client):
    """Probar manejo de errores en endpoint datos"""
    # Test normal que debería pasar
    response = client.post('/datos')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['success'] == True

def test_health_check_endpoint(client):
    """Probar endpoint de health check"""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert data['service'] == 'usuarios'
    assert data['version'] == '2.1.1'
    assert 'timestamp' in data
    assert 'checks' in data
    assert 'ci_cd' in data
    assert data['ci_cd']['pipeline'] == 'active'

def test_health_check_structure(client):
    """Probar estructura completa del health check"""
    response = client.get('/health')
    data = json.loads(response.data)
    
    # Verificar estructura de checks
    assert data['checks']['database'] == 'ok'
    assert data['checks']['memory'] == 'ok'
    assert data['checks']['cpu'] == 'ok'
    
    # Verificar estructura de ci_cd
    assert data['ci_cd']['last_deploy'] == 'ci-cd-test'
    assert data['ci_cd']['environment'] == 'production-ready'

def test_home_endpoint_new_version(client):
    """Probar que el endpoint home muestra la nueva versión"""
    response = client.get('/')
    data = json.loads(response.data)
    
    assert data['version'] == '2.1.1'
    assert 'Workflow Optimizado - Prueba Final' in data['mensaje']
    assert any('health' in endpoint for endpoint in data['endpoints_disponibles'])
    assert data['microservicio'] == 'usuarios'
    assert data['cluster'] == 'microservices-cluster'

def test_main_execution():
    """Probar que el archivo app.py se puede ejecutar"""
    import app
    # Verificar que la app se inicializa correctamente
    assert app.app is not None
    assert app.app.name == 'app'

if __name__ == '__main__':
    pytest.main([__file__])
