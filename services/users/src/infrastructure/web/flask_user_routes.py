from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from dateutil import parser

from src.application.use_cases import GetClientUsersUseCase


def create_user_api_blueprint(use_case: GetClientUsersUseCase):
    """
    Función de fábrica para inyectar el Caso de Uso en el Blueprint.
    Crea y registra un nuevo Blueprint en cada llamada para evitar conflictos en tests.
    """
    user_api_bp = Blueprint('api', __name__)

    @user_api_bp.route('/clients', methods=['GET'])
    def get_client_users():
        """
        Maneja la solicitud HTTP para obtener usuarios CLIENT,
        llama al Caso de Uso y retorna la respuesta.
        """
        try:
            # 1. Llamar al Caso de Uso (Lógica de Negocio)
            users = use_case.execute()

            # 2. Manejo de mensajes específicos
            if not users:
                return jsonify({
                    "message": "No se encontraron usuarios con rol CLIENT.",
                    "clients": []
                }), 404

            # 3. Retornar la respuesta exitosa
            return jsonify({
                "clients": users
            }), 200

        except Exception as e:
            # Si el sistema no puede recuperar la información
            return jsonify({
                "message": "No se pudieron obtener los usuarios. Intenta nuevamente.",
                "error": str(e)
            }), 500

    @user_api_bp.route('/clients/<int:seller_id>', methods=['GET'])
    def get_client_users_by_seller(seller_id):
        """
        Maneja la solicitud HTTP para obtener usuarios CLIENT filtrados por seller_id,
        llama al Caso de Uso y retorna la respuesta.
        """
        try:
            # 1. Llamar al Caso de Uso (Lógica de Negocio)
            # Se pasa el seller_id para filtrar los clientes
            users = use_case.execute_by_seller(seller_id=seller_id)

            # 2. Manejo de mensajes específicos
            if not users:
                return jsonify({
                    # Mensaje más específico para el contexto
                    "message": f"No se encontraron clientes asignados al vendedor con ID {seller_id}.",
                    "users": []
                }), 404

            # 3. Retornar la respuesta exitosa
            return jsonify({
                "clients": users
            }), 200

        except Exception as e:
            # Si el sistema no puede recuperar la información
            return jsonify({
                "message": "No se pudieron obtener los clientes. Intenta nuevamente.",
                "error": str(e)
            }), 500
    return user_api_bp