import pytest
from unittest.mock import patch, MagicMock
import requests


class TestProductsClient:
    """Tests para ProductsClient"""
    
    @patch('src.clients.products_client.requests.get')
    def test_get_all_active_products_success(self, mock_get):
        from src.clients.products_client import ProductsClient
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{'product_id': 1}]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        pc = ProductsClient()
        res = pc.get_all_active_products()
        assert res == [{'product_id': 1}]
        mock_get.assert_called_once()
    
    @patch('src.clients.products_client.requests.get')
    def test_get_all_active_products_empty_response(self, mock_get):
        from src.clients.products_client import ProductsClient
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        
        pc = ProductsClient()
        res = pc.get_all_active_products()
        assert res == []
    
    @patch('src.clients.products_client.requests.get')
    def test_get_all_active_products_request_exception(self, mock_get):
        from src.clients.products_client import ProductsClient
        mock_get.side_effect = requests.exceptions.RequestException('boom')
        
        pc = ProductsClient()
        res = pc.get_all_active_products()
        assert res == []
    
    @patch('src.clients.products_client.requests.get')
    def test_get_all_active_products_timeout(self, mock_get):
        from src.clients.products_client import ProductsClient
        mock_get.side_effect = requests.exceptions.Timeout('timeout')
        
        pc = ProductsClient()
        res = pc.get_all_active_products()
        assert res == []
    
    @patch('src.clients.products_client.requests.get')
    def test_get_all_active_products_http_error(self, mock_get):
        from src.clients.products_client import ProductsClient
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError('404')
        mock_get.return_value = mock_resp
        
        pc = ProductsClient()
        res = pc.get_all_active_products()
        assert res == []
    
    def test_products_client_default_url(self):
        from src.clients.products_client import ProductsClient
        pc = ProductsClient()
        assert isinstance(pc.base_url, str) and pc.base_url.startswith('http') and len(pc.base_url) > 0
        assert pc.timeout == 10
    
    def test_products_client_custom_timeout(self, monkeypatch):
        from src.clients.products_client import ProductsClient
        monkeypatch.setenv('PRODUCTS_SERVICE_TIMEOUT', '20')
        pc = ProductsClient()
        assert pc.timeout == 20

