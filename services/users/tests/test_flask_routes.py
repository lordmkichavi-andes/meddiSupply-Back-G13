import unittest
import json
from unittest.mock import MagicMock, patch
from datetime import datetime, date, timedelta
from flask import Flask

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

class MockRegisterVisitUseCase(MagicMock):
     """Mock para RegisterVisitUseCase"""
     pass


class UserAPITestCase(unittest.TestCase):
    """
    Clase de prueba para las rutas del Blueprint 'api'.
    """

    def setUp(self):
        # 1. Configurar Mocks y Flask App
        self.mock_get_users_uc = MockGetClientUsersUseCase()
        self.mock_register_visit_uc = MockRegisterVisitUseCase()

        # Necesitas una instancia de Flask para montar el Blueprint
        self.app = Flask(__name__)

        # El blueprint se crea con los mocks inyectados
        user_api_bp = create_user_api_blueprint(
            self.mock_get_users_uc,
            self.mock_register_visit_uc
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

    # ----------------------------------------------------------------------
    ## Tests para la ruta POST /visit
    # ----------------------------------------------------------------------

    # Usamos patch para simular la fecha/hora actual, lo que es CRÍTICO para validar fechas
    # 'datetime.now()' está en el módulo estándar, por lo que mockeamos allí
    @patch('api.datetime')
    def test_register_visit_success(self, mock_datetime):
        """Prueba de registro de visita exitoso (código 201)."""

        # 1. Configurar la fecha actual simulada
        # Mockeamos la fecha actual para que sea determinística (ej. 15-Oct-2025)
        mock_now = datetime(2025, 10, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        # El cuerpo de la petición debe tener la fecha dentro del rango (ej. 10-Oct-2025)
        request_payload = {
            "client_id": 101,
            "seller_id": 202,
            "date": "2025-10-10",  # Fecha dentro del rango (5 días de antigüedad)
            "findings": "Todo OK. Próxima visita en un mes."
        }

        # Configurar el mock del Caso de Uso
        mock_response = {"id": 500, "client_id": 101, "visit_date": "2025-10-10"}
        self.mock_register_visit_uc.execute.return_value = {"visit": mock_response}

        # 2. Ejecutar la petición
        response = self.client.post(
            '/visit',
            data=json.dumps(request_payload),
            content_type='application/json'
        )
        response_data = json.loads(response.data)

        # 3. Asertar la respuesta HTTP
        self.assertEqual(response.status_code, 201)
        self.assertIn("Visita registrada exitosamente.", response_data['message'])
        self.assertEqual(response_data['visit']['client_id'], 101)

        # 4. Asertar que el Caso de Uso fue llamado con los argumentos correctos
        # Asegurarse de que la fecha se pasó como objeto date (que es lo que hace .date() en el código)
        expected_date = date(2025, 10, 10)
        self.mock_register_visit_uc.execute.assert_called_once_with(
            client_id=101,
            seller_id=202,
            date=expected_date,
            findings="Todo OK. Próxima visita en un mes."
        )

    def test_register_visit_missing_fields(self):
        """Prueba validación de campos faltantes (código 400)."""
        request_payload = {
            "client_id": 101,
            "seller_id": 202,
            # Faltan 'date' y 'findings'
        }

        response = self.client.post(
            '/visit',
            data=json.dumps(request_payload),
            content_type='application/json'
        )
        response_data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Faltan campos requeridos.", response_data['message'])
        self.assertCountEqual(response_data['missing'], ['date', 'findings'])
        self.mock_register_visit_uc.execute.assert_not_called()

    def test_register_visit_empty_field(self):
        """Prueba validación de campos vacíos (código 400)."""
        request_payload = {
            "client_id": 101,
            "seller_id": 202,
            "date": "2025-10-10",
            "findings": ""  # Campo vacío
        }

        response = self.client.post(
            '/visit',
            data=json.dumps(request_payload),
            content_type='application/json'
        )
        response_data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("Ningún campo puede estar vacío.", response_data['message'])
        self.mock_register_visit_uc.execute.assert_not_called()

    def test_register_visit_invalid_date_format(self):
        """Prueba fecha con formato inválido (código 400)."""
        request_payload = {
            "client_id": 101,
            "seller_id": 202,
            "date": "no-es-una-fecha",  # Formato inválido
            "findings": "Observaciones"
        }

        response = self.client.post(
            '/visit',
            data=json.dumps(request_payload),
            content_type='application/json'
        )
        response_data = json.loads(response.data)

        self.assertEqual(response.status_code, 400)
        self.assertIn("La cadena proporcionada no corresponde a un formato de fecha válido.", response_data['message'])
        self.mock_register_visit_uc.execute.assert_not_called()

    @patch('api.datetime')
    def test_register_visit_future_date(self, mock_datetime):
        """Prueba fecha posterior a la actual (código 400)."""

        # 1. Configurar la fecha actual simulada
        mock_now = datetime(2025, 10, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        request_payload = {
            "client_id": 101,
            "seller_id": 202,
            "date": "2025-10-16",  # Fecha futura
            "findings": "Observaciones"
        }

        # 2. Ejecutar la petición
        response = self.client.post(
            '/visit',
            data=json.dumps(request_payload),
            content_type='application/json'
        )
        response_data = json.loads(response.data)

        # 3. Asertar la respuesta HTTP
        self.assertEqual(response.status_code, 400)
        self.assertIn("La fecha de la visita no puede ser posterior a la fecha actual.", response_data['message'])
        self.mock_register_visit_uc.execute.assert_not_called()

    @patch('api.datetime')
    def test_register_visit_too_old_date(self, mock_datetime):
        """Prueba fecha anterior a 30 días (código 400)."""

        # 1. Configurar la fecha actual simulada
        mock_now = datetime(2025, 10, 31, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        # La fecha de 30 días atrás sería: 1 de Octubre de 2025.
        request_payload = {
            "client_id": 101,
            "seller_id": 202,
            "date": "2025-09-30",  # Fecha anterior a 30 días
            "findings": "Observaciones"
        }

        # 2. Ejecutar la petición
        response = self.client.post(
            '/visit',
            data=json.dumps(request_payload),
            content_type='application/json'
        )
        response_data = json.loads(response.data)

        # 3. Asertar la respuesta HTTP
        self.assertEqual(response.status_code, 400)
        self.assertIn("La fecha de la visita no puede ser anterior a 30 días.", response_data['message'])
        self.mock_register_visit_uc.execute.assert_not_called()

    def test_register_visit_internal_error(self):
        """Prueba cuando el Caso de Uso de registro falla (código 500)."""

        request_payload = {
            "client_id": 101,
            "seller_id": 202,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "findings": "Observaciones"
        }

        # Configurar el mock para levantar una excepción
        self.mock_register_visit_uc.execute.side_effect = Exception("Error de conexión a la BD de visitas")

        # 1. Ejecutar la petición
        response = self.client.post(
            '/visit',
            data=json.dumps(request_payload),
            content_type='application/json'
        )
        response_data = json.loads(response.data)

        # 2. Asertar la respuesta HTTP
        self.assertEqual(response.status_code, 500)
        self.assertIn("No se pudo registrar la visita. Intenta nuevamente.", response_data['message'])
        self.assertIn("Error de conexión a la BD de visitas", response_data['error'])

        # 3. Asertar que el Caso de Uso fue llamado (aunque falló)
        self.mock_register_visit_uc.execute.assert_called_once()


if __name__ == '__main__':
    unittest.main()