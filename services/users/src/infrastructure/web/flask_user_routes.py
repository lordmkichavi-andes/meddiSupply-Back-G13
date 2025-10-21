from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from dateutil import parser

from src.application.use_cases import GetClientUsersUseCase
from src.application.register_visit_usecase import RegisterVisitUseCase


def create_user_api_blueprint(
        use_case: GetClientUsersUseCase,
        register_visit_use_case: RegisterVisitUseCase,
):
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

    @user_api_bp.route('/visit', methods=['POST'])
    def register_visit():
        """
        Maneja la solicitud HTTP POST para registrar una nueva visita,
        validando los datos de entrada, y llama al Caso de Uso.
        """
        data = request.get_json()

        # 1. Extracción y Validación de Campos Vacíos
        required_fields = ['client_id', 'seller_id', 'date', 'findings']

        # Verifica que todos los campos requeridos estén en el cuerpo de la petición
        if not all(field in data for field in required_fields):
            missing_fields = [field for field in required_fields if field not in data]
            return jsonify({
                "message": "Faltan campos requeridos.",
                "missing": missing_fields
            }), 400

        # Verifica que ningún campo requerido esté vacío (o None)
        if any(not data[field] for field in required_fields):
            return jsonify({
                "message": "Ningún campo puede estar vacío."
            }), 400

        client_id = data.get('client_id')
        seller_id = data.get('seller_id')
        fecha_str = data.get('date')
        findings = data.get('findings')

        try:
            # Intenta convertir la cadena de fecha (fecha_str) a un objeto datetime
            # 'parser.parse' intentará adivinar el formato (DD-MM-YYYY, YYYY-MM-DD, etc.)
            visit_date = parser.parse(fecha_str)
        except ValueError:
            # Atrapa el error si la cadena no es una fecha válida en ningún formato reconocido
            return jsonify({
                "message": "La cadena proporcionada no corresponde a un formato de fecha válido."
            }), 400

        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)

        # La fecha no debe ser mayor a la fecha actual
        if visit_date > now:
            return jsonify({
                "message": "La fecha de la visita no puede ser posterior a la fecha actual."
            }), 400

        # La fecha debe ser en los últimos 30 días
        if visit_date < thirty_days_ago:
            return jsonify({
                "message": "La fecha de la visita no puede ser anterior a 30 días."
            }), 400

        try:
            # 3. Llamar al Caso de Uso (Lógica de Negocio)
            # Se asume que el Caso de Uso espera los datos de la visita para registrarlos.
            # Es importante que el caso de uso reciba los datos adecuados.
            response = register_visit_use_case.execute(
                client_id=client_id,
                seller_id=seller_id,
                date=visit_date.date(),  # Se pasa como objeto date o str según necesite tu CU
                findings=findings,
            )

            # 4. Retornar la respuesta exitosa
            return jsonify({
                "message": "Visita registrada exitosamente.",
                "visit": response["visit"]
            }), 201  # 201 Created es apropiado para POST de creación

        except Exception as e:
            # Si el sistema no puede registrar la información (ej. error de BD)
            return jsonify({
                "message": "No se pudo registrar la visita. Intenta nuevamente.",
                "error": str(e)
            }), 500

    return user_api_bp