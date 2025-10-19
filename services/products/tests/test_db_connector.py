import pytest
import psycopg2
from unittest.mock import MagicMock, patch, sentinel

# Importamos las funciones a probar.
# NOTA: Usamos la importación completa para facilitar el mocking global de 'db_connector.db_pool'
from services.products.src.infrastructure.persistence import db_connector
from config import Config


# --- Mocks Comunes (Fixtures) ---

@pytest.fixture
def mock_config():
    """Mockea la clase Config con valores de conexión falsos."""
    with patch('src.infrastructure.persistence.db_connector.Config') as MockConfig:
        MockConfig.DB_HOST = "test_host"
        MockConfig.DB_PORT = 5432
        MockConfig.DB_NAME = "test_db"
        MockConfig.DB_USER = "test_user"
        MockConfig.DB_PASSWORD = "test_password"
        yield MockConfig


@pytest.fixture
def clean_db_pool():
    """Limpia el pool de la base de datos global antes y después de cada test."""
    original_db_pool = db_connector.db_pool
    db_connector.db_pool = None
    yield
    db_connector.db_pool = original_db_pool


# --- Tests para init_db_pool ---

@patch('src.infrastructure.persistence.db_connector.print')
@patch('src.infrastructure.persistence.db_connector.pool.SimpleConnectionPool')
def test_init_db_pool_success(MockSimpleConnectionPool, mock_print, clean_db_pool, mock_config):
    """Prueba la inicialización exitosa del pool de conexiones."""

    # Simular un pool exitoso
    mock_pool_instance = MockSimpleConnectionPool.return_value

    db_connector.init_db_pool()

    # 1. Verificar que se intentó crear el pool con la configuración correcta
    MockSimpleConnectionPool.assert_called_once_with(
        minconn=1,
        maxconn=10,
        host=mock_config.DB_HOST,
        port=mock_config.DB_PORT,
        database=mock_config.DB_NAME,
        user=mock_config.DB_USER,
        password=mock_config.DB_PASSWORD
    )

    # 2. Verificar que la variable global db_pool fue establecida
    assert db_connector.db_pool is mock_pool_instance

    # 3. Verificar el mensaje informativo
    mock_print.assert_called_with("INFO: Pool de conexiones a la base de datos inicializado.")


@patch('src.infrastructure.persistence.db_connector.print')
@patch('src.infrastructure.persistence.db_connector.pool.SimpleConnectionPool',
       side_effect=psycopg2.Error("Conexión fallida"))
def test_init_db_pool_connection_error(MockSimpleConnectionPool, mock_print, clean_db_pool, mock_config):
    """Prueba que se lance ConnectionError si falla la conexión inicial."""

    with pytest.raises(ConnectionError, match="Fallo en la conexión inicial a la base de datos."):
        db_connector.init_db_pool()

    # 1. Verificar el mensaje de error impreso
    mock_print.assert_called_with("ERROR: No se pudo conectar a la base de datos. Conexión fallida")

    # 2. Verificar que la variable global db_pool siga siendo None
    assert db_connector.db_pool is None


def test_init_db_pool_already_initialized(clean_db_pool):
    """Prueba que init_db_pool no se ejecute si ya está inicializado."""

    # Simular que ya está inicializado
    db_connector.db_pool = sentinel.ALREADY_INITIALIZED  # sentinel es un objeto único de mock

    with patch('src.infrastructure.persistence.db_connector.pool.SimpleConnectionPool') as MockPool:
        db_connector.init_db_pool()

        # Verificar que el constructor del pool NO fue llamado
        MockPool.assert_not_called()

        # Verificar que el pool sigue siendo el objeto sentinel
        assert db_connector.db_pool is sentinel.ALREADY_INITIALIZED


# --- Tests para get_connection ---

def test_get_connection_success(clean_db_pool):
    """Prueba la obtención exitosa de una conexión del pool."""

    # Simular un pool inicializado
    mock_conn = MagicMock()
    mock_pool = MagicMock()
    mock_pool.getconn.return_value = mock_conn
    db_connector.db_pool = mock_pool

    conn = db_connector.get_connection()

    # 1. Verificar que se llamó a getconn()
    mock_pool.getconn.assert_called_once()

    # 2. Verificar que se retornó la conexión mockeada
    assert conn is mock_conn


def test_get_connection_pool_not_initialized(clean_db_pool):
    """Prueba que get_connection falle si el pool no ha sido inicializado."""

    db_connector.db_pool = None

    with pytest.raises(ConnectionError, match="El pool de la base de datos no está inicializado."):
        db_connector.get_connection()


# --- Tests para release_connection ---

def test_release_connection_success(clean_db_pool):
    """Prueba que la conexión se devuelva correctamente al pool."""

    # Simular pool inicializado y una conexión para devolver
    mock_conn_to_release = MagicMock()
    mock_pool = MagicMock()
    db_connector.db_pool = mock_pool

    db_connector.release_connection(mock_conn_to_release)

    # 1. Verificar que se llamó a putconn() con la conexión correcta
    mock_pool.putconn.assert_called_once_with(mock_conn_to_release)


def test_release_connection_pool_none(clean_db_pool):
    """Prueba que no haya fallos si se llama a release_connection con db_pool = None."""

    db_connector.db_pool = None
    mock_conn_to_release = MagicMock()

    # La función debe ejecutar sin errores
    db_connector.release_connection(mock_conn_to_release)

    # No hay pool, así que no hay nada que verificar aparte de la ausencia de excepciones
    assert db_connector.db_pool is None