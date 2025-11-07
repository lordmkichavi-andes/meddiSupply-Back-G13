# src/domain/entities.py
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List

# Mapeo de estados de pedido a colores (Regla de Negocio Central)
# Utilizamos constantes para los IDs para mantener el dominio limpio.
# Los IDs se mapean a los de tu script SQL de inserción: 1, 3, 4, 5, y 6 (Nuevo)
ORDER_STATUS_MAP = {
    1: {"name": "En camino"},
    2: {"name": "Demorado"},
    3: {"name": "Entregado"},
    4: {"name": "Cancelado"},
    5: {"name": "Procesando"},
    6: {"name": "Pendiente de aprobación"},
}

@dataclass
class OrderItem:
    """Entidad que representa un producto dentro de una orden."""
    product_id: str
    quantity: int
    price_unit: float
    sku: str = ""
    name: str = ""

@dataclass
class OrderStatus:
    """Entidad para el estado de un pedido."""
    id: int
    name: str

@dataclass
class Order:
    """Entidad central de Pedido."""
    order_id: Optional[str]
    client_id: str
    creation_date: datetime
    last_updated_date: datetime
    status_id: int
    items: List[OrderItem]
    order_value: int
    seller_id: int
    estimated_delivery_date: Optional[datetime] = None,
    address: str = ""
    client_name: str = ""
    seller_name: str = ""



    @property
    def status(self) -> OrderStatus:
        """Devuelve el objeto Status mapeado."""
        status_info = ORDER_STATUS_MAP.get(
            self.status_id,
            {"name": "Desconocido"}
        )
        return OrderStatus(self.status_id, status_info["name"])


