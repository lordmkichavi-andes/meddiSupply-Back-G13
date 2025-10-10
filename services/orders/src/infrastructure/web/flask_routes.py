# src/infrastructure/web/flask_routes.py
from flask import Blueprint, jsonify
from src.application.use_cases import TrackOrdersUseCase

# El caso de uso se inyectará en la función de fábrica de Blueprint (ver app.py)
api_bp = Blueprint('api', __name__)


def create_api_blueprint(use_case: TrackOrdersUseCase):
    """
    Función de fábrica para inyectar el Caso de Uso en el Blueprint.
    Esto permite que el controlador (Web) dependa del Caso de Uso (Application).
    """

    @api_bp.route('/orders/track/<client_id>', methods=['GET'])
    def track_orders(client_id):
        """
        Maneja la solicitud HTTP, llama al Caso de Uso y retorna la respuesta.
        """
        try:
            # 1. Llamar al Caso de Uso (Lógica de Negocio)
            orders = use_case.execute(client_id)

            # 2. Manejo de mensajes específicos (Requisito del Frontend)
            if not orders:
                return jsonify({
                    "message": "¡Ups! Aún no tienes pedidos registrados.",
                    "orders": []
                }), 200

            # 3. Retornar la respuesta exitosa
            return jsonify(orders), 200

        except Exception:
            # Requisito: Si el sistema no puede recuperar la información
            return jsonify({
                "message": "¡Ups! No pudimos obtener los pedidos. Intenta nuevamente."
            }), 500

    return api_bp
