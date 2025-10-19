# tests/infrastructure/persistence/test_pg_repository.py

from datetime import datetime, date
import pytest
from unittest.mock import MagicMock, patch

# Asegúrate de que estas importaciones reflejen la estructura de tu proyecto
from src.infrastructure.persistence.pg_repository import PgOrderRepository
from src.domain.entities import Order


# --- Fixtures y Mocks Centrales ---

# Mock de la Entidad Order para asegurar que existe para las pruebas
class MockOrder(Order):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# Mock de la conexión y del cursor de psycopg2
@pytest.fixture
def mock_db_connection():
    """Retorna un objeto MagicMock que simula una conexión de base de datos."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


@pytest.fixture
def pg_repo_with_mocks(mock_db_connection):
    """
    Crea una instancia de PgOrderRepository y 'mockea' las funciones
    get_connection y release_connection.
    """
    # Usamos patch.multiple para simular ambas funciones
    with patch.multiple(
            'src.infrastructure.persistence.pg_repository',
            get_connection=MagicMock(return_value=mock_db_connection),
            release_connection=MagicMock()
    ) as mocks:
        repo = PgOrderRepository()
        repo.get_connection_mock = mocks['get_connection']
        repo.release_connection_mock = mocks['release_connection']
        repo.conn_mock = mock_db_connection
        repo.cursor_mock = mock_db_connection.cursor.return_value
        yield repo


# --- Tests Unitarios ---

## 🧪 Test Case 1: Recuperación exitosa de pedidos
def test_get_orders_by_client_id_success(pg_repo_with_mocks):
    """
    Verifica que la función retorne una lista de entidades Order
    cuando la base de datos devuelve filas.
    """
    client_id = "CUS123"

    # Datos de ejemplo que el cursor.fetchall() retornaría
    mock_db_rows = [
        # (order_id, creation_date, estimated_delivery_date, status_id, total_value, last_updated_date)
        ("ORD001", datetime(2023, 1, 1, 10, 0), date(2023, 1, 15), 3, 100.00, datetime(2023, 1, 5, 12, 0)),
        ("ORD002", datetime(2023, 2, 1, 11, 0), date(2023, 2, 10), 1, 50.50, datetime(2023, 2, 1, 11, 0)),
    ]

    pg_repo_with_mocks.cursor_mock.fetchall.return_value = mock_db_rows

    # Ejecución del método
    orders = pg_repo_with_mocks.get_orders_by_client_id(client_id)

    # 1. Verificación de la ejecución de la consulta
    pg_repo_with_mocks.cursor_mock.execute.assert_called_once()

    # Verificamos que el parámetro client_id se pasó correctamente a la consulta
    call_args, call_kwargs = pg_repo_with_mocks.cursor_mock.execute.call_args
    assert call_args[1] == (client_id,)

    # 2. Verificación de los resultados
    assert isinstance(orders, list)
    assert len(orders) == 2
    assert isinstance(orders[0], Order)
    assert orders[0].order_id == "ORD001"
    assert orders[1].total_value == 50.50

    # 3. Verificación del cleanup (cierre de conexión)
    pg_repo_with_mocks.release_connection_mock.assert_called_once_with(pg_repo_with_mocks.conn_mock)


## 🧪 Test Case 2: No hay pedidos para el cliente
def test_get_orders_by_client_id_empty(pg_repo_with_mocks):
    """
    Verifica que la función retorne una lista vacía si no se encuentran pedidos.
    """
    client_id = "CUS999"
    pg_repo_with_mocks.cursor_mock.fetchall.return_value = []

    orders = pg_repo_with_mocks.get_orders_by_client_id(client_id)

    # 1. Verificación de los resultados
    assert orders == []

    # 2. Verificación del cleanup (cierre de conexión)
    pg_repo_with_mocks.release_connection_mock.assert_called_once()


## 🧪 Test Case 3: Manejo de errores de la base de datos
def test_get_orders_by_client_id_db_error(pg_repo_with_mocks):
    """
    Verifica que se lance una excepción cuando psycopg2.Error ocurra (ej. timeout de DB).
    """
    client_id = "ERROR_CLIENT"
    # Mockeamos que .execute() lance una excepción de psycopg2
    pg_repo_with_mocks.cursor_mock.execute.side_effect = psycopg2.Error("Simulated DB error")

    # Se espera que el método lance la excepción personalizada
    with pytest.raises(Exception, match="Database error during order retrieval."):
        pg_repo_with_mocks.get_orders_by_client_id(client_id)

    # 1. Verificación de que la conexión fue liberada A PESAR del error
    pg_repo_with_mocks.release_connection_mock.assert_called_once_with(pg_repo_with_mocks.conn_mock)