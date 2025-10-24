from flask import Blueprint, jsonify, request
from src.application.use_cases import TrackOrdersUseCase, CreateOrderUseCase
from src.domain.entities import Order, OrderItem
from datetime import datetime

# ELIMINAMOS la declaración global de api_bp.
# Ya no necesitamos el comentario sobre la inyección de dependencias aquí,
# ya que la crearemos dentro de la función de fábrica.

def create_api_blueprint(track_case: TrackOrdersUseCase, create_case: CreateOrderUseCase):
    """
    Función de fábrica para inyectar el Caso de Uso en el Blueprint.
    Crea y registra un nuevo Blueprint en cada llamada para evitar conflictos en tests.
    """
    # MOVER LA CREACIÓN DEL BLUEPRINT AQUÍ
    api_bp = Blueprint('api', __name__)


    @api_bp.route('/track/<int:client_id>', methods=['GET'])
    def track_orders(client_id):
        try:
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
        except Exception:
            # Requisito: Si el sistema no puede recuperar la información
            return jsonify({
                "message": "¡Ups! No pudimos obtener los pedidos. Intenta nuevamente."
            }), 500

    @api_bp.route('/', methods=['POST'])
    def create_order():
        try:
            data = request.json
            # Validaciones mínimas
            if "client_id" not in data or "products" not in data:
                return jsonify({"error": "client_id and products are required"}), 400

            # Procesar los productos
            order_items = []
            order_value = 0
            for item in data["products"]:
                product_id = item.get("product_id")
                quantity = item.get("quantity")
                price_unit = item.get("price_unit")
                order_value += quantity * price_unit
                if not product_id or not quantity:
                    return jsonify({"error": "Each product must have product_id and quantity"}), 400
                order_item = OrderItem(
                    product_id=product_id,
                    quantity=quantity,
                    price_unit=price_unit,
                    # Puedes incluir price_at_purchase si tu modelo lo requiere
                )
                order_items.append(order_item)
                # Crear la orden base
            order = Order(
                order_id=None,
                client_id=data["client_id"],
                creation_date=datetime.utcnow(),
                last_updated_date=datetime.utcnow(),
                status_id=data.get("status_id"),
                estimated_delivery_date=data.get("estimated_delivery_time"),
                orders=order_items,
                order_value = order_value
            )
            # Ejecutar el caso de uso para guardar la orden y los productos
            created_order = create_case.execute(order, order_items)
            return jsonify({
                "order_id": created_order.order_id,
                "message": "Order created successfully"
            }), 201

        except Exception:
            # Requisito: Si el sistema no puede recuperar la información
            return jsonify({
                "message": "¡Ups! No pudimos crear el pedido. Intenta nuevamente."
            }), 500

    return api_bp
