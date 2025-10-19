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
    # Mapear periodos a los valores de la base de datos
    period_mapping = {
        'bimestral': 'bimonthly',
        'trimestral': 'quarterly', 
        'semestral': 'semiannual',
        'anual': 'annual'
    }
    db_period = period_mapping.get(period, period)
    
    # Consulta principal para datos básicos de ventas
    sales_query = """
    SELECT 
        total_sales as ventas_totales,
        total_orders as pedidos,
        period_start,
        period_end
    FROM reportes.sales 
    WHERE vendor_id = %s AND period_type = %s
    LIMIT 1
    """
    
    # Consulta para productos (separada para evitar duplicados)
    products_query = """
    SELECT 
        p.name as nombre,
        SUM(sd.line_amount) as ventas,
        SUM(sd.quantity) as cantidad
    FROM reportes.sales s
    JOIN reportes.sale_details sd ON s.id = sd.sale_id
    JOIN reportes.products p ON sd.product_id = p.id
    WHERE s.vendor_id = %s AND s.period_type = %s
    GROUP BY p.name
    ORDER BY p.name
    """
    
    # Consulta para datos del gráfico (separada)
    chart_query = """
    SELECT DISTINCT
        scp.idx,
        scp.value
    FROM reportes.sales s
    JOIN reportes.sales_chart_points scp ON s.id = scp.sale_id
    WHERE s.vendor_id = %s AND s.period_type = %s
    ORDER BY scp.idx
    """
    
    # Ejecutar consultas
    sales_result = execute_query(sales_query, (vendor_id, db_period), fetch_one=True)
    products_result = execute_query(products_query, (vendor_id, db_period), fetch_all=True)
    chart_result = execute_query(chart_query, (vendor_id, db_period), fetch_all=True)
    
    if sales_result:
        # Construir resultado combinando las consultas separadas
        data = dict(sales_result)
        
        # Agregar productos (convertir a formato esperado)
        data['productos'] = [
            {
                'nombre': row['nombre'],
                'ventas': float(row['ventas']),
                'cantidad': int(row['cantidad'])
            }
            for row in (products_result or [])
        ]
        
        # Agregar gráfico (convertir a array simple)
        data['grafico'] = [row['value'] for row in (chart_result or [])]
        
        # Crear periodo string
        data['periodo'] = f"{data['period_start']} - {data['period_end']}"
        
        # Mapear campos a camelCase para el modelo
        data['ventasTotales'] = data['ventas_totales']
        
        return data
    return None


def validate_sales_data_availability(vendor_id: str, period: str) -> bool:
    """Valida si existen datos para un vendedor y período específico."""
    # Mapear periodos a los valores de la base de datos
    period_mapping = {
        'bimestral': 'bimonthly',
        'trimestral': 'quarterly', 
        'semestral': 'semiannual',
        'anual': 'annual'
    }
    db_period = period_mapping.get(period, period)
    
    query = """
    SELECT COUNT(*) as count 
    FROM reportes.sales 
    WHERE vendor_id = %s AND period_type = %s
    """
    
    result = execute_query(query, (vendor_id, db_period), fetch_one=True)
    return result['count'] > 0 if result else False
