import pytest
from unittest.mock import MagicMock, patch, mock_open
import psycopg2

# Importamos la función a probar y las dependencias (aunque las mockearemos)
from src.infrastructure.persistence.db_initializer import initialize_database, _read_sql_file


# --- Mocks Comunes (Fixtures) ---

@pytest.fixture
def mock_db_connection():
    """Mockea la conexión y el cursor de psycopg2."""
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


@pytest.fixture(autouse=True)
def mock_db_connector(mock_db_connection):
    """Mockea get_connection y release_connection a nivel de módulo."""
    with patch('src.infrastructure.persistence.db_initializer.get_connection',
               return_value=mock_db_connection) as get_conn_mock, \
            patch('src.infrastructure.persistence.db_initializer.release_connection') as release_conn_mock:
        yield get_conn_mock, release_conn_mock


@pytest.fixture
def mock_config():
    """Mockea la clase Config para controlar RUN_DB_INIT_ON_STARTUP."""
    with patch('src.infrastructure.persistence.db_initializer.Config') as MockConfig:
        # Establecer el valor por defecto a True para la mayoría de los tests
        MockConfig.RUN_DB_INIT_ON_STARTUP = True
        yield MockConfig


# --- Tests de la Función Auxiliar (_read_sql_file) ---

def test_read_sql_file_success():
    """Verifica la lectura exitosa de un archivo."""
    mock_data = "CREATE TABLE users;"
    with patch('builtins.open', mock_open(read_data=mock_data)):
        result = _read_sql_file("dummy_path.sql")
        assert result == mock_data


def test_read_sql_file_not_found():
    """Verifica que maneje FileNotFoundError correctamente."""
    with patch('builtins.open', side_effect=FileNotFoundError), \
            patch('builtins.print') as mock_print:
        result = _read_sql_file("non_existent.sql")
        assert result == ""
        # Verifica que se imprima el error
        mock_print.assert_called_once()


# --- Tests de initialize_database() ---

@patch('src.infrastructure.persistence.db_initializer.print')
def test_initialization_skipped(mock_print, mock_config, mock_db_connector):
    """Prueba que la inicialización se omita si la configuración lo indica."""
    mock_config.RUN_DB_INIT_ON_STARTUP = False

    initialize_database()

    # Verifica que se haya impreso el mensaje de omisión
    mock_print.assert_called_with("INFO: Inicialización de la base de datos omitida por configuración.")
    # Verifica que get_connection NO haya sido llamado
    mock_db_connector[0].assert_not_called()


@patch('src.infrastructure.persistence.db_initializer.print')
@patch('src.infrastructure.persistence.db_initializer._read_sql_file', side_effect=["", "INSERT INTO data;"])
def test_initialization_schema_missing(mock_read_sql, mock_print, mock_config):
    """Prueba que la inicialización aborte si el esquema está vacío o no se encontró."""
    initialize_database()

    # Verifica que se haya impreso el mensaje de error y aborto
    mock_print.assert_any_call(
        "ERROR: El script de esquema (schema.sql) está vacío o no se encontró. Abortando inicialización.")
    # Verifica que get_connection NO haya sido llamado (no es necesario mockearlo aquí)
    assert mock_read_sql.call_count == 2  # Intentó leer ambos archivos


@patch('src.infrastructure.persistence.db_initializer.print')
@patch('src.infrastructure.persistence.db_initializer._read_sql_file',
       side_effect=["CREATE TABLE;", "INSERT INTO data;"])
def test_initialization_success(mock_read_sql, mock_print, mock_db_connector, mock_db_connection, mock_config):
    """Prueba el flujo completo de inicialización exitosa."""
    get_conn_mock, release_conn_mock = mock_db_connector
    mock_cursor = mock_db_connection.cursor.return_value

    initialize_database()

    # 1. Verificación de la conexión
    get_conn_mock.assert_called_once()

    # 2. Verificación de la ejecución de comandos SQL
    mock_cursor.execute.assert_any_call("CREATE TABLE;")  # Ejecución del esquema
    mock_cursor.execute.assert_any_call("INSERT INTO data;")  # Ejecución de la inserción

    # 3. Verificación de commits (hay dos en el código: uno después del esquema, otro al final)
    assert mock_db_connection.commit.call_count == 2

    # 4. Verificación del cleanup
    release_conn_mock.assert_called_once_with(mock_db_connection)

    # 5. Verificación de mensajes informativos
    mock_print.assert_any_call("INFO: Ejecutando scripts de creación de esquema...")
    mock_print.assert_any_call("INFO: Ejecutando scripts de inserción de datos de prueba...")
    mock_print.assert_any_call(
        "INFO: El script de inserción se ejecutó con éxito (los datos se insertan solo si están vacíos).")


