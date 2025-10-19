import unittest
import json
from unittest.mock import Mock
from flask import Flask
from users.src.infrastructure.web.flask_user_routes import create_user_api_blueprint

# Datos simulados
MOCK_USER_DATA = [
    {"id": "USR001", "status": "Activo", "name": "Paciente A"},
    {"id": "USR002", "status": "Inactivo", "name": "Paciente B"}
]

CLIENT_ID_EXISTS = "client_123"
CLIENT_ID_NOT_FOUND = "client_404"
CLIENT_ID_ERROR = "client_error"


class TestUserRoutes(unittest.TestCase):
    """
    Pruebas unitarias para las rutas Flask del servicio users.
    """

    def setUp(self):
        self.app = Flask(__name__)
        self.mock_use_case = Mock()
        self.app.register_blueprint(create_user_api_blueprint(self.mock_use_case))
        self.client = self.app.test_client()

    def test_track_users_success(self):
        """Debe retornar 200 y los usuarios si el cliente tiene registros."""
        self.mock_use_case.execute.return_value = MOCK_USER_DATA

        response = self.client.get(f'/track/{CLIENT_ID_EXISTS}')
        response_data = json.loads(response.data)

        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_EXISTS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, MOCK_USER_DATA)

    def test_track_users_not_found(self):
        """Debe retornar 404 si el cliente no tiene usuarios registrados."""
        self.mock_use_case.execute.return_value = []

        response = self.client.get(f'/track/{CLIENT_ID_NOT_FOUND}')
        response_data = json.loads(response.data)

        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_NOT_FOUND)
        self.assertEqual(response.status_code, 404)
        self.assertIn("Aún no tienes usuarios registrados", response_data['message'])
        self.assertEqual(response_data['users'], [])

    def test_track_users_internal_server_error(self):
        """Debe retornar 500 si ocurre un error inesperado."""
        self.mock_use_case.execute.side_effect = Exception("Simulated DB error")

        response = self.client.get(f'/track/{CLIENT_ID_ERROR}')
        response_data = json.loads(response.data)

        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_ERROR)
        self.assertEqual(response.status_code, 500)
        self.assertIn("No pudimos obtener los usuarios", response_data['message'])


if __name__ == '__main__':
    unittest.main()
