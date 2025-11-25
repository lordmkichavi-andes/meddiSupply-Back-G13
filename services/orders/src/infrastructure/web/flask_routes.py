from flask import Blueprint, jsonify, request, current_app
from src.application.use_cases import TrackOrdersUseCase, CreateOrderUseCase, GetClientPurchaseHistoryUseCase, GetAllOrdersUseCase, GetOrdersByIDUseCase
from src.domain.entities import Order, OrderItem
from datetime import datetime
from typing import List, Dict, Any



# ELIMINAMOS la declaración global de api_bp.
# Ya no necesitamos el comentario sobre la inyección de dependencias aquí,
# ya que la crearemos dentro de la función de fábrica.

def create_api_blueprint(
    track_case: TrackOrdersUseCase, 
    create_case: CreateOrderUseCase,
    history_case: GetClientPurchaseHistoryUseCase,
    all_orders_case: GetAllOrdersUseCase,
    get_order_by_id_case: GetOrdersByIDUseCase
):
    """
    Función de fábrica para inyectar el Caso de Uso en el Blueprint.
    Crea y registra un nuevo Blueprint en cada llamada para evitar conflictos en tests.
    """
    # MOVER LA CREACIÓN DEL BLUEPRINT AQUÍ
    api_bp = Blueprint('api', __name__)


    @api_bp.route('/track/<int:client_id>', methods=['GET'])
    def track_orders(client_id):
        """
        Maneja la solicitud HTTP, llama al Caso de Uso y retorna la respuesta.
        """
        # 1. Llamar al Caso de Uso (Lógica de Negocio)
        orders = track_case.execute(client_id)

        # 2. Manejo de mensajes específicos (Requisito del Frontend)
        if not orders:
            return jsonify({
                "message": "¡Ups! Aún no tienes pedidos registrados.",
                "orders": []
            }), 404

        # 3. Retornar la respuesta exitosa
        return jsonify(orders), 200

    @api_bp.route('/', methods=['POST'])
    def create_order():
        data = request.json
        # Validaciones mínimas
        if "client_id" not in data or "products" not in data:
            return jsonify({"error": "client_id and products are required"}), 400

        order_items = []
        products_data = []
        order_value = 0

        for item in data["products"]:
            product_id = item.get("product_id")
            quantity = item.get("quantity")
            price_unit = item.get("price_unit")
            order_value += quantity * price_unit

            if not product_id or not quantity:
                return jsonify({"error": "Each product must have product_id and quantity"}), 400

            # Línea de la orden
            order_item = OrderItem(
                product_id=product_id,
                quantity=quantity,
                price_unit=price_unit
            )
            order_items.append(order_item)

            # Datos del producto como dict (no entidad)
            products_data.append({
                "product_id": product_id,
                "name": item.get("name"),
                "sku": item.get("sku"),
                "category_name": item.get("category_name"),
                "total_quantity": item.get("total_quantity"),
                "value": item.get("value"),
                "image_url": item.get("image_url")
            })

        # Cabecera de la orden
        order = Order(
            order_id=None,
            client_id=data["client_id"],
            seller_id=data["seller_id"],
            creation_date=datetime.utcnow(),
            last_updated_date=datetime.utcnow(),
            status_id=data.get("status_id"),
            estimated_delivery_date=data.get("estimated_delivery_time"),
            items=order_items,
            order_value=order_value
        )

        # Caso de uso recibe también products_data
        created_order = create_case.execute(order, order_items, products_data)

        return jsonify({
            "order_id": created_order.order_id,
            "message": "Order created successfully"
        }), 201


    @api_bp.route('/history/<int:client_id>', methods=['GET']) 
    def get_purchase_history(client_id):
        """
        Endpoint para el Orquestador: Obtiene el historial reciente de productos comprados.
        """
        try:
            history = history_case.execute(client_id)

            if not history:
                return jsonify({"products": []}), 404

            return jsonify({"products": history}), 200

        except Exception as e:
            current_app.logger.error(f"Error al consultar historial del cliente {client_id}: {e}")
            return jsonify({"message": "Error interno del servicio de órdenes al obtener historial."}), 500

    @api_bp.route('/<int:order_id>', methods=['GET'])
    def get_order_by_id(order_id):
        try:
            order = get_order_by_id_case.execute(order_id)

            if not order:
                return jsonify({"order": {}}), 404

            return jsonify({"order": order}), 200

        except Exception as e:
            current_app.logger.error(f"Error al consultar el pedido identificado con el id:  {order_id}: {e}")
            return jsonify({"message": "Error interno del servicio de órdenes al obtener información del pedido ."}), 500

    @api_bp.route('/all', methods=['GET'])
    def get_all_orders():
        """
        Endpoint para Reportes/Web: Retorna todas las órdenes con sus líneas detalladas.
        """
        try:
            orders = all_orders_case.execute()

            if not orders:
                return jsonify({"orders": []}), 404

            return jsonify({"orders": orders}), 200

        except Exception as e:
            current_app.logger.error(f"Error al consultar todas las órdenes: {e}")
            return jsonify({"message": "Error interno del servicio de órdenes al obtener todas las órdenes."}), 500
    return api_bp
