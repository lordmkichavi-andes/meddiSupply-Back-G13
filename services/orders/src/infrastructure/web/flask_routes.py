from flask import Blueprint, jsonify
from orders.src.application.use_cases import TrackOrdersUseCase

# ELIMINAMOS la declaración global de api_bp.
# Ya no necesitamos el comentario sobre la inyección de dependencias aquí,
# ya que la crearemos dentro de la función de fábrica.

def create_api_blueprint(use_case: TrackOrdersUseCase):
    """
    Función de fábrica para inyectar el Caso de Uso en el Blueprint.
    Crea y registra un nuevo Blueprint en cada llamada para evitar conflictos en tests.
    """
    # MOVER LA CREACIÓN DEL BLUEPRINT AQUÍ
    api_bp = Blueprint('api', __name__)

    @api_bp.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok'})

    @api_bp.route('/track/<client_id>', methods=['GET'])
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
                }), 404

            # 3. Retornar la respuesta exitosa
            return jsonify(orders), 200

        except Exception:
            # Requisito: Si el sistema no puede recuperar la información
            return jsonify({
                "message": "¡Ups! No pudimos obtener los pedidos. Intenta nuevamente."
            }), 500

    return api_bp
