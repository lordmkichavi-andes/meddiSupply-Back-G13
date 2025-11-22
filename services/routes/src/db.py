"""Conector a base de datos transaccional para el servicio de rutas."""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Any, Optional, List, Dict
import logging
import requests

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
    query = "SELECT vehicle_id, capacity, color, label FROM routes.vehicles ORDER BY vehicle_id"
    result = execute_query(query, fetch_all=True)
    return result or []


def get_clientes() -> List[Dict[str, Any]]:
    """Obtiene todos los clientes.
    Consulta usuarios del servicio de users. La demanda se calcula desde orders local.
    """
    try:
        # 1. Consultar usuarios del servicio de users (obtiene todos los datos del cliente)
        users_service_url = os.getenv('USERS_SERVICE_URL', 'http://MediSu-MediS-5XPY2MhrDivI-109634141.us-east-1.elb.amazonaws.com')
        users_endpoint = f"{users_service_url}/users/clients"
        
        try:
            response = requests.get(users_endpoint, timeout=5)
            if response.status_code == 200:
                users_data = response.json().get('clients', [])
            else:
                logger.warning(f"Error al consultar servicio de users: {response.status_code}")
                users_data = []
        except Exception as e:
            logger.error(f"Error consultando servicio de users: {e}")
            users_data = []
        
        if not users_data:
            return []
        
        # 2. Obtener demanda desde orders local usando client_id del MS
        client_ids = [user.get('client_id') for user in users_data if user.get('client_id')]
        
        demanda_dict = {}
        if client_ids:
            # Consultar demanda desde orders.Orders usando client_id
            placeholders = ','.join(['%s'] * len(client_ids))
            query = f"""
            SELECT
                client_id,
                SUM(CASE WHEN status_id = 2 THEN 1 ELSE 0 END) AS demanda
            FROM
                orders.Orders
            WHERE
                client_id IN ({placeholders})
            GROUP BY
                client_id
            """
            demanda_data = execute_query(query, tuple(client_ids), fetch_all=True)
            demanda_dict = {item.get('client_id'): item.get('demanda', 0) for item in (demanda_data or [])}
        
        # 3. Construir resultado con datos del servicio de users
        result = []
        for user in users_data:
            client_id = user.get('client_id')
            
            # Construir nombre completo
            name = user.get('name', '')
            last_name = user.get('last_name', '')
            nombre = f"{name} {last_name}".strip() if name or last_name else 'Cliente sin nombre'
            
            result.append({
                'id': client_id or user.get('user_id'),  # Usar client_id si está disponible
                'nombre': nombre,
                'direccion': user.get('address'),
                'latitud': user.get('latitude'),
                'longitud': user.get('longitude'),
                'demanda': demanda_dict.get(client_id, 0) if client_id else 0
            })
        
        # 4. Ordenar por demanda y nombre
        result.sort(key=lambda x: (-x['demanda'], x['nombre']))
        
        return result
        
    except Exception as e:
        logger.error(f"Error en get_clientes: {e}")
        return []

def get_clientes_by_seller(seller_id: int) -> List[Dict[str, Any]]:
    """Obtiene todos los clientes filtrados por seller_id.
    Consulta usuarios del servicio de users (obtiene todos los datos del cliente).
    """
    try:
        # 1. Consultar usuarios del servicio de users filtrados por seller_id
        # Este endpoint ya devuelve client_id, address, latitude, longitude, name
        users_service_url = os.getenv('USERS_SERVICE_URL', 'http://MediSu-MediS-5XPY2MhrDivI-109634141.us-east-1.elb.amazonaws.com')
        users_endpoint = f"{users_service_url}/users/clients/{seller_id}"
        
        try:
            response = requests.get(users_endpoint, timeout=5)
            if response.status_code == 200:
                users_data = response.json().get('clients', [])
            else:
                logger.warning(f"Error al consultar servicio de users: {response.status_code}")
                users_data = []
        except Exception as e:
            logger.error(f"Error consultando servicio de users: {e}")
            users_data = []
        
        if not users_data:
            return []
        
        # 2. El servicio de users ya devuelve todos los datos necesarios:
        # client_id, name (perfil), address, latitude, longitude
        result = []
        for user in users_data:
            name = user.get('name', 'Cliente sin nombre')
            client_name = name  # El servicio devuelve 'name' que es el perfil
            
            result.append({
                'id': user.get('client_id'),
                'name': name,
                'client': client_name,
                'address': user.get('address'),
                'latitude': user.get('latitude'),
                'longitude': user.get('longitude')
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error en get_clientes_by_seller: {e}")
        return []
