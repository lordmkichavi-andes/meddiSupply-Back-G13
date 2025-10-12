# src/domain/entities.py
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

# Mapeo de estados de pedido a colores (Regla de Negocio Central)
# Utilizamos constantes para los IDs para mantener el dominio limpio.
# Los IDs se mapean a los de tu script SQL de inserción: 1, 3, 4, 5, y 6 (Nuevo)
ORDER_STATUS_MAP = {
    6: {"name": "Pendiente de aprobación", "color": "amarillo"},
    5: {"name": "Procesando", "color": "azul"},
    1: {"name": "En camino", "color": "morado"},
    2: {"name": "Demorado", "color": "naranja"},
    3: {"name": "Entregado", "color": "verde"},
    4: {"name": "Cancelado", "color": "rojo"},
}

@dataclass
class OrderStatus:
    """Entidad para el estado de un pedido."""
    id: int
    name: str
    color: str

@dataclass
class Order:
    """Entidad central de Pedido."""
    order_id: str
    creation_date: datetime
    last_updated_date: datetime
    status_id: int
    estimated_delivery_date: Optional[datetime] = None

    @property
    def status(self) -> OrderStatus:
        """Devuelve el objeto Status mapeado."""
        status_info = ORDER_STATUS_MAP.get(
            self.status_id,
            {"name": "Desconocido", "color": "gris"}
        )
        return OrderStatus(self.status_id, status_info["name"], status_info["color"])
