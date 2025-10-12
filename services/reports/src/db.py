"""Conector a base de datos transaccional para el servicio de reportes."""

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


def get_vendors() -> List[Dict[str, Any]]:
    """Obtiene todos los vendedores disponibles."""
    query = """
    SELECT id, name, email, region, active 
    FROM reportes.vendors 
    WHERE active = true 
    ORDER BY name
    """
    result = execute_query(query, fetch_all=True)
    return result or []


def get_products() -> List[Dict[str, Any]]:
    """Obtiene todos los productos disponibles."""
    query = """
    SELECT id, name, category, price, unit 
    FROM reportes.products 
    ORDER BY name
    """
    result = execute_query(query, fetch_all=True)
    return result or []


def get_periods() -> List[Dict[str, str]]:
    """Obtiene los períodos disponibles para reportes."""
    return [
        {'value': 'bimestral', 'label': 'Bimestral'},
        {'value': 'trimestral', 'label': 'Trimestral'},
        {'value': 'semestral', 'label': 'Semestral'},
        {'value': 'anual', 'label': 'Anual'}
    ]


def get_sales_report_data(vendor_id: str, period: str) -> Optional[Dict[str, Any]]:
    """Obtiene los datos de reporte de ventas para un vendedor y período específico."""
    query = """
    SELECT 
        sr.ventas_totales,
        sr.pedidos,
        sr.grafico,
        sr.periodo,
        json_agg(
            json_build_object(
                'nombre', p.name,
                'ventas', srp.ventas,
                'cantidad', srp.cantidad
            ) ORDER BY p.name
        ) as productos
    FROM reportes.sales_reports sr
    JOIN reportes.sales_report_products srp ON sr.id = srp.sales_report_id
    JOIN reportes.products p ON srp.product_id = p.id
    WHERE sr.vendor_id = %s AND sr.period_type = %s
    GROUP BY sr.id, sr.ventas_totales, sr.pedidos, sr.grafico, sr.periodo
    """
    
    result = execute_query(query, (vendor_id, period), fetch_one=True)
    return dict(result) if result else None


def validate_sales_data_availability(vendor_id: str, period: str) -> bool:
    """Valida si existen datos para un vendedor y período específico."""
    query = """
    SELECT COUNT(*) as count 
    FROM reportes.sales_reports 
    WHERE vendor_id = %s AND period_type = %s
    """
    
    result = execute_query(query, (vendor_id, period), fetch_one=True)
    return result['count'] > 0 if result else False
