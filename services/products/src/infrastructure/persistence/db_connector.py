# src/infrastructure/persistence/db_connector.py
import psycopg2
from psycopg2 import pool
from config import Config

# Se usa un pool de conexiones para manejo eficiente en un entorno web
db_pool = None

def init_db_pool():
    """Inicializa el pool de conexiones de PostgreSQL."""
    global db_pool
    if db_pool is None:
        try:
            db_pool = pool.SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=Config.DB_HOST,
                port=Config.DB_PORT,
                database=Config.DB_NAME,
                user=Config.DB_USER,
                password=Config.DB_PASSWORD
            )
            print("INFO: Pool de conexiones a la base de datos inicializado.")
        except psycopg2.Error as e:
            print(f"ERROR: No se pudo conectar a la base de datos. {e}")
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
