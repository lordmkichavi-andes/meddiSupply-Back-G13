from datetime import datetime
import pytest
import psycopg2
from unittest.mock import MagicMock, patch

# Asegúrate de que estas importaciones reflejen la estructura de tu microservicio 'products'
try:
    from src.infrastructure.persistence.pg_product_repository import PgProductRepository
    from src.domain.entities import Product
except ImportError:
    # Mocks de emergencia si la estructura de carpetas no está completa
    class Product:
        def __init__(self, product_id, name, price, stock, is_active=True):
            self.product_id = product_id
            self.name = name
            self.price = price
            self.stock = stock
            self.is_active = is_active
            # Añadir campo adicional si tu DB lo retorna (e.g., last_updated)
            self.last_updated_date = datetime.now() 


    class PgProductRepository:
        def __init__(self):
            pass

        def get_product_by_id(self, product_id):
            pass


# --- Fixtures y Mocks Centrales ---

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
    Crea una instancia de PgProductRepository y 'mockea' las funciones
    get_connection y release_connection.
    """
    # 1. Patch de get_connection (asumimos que está en db_connector o similar)
    with patch(
            'src.infrastructure.persistence.pg_product_repository.get_connection',
            return_value=mock_db_connection
    ) as get_conn_mock:
        # 2. Patch de release_connection (anidado)
        with patch(
                'src.infrastructure.persistence.pg_product_repository.release_connection'
        ) as release_conn_mock:
            repo = PgProductRepository()

            # Asignación directa de los objetos mock capturados:
            repo.get_connection_mock = get_conn_mock
            repo.release_connection_mock = release_conn_mock
            repo.conn_mock = mock_db_connection
            repo.cursor_mock = mock_db_connection.cursor.return_value

            yield repo