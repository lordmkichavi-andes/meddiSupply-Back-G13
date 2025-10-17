import unittest
from unittest.mock import patch, Mock, mock_open
import sys
from psycopg2 import Error as Psycopg2Error, ProgrammingError

# Aseguramos que el módulo 'src' se puede importar
sys.path.append('orders.src')
import orders.src.infrastructure.persistence.db_initializer as db_initializer


# --- Mocks de Configuración y Datos ---

# Mock de la configuración para controlar el flujo
class MockConfig:
    RUN_DB_INIT_ON_STARTUP = True


# Mock de scripts SQL
MOCK_SCHEMA_SQL = "CREATE TABLE orders (id VARCHAR(255));"
MOCK_INSERT_SQL = "INSERT INTO orders (id) VALUES ('TEST');"

# Reemplazamos el módulo de configuración real con nuestro mock
db_initializer.Config = MockConfig


class TestDBInitializer(unittest.TestCase):
    """
    Pruebas unitarias para la inicialización de la base de datos,
    simulando la lectura de archivos y la ejecución de SQL.
    """

    def setUp(self):
        """Resetear mocks y configuraciones antes de cada prueba."""
        # Se asegura que la configuración de la prueba es la predeterminada
        db_initializer.Config.RUN_DB_INIT_ON_STARTUP = True

    # --- Test de la función privada _read_sql_file ---

    @patch('builtins.open', new_callable=mock_open, read_data=MOCK_SCHEMA_SQL)
    def test_read_sql_file_success(self, mock_file):
        """Verifica la lectura exitosa de un archivo SQL."""
        print("Ejecutando test_read_sql_file_success...")
        content = db_initializer._read_sql_file("/fake/path/schema.sql")
        self.assertEqual(content, MOCK_SCHEMA_SQL)
        mock_file.assert_called_once_with("/fake/path/schema.sql", 'r', encoding='utf-8')

    # --- Tests de la función initialize_database ---

    def test_initialize_database_skipped_by_config(self):
        """Verifica que la inicialización se omite si la bandera de Config es False."""
        print("Ejecutando test_initialize_database_skipped_by_config...")
        db_initializer.Config.RUN_DB_INIT_ON_STARTUP = False

        # Patchamos get_connection para asegurar que no se llama
        with patch('infrastructure.persistence.db_connector.get_connection') as mock_get_conn:
            db_initializer.initialize_database()
            mock_get_conn.assert_not_called()



if __name__ == '__main__':
    unittest.main()
