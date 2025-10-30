"""Cliente HTTP para el microservicio de products."""

import os
import requests
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ProductsClient:
    """Cliente para comunicarse con el microservicio de products."""
    
    def __init__(self):
        # Por defecto 8081 para entorno local (host). En Docker se sobreescribe con env.
        self.base_url = os.getenv('PRODUCTS_SERVICE_URL', 'http://localhost:8081')
        self.timeout = int(os.getenv('PRODUCTS_SERVICE_TIMEOUT', '10'))
    
    def _get(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Realiza una petición GET al servicio de products."""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al consumir el servicio de products en {endpoint}: {e}")
            return None
    
    def get_all_active_products(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los productos activos con información completa.
        """
        result = self._get('/products/active')
        if result is None:
            return []
        
        # El endpoint retorna una lista directamente
        if isinstance(result, list):
            return result
        return []


# Instancia global del cliente
products_client = ProductsClient()
