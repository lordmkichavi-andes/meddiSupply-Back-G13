import unittest
import json
from unittest.mock import MagicMock

# Importa Flask y los componentes necesarios para las pruebas de API
from flask import Flask, Blueprint, jsonify


# ==============================================================================
# MOCKS Y ESTRUCTURAS MÍNIMAS (Deben estar en el mismo archivo o importadas)
# ==============================================================================

# 1. Mock de la Interfaz del Caso de Uso (simulamos src.application.use_cases.GetClientUsersUseCase)
class GetClientUsersUseCase:
    """Mock de la clase de Caso de Uso."""

    def execute(self):
        raise NotImplementedError


# 2. Mock de la Entidad Cliente (Necesitamos un to_dict para serialización)
class MockClient:
    """Mock mínimo para simular una entidad Client con un método de serialización."""

    def __init__(self, user_id, name):
        self.user_id = user_id
        self.name = name

    def to_dict(self):
        """Método necesario para que Flask pueda serializarlo a JSON."""
        return {"user_id": self.user_id, "name": self.name, "role": "CLIENT"}


# Datos serializados de ejemplo para las respuestas esperadas
EXPECTED_CLIENT_DATA = [
    MockClient("C001", "Juan").to_dict(),
    MockClient("C002", "Maria").to_dict(),
]


# 3. Código del Blueprint a testear (copiado para ser autocontenido)
def create_user_api_blueprint(use_case: GetClientUsersUseCase):
    user_api_bp = Blueprint('api', __name__)

    @user_api_bp.route('/users/clients', methods=['GET'])
    def get_client_users():
        try:
            # NOTA: En tu código anterior, el controlador debería llamar a .to_dict()
            # si el Caso de Uso retorna entidades. Asumo esta conversión aquí.
            client_entities = use_case.execute()
            users = [c.to_dict() for c in client_entities]  # Simulación de la conversión a diccionario

            if not users:
                return jsonify({
                    "message": "No se encontraron usuarios con rol CLIENT.",
                    "users": []
                }), 404

            return jsonify({
                "users": users
            }), 200

        except Exception as e:
            return jsonify({
                "message": "No se pudieron obtener los usuarios. Intenta nuevamente.",
                "error": str(e)
            }), 500

    return user_api_bp


# ==============================================================================
# CLASE DE TEST
# ==============================================================================

class TestUserApiBlueprint(unittest.TestCase):

    def setUp(self):
        """Configuración de mocks y la aplicación Flask."""

        # 1. Crear mock del Caso de Uso que se inyectará
        self.mock_use_case = MagicMock(spec=GetClientUsersUseCase)

        # 2. Crear la aplicación Flask de prueba
        app = Flask(__name__)

        # 3. Registrar el Blueprint inyectando el mock
        api_bp = create_user_api_blueprint(self.mock_use_case)
        app.register_blueprint(api_bp)

        # 4. Configurar el cliente de prueba para hacer peticiones simuladas
        self.app = app.test_client()
        self.app.testing = True

    # ------------------------------------
    # Caso 1: Éxito (200 OK)
    # ------------------------------------
    def test_get_client_users_success(self):
        """Debe retornar 200 OK y la lista de usuarios."""

        # Simular que el caso de uso retorna dos entidades Cliente
        client_entities = [MockClient("C001", "Juan"), MockClient("C002", "Maria")]
        self.mock_use_case.execute.return_value = client_entities

        # Ejecutar la solicitud GET
        response = self.app.get('/users/clients')

        # Verificaciones
        self.assertEqual(response.status_code, 200)
        self.mock_use_case.execute.assert_called_once()

        data = json.loads(response.data)
        self.assertIn("users", data)
        self.assertEqual(data["users"], EXPECTED_CLIENT_DATA)

    # ------------------------------------
    # Caso 2: No Encontrado (404 Not Found)
    # ------------------------------------
    def test_get_client_users_not_found(self):
        """Debe retornar 404 Not Found cuando la lista de usuarios está vacía."""

        # Simular que el caso de uso retorna una lista vacía
        self.mock_use_case.execute.return_value = []

        # Ejecutar la solicitud GET
        response = self.app.get('/users/clients')

        # Verificaciones
        self.assertEqual(response.status_code, 404)

        data = json.loads(response.data)
        self.assertIn("message", data)
        self.assertEqual(data["message"], "No se encontraron usuarios con rol CLIENT.")
        self.assertEqual(data["users"], [])

    # ------------------------------------
    # Caso 3: Error Interno (500 Internal Server Error)
    # ------------------------------------
    def test_get_client_users_internal_error(self):
        """Debe retornar 500 Internal Server Error si el Caso de Uso falla."""

        error_message = "Error de conexión con el repositorio."

        # Simular que el caso de uso lanza una excepción
        self.mock_use_case.execute.side_effect = Exception(error_message)

        # Ejecutar la solicitud GET
        response = self.app.get('/users/clients')

        # Verificaciones
        self.assertEqual(response.status_code, 500)

        data = json.loads(response.data)
        self.assertIn("message", data)
        self.assertIn("error", data)
        self.assertEqual(data["message"], "No se pudieron obtener los usuarios. Intenta nuevamente.")
        self.assertEqual(data["error"], error_message)


if __name__ == '__main__':
    unittest.main()