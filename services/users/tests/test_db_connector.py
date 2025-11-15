import unittest
from unittest.mock import patch, MagicMock
import psycopg2
from psycopg2 import pool
import os
import sys

# Importar el módulo real a testear
from src.infrastructure.persistence import db_connector

# Variables de entorno simuladas para el éxito
MOCK_ENV_VARS = {
    "DB_HOST": "test_host",
    "DB_PORT": "6000",
    "DB_NAME": "test_db",
    "DB_USER": "test_user",
    "DB_PASSWORD": "test_password"
}

BUILTINS_PATH = 'builtins.print'


class TestDBConnector(unittest.TestCase):

    def tearDown(self):
        """Asegura que db_pool esté reseteado después de cada prueba."""
        db_connector.db_pool = None

    @patch('src.infrastructure.persistence.db_connector.os.getenv', side_effect=lambda k, default=None: MOCK_ENV_VARS.get(k, default))
    @patch('src.infrastructure.persistence.db_connector.pool.SimpleConnectionPool')
    @patch(BUILTINS_PATH)
    def test_init_db_pool_success(self, mock_print, MockSimpleConnectionPool, mock_getenv):
        """Prueba la inicialización exitosa del pool de conexiones."""
        # Simular una instancia de pool exitosa
        mock_pool_instance = MagicMock()
        MockSimpleConnectionPool.return_value = mock_pool_instance

        db_connector.init_db_pool()

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
        self.assertEqual(db_connector.db_pool, mock_pool_instance)

        # 3. Verificar el mensaje de éxito usando el mock_print
        expected_message = "✅ Pool de conexiones a la base de datos inicializado."
        mock_print.assert_any_call(expected_message)

    @patch('src.infrastructure.persistence.db_connector.os.getenv', side_effect=lambda k, default=None: MOCK_ENV_VARS.get(k, default))
    @patch('src.infrastructure.persistence.db_connector.pool.SimpleConnectionPool', side_effect=psycopg2.Error("Auth failed"))
    @patch(BUILTINS_PATH)
    def test_init_db_pool_connection_error(self, mock_print, MockSimpleConnectionPool, mock_getenv):
        """Prueba el manejo de errores de conexión de psycopg2."""
        # Esperar que se lance ConnectionError
        with self.assertRaisesRegex(ConnectionError, "Fallo en la conexión inicial a la base de datos."):
            db_connector.init_db_pool()

        # 1. Verificar que el pool no se haya establecido
        self.assertIsNone(db_connector.db_pool)

        # 2. Verificar el mensaje de error en la salida
        printed_call_args = [call_args[0][0] for call_args in mock_print.call_args_list]
        self.assertTrue(
            any("❌ Error al conectar a la base de datos" in arg for arg in printed_call_args),
            "No se encontró el mensaje de error de conexión en la salida impresa."
        )

    @patch('src.infrastructure.persistence.db_connector.os.getenv', side_effect=lambda k, default=None: MOCK_ENV_VARS.get(k, default))
    @patch('src.infrastructure.persistence.db_connector.pool.SimpleConnectionPool')
    @patch(BUILTINS_PATH)
    def test_init_db_pool_already_initialized(self, mock_print, MockSimpleConnectionPool, mock_getenv):
        """Prueba que init_db_pool no reinicializa si el pool ya existe."""
        # Inicializar el pool una vez
        mock_pool_instance = MagicMock()
        MockSimpleConnectionPool.return_value = mock_pool_instance
        db_connector.init_db_pool()
        
        # Resetear el mock para verificar que no se llama de nuevo
        MockSimpleConnectionPool.reset_mock()
        mock_print.reset_mock()
        
        # Llamar init_db_pool de nuevo
        db_connector.init_db_pool()
        
        # Verificar que SimpleConnectionPool no se llamó de nuevo
        MockSimpleConnectionPool.assert_not_called()
        # Verificar que el print de éxito no se llamó de nuevo
        self.assertEqual(mock_print.call_count, 0)

    def test_get_connection_success(self):
        """Prueba la obtención exitosa de una conexión cuando el pool está inicializado."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        mock_pool.getconn.return_value = mock_conn
        db_connector.db_pool = mock_pool

        conn = db_connector.get_connection()

        self.assertEqual(conn, mock_conn)
        mock_pool.getconn.assert_called_once()

    def test_get_connection_not_initialized(self):
        """Prueba que se lanza una excepción si se llama a get_connection sin init_db_pool."""
        db_connector.db_pool = None

        with self.assertRaisesRegex(ConnectionError, "El pool de la base de datos no está inicializado."):
            db_connector.get_connection()

    def test_release_connection(self):
        """Prueba que release_connection devuelve la conexión al pool."""
        mock_pool = MagicMock()
        mock_conn = MagicMock()
        db_connector.db_pool = mock_pool

        db_connector.release_connection(mock_conn)

        mock_pool.putconn.assert_called_once_with(mock_conn)

    def test_release_connection_not_initialized(self):
        """Prueba que release_connection no falla si el pool no está inicializado."""
        db_connector.db_pool = None

        # La función debe ejecutarse sin errores
        try:
            db_connector.release_connection(MagicMock())
        except Exception as e:
            self.fail(f"release_connection falló inesperadamente: {e}")


if __name__ == '__main__':
    unittest.main()
