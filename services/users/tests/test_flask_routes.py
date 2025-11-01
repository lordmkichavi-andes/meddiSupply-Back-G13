import unittest
import json
from unittest.mock import MagicMock, patch
from flask import Flask
from datetime import datetime, date, timedelta

# Importa la función de fábrica desde tu archivo (asume que tu código se llama 'api.py')
from src.infrastructure.web.flask_user_routes import create_user_api_blueprint

# --- Clases de Mock para los Casos de Uso ---
# Usamos MagicMock porque permite definir métodos sin implementarlos
# y rastrea si fueron llamados.

class MockGetClientUsersUseCase(MagicMock):
    """
    Mock para GetClientUsersUseCase.
    MagicMock automáticamente expone 'execute.return_value' y 'execute_by_seller.return_value'.
    """
    pass

class UserAPITestCase(unittest.TestCase):
    """
    Clase de prueba para las rutas del Blueprint 'api'.
    """

    def setUp(self):
        # 1. Configurar Mocks y Flask App
        self.mock_get_users_uc = MockGetClientUsersUseCase()

        # Necesitas una instancia de Flask para montar el Blueprint
        self.app = Flask(__name__)

        # El blueprint se crea con los mocks inyectados
        user_api_bp = create_user_api_blueprint(
            self.mock_get_users_uc,
        )

        # Registrar el Blueprint en la app base
        self.app.register_blueprint(user_api_bp)

        # Crear el cliente de prueba de Flask
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        # Limpiar el contexto de la aplicación después de cada prueba
        self.app_context.pop()

    # ----------------------------------------------------------------------
    ## Tests para la ruta GET /clients
    # ----------------------------------------------------------------------

    def test_get_client_users_success(self):
        """Prueba obtener clientes exitosamente (código 200)."""
        mock_clients = [
            {"id": 1, "name": "Client A"},
            {"id": 2, "name": "Client B"}
        ]
        # Configurar el mock para devolver datos
        self.mock_get_users_uc.execute.return_value = mock_clients

        # 1. Ejecutar la petición
        response = self.client.get('/clients')
        response_data = json.loads(response.data)

        # 2. Asertar la respuesta HTTP
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        self.assertIn('clients', response_data)
        self.assertEqual(len(response_data['clients']), 2)

        # 3. Asertar que el Caso de Uso fue llamado
        self.mock_get_users_uc.execute.assert_called_once()

    def test_get_client_users_not_found(self):
        """Prueba cuando no se encuentran clientes (código 404)."""
        # Configurar el mock para devolver una lista vacía
        self.mock_get_users_uc.execute.return_value = []

        # 1. Ejecutar la petición
        response = self.client.get('/clients')
        response_data = json.loads(response.data)

        # 2. Asertar la respuesta HTTP
        self.assertEqual(response.status_code, 404)
        self.assertIn("No se encontraron usuarios con rol CLIENT.", response_data['message'])

        # 3. Asertar que el Caso de Uso fue llamado
        self.mock_get_users_uc.execute.assert_called_once()

    def test_get_client_users_internal_error(self):
        """Prueba cuando el Caso de Uso lanza una excepción (código 500)."""
        # Configurar el mock para levantar una excepción simulada
        self.mock_get_users_uc.execute.side_effect = Exception("Error de base de datos simulado")

        # 1. Ejecutar la petición
        response = self.client.get('/clients')
        response_data = json.loads(response.data)

        # 2. Asertar la respuesta HTTP
        self.assertEqual(response.status_code, 500)
        self.assertIn("No se pudieron obtener los usuarios. Intenta nuevamente.", response_data['message'])
        self.assertIn("Error de base de datos simulado", response_data['error'])

        # 3. Asertar que el Caso de Uso fue llamado
        self.mock_get_users_uc.execute.assert_called_once()

    # ----------------------------------------------------------------------
    ## Tests para la ruta GET /clients/<int:seller_id>
    # ----------------------------------------------------------------------

    def test_get_client_users_by_seller_success(self):
        """Prueba obtener clientes por vendedor exitosamente (código 200)."""
        seller_id = 42
        mock_clients = [{"id": 3, "name": "Client C"}]

        self.mock_get_users_uc.execute_by_seller.return_value = mock_clients

        # 1. Ejecutar la petición
        response = self.client.get(f'/clients/{seller_id}')
        response_data = json.loads(response.data)

        # 2. Asertar la respuesta HTTP
        self.assertEqual(response.status_code, 200)
        self.assertIn('clients', response_data)
        self.assertEqual(len(response_data['clients']), 1)

        # 3. Asertar que el Caso de Uso fue llamado con el argumento correcto
        self.mock_get_users_uc.execute_by_seller.assert_called_once_with(seller_id=seller_id)

    def test_get_client_users_by_seller_not_found(self):
        """Prueba cuando no hay clientes para el vendedor (código 404)."""
        seller_id = 99
        self.mock_get_users_uc.execute_by_seller.return_value = []

        # 1. Ejecutar la petición
        response = self.client.get(f'/clients/{seller_id}')
        response_data = json.loads(response.data)

        # 2. Asertar la respuesta HTTP
        self.assertEqual(response.status_code, 404)
        self.assertIn(f"No se encontraron clientes asignados al vendedor con ID {seller_id}.", response_data['message'])

        # 3. Asertar que el Caso de Uso fue llamado
        self.mock_get_users_uc.execute_by_seller.assert_called_once()

if __name__ == '__main__':
    unittest.main()