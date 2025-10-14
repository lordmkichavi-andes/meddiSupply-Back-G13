# src/infrastructure/persistence/db_initializer.py
import os
import psycopg2
from .db_connector import get_connection, release_connection
from orders.config import Config

# Rutas a los archivos SQL
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
RESOURCES_DIR = os.path.join(BASE_DIR, 'resources')
SCHEMA_FILE = os.path.join(RESOURCES_DIR, 'schema.sql')
INSERT_DATA_FILE = os.path.join(RESOURCES_DIR, 'insert_data.sql')


def _read_sql_file(filepath: str) -> str:
    """Lee el contenido de un archivo SQL."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        print(f"ERROR: Archivo SQL no encontrado: {filepath}")
        return ""


def initialize_database():
    """
    Crea las tablas y las puebla con datos si están vacías, leyendo los scripts de archivos.
    """
    if not Config.RUN_DB_INIT_ON_STARTUP:
        print("INFO: Inicialización de la base de datos omitida por configuración.")
        return

    # Cargar los scripts SQL desde archivos
    ORDER_SCHEMA_SQL = _read_sql_file(SCHEMA_FILE)
    INSERT_DATA_SQL = _read_sql_file(INSERT_DATA_FILE)

    if not ORDER_SCHEMA_SQL:
        print("ERROR: El script de esquema (schema.sql) está vacío o no se encontró. Abortando inicialización.")
        return

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        print("INFO: Ejecutando scripts de creación de esquema...")

        # 1. Crear Tablas (Ejecuta el script de esquema)
        cursor.execute(ORDER_SCHEMA_SQL)
        conn.commit()

        print("INFO: Ejecutando scripts de inserción de datos de prueba...")

        # 2. Insertar Datos (Ejecuta el script de inserción con validación)
        # Usamos try/except dentro del loop principal para asegurar que la conexión se libere
        try:
            cursor.execute(INSERT_DATA_SQL)

            # Verifica si se insertó algo para reportar el éxito
            # Nota: psycopg2.rowcount solo es confiable para la última consulta ejecutada.
            # Aquí, solo validamos que no haya errores al ejecutar el script de inserción.
            if any(s.strip().startswith('INSERT') for s in INSERT_DATA_SQL.split(';')):
                print("INFO: El script de inserción se ejecutó con éxito (los datos se insertan solo si están vacíos).")

        except psycopg2.ProgrammingError as pe:
            # Esto puede ocurrir si el script de inserción no es perfecto.
            print(
                f"ADVERTENCIA: Fallo al ejecutar el script de inserción (posiblemente datos ya existentes o error de sintaxis): {pe}")

        conn.commit()

    except psycopg2.Error as e:
        print(f"ERROR: Fallo durante la inicialización de la base de datos (Esquema o Conexión): {e}")
        if conn:
            conn.rollback()  # Asegura que no queden cambios parciales
    except ConnectionError as e:
        print(f"ERROR: {e}")
    finally:
        if conn:
            release_connection(conn)
