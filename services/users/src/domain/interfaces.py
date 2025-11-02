from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .entities import Client

class UserRepository(ABC):
    """
    Contrato (Interfaz) para la capa de acceso a datos de Usuarios.
    La capa de Aplicación solo conoce esta Interfaz, no la implementación.
    """
    @abstractmethod
    def get_users_by_role(self, role: str) -> List[Client]:
        """Recupera la lista de usuarios con un rol específico."""
        pass

    @abstractmethod
    def get_users_by_seller(self, seller_id: int) -> List[Client]:
        """Recupera la lista de usuarios con un rol específico."""
        pass

    @abstractmethod
    def db_get_client_data(self, client_id: int) -> Optional[Dict[str, Any]]:
        """Obtiene el perfil enriquecido para el motor de recomendaciones."""
        pass

    @abstractmethod
    def save_visit(self, client_id: int, seller_id: int, date: str, findings: str):
        """Registra visitas"""
        pass