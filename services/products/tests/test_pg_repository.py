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


# --- Tests Unitarios ---

## 🧪 Test Case 1: Recuperación exitosa de un producto por ID
# def test_get_product_by_id_success(pg_repo_with_mocks):
#     """
#     Verifica que la función retorne una entidad Product
#     cuando la base de datos devuelve una fila.
#     """
#     product_id = "PROD001"
    
#     # Datos de ejemplo que el cursor.fetchone() retornaría
#     # Orden: product_id, name, price, stock, is_active, last_updated_date
#     mock_db_row = ("PROD001", "Laptop Pro", 1200.50, 50, True, datetime(2024, 1, 1))

#     # Mockeamos fetchone ya que usualmente solo buscamos un registro
#     pg_repo_with_mocks.cursor_mock.fetchone.return_value = mock_db_row

#     # Ejecución del método
#     product = pg_repo_with_mocks.get_product_by_id(product_id)

#     # 1. Verificación de la ejecución de la consulta
#     pg_repo_with_mocks.cursor_mock.execute.assert_called_once()

#     # Verificamos que el parámetro product_id se pasó correctamente
#     call_args, _ = pg_repo_with_mocks.cursor_mock.execute.call_args
#     assert call_args[1] == (product_id,)

#     # 2. Verificación del resultado
#     assert isinstance(product, Product)
#     assert product.product_id == "PROD001"
#     assert product.name == "Laptop Pro"
#     assert product.price == 1200.50

#     # 3. Verificación del cleanup (cierre de conexión)
#     pg_repo_with_mocks.release_connection_mock.assert_called_once_with(pg_repo_with_mocks.conn_mock)


## 🧪 Test Case 2: Producto no encontrado (None)
def test_get_product_by_id_not_found(pg_repo_with_mocks):
    """
    Verifica que la función retorne None cuando el producto no se encuentra.
    """
    product_id = "PROD999"
    # Mockeamos fetchone para que devuelva None (no hay resultado)
    pg_repo_with_mocks.cursor_mock.fetchone.return_value = None 

    # Ejecución del método
    product = pg_repo_with_mocks.get_product_by_id(product_id)

    # 1. Verificación del resultado
    assert product is None

    # 2. Verificación del cleanup
    pg_repo_with_mocks.release_connection_mock.assert_called_once_with(pg_repo_with_mocks.conn_mock)


## 🧪 Test Case 3: Manejo de errores de la base de datos
def test_get_product_by_id_db_error(pg_repo_with_mocks):
    """
    Verifica que se lance una excepción cuando psycopg2.Error ocurra.
    """
    product_id = "ERROR_PROD"
    # Mockeamos que .execute() lance una excepción de psycopg2
    pg_repo_with_mocks.cursor_mock.execute.side_effect = psycopg2.Error("Simulated DB error")

    # Se espera que el método lance una excepción (debes adaptarla si tienes una excepción personalizada)
    with pytest.raises(Exception, match="Simulated DB error"):
        pg_repo_with_mocks.get_product_by_id(product_id)

    # Verificación de que la conexión fue liberada A PESAR del error (CRÍTICO para cobertura)
    pg_repo_with_mocks.release_connection_mock.assert_called_once_with(pg_repo_with_mocks.conn_mock)