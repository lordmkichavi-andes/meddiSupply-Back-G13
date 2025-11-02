from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, runtime_checkable, Protocol
from .entities import Client
from werkzeug.datastructures import FileStorage

class UserRepository(ABC):
    @abstractmethod
    def get_users_by_role(self, role: str) -> List[Client]:
        pass

    @abstractmethod
    def get_users_by_seller(self, seller_id: int) -> List[Client]:
        pass

    @abstractmethod
    def db_get_client_data(self, client_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_by_id(self, visit_id: int) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def save_visit(self, client_id: int, seller_id: int, date: str, findings: str):
        """Registra visitas"""
        pass

    @abstractmethod
    def get_recent_evidences_by_client(self, client_id: int) -> List[Dict[str, str]]:
        """
        Obtiene las URLs y tipos de archivos de evidencia visual (media) 
        asociados a las visitas recientes de un cliente.
        """
        pass

    @abstractmethod
    def get_products(self) -> List[Dict[str, Any]]:
        """Obtiene el catálogo de productos activos."""
        pass

@runtime_checkable
class StorageServiceInterface(Protocol):
    """
    Define el contrato para cualquier servicio de almacenamiento de archivos.
    Esto permite que la Capa de Aplicación (Use Case) dependa de la abstracción,
    no de la implementación concreta (como boto3/S3).
    """

    @abstractmethod
    def upload_file(self, file: FileStorage, visit_id: int) -> str:
        """
        Sube un archivo y retorna su URL de acceso.
        """
        pass