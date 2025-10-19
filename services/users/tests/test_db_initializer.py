import unittest
from unittest.mock import patch, mock_open, MagicMock
import psycopg2
import os

# Importa la función que quieres probar y la configuración
# Asumo que esta función está en un módulo llamado 'db_initializer'
from .db_initializer import initialize_database, _read_sql_file
from config import Config


class TestDatabaseInitializer(unittest.TestCase):
    # ----------------------------------------------------
    # Configuración de Mocks y Valores de Prueba
    # ----------------------------------------------------

    # Scripts SQL simulados para las pruebas
    MOCK_SCHEMA_SQL = "CREATE TABLE test_table (id INT);"
    MOCK_INSERT_SQL = "INSERT INTO test_table (id) VALUES (1);"

    # Rutas simuladas (solo para verificar que os.path.exists sea llamado)
    @patch('db_initializer.SCHEMA_FILE', '/mock/path/schema.sql')
    @patch('db_initializer.INSERT_DATA_FILE', '/mock/path/insert_data.sql')
    def setUp(self):
        """Prepara el entorno de cada prueba."""
        # Asegura que la inicialización esté habilitada por defecto en las pruebas
        Config.RUN_DB_INIT_ON_STARTUP = True

        # Mock de la conexión y el cursor
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

    # ----------------------------------------------------
    # Pruebas de la Función Auxiliar _read_sql_file
    # ----------------------------------------------------

    def test_read_sql_file_success(self):
        """Prueba la lectura exitosa de un archivo SQL."""
        # Usamos mock_open para simular el archivo
        with patch("builtins.open", mock_open(read_data=self.MOCK_SCHEMA_SQL)):
            content = _read_sql_file("/dummy/path/schema.sql")
            self.assertEqual(content, self.MOCK_SCHEMA_SQL)

    def test_read_sql_file_not_found(self):
        """Prueba qué pasa cuando el archivo SQL no se encuentra."""
        # open lanza FileNotFoundError por defecto sin 'read_data'
        with patch("builtins.open", side_effect=FileNotFoundError):
            with patch('sys.stdout') as mock_print:  # Captura la salida de impresión
                content = _read_sql_file("/dummy/path/missing.sql")
                self.assertEqual(content, "")
                mock_print.assert_called_with("ERROR: Archivo SQL no encontrado: /dummy/path/missing.sql")

    # ----------------------------------------------------
    # Pruebas de initialize_database (Casos de Éxito)
    # ----------------------------------------------------

    @patch('db_initializer._read_sql_file', side_effect=[MOCK_SCHEMA_SQL, MOCK_INSERT_SQL])
    @patch('db_initializer.os.path.exists', return_value=True)  # Archivos existen
    @patch('db_initializer.get_connection')
    def test_initialization_success_with_data(self, mock_get_conn, mock_exists, mock_read_file):
        """Prueba el flujo completo de inicialización con éxito (esquema y datos)."""
        mock_get_conn.return_value = self.mock_conn

        initialize_database()

        # 1. Verificar llamadas de la DB
        mock_get_conn.assert_called_once()
        self.mock_cursor.execute.assert_any_call(self.MOCK_SCHEMA_SQL)  # Ejecuta esquema
        self.mock_conn.commit.assert_called()  # Commit después del esquema
        self.mock_cursor.execute.assert_any_call(self.MOCK_INSERT_SQL)  # Ejecuta datos
        self.mock_conn.commit.assert_called()  # Commit después de los datos
        self.mock_cursor.close.assert_called_once()

        # 2. Verificar liberación de la conexión
        with patch('db_initializer.release_connection') as mock_release:
            initialize_database()
            mock_release.assert_called_once_with(self.mock_conn)

    @patch('db_initializer._read_sql_file', side_effect=[MOCK_SCHEMA_SQL, ""])  # No hay script de datos
    @patch('db_initializer.os.path.exists', return_value=True)
    @patch('db_initializer.get_connection')
    def test_initialization_success_only_schema(self, mock_get_conn, mock_exists, mock_read_file):
        """Prueba la inicialización exitosa cuando no hay datos de inserción."""
        mock_get_conn.return_value = self.mock_conn

        initialize_database()

        # 1. Verificar que SOLO se ejecute el script de esquema
        self.mock_cursor.execute.assert_called_once_with(self.MOCK_SCHEMA_SQL)
        self.mock_conn.commit.assert_called_once()
        self.mock_cursor.close.assert_called_once()

    # ----------------------------------------------------
    # Pruebas de initialize_database (Casos de Error/Exclusión)
    # ----------------------------------------------------

    def test_initialization_skipped_by_config(self):
        """Prueba que la inicialización se omita si Config.RUN_DB_INIT_ON_STARTUP es False."""
        Config.RUN_DB_INIT_ON_STARTUP = False

        with patch('db_initializer.get_connection') as mock_get_conn:
            initialize_database()
            mock_get_conn.assert_not_called()  # Verifica que no se intenta conectar

    @patch('db_initializer.os.path.exists', side_effect=[False, True])  # Falla schema.sql
    @patch('db_initializer._read_sql_file')
    @patch('db_initializer.get_connection')
    def test_initialization_aborted_missing_schema_file(self, mock_get_conn, mock_read_file, mock_exists):
        """Prueba que la inicialización aborte si schema.sql no existe."""
        initialize_database()

        mock_read_file.assert_not_called()
        mock_get_conn.assert_not_called()

    @patch('db_initializer._read_sql_file', return_value="")  # Retorna string vacío
    @patch('db_initializer.os.path.exists', return_value=True)
    @patch('db_initializer.get_connection')
    def test_initialization_aborted_empty_schema_script(self, mock_get_conn, mock_exists, mock_read_file):
        """Prueba que la inicialización aborte si el script de esquema está vacío."""
        initialize_database()

        mock_get_conn.assert_not_called()

    @patch('db_initializer.get_connection', side_effect=ConnectionError("Fallo de red"))
    def test_initialization_connection_error(self, mock_get_conn):
        """Prueba el manejo de un error al intentar obtener la conexión."""
        with patch('sys.stdout') as mock_print:
            initialize_database()
            mock_print.assert_called_with("❌ ERROR: Fallo de red")

        mock_get_conn.assert_called_once()

    @patch('db_initializer._read_sql_file', side_effect=[MOCK_SCHEMA_SQL, MOCK_INSERT_SQL])
    @patch('db_initializer.os.path.exists', return_value=True)
    @patch('db_initializer.get_connection')
    def test_initialization_error_on_schema_creation(self, mock_get_conn, mock_exists, mock_read_file):
        """Prueba el manejo de un error al ejecutar el script de esquema."""
        mock_get_conn.return_value = self.mock_conn

        # Simula un error de DB al crear el esquema
        self.mock_cursor.execute.side_effect = psycopg2.Error("Tabla inválida")

        initialize_database()

        # 1. Verifica que se llama a rollback y se libera la conexión
        self.mock_conn.rollback.assert_called_once()
        with patch('db_initializer.release_connection') as mock_release:
            initialize_database()
            mock_release.assert_called_once_with(self.mock_conn)

    @patch('db_initializer._read_sql_file', side_effect=[MOCK_SCHEMA_SQL, MOCK_INSERT_SQL])
    @patch('db_initializer.os.path.exists', return_value=True)
    @patch('db_initializer.get_connection')
    def test_initialization_handle_data_insertion_warning(self, mock_get_conn, mock_exists, mock_read_file):
        """Prueba el manejo del error al insertar datos (típico cuando ya existen)."""
        mock_get_conn.return_value = self.mock_conn

        # El primer execute (esquema) pasa, el segundo (datos) falla con un error
        self.mock_cursor.execute.side_effect = [
            None,  # Esquema pasa
            psycopg2.Error("Duplicate Key Error")  # Inserción de datos falla
        ]

        initialize_database()

        # 1. Verificar que el error de datos solo causa un rollback y no falla el proceso
        self.assertEqual(self.mock_cursor.execute.call_count, 2)
        self.mock_conn.commit.call_count, 1  # Solo el commit de la creación del esquema
        self.mock_conn.rollback.assert_called_once()  # Rollback de la inserción fallida
        self.mock_cursor.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()