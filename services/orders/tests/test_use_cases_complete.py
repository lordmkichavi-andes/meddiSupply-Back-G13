"""Tests completos para use_cases.py para aumentar cobertura."""

import unittest
import sys
from unittest.mock import Mock
from datetime import datetime, date

sys.path.append('src')

from src.application.use_cases import (
    TrackOrdersUseCase, 
    CreateOrderUseCase, 
    GetAllOrdersUseCase,
    GetClientPurchaseHistoryUseCase,
    GetOrdersByIDUseCase
)
from src.domain.entities import Order, OrderItem


class MockStatus:
    def __init__(self, name):
        self.name = name


class MockOrder:
    def __init__(self, order_id, creation_date, status_id, estimated_delivery_date=None, client_id=None, seller_id=None, order_value=0.0):
        self.order_id = order_id
        self.creation_date = creation_date
        self.status_id = status_id
        self.estimated_delivery_date = estimated_delivery_date
        self.client_id = client_id
        self.seller_id = seller_id
        self.order_value = order_value
        self.items = []

    @property
    def status(self):
        status_map = {
            1: MockStatus("En camino"),
            5: MockStatus("Procesando"),
            99: MockStatus("Entregado")
        }
        return status_map.get(self.status_id, MockStatus("Desconocido"))


class TestTrackOrdersUseCaseComplete(unittest.TestCase):
    """Tests completos para TrackOrdersUseCase."""

    def setUp(self):
        self.mock_repository = Mock()
        self.use_case = TrackOrdersUseCase(self.mock_repository)

    def test_execute_with_orders_status_1_with_date(self):
        """Test con orden status 1 (En camino) con fecha estimada."""
        orders = [
            MockOrder(
                order_id="O001",
                creation_date=datetime(2023, 10, 1, 10, 0),
                status_id=1,
                estimated_delivery_date=datetime(2023, 10, 10, 15, 30)
            )
        ]
        self.mock_repository.get_orders_by_client_id.return_value = orders
        
        result = self.use_case.execute("client_123")
        
        assert len(result) == 1
        assert result[0]['status'] == "En camino"
        assert result[0]['estimated_delivery_time'] == "2023-10-10 15:30"

    def test_execute_with_orders_status_5_without_date(self):
        """Test con orden status 5 (Procesando) sin fecha estimada."""
        orders = [
            MockOrder(
                order_id="O002",
                creation_date=datetime(2023, 10, 2, 11, 0),
                status_id=5,
                estimated_delivery_date=None
            )
        ]
        self.mock_repository.get_orders_by_client_id.return_value = orders
        
        result = self.use_case.execute("client_123")
        
        assert len(result) == 1
        assert result[0]['status'] == "Procesando"
        assert result[0]['estimated_delivery_time'] == "Entrega pendiente de programación"

    def test_execute_with_orders_status_other(self):
        """Test con orden status diferente (no 1 ni 5)."""
        orders = [
            MockOrder(
                order_id="O003",
                creation_date=datetime(2023, 10, 3, 12, 0),
                status_id=99,
                estimated_delivery_date=datetime(2023, 10, 15, 10, 0)
            )
        ]
        self.mock_repository.get_orders_by_client_id.return_value = orders
        
        result = self.use_case.execute("client_123")
        
        assert len(result) == 1
        assert result[0]['status'] == "Entregado"
        assert result[0]['estimated_delivery_time'] is None

    def test_execute_sorts_by_creation_date_desc(self):
        """Test que las órdenes se ordenan por creation_date descendente."""
        orders = [
            MockOrder("O001", datetime(2023, 10, 1), 1, None),
            MockOrder("O002", datetime(2023, 10, 3), 5, None),
            MockOrder("O003", datetime(2023, 10, 2), 99, None)
        ]
        self.mock_repository.get_orders_by_client_id.return_value = orders
        
        result = self.use_case.execute("client_123")
        
        # Debe estar ordenado por creation_date DESC
        assert result[0]['order_id'] == "O002"  # Más reciente
        assert result[1]['order_id'] == "O003"
        assert result[2]['order_id'] == "O001"  # Más antigua


