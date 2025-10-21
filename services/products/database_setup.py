# database_setup.py
import os
import psycopg2
from psycopg2 import pool
from config import Config

db_pool = None
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
INSERT_DATA_FILE = 'insert_data.sql'

def setup_database():
    init_db_pool()
    initialize_database()


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
    print(f"🔍 INSERT_DATA_FILE: {INSERT_DATA_FILE}")

    # Verificar que los archivos existan
    if not os.path.exists(INSERT_DATA_FILE):
        print(f"⚠️  ADVERTENCIA: No se encuentra {INSERT_DATA_FILE}")

    # Cargar los scripts SQL desde archivos
    INSERT_DATA_SQL = _read_sql_file(INSERT_DATA_FILE)


    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        print("📊 Ejecutando scripts de creación de esquema...")

        # 1. Crear Tablas
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


def init_db_pool():
    global db_pool
    if db_pool is None:
        try:
            db_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "postgres"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "postgres")
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

if __name__ == '__main__':
    setup_database()