import unittest
from unittest.mock import patch, MagicMock
import psycopg2
import os

# Asegúrate de importar las funciones del archivo que vamos a testear
from db_manager import init_db_pool, get_connection, release_connection, db_pool

# Definimos la ruta donde se encuentra el objeto psycopg2.pool.SimpleConnectionPool
# que necesitamos simular. Como se usa directamente en db_manager.py, la ruta es 'db_manager.psycopg2.pool'.
PSQL_POOL_PATH = 'db_manager.pool.SimpleConnectionPool'
PSQL_ERROR_PATH = 'db_manager.psycopg2.Error'


class DBManagerTestCase(unittest.TestCase):

    def setUp(self):
        """
        Reinicia la variable global db_pool antes de cada test para asegurar el aislamiento.
        """
        global db_pool
        db_pool = None

    def tearDown(self):
        """
        Limpia la variable global db_pool después de cada test.
        """
        global db_pool
        db_pool = None

    ## ----------------------------------------------------------------------
    ## Tests para init_db_pool()
    ## ----------------------------------------------------------------------

    @patch('db_manager.os.getenv')
    @patch(PSQL_POOL_PATH)
    def test_init_db_pool_success(self, MockSimpleConnectionPool, mock_getenv):
        """Prueba que el pool se inicializa exitosamente con variables de entorno."""

        # 1. Configurar los mocks de entorno
        mock_getenv.side_effect = lambda key, default: {
            "DB_HOST": "test_host",
            "DB_PORT": "6000",
            "DB_NAME": "test_db",
            "DB_USER": "test_user",
            "DB_PASSWORD": "test_password"
        }.get(key, default)

        # 2. Ejecutar la función
        init_db_pool()

        # 3. Asertar: El pool global debe estar inicializado con la instancia Mock
        self.assertIsNotNone(db_pool)
        self.assertEqual(db_pool, MockSimpleConnectionPool.return_value)

        # 4. Asertar: Se llamó al constructor con los argumentos correctos
        MockSimpleConnectionPool.assert_called_once_with(
            minconn=1,
            maxconn=10,
            host="test_host",
            port="6000",
            database="test_db",
            user="test_user",
            password="test_password"
        )

    @patch(PSQL_POOL_PATH)
    def test_init_db_pool_uses_default_values(self, MockSimpleConnectionPool):
        """Prueba que el pool usa los valores por defecto si las variables de entorno no existen."""
        # Al no mockear os.getenv, automáticamente usará los valores por defecto (localhost, 5432, postgres, etc.)

        init_db_pool()

        # Asertar: Se llamó al constructor con los valores por defecto
        MockSimpleConnectionPool.assert_called_once_with(
            minconn=1,
            maxconn=10,
            host="localhost",  # Valor por defecto
            port="5432",  # Valor por defecto
            database="postgres",
            user="postgres",
            password="postgres"
        )

    @patch(PSQL_POOL_PATH, side_effect=psycopg2.Error("Simulated DB Error"))
    @patch(PSQL_ERROR_PATH, psycopg2.Error)
    def test_init_db_pool_connection_error(self, MockPsycopg2Error, MockSimpleConnectionPool):
        """Prueba que se lanza ConnectionError si falla la conexión inicial."""

        # Asertar: La función levanta una excepción ConnectionError
        with self.assertRaisesRegex(ConnectionError, "Fallo en la conexión inicial a la base de datos."):
            init_db_pool()

        # Asertar: El pool no se inicializó
        self.assertIsNone(db_pool)

        # Asertar: Se intentó llamar al constructor del pool
        MockSimpleConnectionPool.assert_called_once()

    ## ----------------------------------------------------------------------
    ## Tests para get_connection()
    ## ----------------------------------------------------------------------

    def test_get_connection_pool_not_initialized(self):
        """Prueba que lanza error si el pool global es None."""

        # La variable db_pool es None por el setUp
        with self.assertRaisesRegex(ConnectionError, "El pool de la base de datos no está inicializado."):
            get_connection()

    @patch('db_manager.db_pool')
    def test_get_connection_success(self, MockDBPool):
        """Prueba que se llama correctamente al método getconn() del pool."""

        # 1. Configurar el pool simulado
        mock_conn = MagicMock()
        MockDBPool.getconn.return_value = mock_conn

        # 2. Ejecutar la función (db_manager.db_pool será reemplazado por MockDBPool)
        connection = get_connection()

        # 3. Asertar: Se obtuvo la conexión simulada
        self.assertEqual(connection, mock_conn)

        # 4. Asertar: Se llamó al método getconn() del mock
        MockDBPool.getconn.assert_called_once()

    ## ----------------------------------------------------------------------
    ## Tests para release_connection()
    ## ----------------------------------------------------------------------

    @patch('db_manager.db_pool')
    def test_release_connection_success(self, MockDBPool):
        """Prueba que se llama correctamente al método putconn() del pool."""

        # 1. Configurar conexión simulada
        mock_conn = MagicMock()

        # 2. Ejecutar la función
        release_connection(mock_conn)

        # 3. Asertar: Se llamó al método putconn() del pool simulado con la conexión
        MockDBPool.putconn.assert_called_once_with(mock_conn)

    def test_release_connection_pool_not_initialized(self):
        """Prueba que no hace nada si el pool global es None (comportamiento seguro)."""

        # La variable db_pool es None por el setUp
        mock_conn = MagicMock()
        release_connection(mock_conn)

        # No hay nada que asertar aquí, más allá de que no se levantó ninguna excepción.
        # Solo verificamos que el test pasó sin errores.
        self.assertIsNone(db_pool)


if __name__ == '__main__':
    unittest.main()