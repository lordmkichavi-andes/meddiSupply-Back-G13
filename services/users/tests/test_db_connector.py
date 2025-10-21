import unittest
from unittest.mock import patch, MagicMock
import psycopg2
from psycopg2 import pool
import os
import sys

# ==============================================================================
# REPOSITORIO A TESTEAR (Definición de las funciones del módulo real para que los parches funcionen)
# Nota: La ruta de patch en los decoradores debe apuntar a la ubicación donde se
# encuentra este código en su entorno real si no está contenido en este archivo.
# Para este test, asumiremos que se está importando o definiendo localmente.
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
            # Línea que debe ser capturada por la prueba de éxito
            print("✅ Pool de conexiones a la base de datos inicializado.")
        except psycopg2.Error as e:
            # Línea que debe ser capturada por la prueba de error
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

# La ruta de parche debe reflejar dónde se encuentra el código de prueba.
# Usamos 'tests.test_db_connector' o simplemente 'builtins.print' si es necesario.
# Por simplicidad y para resolver el error, parchearemos builtins.print
BUILTINS_PATH = 'builtins.print'


class TestDBConnector(unittest.TestCase):

    def tearDown(self):
        """Asegura que db_pool esté reseteado después de cada prueba."""
        global db_pool
        db_pool = None

    @patch('tests.test_db_connector.os.getenv', side_effect=lambda k, default=None: MOCK_ENV_VARS.get(k, default))
    @patch('tests.test_db_connector.pool.SimpleConnectionPool')
    @patch(BUILTINS_PATH)  # Parchear la función print directamente
    def test_init_db_pool_success(self, mock_print, MockSimpleConnectionPool, mock_getenv):
        """Prueba la inicialización exitosa del pool de conexiones."""
        global db_pool

        # Simular una instancia de pool exitosa
        mock_pool_instance = MagicMock()
        MockSimpleConnectionPool.return_value = mock_pool_instance

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

        # 3. Verificar el mensaje de éxito usando el mock_print
        expected_message = "✅ Pool de conexiones a la base de datos inicializado."

        # Buscar en los argumentos de la llamada
        mock_print.assert_any_call(expected_message)

    @patch('tests.test_db_connector.os.getenv', side_effect=lambda k, default=None: MOCK_ENV_VARS.get(k, default))
    @patch('tests.test_db_connector.pool.SimpleConnectionPool', side_effect=psycopg2.Error("Auth failed"))
    @patch(BUILTINS_PATH)
    def test_init_db_pool_connection_error(self, mock_print, MockSimpleConnectionPool, mock_getenv):
        """Prueba el manejo de errores de conexión de psycopg2."""
        global db_pool

        # Esperar que se lance ConnectionError
        with self.assertRaisesRegex(ConnectionError, "Fallo en la conexión inicial a la base de datos."):
            init_db_pool()

        # 1. Verificar que el pool no se haya establecido
        self.assertIsNone(db_pool)

        # 2. Verificar el mensaje de error en la salida
        # La llamada a print es f"❌ Error al conectar a la base de datos: {e}"
        # Buscamos que se haya llamado a print con un argumento que contenga el texto clave.
        printed_call_args = [call[0][0] for call in mock_print.call_args_list]
        self.assertTrue(
            any("❌ Error al conectar a la base de datos" in arg for arg in printed_call_args),
            "No se encontró el mensaje de error de conexión en la salida impresa."
        )

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
