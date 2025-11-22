"""Tests simples para calculate_route.py sin ortools completo."""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Mock ortools antes de importar
sys.modules['ortools'] = MagicMock()
sys.modules['ortools.constraint_solver'] = MagicMock()
sys.modules['ortools.constraint_solver.routing_enums_pb2'] = MagicMock()
sys.modules['ortools.constraint_solver.pywrapcp'] = MagicMock()

def import_from_file(module_name, file_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Importar módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Importar calculate_route
calculate_route_path = os.path.join(parent_dir, "src", "utils", "calculate_route.py")
calculate_route_module = import_from_file("calculate_route", calculate_route_path)


class TestCalculateRouteSimple:
    """Tests simples para calculate_route.py."""

    def test_haversine_distance(self):
        """Test de la función haversine_distance."""
        # Distancia entre dos puntos cercanos
        lat1, lon1 = 4.60971, -74.08175
        lat2, lon2 = 4.61000, -74.08200
        
        distance = calculate_route_module.haversine_distance(lat1, lon1, lat2, lon2)
        
        # La distancia debería ser pequeña (menos de 1 km)
        assert 0 < distance < 1

    def test_haversine_distance_same_point(self):
        """Test haversine_distance con el mismo punto."""
        lat, lon = 4.60971, -74.08175
        distance = calculate_route_module.haversine_distance(lat, lon, lat, lon)
        assert distance == 0.0

    def test_create_time_matrix_empty(self):
        """Test create_time_matrix con lista vacía."""
        result = calculate_route_module.create_time_matrix([])
        assert result == []

    def test_create_time_matrix_single_point(self):
        """Test create_time_matrix con un solo punto."""
        coordinates = [(4.60971, -74.08175)]
        result = calculate_route_module.create_time_matrix(coordinates)
        assert len(result) == 1
        assert result[0][0] == 0  # Distancia a sí mismo es 0

    def test_generate_optimized_route_empty(self):
        """Test generate_optimized_route con lista vacía."""
        result = calculate_route_module.generate_optimized_route([])
        assert result == []

    def test_generate_optimized_route_single_location(self):
        """Test generate_optimized_route con una sola ubicación."""
        locations = [{
            'id': 1,
            'name': 'Test',
            'latitude': '4.60971',
            'longitude': '-74.08175'
        }]
        result = calculate_route_module.generate_optimized_route(locations)
        assert len(result) == 1
        assert result[0]['id'] == 1

    def test_generate_optimized_route_invalid_coordinates(self):
        """Test generate_optimized_route con coordenadas inválidas."""
        locations = [{
            'id': 1,
            'name': 'Test',
            # Faltan latitude y longitude
        }]
        result = calculate_route_module.generate_optimized_route(locations)
        assert 'error' in result

    def test_generate_optimized_route_invalid_latitude(self):
        """Test generate_optimized_route con latitud inválida."""
        locations = [{
            'id': 1,
            'name': 'Test',
            'latitude': 'invalid',
            'longitude': '-74.08175'
        }]
        result = calculate_route_module.generate_optimized_route(locations)
        assert 'error' in result

    def test_generate_optimized_route_invalid_longitude(self):
        """Test generate_optimized_route con longitud inválida."""
        locations = [{
            'id': 1,
            'name': 'Test',
            'latitude': '4.60971',
            'longitude': 'invalid'
        }]
        result = calculate_route_module.generate_optimized_route(locations)
        assert 'error' in result

