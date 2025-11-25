"""Tests completos para pg_repository.py para aumentar cobertura."""

import pytest
import psycopg2
from unittest.mock import MagicMock, patch, Mock
from datetime import datetime, date

from src.infrastructure.persistence.pg_repository import PgOrderRepository
from src.domain.entities import Order, OrderItem


@pytest.fixture
def mock_db_connection():
    """Retorna un objeto MagicMock que simula una conexión de base de datos."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn, mock_cursor


@pytest.fixture
def pg_repo_with_mocks(mock_db_connection):
    """Crea una instancia de PgOrderRepository con mocks."""
    mock_conn, mock_cursor = mock_db_connection
    
    with patch('src.infrastructure.persistence.pg_repository.get_connection', return_value=mock_conn), \
         patch('src.infrastructure.persistence.pg_repository.release_connection') as release_mock:
        repo = PgOrderRepository()
        repo.release_mock = release_mock
        repo.conn_mock = mock_conn
        repo.cursor_mock = mock_cursor
        yield repo


class TestInsertOrder:
    """Tests para insert_order."""

    def test_insert_order_success(self, pg_repo_with_mocks):
        """Test inserción exitosa de orden."""
        order = Order(
            order_id=None,
            client_id=1,
            seller_id=2,
            creation_date=datetime.now(),
            last_updated_date=datetime.now(),
            status_id=1,
            estimated_delivery_date=date(2023, 12, 25),
            items=[],
            order_value=100.0
        )
        order_items = [
            OrderItem(product_id=1, quantity=2, price_unit=50.0)
        ]
        # 👇 ahora pasamos products_data vacío o simulado
        products_data = []

        # Mock del fetchone para retornar el nuevo order_id
        pg_repo_with_mocks.cursor_mock.fetchone.return_value = (123,)

        # Mock execute_batch
        with patch('src.infrastructure.persistence.pg_repository.psycopg2.extras.execute_batch'):
            result = pg_repo_with_mocks.insert_order(order, order_items, products_data)

        assert result.order_id == 123
        assert pg_repo_with_mocks.cursor_mock.execute.call_count >= 1  # order insert
        pg_repo_with_mocks.conn_mock.commit.assert_called_once()
        pg_repo_with_mocks.release_mock.assert_called_once()


class TestGetOrdersByClientId:
    """Tests para get_orders_by_client_id."""

    def test_get_orders_by_client_id_success(self, pg_repo_with_mocks):
        """Test obtención exitosa de órdenes por cliente."""
        mock_rows = [
            (1, 1, datetime(2023, 10, 1), datetime(2023, 10, 1), date(2023, 10, 15), 1, 100.0, 2),
            (2, 1, datetime(2023, 10, 2), datetime(2023, 10, 2), None, 5, 200.0, 2)
        ]
        pg_repo_with_mocks.cursor_mock.fetchall.return_value = mock_rows
        
        result = pg_repo_with_mocks.get_orders_by_client_id(1)
        
        assert len(result) == 2
        assert result[0].order_id == 1
        assert result[1].order_id == 2
        pg_repo_with_mocks.cursor_mock.execute.assert_called_once()
        pg_repo_with_mocks.release_mock.assert_called_once()

    def test_get_orders_by_client_id_db_error(self, pg_repo_with_mocks):
        """Test obtención con error de base de datos."""
        pg_repo_with_mocks.cursor_mock.execute.side_effect = psycopg2.Error("DB Error")
        
        with pytest.raises(Exception, match="Database error during order retrieval by client"):
            pg_repo_with_mocks.get_orders_by_client_id(1)
        
        pg_repo_with_mocks.conn_mock.rollback.assert_called_once()
        pg_repo_with_mocks.release_mock.assert_called_once()


class TestGetAllOrdersWithDetails:
    """Tests para get_all_orders_with_details."""

    def test_get_all_orders_with_details_success(self, pg_repo_with_mocks):
        """Test obtención exitosa de todas las órdenes con detalles."""
        # Mock de cursor.description
        pg_repo_with_mocks.cursor_mock.description = [
            ('order_id',), ('client_id',), ('creation_date',), ('total_value',),
            ('quantity',), ('price_unit',), ('sku',), ('product_name',)
        ]
        
        mock_rows = [
            (1, 1, datetime(2023, 10, 1), 100.0, 2, 50.0, 'SKU001', 'Product 1'),
            (1, 1, datetime(2023, 10, 1), 100.0, 1, 50.0, 'SKU002', 'Product 2'),
            (2, 2, datetime(2023, 10, 2), 200.0, 3, 66.67, 'SKU003', 'Product 3')
        ]
        pg_repo_with_mocks.cursor_mock.fetchall.return_value = mock_rows
        
        result = pg_repo_with_mocks.get_all_orders_with_details()
        
        assert len(result) == 2  # 2 órdenes únicas
        assert result[0]['order_id'] == 1
        assert len(result[0]['lines']) == 2  # 2 líneas para orden 1
        assert result[1]['order_id'] == 2
        assert len(result[1]['lines']) == 1  # 1 línea para orden 2
        pg_repo_with_mocks.release_mock.assert_called_once()

    def test_get_all_orders_with_details_db_error(self, pg_repo_with_mocks):
        """Test obtención con error de base de datos."""
        pg_repo_with_mocks.cursor_mock.execute.side_effect = psycopg2.Error("DB Error")
        
        with pytest.raises(Exception):
            pg_repo_with_mocks.get_all_orders_with_details()
        
        pg_repo_with_mocks.conn_mock.rollback.assert_called_once()
        pg_repo_with_mocks.release_mock.assert_called_once()

