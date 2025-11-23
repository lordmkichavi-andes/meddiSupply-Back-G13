"""Tests simples para endpoints usando Flask test client."""

import pytest
import sys
import os
from unittest.mock import patch, Mock, MagicMock

# Mock ortools antes de importar cualquier cosa que lo use
sys.modules['ortools'] = MagicMock()
sys.modules['ortools.constraint_solver'] = MagicMock()
sys.modules['ortools.constraint_solver.routing_enums_pb2'] = MagicMock()
sys.modules['ortools.constraint_solver.pywrapcp'] = MagicMock()

# Agregar el directorio src al path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, "src")
sys.path.insert(0, parent_dir)
sys.path.insert(0, src_dir)

# Importar después de agregar al path
from flask import Flask
from src.blueprints.routes import routes_bp


class TestEndpointsSimple:
    """Tests simples para endpoints."""

    def setup_method(self):
        """Configurar app Flask para cada test."""
        self.app = Flask(__name__)
        self.app.register_blueprint(routes_bp)
        self.client = self.app.test_client()

    @patch('src.blueprints.routes.get_vehiculos')
    def test_get_vehicles_success(self, mock_get_vehiculos):
        """Test exitoso de /vehicles."""
        mock_get_vehiculos.return_value = [
            {'vehicle_id': 1, 'capacity': 100, 'color': 'red', 'label': 'Truck 1'}
        ]
        
        response = self.client.get('/vehicles')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        # Vehiculo.to_dict() devuelve 'id', 'capacidad', 'color', 'etiqueta'
        assert data[0]['id'] == 1

    @patch('src.blueprints.routes.get_vehiculos')
    def test_get_vehicles_error(self, mock_get_vehiculos):
        """Test de /vehicles con error."""
        mock_get_vehiculos.side_effect = Exception("Database error")
        
        response = self.client.get('/vehicles')
        assert response.status_code == 500
        data = response.get_json()
        assert 'Error obteniendo vehículos' in data['message']

    @patch('src.blueprints.routes.get_clientes')
    def test_get_clients_success(self, mock_get_clientes):
        """Test exitoso de /clients."""
        mock_get_clientes.return_value = [
            {
                'id': 1,
                'nombre': 'Test Client',
                'direccion': 'Test Address',
                'latitud': 4.60971,
                'longitud': -74.08175,
                'demanda': 10
            }
        ]
        
        response = self.client.get('/clients')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]['id'] == 1

    @patch('src.blueprints.routes.get_clientes')
    def test_get_clients_error(self, mock_get_clientes):
        """Test de /clients con error."""
        mock_get_clientes.side_effect = Exception("Database error")
        
        response = self.client.get('/clients')
        assert response.status_code == 500
        data = response.get_json()
        assert 'Error obteniendo clientes' in data['message']

    def test_health_endpoint(self):
        """Test del endpoint /health."""
        response = self.client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'ok'

    @patch('src.blueprints.routes.get_clientes_by_seller')
    @patch('src.blueprints.routes.generate_optimized_route')
    def test_get_seller_routes_success(self, mock_generate_route, mock_get_clientes):
        """Test exitoso de /seller/<seller_ID>."""
        mock_get_clientes.return_value = [
            {
                'id': 1,
                'name': 'Client 1',
                'client': 'Client 1',
                'address': 'Address 1',
                'latitude': '4.60971',
                'longitude': '-74.08175'
            },
            {
                'id': 2,
                'name': 'Client 2',
                'client': 'Client 2',
                'address': 'Address 2',
                'latitude': '4.61000',
                'longitude': '-74.08200'
            },
            {
                'id': 3,
                'name': 'Client 3',
                'client': 'Client 3',
                'address': 'Address 3',
                'latitude': '4.61100',
                'longitude': '-74.08300'
            },
            {
                'id': 4,
                'name': 'Client 4',
                'client': 'Client 4',
                'address': 'Address 4',
                'latitude': '4.61200',
                'longitude': '-74.08400'
            }
        ]
        mock_generate_route.return_value = [
            {'id': 1, 'name': 'Client 1', 'latitude': '4.60971', 'longitude': '-74.08175'},
            {'id': 2, 'name': 'Client 2', 'latitude': '4.61000', 'longitude': '-74.08200'},
            {'id': 3, 'name': 'Client 3', 'latitude': '4.61100', 'longitude': '-74.08300'},
            {'id': 4, 'name': 'Client 4', 'latitude': '4.61200', 'longitude': '-74.08400'}
        ]
        
        response = self.client.get('/seller/1')
        assert response.status_code == 200
        data = response.get_json()
        assert 'visits' in data
        assert 'number_visits' in data

    @patch('src.blueprints.routes.get_clientes_by_seller')
    @patch('src.blueprints.routes.generate_optimized_route')
    def test_get_seller_routes_less_than_4(self, mock_generate_route, mock_get_clientes):
        """Test de /seller/<seller_ID> con menos de 4 clientes."""
        mock_get_clientes.return_value = [
            {
                'id': 1,
                'name': 'Client 1',
                'client': 'Client 1',
                'address': 'Address 1',
                'latitude': '4.60971',
                'longitude': '-74.08175'
            }
        ]
        mock_generate_route.return_value = [
            {'id': 1, 'name': 'Client 1', 'latitude': '4.60971', 'longitude': '-74.08175'}
        ]
        
        response = self.client.get('/seller/1')
        assert response.status_code == 200
        data = response.get_json()
        assert 'visits' in data

    @patch('src.blueprints.routes.get_clientes_by_seller')
    @patch('src.blueprints.routes.generate_optimized_route')
    def test_get_seller_routes_with_error(self, mock_generate_route, mock_get_clientes):
        """Test de /seller/<seller_ID> cuando generate_optimized_route retorna error."""
        mock_get_clientes.return_value = [
            {
                'id': 1,
                'name': 'Client 1',
                'client': 'Client 1',
                'address': 'Address 1',
                'latitude': '4.60971',
                'longitude': '-74.08175'
            }
        ]
        mock_generate_route.return_value = {'error': 'Solver error'}
        
        response = self.client.get('/seller/1')
        assert response.status_code == 500
        data = response.get_json()
        assert 'visits' in data

