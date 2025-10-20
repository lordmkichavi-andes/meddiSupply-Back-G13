import os
import psycopg2
from psycopg2 import pool

db_pool = None

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