class TestCreateOrderUseCase(unittest.TestCase):
    """Tests para CreateOrderUseCase."""

    def setUp(self):
        self.mock_repository = Mock()
        self.use_case = CreateOrderUseCase(self.mock_repository)

    def test_execute_calls_repository(self):
        """Test que execute llama al repositorio."""
        order = Order(
            order_id=None,
            client_id=1,
            seller_id=2,
            creation_date=datetime.now(),
            last_updated_date=datetime.now(),
            status_id=1,
            estimated_delivery_date=None,
            items=[],
            order_value=100.0
        )
        order_items = []
        products_data = []  # 👈 añadido

        mock_return_order = Order(
            order_id=123,
            client_id=1,
            seller_id=2,
            creation_date=datetime.now(),
            last_updated_date=datetime.now(),
            status_id=1,
            estimated_delivery_date=None,
            items=[],
            order_value=100.0
        )
        self.mock_repository.insert_order.return_value = mock_return_order

        # 👇 ahora pasamos products_data
        result = self.use_case.execute(order, order_items, products_data)

        # 👇 verificamos la llamada con los tres argumentos
        self.mock_repository.insert_order.assert_called_once_with(order, order_items, products_data)
        assert result.order_id == 123


class TestGetAllOrdersUseCase(unittest.TestCase):
    """Tests para GetAllOrdersUseCase."""

    def setUp(self):
        self.mock_repository = Mock()
        self.use_case = GetAllOrdersUseCase(self.mock_repository)

    def test_execute_calls_repository(self):
        """Test que execute llama al repositorio."""
        mock_orders = [{"order_id": 1, "client_id": 1}]
        self.mock_repository.get_all_orders_with_details.return_value = mock_orders
        
        result = self.use_case.execute()
        
        self.mock_repository.get_all_orders_with_details.assert_called_once()
        assert result == mock_orders


class TestGetClientPurchaseHistoryUseCase(unittest.TestCase):
    """Tests para GetClientPurchaseHistoryUseCase."""

    def setUp(self):
        self.mock_repository = Mock()
        self.use_case = GetClientPurchaseHistoryUseCase(self.mock_repository)

    def test_execute_calls_repository_with_default_limit(self):
        """Test que execute llama al repositorio con límite por defecto."""
        mock_history = [{"sku": "PROD001", "name": "Product 1"}]
        self.mock_repository.get_recent_purchase_history.return_value = mock_history
        
        result = self.use_case.execute(client_id=1)
        
        self.mock_repository.get_recent_purchase_history.assert_called_once_with(1, 10)
        assert result == mock_history

    def test_execute_calls_repository_with_custom_limit(self):
        """Test que execute llama al repositorio con límite personalizado."""
        mock_history = [{"sku": "PROD001", "name": "Product 1"}]
        self.mock_repository.get_recent_purchase_history.return_value = mock_history
        
        result = self.use_case.execute(client_id=1, limit=5)
        
        self.mock_repository.get_recent_purchase_history.assert_called_once_with(1, 5)
        assert result == mock_history


class TestGetOrdersByIDUseCase(unittest.TestCase):
    """Tests para GetOrdersByIDUseCase."""

    def setUp(self):
        self.mock_repository = Mock()
        self.use_case = GetOrdersByIDUseCase(self.mock_repository)

    def test_execute_calls_repository(self):
        """Test que execute llama al repositorio."""
        mock_order = Order(
            order_id=123,
            client_id=1,
            seller_id=2,
            creation_date=datetime.now(),
            last_updated_date=datetime.now(),
            status_id=1,
            estimated_delivery_date=None,
            items=[],
            order_value=100.0
        )
        self.mock_repository.get_order_with_details_by_id.return_value = mock_order
        
        result = self.use_case.execute(order_id=123)
        
        self.mock_repository.get_order_with_details_by_id.assert_called_once_with(123)
        assert result.order_id == 123


if __name__ == '__main__':
    unittest.main()

