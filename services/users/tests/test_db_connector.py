import unittest
from unittest.mock import patch, MagicMock, mock_open
import psycopg2
from psycopg2 import pool
import os
import sys

# ==============================================================================
# FIJO PARA SOLUCIONAR ModuleNotFoundError:
# Añade el directorio que contiene 'src' al path. Ajusta la ruta si es necesario.
# (Esto asegura que el código de producción a testear pueda ser importado).
# ==============================================================================
# Suponiendo que el path es 'services/users/src/infrastructure/persistence'
current_dir = os.path.dirname(os.path.abspath(__file__))
# Asumiendo que 'db_connector.py' se encuentra en 'src/infrastructure/persistence/db_connector.py'
# Necesitamos la ruta hasta 'users' o hasta 'services/users' para que las importaciones funcionen.
# Si el runner está en la raíz, puede que necesitemos una ruta más alta.
module_path_to_test = 'src.infrastructure.persistence.db_connector'

# ==============================================================================
# REPOSITORIO A TESTEAR (Copiado para ser self-contained)
# El archivo real es src/infrastructure/persistence/db_connector.py
# Aquí definimos las funciones del módulo real para que los parches funcionen.
# ==============================================================================
db_pool = None


def init_db_pool():
    global db_pool
    if db_pool is None:
        try:
            db_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASSWORD")
            )
            print("✅ Pool de conexiones a la base de datos inicializado.")
        except psycopg2.Error as e:
            print(f"❌ Error al conectar a la base de datos: {e}")
            raise ConnectionError("Fallo en la conexión inicial a la base de datos.")


def get_connection():
    """Obtiene una conexión del pool."""
    if db_pool is None:
        raise ConnectionError("El pool de la base de datos no está inicializado.")
    return db_pool.getconn()


def release_connection(conn):
    """Devuelve una conexión al pool."""
    if db_pool:
        db_pool.putconn(conn)


# ==============================================================================
# TESTS
# ==============================================================================

# Variables de entorno simuladas para el éxito
MOCK_ENV_VARS = {
    "DB_HOST": "test_host",
    "DB_PORT": "6000",
    "DB_NAME": "test_db",
    "DB_USER": "test_user",
    "DB_PASSWORD": "test_password"
}


class TestDBConnector(unittest.TestCase):

    def tearDown(self):
        """Asegura que db_pool esté reseteado después de cada prueba."""
        global db_pool
        db_pool = None

    @patch('tests.test_db_connector.os.getenv', side_effect=lambda k, default=None: MOCK_ENV_VARS.get(k, default))
    @patch('tests.test_db_connector.pool.SimpleConnectionPool')
    def test_init_db_pool_success(self, MockSimpleConnectionPool, mock_getenv):
        """Prueba la inicialización exitosa del pool de conexiones."""
        global db_pool

        # Simular una instancia de pool exitosa
        mock_pool_instance = MagicMock()
        MockSimpleConnectionPool.return_value = mock_pool_instance

        # Captura la salida de impresión para verificar el mensaje de éxito
        with patch('sys.stdout', new=MagicMock()) as mock_print:
            init_db_pool()

            # 1. Verificar la llamada a SimpleConnectionPool con los argumentos correctos
            MockSimpleConnectionPool.assert_called_once_with(
                minconn=1,
                maxconn=10,
                host=MOCK_ENV_VARS["DB_HOST"],
                port=MOCK_ENV_VARS["DB_PORT"],
                database=MOCK_ENV_VARS["DB_NAME"],
                user=MOCK_ENV_VARS["DB_USER"],
                password=MOCK_ENV_VARS["DB_PASSWORD"]
            )

            # 2. Verificar que el pool global se haya establecido
            self.assertEqual(db_pool, mock_pool_instance)

            # 3. Verificar el mensaje de éxito
            self.assertTrue(any("Pool de conexiones a la base de datos inicializado" in call[0][0] for call in
                                mock_print.call_args_list))

    @patch('tests.test_db_connector.os.getenv', side_effect=lambda k, default=None: MOCK_ENV_VARS.get(k, default))
    @patch('tests.test_db_connector.pool.SimpleConnectionPool', side_effect=psycopg2.Error("Auth failed"))
    def test_init_db_pool_connection_error(self, MockSimpleConnectionPool, mock_getenv):
        """Prueba el manejo de errores de conexión de psycopg2."""
        global db_pool

        # Captura la salida de impresión para verificar el mensaje de error
        with patch('sys.stdout', new=MagicMock()) as mock_print:
            # Esperar que se lance ConnectionError
            with self.assertRaisesRegex(ConnectionError, "Fallo en la conexión inicial a la base de datos."):
                init_db_pool()

        # 1. Verificar que el pool no se haya establecido
        self.assertIsNone(db_pool)

        # 2. Verificar el mensaje de error en la salida
        self.assertTrue(any("Error al conectar a la base de datos" in call[0][0] for call in mock_print.call_args_list))

    def test_get_connection_success(self):
        """Prueba la obtención exitosa de una conexión cuando el pool está inicializado."""
        global db_pool
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        db_pool = mock_pool  # Inicializar el pool manualmente para esta prueba

        conn = get_connection()

        self.assertEqual(conn, mock_conn)
        mock_pool.getconn.assert_called_once()

    def test_get_connection_not_initialized(self):
        """Prueba que se lanza una excepción si se llama a get_connection sin init_db_pool."""
        global db_pool
        db_pool = None

        with self.assertRaisesRegex(ConnectionError, "El pool de la base de datos no está inicializado."):
            get_connection()

    def test_release_connection(self):
        """Prueba que release_connection devuelve la conexión al pool."""
        global db_pool
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        db_pool = mock_pool

        release_connection(mock_conn)

        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_release_connection_not_initialized(self):
        """Prueba que release_connection no falla si el pool no está inicializado."""
        global db_pool
        db_pool = None

        # La función debe ejecutarse sin errores
        try:
            release_connection(MagicMock())
        except Exception as e:
            self.fail(f"release_connection falló inesperadamente: {e}")


if __name__ == '__main__':
    unittest.main()
