import os
import psycopg2
from .db_connector import get_connection, release_connection
from config import Config

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

    # DEBUG: Verificar rutas
    print(f"🔍 BASE_DIR: {BASE_DIR}")
    print(f"🔍 RESOURCES_DIR: {RESOURCES_DIR}")
    print(f"🔍 SCHEMA_FILE: {SCHEMA_FILE}")
    print(f"🔍 INSERT_DATA_FILE: {INSERT_DATA_FILE}")
    
    # Verificar que los archivos existan
    if not os.path.exists(SCHEMA_FILE):
        print(f"❌ ERROR: No se encuentra {SCHEMA_FILE}")
        return
    if not os.path.exists(INSERT_DATA_FILE):
        print(f"⚠️  ADVERTENCIA: No se encuentra {INSERT_DATA_FILE}")

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

        print("📊 Ejecutando scripts de creación de esquema...")

        # 1. Crear Tablas
        cursor.execute(ORDER_SCHEMA_SQL)
        conn.commit()
        print("✅ Esquema creado correctamente.")

        print("📝 Ejecutando scripts de inserción de datos de prueba...")

        # 2. Insertar Datos
        if INSERT_DATA_SQL:
            try:
                cursor.execute(INSERT_DATA_SQL)
                conn.commit()
                print("✅ Datos de prueba insertados correctamente.")
            except psycopg2.Error as pe:
                print(f"⚠️  ADVERTENCIA: Error al insertar datos (posiblemente ya existen): {pe}")
                conn.rollback()

        cursor.close()

    except psycopg2.Error as e:
        print(f"❌ ERROR: Fallo durante la inicialización de la base de datos: {e}")
        if conn:
            conn.rollback()
    except ConnectionError as e:
        print(f"❌ ERROR: {e}")
    finally:
        if conn:
            release_connection(conn)
