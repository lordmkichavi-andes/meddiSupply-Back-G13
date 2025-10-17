# src/application/use_cases.py
from typing import List, Dict, Any
from src.domain.interfaces import OrderRepository
from src.domain.entities import Order


class TrackOrdersUseCase:
    """
    Caso de uso: Obtener, procesar y formatear pedidos para el seguimiento.
    Depende de OrderRepository (patrón de inyección de dependencias).
    """

    def __init__(self, order_repository: OrderRepository):
        self.repository = order_repository

    def execute(self, client_id: str) -> List[Dict[str, Any]]:
        """
        Ejecuta la lógica de negocio para obtener la lista de pedidos.
        """
        # 1. Obtener datos (Usando el Repositorio - Capa de Infraestructura)
        orders = self.repository.get_orders_by_client_id(client_id)

        # 2. Requisito: Si no hay pedidos
        if not orders:
            return []

        # 3. Requisito: Ordenar por fecha de última actualización descendente
        orders.sort(key=lambda order: order.last_updated_date, reverse=True)

        # 4. Formatear y aplicar reglas de negocio (estados, fechas)
        formatted_orders = []
        for order in orders:

            estimated_delivery = None
            # Requisito: Solo Procesando (5) y En camino (1) necesitan fecha estimada
            if order.status_id in [5, 1]:
                if order.estimated_delivery_date:
                    estimated_delivery = order.estimated_delivery_date.strftime('%Y-%m-%d %H:%M')
                else:
                    # Requisito: Mensaje si no existe fecha programada
                    estimated_delivery = "Entrega pendiente de programación"

            formatted_orders.append({
                "numero_pedido": order.order_id,
                "fecha_creacion": order.creation_date.strftime('%Y-%m-%d'),
                "fecha_ultima_actualizacion": order.last_updated_date.strftime('%Y-%m-%d %H:%M:%S'),
                "estado_nombre": order.status.name,
                "fecha_entrega_estimada": estimated_delivery
            })

        return formatted_orders

class CreateOrderUseCase:
    """
    Caso de uso: Crear una nueva orden.
    """

    def __init__(self, order_repository: OrderRepository):
        self.repository = order_repository

    def execute(self, order: Order) -> Order:
        """
        Ejecuta la lógica para insertar una nueva orden.
        """
        return self.repository.insert_order(order)
