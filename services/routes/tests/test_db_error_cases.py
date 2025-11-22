"""Tests para casos de error en db.py que aumentan cobertura."""

import pytest
import sys
import os
import importlib.util
from unittest.mock import Mock, patch, MagicMock

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

# Importar db
db_path = os.path.join(parent_dir, "src", "db.py")
db_module = import_from_file("db", db_path)


class TestDbErrorCases:
    """Tests para casos de error en db.py."""

    @patch.object(db_module, 'requests')
    def test_get_clientes_http_error(self, mock_requests):
        """Test get_clientes cuando el servicio de users retorna error HTTP."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.get.return_value = mock_response
        
        result = db_module.get_clientes()
        assert result == []

    @patch.object(db_module, 'requests')
    def test_get_clientes_timeout(self, mock_requests):
        """Test get_clientes cuando hay timeout en la petición."""
        import requests
        mock_requests.get.side_effect = requests.exceptions.Timeout("Timeout")
        
        result = db_module.get_clientes()
        assert result == []

    @patch.object(db_module, 'requests')
    def test_get_clientes_connection_error(self, mock_requests):
        """Test get_clientes cuando hay error de conexión."""
        import requests
        mock_requests.get.side_effect = requests.exceptions.ConnectionError("Connection error")
        
        result = db_module.get_clientes()
        assert result == []

    @patch.object(db_module, 'requests')
    @patch.object(db_module, 'execute_query')
    def test_get_clientes_without_client_ids(self, mock_execute, mock_requests):
        """Test get_clientes cuando los usuarios no tienen client_id."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'clients': [
                {
                    'user_id': 1,
                    'name': 'Test',
                    'last_name': 'User',
                    'address': 'Test Address',
                    'latitude': '4.60971',
                    'longitude': '-74.08175'
                    # Sin client_id
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_execute.return_value = []
        
        result = db_module.get_clientes()
        assert len(result) == 1
        assert result[0]['id'] == 1  # Usa user_id cuando no hay client_id
        assert result[0]['demanda'] == 0

    @patch.object(db_module, 'requests')
    @patch.object(db_module, 'execute_query')
    def test_get_clientes_with_empty_name(self, mock_execute, mock_requests):
        """Test get_clientes cuando el nombre está vacío."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'clients': [
                {
                    'user_id': 1,
                    'client_id': 1,
                    'name': '',
                    'last_name': '',
                    'address': 'Test Address',
                    'latitude': '4.60971',
                    'longitude': '-74.08175'
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        mock_execute.return_value = []
        
        result = db_module.get_clientes()
        assert len(result) == 1
        assert result[0]['nombre'] == 'Cliente sin nombre'

    @patch.object(db_module, 'requests')
    def test_get_clientes_by_seller_http_error(self, mock_requests):
        """Test get_clientes_by_seller cuando el servicio de users retorna error HTTP."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_requests.get.return_value = mock_response
        
        result = db_module.get_clientes_by_seller(1)
        assert result == []

    @patch.object(db_module, 'requests')
    def test_get_clientes_by_seller_timeout(self, mock_requests):
        """Test get_clientes_by_seller cuando hay timeout."""
        import requests
        mock_requests.get.side_effect = requests.exceptions.Timeout("Timeout")
        
        result = db_module.get_clientes_by_seller(1)
        assert result == []

    @patch.object(db_module, 'requests')
    def test_get_clientes_by_seller_connection_error(self, mock_requests):
        """Test get_clientes_by_seller cuando hay error de conexión."""
        import requests
        mock_requests.get.side_effect = requests.exceptions.ConnectionError("Connection error")
        
        result = db_module.get_clientes_by_seller(1)
        assert result == []

    @patch.object(db_module, 'requests')
    def test_get_clientes_by_seller_empty_name(self, mock_requests):
        """Test get_clientes_by_seller cuando el nombre está vacío."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'clients': [
                {
                    'client_id': 1,
                    'name': '',
                    'address': 'Test Address',
                    'latitude': '4.60971',
                    'longitude': '-74.08175'
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        
        result = db_module.get_clientes_by_seller(1)
        assert len(result) == 1
        # get_clientes_by_seller usa directamente el valor de 'name', no aplica 'Cliente sin nombre'
        assert result[0]['name'] == ''

    @patch.object(db_module, 'execute_query')
    def test_get_vehiculos_with_none_result(self, mock_execute):
        """Test get_vehiculos cuando execute_query retorna None."""
        mock_execute.return_value = None
        
        result = db_module.get_vehiculos()
        assert result == []

    def test_get_clientes_exception(self):
        """Test get_clientes cuando ocurre una excepción general."""
        with patch.object(db_module, 'requests') as mock_requests:
            mock_requests.get.side_effect = Exception("General error")
            
            result = db_module.get_clientes()
            assert result == []

    def test_get_clientes_by_seller_exception(self):
        """Test get_clientes_by_seller cuando ocurre una excepción general."""
        with patch.object(db_module, 'requests') as mock_requests:
            mock_requests.get.side_effect = Exception("General error")
            
            result = db_module.get_clientes_by_seller(1)
            assert result == []

    def test_get_clientes_exception_in_try_block(self):
        """Test get_clientes cuando ocurre una excepción en el bloque try principal."""
        # Simular un error al acceder a os.getenv
        with patch('src.db.os.getenv', side_effect=Exception("Env error")):
            result = db_module.get_clientes()
            assert result == []

    def test_get_clientes_by_seller_exception_in_try_block(self):
        """Test get_clientes_by_seller cuando ocurre una excepción en el bloque try principal."""
        # Simular un error al acceder a os.getenv
        with patch('src.db.os.getenv', side_effect=Exception("Env error")):
            result = db_module.get_clientes_by_seller(1)
            assert result == []

