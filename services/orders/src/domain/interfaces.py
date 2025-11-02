# src/domain/interfaces.py
from abc import ABC, abstractmethod
from typing import List
from .entities import Order, OrderItem
from typing import List, Dict, Any

class OrderRepository(ABC):
    """
    Contrato (Interfaz) para la capa de acceso a datos de Pedidos.
    La capa de Aplicación solo conoce esta Interfaz, no la implementación.
    """
    @abstractmethod
    def get_orders_by_client_id(self, user_id: str) -> List[Order]:
        """Recupera la lista de pedidos para un cliente."""
        pass

    @abstractmethod
    def insert_order(self, order: Order, order_items: List[OrderItem]) -> Order:
        """Inserta una nueva orden en la base de datos y retorna la entidad creada."""
        pass

    @abstractmethod
    def get_all_orders_with_details(self) -> List[Dict[str, Any]]:
        """
        Recupera TODAS las órdenes con sus líneas de producto y detalles agrupados.
        Usado por el GetAllOrdersUseCase.
        """
        pass
        
    @abstractmethod
    def get_recent_purchase_history(self, client_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recupera el historial reciente (SKU y nombre) de productos comprados por un cliente.
        Usado por el GetClientPurchaseHistoryUseCase.
        """
        pass
