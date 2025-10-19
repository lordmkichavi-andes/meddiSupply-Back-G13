"""Conector a base de datos transaccional para el servicio de rutas."""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Any, Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


def get_connection():
    """Obtiene conexión a la base de datos transaccional."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT', 5432),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD'),
            sslmode='require'
        )
        return conn
    except Exception as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        return None


def execute_query(query: str, params: tuple = None, fetch_one: bool = False, fetch_all: bool = False) -> Any:
    """Ejecuta una consulta SQL y retorna el resultado."""
    conn = None
    try:
        conn = get_connection()
        if not conn:
            return None
            
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.rowcount
                
    except Exception as e:
        logger.error(f"Error ejecutando consulta: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()


def get_vehiculos() -> List[Dict[str, Any]]:
    """Obtiene todos los vehículos disponibles."""
    query = "SELECT id, capacidad, color, etiqueta FROM rutas.vehiculos ORDER BY id"
    result = execute_query(query, fetch_all=True)
    return result or []


def get_clientes() -> List[Dict[str, Any]]:
    """Obtiene todos los clientes."""
    query = """
    SELECT id, nombre, direccion, latitud, longitud, demanda 
    FROM rutas.clientes 
    ORDER BY nombre
    """
    result = execute_query(query, fetch_all=True)
    return result or []

