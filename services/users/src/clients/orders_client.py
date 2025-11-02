"""Cliente HTTP para el microservicio de orders."""

import os
import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class OrdersClient:
    """Cliente para comunicarse con el microservicio de orders."""
    
    def __init__(self):
        self.base_url = os.getenv('ORDERS_SERVICE_URL', 'http://MediSu-MediS-5XPY2MhrDivI-109634141.us-east-1.elb.amazonaws.com/')
        self.timeout = int(os.getenv('ORDERS_SERVICE_TIMEOUT', '10'))
    
    def _get(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Realiza una petición GET al servicio de orders."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status() 
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al consumir el servicio de orders en {endpoint}: {e}")
            return None
    
    def get_client_purchase_history(self, client_id: int) -> List[Dict[str, Any]]:
        """
        Obtiene el historial de compras reciente de un cliente.
        
        El endpoint esperado es: GET /history/<client_id>
        Retorna {"products": [...]}.
        """
        endpoint = f"/history/{client_id}"
        
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 404:
                return []
            
            response.raise_for_status() 
            
            result = response.json()
            if isinstance(result, dict) and 'products' in result:
                return result['products']
            
            return []
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener historial del cliente {client_id} en Orders Service: {e}")
            return []

    def get_client_detail(self, client_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene la información de detalle de un único cliente.
        
        El endpoint esperado es: GET /<client_id>
        Retorna la información del cliente {...} o None si no se encuentra.
        """
        endpoint = f"/users/detail/{client_id}"
        
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, timeout=self.timeout)
            
            if response.status_code == 404:
                logger.warning(f"Cliente con ID {client_id} no encontrado en el servicio externo.")
                return None
            
            response.raise_for_status() 
            
            result = response.json()
            
            if isinstance(result, dict):
                return result
            
            return None 
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener detalle del cliente {client_id} en Orders Service: {e}")
            return None

orders_client = OrdersClient()