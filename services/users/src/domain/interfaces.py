from abc import ABC, abstractmethod
from typing import List
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