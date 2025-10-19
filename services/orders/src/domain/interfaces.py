# src/domain/interfaces.py
from abc import ABC, abstractmethod
from typing import List
from .entities import Order

class OrderRepository(ABC):
    """
    Contrato (Interfaz) para la capa de acceso a datos de Pedidos.
    La capa de Aplicación solo conoce esta Interfaz, no la implementación.
    """
    @abstractmethod
    def get_orders_by_client_id(self, client_id: str) -> List[Order]:
        """Recupera la lista de pedidos para un cliente."""
        pass

    @abstractmethod
    def insert_order(self, order: Order) -> Order:
        """Inserta una nueva orden en la base de datos y retorna la entidad creada."""
        pass
