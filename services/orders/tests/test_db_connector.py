import unittest
import json
from unittest.mock import Mock, patch
from flask import Flask
# Importamos la función de fábrica desde la infraestructura
from orders.src.infrastructure.web.flask_routes import create_api_blueprint

# Definición de datos de prueba
MOCK_ORDER_DATA = [
    {"id": "ORD001", "status": "En tránsito", "item": "Medicamento X"},
    {"id": "ORD002", "status": "Entregado", "item": "Suministro Y"}
]
CLIENT_ID_EXISTS = "client_123"
CLIENT_ID_NOT_FOUND = "client_404"
CLIENT_ID_ERROR = "client_error"


class TestFlaskRoutes(unittest.TestCase):
    """
    Clase para probar las rutas de Flask, asegurando que interactúan
    correctamente con el Caso de Uso (simulado con mocks).
    """

    def setUp(self):
        """
        Configura la aplicación Flask y el cliente de prueba antes de cada test.
        """
        self.app = Flask(__name__)
        self.mock_use_case = Mock()  # Creamos un mock del Caso de Uso

        # Usamos la función de fábrica para inyectar el mock en el Blueprint
        self.app.register_blueprint(create_api_blueprint(self.mock_use_case))
        self.client = self.app.test_client()

    # --- Test de la ruta /health ---
    def test_health_check(self):
        """
        Prueba que la ruta /health retorna el estado 'ok' y código 200.
        """
        print("Ejecutando test_health_check...")
        response = self.client.get('/health')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {'status': 'ok'})

    # --- Tests de la ruta /track/<client_id> ---

    def test_track_orders_success(self):
        """
        Prueba el escenario de éxito: el Caso de Uso devuelve datos.
        Debe retornar 200 y los datos de las órdenes.
        """
        print(f"Ejecutando test_track_orders_success para ID: {CLIENT_ID_EXISTS}")
        # Configurar el mock para devolver datos de prueba
        self.mock_use_case.execute.return_value = MOCK_ORDER_DATA

        response = self.client.get(f'/track/{CLIENT_ID_EXISTS}')
        response_data = json.loads(response.data)

        # 1. Verificar la llamada al Caso de Uso
        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_EXISTS)

        # 2. Verificar el código de estado y la respuesta
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, MOCK_ORDER_DATA)

    def test_track_orders_not_found(self):
        """
        Prueba el escenario "no hay pedidos": el Caso de Uso devuelve una lista vacía.
        Debe retornar 404 y un mensaje específico.
        """
        print(f"Ejecutando test_track_orders_not_found para ID: {CLIENT_ID_NOT_FOUND}")
        # Configurar el mock para devolver una lista vacía
        self.mock_use_case.execute.return_value = []

        response = self.client.get(f'/track/{CLIENT_ID_NOT_FOUND}')
        response_data = json.loads(response.data)

        # 1. Verificar la llamada al Caso de Uso
        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_NOT_FOUND)

        # 2. Verificar el código de estado y el mensaje
        self.assertEqual(response.status_code, 404)
        self.assertIn("Aún no tienes pedidos registrados", response_data['message'])
        self.assertEqual(response_data['orders'], [])

    def test_track_orders_internal_server_error(self):
        """
        Prueba el escenario de error del sistema: el Caso de Uso lanza una excepción.
        Debe retornar 500 y un mensaje de error genérico.
        """
        print(f"Ejecutando test_track_orders_internal_server_error para ID: {CLIENT_ID_ERROR}")
        # Configurar el mock para lanzar una excepción (simulando un fallo de DB, API externa, etc.)
        self.mock_use_case.execute.side_effect = Exception("Simulated DB connection error")

        response = self.client.get(f'/track/{CLIENT_ID_ERROR}')
        response_data = json.loads(response.data)

        # 1. Verificar la llamada al Caso de Uso
        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_ERROR)

        # 2. Verificar el código de estado y el mensaje
        self.assertEqual(response.status_code, 500)
        self.assertIn("No pudimos obtener los pedidos", response_data['message'])
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