@patch('src.infrastructure.persistence.db_initializer.print')
@patch('src.infrastructure.persistence.db_initializer._read_sql_file',
       side_effect=["CREATE TABLE;", "INSERT INTO data;"])
def test_initialization_data_error_handled(mock_read_sql, mock_print, mock_db_connector, mock_db_connection,
                                           mock_config):
    """
    Prueba el caso donde la inserción de datos falla con psycopg2.ProgrammingError
    (ej. datos ya existentes), pero el proceso continúa y se commite.
    """
    get_conn_mock, release_conn_mock = mock_db_connector
    mock_cursor = mock_db_connection.cursor.return_value

    # Forzamos que la segunda llamada a execute (la de INSERT) lance un error
    mock_cursor.execute.side_effect = [
        None,  # Primera llamada (CREATE TABLE) es exitosa
        psycopg2.ProgrammingError("Datos existentes")  # Segunda llamada (INSERT) falla
    ]

    initialize_database()

    # 1. El esquema (primera execute) debería haberse commiteado (primer commit)
    # 2. El error de inserción debería haber sido atrapado
    # 3. La función debería haber intentado el commit final (segundo commit)
    assert mock_db_connection.commit.call_count == 2

    # 4. Verificación del cleanup
    release_conn_mock.assert_called_once_with(mock_db_connection)

    # 5. Verificación de mensajes de ADVERTENCIA
    mock_print.assert_any_call(
        "ADVERTENCIA: Fallo al ejecutar el script de inserción (posiblemente datos ya existentes o error de sintaxis): Datos existentes"
    )


@patch('src.infrastructure.persistence.db_initializer.print')
@patch('src.infrastructure.persistence.db_initializer._read_sql_file',
       side_effect=["CREATE TABLE;", "INSERT INTO data;"])
def test_initialization_db_error_rollback(mock_read_sql, mock_print, mock_db_connector, mock_db_connection):
    """
    Prueba el manejo de errores graves de psycopg2 (ej. error de conexión después de get_connection
    o error de sintaxis en el esquema) que fuerzan un rollback.
    """
    get_conn_mock, release_conn_mock = mock_db_connector
    mock_cursor = mock_db_connection.cursor.return_value

    # Forzamos que la ejecución del esquema falle con un error general de DB
    mock_cursor.execute.side_effect = psycopg2.Error("Error fatal de DB")

    initialize_database()

    # 1. Verificación de que NUNCA se llama a commit
    mock_db_connection.commit.assert_not_called()

    # 2. Verificación de que se llama a rollback
    mock_db_connection.rollback.assert_called_once()

    # 3. Verificación del cleanup
    release_conn_mock.assert_called_once_with(mock_db_connection)

    # 4. Verificación de mensajes de ERROR
    mock_print.assert_any_call(
        "ERROR: Fallo durante la inicialización de la base de datos (Esquema o Conexión): Error fatal de DB")


@patch('src.infrastructure.persistence.db_initializer.print')
def test_initialization_connection_error_handled(mock_print, mock_config, mock_db_connector):
    """Prueba el manejo de un error de conexión al intentar obtenerla."""
    get_conn_mock, release_conn_mock = mock_db_connector

    # Forzamos que get_connection falle
    get_conn_mock.side_effect = ConnectionError("No se pudo conectar")

    initialize_database()

    # 1. Verificación de que get_connection fue llamado
    get_conn_mock.assert_called_once()

    # 2. Verificación de que release_connection NO fue llamado (conn es None)
    release_conn_mock.assert_not_called()

    # 3. Verificación de mensajes de ERROR
    mock_print.assert_any_call("ERROR: No se pudo conectar")
