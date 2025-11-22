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
    Consulta usuarios del servicio de users y los combina con datos locales.
    """
    try:
        # 1. Obtener datos locales de la base de datos (client_id, address, latitud, longitud, demanda)
        query = """
        SELECT
            c.client_id AS id,
            c.user_id,
            c.address AS direccion,
            c.latitude AS latitud,
            c.longitude AS longitud,
            SUM(CASE WHEN o.status_id = 2 THEN 1 ELSE 0 END) AS demanda
        FROM
            users.Clients c
        LEFT JOIN
            orders.Orders o ON c.client_id = o.client_id
        GROUP BY
            c.client_id, c.user_id, c.address, c.latitude, c.longitude
        ORDER BY
            demanda DESC, c.client_id
        """
        local_data = execute_query(query, fetch_all=True)
        
        if not local_data:
            return []
        
        # 2. Consultar usuarios del servicio de users
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
        
        # 3. Crear diccionario de usuarios por user_id para búsqueda rápida
        users_dict = {user.get('user_id'): user for user in users_data}
        
        # 4. Combinar datos locales con datos de usuarios
        result = []
        for client in local_data:
            user_id = client.get('user_id')
            user_info = users_dict.get(user_id) if user_id else None
            
            # Construir nombre desde el servicio de users
            nombre = 'Cliente sin nombre'  # Fallback si no hay usuario
            if user_info:
                name = user_info.get('name', '')
                last_name = user_info.get('last_name', '')
                nombre = f"{name} {last_name}".strip() if name or last_name else nombre
            
            result.append({
                'id': client.get('id'),
                'nombre': nombre,
                'direccion': client.get('direccion'),
                'latitud': client.get('latitud'),
                'longitud': client.get('longitud'),
                'demanda': client.get('demanda', 0)
            })
        
        # 5. Ordenar por demanda y nombre
        result.sort(key=lambda x: (-x['demanda'], x['nombre']))
        
        return result
        
    except Exception as e:
        logger.error(f"Error en get_clientes: {e}")
        return []

def get_clientes_by_seller(seller_id: int) -> List[Dict[str, Any]]:
    """Obtiene todos los clientes filtrados por seller_id.
    Consulta usuarios del servicio de users y los combina con datos locales.
    """
    try:
        # 1. Obtener datos locales de la base de datos (client_id, address, latitud, longitud)
    query = """
    SELECT
    c.client_id AS id,
            c.user_id,
    c.address AS address,
    c.latitude AS latitude,
    c.longitude AS longitude
    FROM
        users.Clients c
    WHERE
        c.seller_id = %s
        ORDER BY
            c.client_id
        """
        local_data = execute_query(query, (seller_id,), fetch_all=True)
        
        if not local_data:
            return []
        
        # 2. Consultar usuarios del servicio de users filtrados por seller_id
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
        
        # 3. Crear diccionario de usuarios por client_id para búsqueda rápida
        users_dict = {user.get('client_id'): user for user in users_data}
        
        # 4. Combinar datos locales con datos de usuarios
        result = []
        for client in local_data:
            client_id = client.get('id')
            user_info = users_dict.get(client_id) if client_id else None
            
            # Usar datos del servicio de users si están disponibles, sino usar datos locales
            if user_info:
                # El servicio de users devuelve 'name' que es el perfil del cliente
                name = user_info.get('name', 'Cliente sin nombre')
                client_name = name
                # Preferir address, latitude, longitude del servicio de users si están disponibles
                address = user_info.get('address') or client.get('address')
                latitude = user_info.get('latitude') or client.get('latitude')
                longitude = user_info.get('longitude') or client.get('longitude')
            else:
                # Fallback a datos locales si no hay información del servicio de users
                name = 'Cliente sin nombre'
                client_name = name
                address = client.get('address')
                latitude = client.get('latitude')
                longitude = client.get('longitude')
            
            result.append({
                'id': client_id,
                'name': name,
                'client': client_name,
                'address': address,
                'latitude': latitude,
                'longitude': longitude
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error en get_clientes_by_seller: {e}")
        return []
