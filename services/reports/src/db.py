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
    SELECT
    s.seller_id AS id, -- ID del vendedor
    u.name || ' ' || u.last_name AS name, -- Nombre y apellido
    u.email AS email,
    s.zone AS region, -- Zona de trabajo del vendedor
    u.active AS active -- Estado de actividad del usuario
    FROM
        users.sellers s
    JOIN
        users.Users u ON s.user_id = u.user_id
    ORDER BY
    name
    """
    result = execute_query(query, fetch_all=True)
    return result or []


def get_products() -> List[Dict[str, Any]]:
    """Obtiene todos los productos disponibles."""
    query = """
    SELECT
    p.product_id AS id, -- ID del Producto
    p.name AS name, -- Nombre del Producto
    c.name AS category, -- Nombre de la Categoría
    p.value AS price, -- Precio del Producto (el campo 'value' es el precio en tu esquema)
    u.name AS unit -- Nombre de la Unidad de Medida
    FROM
        products.Products p
    JOIN
        products.Category c ON p.category_id = c.category_id
    JOIN
        products.units u ON p.unit_id = u.unit_id
    ORDER BY
        name
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
            SUM(o.total_value) AS ventas_totales,
            COUNT(o.order_id) AS pedidos,
            '2025-01-01' AS period_start,
            '2025-02-28' AS period_end
            FROM
                users.sellers s
            JOIN
                users.Users u ON s.user_id = u.user_id 
            LEFT JOIN
                users.Clients c ON s.seller_id = c.seller_id 
            LEFT JOIN
                orders.Orders o ON c.client_id = o.client_id 
            WHERE
                o.status_id = 3
                AND s.seller_id = %s 
            GROUP BY
                s.seller_id, u.name, u.last_name, s.zone
            ORDER BY
                ventas_totales DESC
        """
    
    # Consulta para productos (separada para evitar duplicados)
    products_query = """
        SELECT
        p.name AS nombre,
        SUM(ol.quantity) AS cantidad,    
        SUM(ol.quantity * ol.price_unit) AS ventas
        FROM
            users.sellers s
        JOIN
            users.Users u ON s.user_id = u.user_id
        JOIN
            users.Clients c ON s.seller_id = c.seller_id
        JOIN
            orders.Orders o ON c.client_id = o.client_id
        JOIN
            orders.OrderLines ol ON o.order_id = ol.order_id
        JOIN
            products.Products p ON ol.product_id = p.product_id
        WHERE
            -- Filtrar por el ID del vendedor que deseas analizar
            s.seller_id = 1
            -- Opcional: Filtrar solo órdenes completadas (asumiendo 3 = Entregado/Vendido)
            AND o.status_id = 3
        GROUP BY
            s.seller_id, u.name, u.last_name, p.product_id, p.name
        ORDER BY
            nombre
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
    sales_result = execute_query(sales_query, (vendor_id ), fetch_one=True)
    products_result = execute_query(products_query, (vendor_id ), fetch_all=True)
    chart_result = execute_query(chart_query, (vendor_id ), fetch_all=True)
    
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