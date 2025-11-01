"""Conector a base de datos para el servicio offer_manager."""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Any, Optional, List, Dict
import logging
from src.clients.products_client import products_client

logger = logging.getLogger(__name__)


def get_connection():
    """Obtiene conexión a la base de datos."""
    try:
        host = os.getenv('DB_HOST')
        # Si es RDS (contiene .rds.amazonaws.com), usar SSL por defecto
        sslmode = os.getenv('DB_SSLMODE')
        if not sslmode and host and '.rds.amazonaws.com' in host:
            sslmode = 'require'
        elif not sslmode:
            sslmode = 'disable'
        
        conn = psycopg2.connect(
            host=host,
            port=os.getenv('DB_PORT', 5432),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD'),
            sslmode=sslmode
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
                result = cursor.fetchone()
                # Asegurar commit para operaciones como INSERT ... RETURNING
                try:
                    if cursor.statusmessage and cursor.statusmessage.split()[0] in {"INSERT", "UPDATE", "DELETE"}:
                        conn.commit()
                except Exception:
                    pass
                return result
            elif fetch_all:
                result = cursor.fetchall()
                return result
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


def get_products() -> List[Dict[str, Any]]:
    """Obtiene todos los productos activos para el selector a través del microservicio de products."""
    try:
        return products_client.get_all_active_products()
    except Exception as e:
        logger.error(f"Error obteniendo productos del microservicio: {e}")
        return []


def create_sales_plan(plan_data: Dict[str, Any]) -> Optional[int]:
    """Crea un nuevo plan de venta y retorna el ID del plan creado."""
    try:
        # Crear el plan principal
        plan_query = """
        INSERT INTO offers.sales_plans 
        (region, quarter, year, total_goal, created_by)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING plan_id
        """
        
        plan_params = (
            plan_data['region'],
            plan_data['quarter'],
            plan_data['year'],
            plan_data['total_goal'],
            plan_data['created_by']
        )
        
        plan_result = execute_query(plan_query, plan_params, fetch_one=True)
        if not plan_result:
            logger.error("Error: plan_result es None después de insertar plan principal")
            return None
        
        plan_id = plan_result['plan_id']
        logger.info(f"Plan creado con ID: {plan_id}")
        
        # Crear los productos del plan
        for product in plan_data['products']:
            product_query = """
            INSERT INTO offers.sales_plan_products 
            (plan_id, product_id, individual_goal)
            VALUES (%s, %s, %s)
            """
            
            product_params = (
                plan_id,
                product['product_id'],
                product['individual_goal']
            )
            
            result = execute_query(product_query, product_params)
            if result is None:
                logger.error(f"Error insertando producto {product['product_id']} para plan {plan_id}")
                return None
            
        logger.info(f"Plan {plan_id} creado exitosamente con {len(plan_data['products'])} productos")
        return plan_id
    except Exception as e:
        logger.error(f"Error en create_sales_plan: {str(e)}", exc_info=True)
        return None


def get_sales_plans(region: Optional[str] = None) -> List[Dict[str, Any]]:
    """Obtiene los planes de venta, opcionalmente filtrados por región."""
    base_query = """
    SELECT 
        sp.plan_id,
        sp.region,
        sp.quarter,
        sp.year,
        sp.total_goal,
        sp.is_active,
        sp.creation_date
    FROM offers.sales_plans sp
    """
    
    if region:
        query = base_query + " WHERE sp.region = %s ORDER BY sp.creation_date DESC"
        params = (region,)
    else:
        query = base_query + " ORDER BY sp.creation_date DESC"
        params = None
    
    result = execute_query(query, params, fetch_all=True)
    return result or []


def get_sales_plan_products(plan_id: int) -> List[Dict[str, Any]]:
    """Obtiene los productos de un plan de venta específico."""
    query = """
    SELECT 
        spp.plan_product_id,
        spp.product_id,
        spp.individual_goal
    FROM offers.sales_plan_products spp
    WHERE spp.plan_id = %s
    ORDER BY spp.plan_product_id
    """
    
    result = execute_query(query, (plan_id,), fetch_all=True)
    if not result:
        return []
    
    # Obtener todos los productos activos para enriquecer la información
    try:
        all_products = products_client.get_all_active_products()
        products_dict = {p['product_id']: p for p in all_products}
    except Exception as e:
        logger.error(f"Error obteniendo productos para enriquecer: {e}")
        products_dict = {}
    
    # Enriquecer con información del microservicio de products
    enriched_products = []
    for item in result:
        product_id = item['product_id']
        product_info = products_dict.get(product_id, {})
        
        enriched_item = {
            'plan_product_id': item['plan_product_id'],
            'product_id': product_id,
            'individual_goal': float(item['individual_goal']),
            'sku': product_info.get('sku', ''),
            'product_name': product_info.get('name', ''),
            'product_value': product_info.get('value', 0),
            'unit_name': product_info.get('unit_name', ''),
            'unit_symbol': product_info.get('unit_symbol', '')
        }
        enriched_products.append(enriched_item)
    
    return enriched_products


def get_sales_plan_by_id(plan_id: int) -> Optional[Dict[str, Any]]:
    """Obtiene un plan de venta específico por su ID."""
    query = """
    SELECT 
        sp.plan_id,
        sp.region,
        sp.quarter,
        sp.year,
        sp.total_goal,
        sp.is_active,
        sp.creation_date,
        sp.created_by
    FROM offers.sales_plans sp
    WHERE sp.plan_id = %s
    """

    result = execute_query(query, (plan_id,), fetch_one=True)
    return result

def save_visit(client_id: int, seller_id: int, date: str, findings: str):
    """
    Guarda la información de una nueva visita en la base de datos.

    :param visit_data: Diccionario con client_id, seller_id, date y findings.
    :return: Una instancia de la Visita recién creada con su visit_id.
    """
    conn = None
    new_visit_id = None

    conn = get_connection()
    cursor = conn.cursor()

    # Consulta SQL para insertar la nueva visita
    # RETURNING visit_id es crucial para obtener el ID generado automáticamente
    query = """
        INSERT INTO users.Visits (client_id, seller_id, date, findings)
        VALUES (%s, %s, %s, %s)
        RETURNING visit_id;
    """



    # 1. Ejecutamos la inserción
    new_visit_id = execute_query(query, (
        client_id,
        seller_id,
        date,  # La fecha ya viene validada como objeto date o similar
        findings,
    ), fetch_one=True)


    # 4. Creamos y devolvemos el objeto de dominio (Visita)
    # Asumiendo que existe una clase 'Visit' para mapear el registro.
    # Si no tienes una clase, simplemente devuelve el diccionario con el ID:
    return {
        "visit_id": new_visit_id,
        "client_id": client_id,
        "seller_id": seller_id,
        "date": date,
        "findings":findings,
    }
    # Si tienes una clase Visit, sería:
    # return Visit(visit_id=new_visit_id, client_id=..., seller_id=..., findings=...)

