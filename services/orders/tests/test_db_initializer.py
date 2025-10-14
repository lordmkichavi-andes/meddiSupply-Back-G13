import unittest
from unittest.mock import patch, Mock, mock_open
import sys
from psycopg2 import Error as Psycopg2Error, ProgrammingError

# Aseguramos que el módulo 'src' se puede importar
sys.path.append('src')
import infrastructure.persistence.db_initializer as db_initializer


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

    @patch('builtins.open', side_effect=FileNotFoundError)
    @patch('builtins.print')
    def test_read_sql_file_not_found(self, mock_print, mock_open):
        """Verifica el manejo de FileNotFoundError."""
        print("Ejecutando test_read_sql_file_not_found...")
        filepath = "/fake/path/missing.sql"
        content = db_initializer._read_sql_file(filepath)
        self.assertEqual(content, "")
        mock_print.assert_called_once_with(f"ERROR: Archivo SQL no encontrado: {filepath}")

    # --- Tests de la función initialize_database ---

    def test_initialize_database_skipped_by_config(self):
        """Verifica que la inicialización se omite si la bandera de Config es False."""
        print("Ejecutando test_initialize_database_skipped_by_config...")
        db_initializer.Config.RUN_DB_INIT_ON_STARTUP = False

        # Patchamos get_connection para asegurar que no se llama
        with patch('infrastructure.persistence.db_connector.get_connection') as mock_get_conn:
            db_initializer.initialize_database()
            mock_get_conn.assert_not_called()

    @patch('infrastructure.persistence.db_connector.release_connection')
    @patch('infrastructure.persistence.db_connector.get_connection')
    @patch('infrastructure.persistence.db_initializer._read_sql_file', side_effect=["", MOCK_INSERT_SQL])
    @patch('builtins.print')
    def test_initialize_database_empty_schema_file(self, mock_print, mock_read, mock_get_conn, mock_release_conn):
        """Verifica el manejo si schema.sql está vacío."""
        print("Ejecutando test_initialize_database_empty_schema_file...")
        db_connector_mock = Mock()
        mock_get_conn.return_value = db_connector_mock

        db_initializer.initialize_database()

        # No debería haber intento de conexión
        mock_get_conn.assert_not_called()

        # Debería imprimir el error y abortar
        mock_print.assert_any_call(
            "ERROR: El script de esquema (schema.sql) está vacío o no se encontró. Abortando inicialización.")

    @patch('infrastructure.persistence.db_connector.release_connection')
    @patch('infrastructure.persistence.db_connector.get_connection',
           side_effect=ConnectionError("Pool no inicializado"))
    @patch('infrastructure.persistence.db_initializer._read_sql_file', side_effect=[MOCK_SCHEMA_SQL, MOCK_INSERT_SQL])
    @patch('builtins.print')
    def test_initialize_database_connection_error(self, mock_print, mock_read, mock_release_conn):
        """Verifica el manejo si get_connection lanza ConnectionError."""
        print("Ejecutando test_initialize_database_connection_error...")

        db_initializer.initialize_database()

        # Debe imprimir el error de conexión
        mock_print.assert_any_call("ERROR: Pool no inicializado")
        mock_release_conn.assert_not_called()

    @patch('infrastructure.persistence.db_connector.release_connection')
    @patch('infrastructure.persistence.db_connector.get_connection')
    @patch('infrastructure.persistence.db_initializer._read_sql_file', side_effect=[MOCK_SCHEMA_SQL, MOCK_INSERT_SQL])
    @patch('builtins.print')
    def test_initialize_database_schema_execution_failure(self, mock_print, mock_read, mock_get_conn,
                                                          mock_release_conn):
        """Verifica el manejo si falla la ejecución del esquema (psycopg2.Error)."""
        print("Ejecutando test_initialize_database_schema_execution_failure...")

        # Configurar los mocks de conexión y cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Simular fallo al ejecutar el script de esquema
        mock_cursor.execute.side_effect = Psycopg2Error("Error de sintaxis en esquema")

        db_initializer.initialize_database()

        # 1. Verificar rollback y liberación
        mock_conn.rollback.assert_called_once()
        mock_release_conn.assert_called_once_with(mock_conn)

        # 2. Verificar mensaje de error
        mock_print.assert_any_call(
            "ERROR: Fallo durante la inicialización de la base de datos (Esquema o Conexión): Error de sintaxis en esquema"
        )

    @patch('infrastructure.persistence.db_connector.release_connection')
    @patch('infrastructure.persistence.db_connector.get_connection')
    @patch('infrastructure.persistence.db_initializer._read_sql_file', side_effect=[MOCK_SCHEMA_SQL, MOCK_INSERT_SQL])
    @patch('builtins.print')
    def test_initialize_database_insert_execution_warning(self, mock_print, mock_read, mock_get_conn,
                                                          mock_release_conn):
        """
        Verifica el manejo si falla la inserción (ProgrammingError), lo cual
        es un ADVERTENCIA en este caso.
        """
        print("Ejecutando test_initialize_database_insert_execution_warning...")

        # Configurar los mocks de conexión y cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Configurar el primer execute (schema) para que pase, y el segundo (insert) para que falle
        mock_cursor.execute.side_effect = [None, ProgrammingError("Datos ya existentes")]

        db_initializer.initialize_database()

        # 1. Verificar commit después del esquema y el commit final
        self.assertEqual(mock_conn.commit.call_count, 2)

        # 2. Verificar mensaje de advertencia y que no se llamó a rollback
        mock_print.assert_any_call(
            "ADVERTENCIA: Fallo al ejecutar el script de inserción (posiblemente datos ya existentes o error de sintaxis): Datos ya existentes"
        )
        mock_conn.rollback.assert_not_called()  # Rollback solo se llama en el except principal
        mock_release_conn.assert_called_once_with(mock_conn)

    @patch('infrastructure.persistence.db_connector.release_connection')
    @patch('infrastructure.persistence.db_connector.get_connection')
    @patch('infrastructure.persistence.db_initializer._read_sql_file', side_effect=[MOCK_SCHEMA_SQL, MOCK_INSERT_SQL])
    @patch('builtins.print')
    def test_initialize_database_success_with_data_insertion(self, mock_print, mock_read, mock_get_conn,
                                                             mock_release_conn):
        """Verifica el escenario de éxito completo: esquema e inserción."""
        print("Ejecutando test_initialize_database_success_with_data_insertion...")

        # Configurar los mocks de conexión y cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # No side_effects, ambos executes pasan.

        db_initializer.initialize_database()

        # 1. Verificar llamadas a execute (dos veces: esquema e inserción)
        self.assertEqual(mock_cursor.execute.call_count, 2)

        # 2. Verificar commits (dos veces: después del esquema y el commit final)
        self.assertEqual(mock_conn.commit.call_count, 2)

        # 3. Verificar liberación de conexión
        mock_release_conn.assert_called_once_with(mock_conn)

        # 4. Verificar mensajes de éxito
        mock_print.assert_any_call("INFO: Ejecutando scripts de creación de esquema...")
        mock_print.assert_any_call("INFO: Ejecutando scripts de inserción de datos de prueba...")
        mock_print.assert_any_call(
            "INFO: El script de inserción se ejecutó con éxito (los datos se insertan solo si están vacíos).")


if __name__ == '__main__':
    unittest.main()
