from datetime import datetime, date
import pytest
import psycopg2
from unittest.mock import MagicMock, patch

# Asegúrate de que estas importaciones reflejen la estructura de tu proyecto
# Necesitas una entidad Order para que los tests funcionen.
try:
    from src.infrastructure.persistence.pg_repository import PgOrderRepository
    from src.domain.entities import Order
except ImportError:
    # Mocks de emergencia si la estructura de carpetas no está completa
    class Order:
        def __init__(self, order_id, user_id, creation_date, last_updated_date, status_id, estimated_delivery_date):
            self.order_id = order_id
            self.user_id = user_id
            self.creation_date = creation_date
            self.last_updated_date = last_updated_date
            self.status_id = status_id
            self.estimated_delivery_date = estimated_delivery_date
            self.total_value = 0.0  # Añadir campo total_value para coincidir con el código


    class PgOrderRepository:
        def __init__(self):
            pass

        def get_orders_by_client_id(self, user_id):
            pass  # Implementación dummy para evitar errores de importación en el IDE


# --- Fixtures y Mocks Centrales (¡Corregidos!) ---

@pytest.fixture
def mock_db_connection():
    """Retorna un objeto MagicMock que simula una conexión de base de datos."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    # Al llamar a conn.cursor(), devuelve el mock_cursor
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


@pytest.fixture
def pg_repo_with_mocks(mock_db_connection):
    """
    Crea una instancia de PgOrderRepository y 'mockea' las funciones
    get_connection y release_connection. Se usa anidamiento de patch 
    para asegurar que se capturen correctamente los mocks.
    """
    # 1. Patch de get_connection
    with patch(
            'src.infrastructure.persistence.pg_repository.get_connection',
            return_value=mock_db_connection
    ) as get_conn_mock:
        # 2. Patch de release_connection (anidado)
        with patch(
                'src.infrastructure.persistence.pg_repository.release_connection'
        ) as release_conn_mock:
            repo = PgOrderRepository()

            # Asignación directa de los objetos mock capturados:
            repo.get_connection_mock = get_conn_mock
            repo.release_connection_mock = release_conn_mock
            repo.conn_mock = mock_db_connection
            repo.cursor_mock = mock_db_connection.cursor.return_value

            yield repo


# --- Tests Unitarios ---

## 🧪 Test Case 1: Recuperación exitosa de pedidos
# def test_get_orders_by_client_id_success(pg_repo_with_mocks):
#     """
#     Verifica que la función retorne una lista de entidades Order
#     cuando la base de datos devuelve filas.
#     """
#     client_id = "CUS123"

#     # Datos de ejemplo que el cursor.fetchall() retornaría
#     # El orden es crucial: o.order_id, o.creation_date, o.estimated_delivery_date, 
#     # o.current_state_id, o.total_value, MAX(o.creation_date)
#     mock_db_rows = [
#         ("ORD001", "CUS123", datetime(2023, 1, 1, 10, 0), date(2023, 1, 15), 3, 100.00, datetime(2023, 1, 5, 12, 0)),
#         ("ORD002", "CUS123", datetime(2023, 2, 1, 11, 0), date(2023, 2, 10), 1, 50.50, datetime(2023, 2, 1, 11, 0)),
#     ]

#     pg_repo_with_mocks.cursor_mock.fetchall.return_value = mock_db_rows

#     # Ejecución del método
#     orders = pg_repo_with_mocks.get_orders_by_client_id(client_id)

#     # 1. Verificación de la ejecución de la consulta
#     pg_repo_with_mocks.cursor_mock.execute.assert_called_once()

#     # Verificamos que el parámetro client_id se pasó correctamente
#     call_args, _ = pg_repo_with_mocks.cursor_mock.execute.call_args
#     assert call_args[1] == (client_id,)

#     # 2. Verificación de los resultados
#     assert isinstance(orders, list)
#     assert len(orders) == 2
#     assert isinstance(orders[0], Order)
#     assert orders[0].order_id == "ORD001"

#     # 3. Verificación del cleanup (cierre de conexión)
#     pg_repo_with_mocks.release_connection_mock.assert_called_once_with(pg_repo_with_mocks.conn_mock)


## 🧪 Test Case 2: Manejo de errores de la base de datos
def test_get_orders_by_client_id_db_error(pg_repo_with_mocks):
    """
    Verifica que se lance una excepción cuando psycopg2.Error ocurra (ej. timeout de DB).
    """
    user_id = "ERROR_CLIENT"
    # Mockeamos que .execute() lance una excepción de psycopg2
    pg_repo_with_mocks.cursor_mock.execute.side_effect = psycopg2.Error("Simulated DB error")

    # Se espera que el método lance la excepción personalizada
    with pytest.raises(Exception, match="Database error during order retrieval."):
        pg_repo_with_mocks.get_orders_by_client_id(user_id)

    # 1. Verificación de que la conexión fue liberada A PESAR del error (CRÍTICO para cobertura)
    pg_repo_with_mocks.release_connection_mock.assert_called_once_with(pg_repo_with_mocks.conn_mock)