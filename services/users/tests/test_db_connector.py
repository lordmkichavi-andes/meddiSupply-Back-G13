import unittest
from unittest.mock import Mock
from flask import Flask
from users.src.infrastructure.web.flask_user_routes import create_user_api_blueprint

# Datos simulados
MOCK_USER_DATA = [
    {"id": "USR001", "status": "Activo", "name": "Paciente A"},
    {"id": "USR002", "status": "Inactivo", "name": "Paciente B"}
]

class TestUserRoutes(unittest.TestCase):
    """
    Pruebas unitarias para las rutas Flask del servicio users.
    """

    def setUp(self):
        self.app = Flask(__name__)
        self.mock_use_case = Mock()
        self.app.register_blueprint(create_user_api_blueprint(self.mock_use_case))
        self.client = self.app.test_client()

    def test_get_users_success(self):
        """Debe retornar 200 y los usuarios si existen registros CLIENT."""
        self.mock_use_case.execute.return_value = MOCK_USER_DATA

        response = self.client.get('/users/clients')
        response_data = response.get_json()

        self.mock_use_case.execute.assert_called_once_with()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['users'], MOCK_USER_DATA)

    def test_get_users_not_found(self):
        """Debe retornar 404 si no hay usuarios CLIENT."""
        self.mock_use_case.execute.return_value = []

        response = self.client.get('/users/clients')
        response_data = response.get_json()

        self.mock_use_case.execute.assert_called_once_with()
        self.assertEqual(response.status_code, 404)
        self.assertIn("No se encontraron usuarios", response_data['message'])
        self.assertEqual(response_data['users'], [])

    def test_get_users_internal_error(self):
        """Debe retornar 500 si ocurre un error inesperado."""
        self.mock_use_case.execute.side_effect = Exception("Simulated DB error")

        response = self.client.get('/users/clients')
        response_data = response.get_json()

        self.mock_use_case.execute.assert_called_once_with()
        self.assertEqual(response.status_code, 500)
        self.assertIn("No se pudieron obtener los usuarios", response_data['message'])
        self.assertIn("Simulated DB error", response_data['error'])


if __name__ == '__main__':
    unittest.main()
