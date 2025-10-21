import unittest
import json
from unittest.mock import Mock, patch
from flask import Flask
# Importamos la función de fábrica desde la infraestructura
from orders.src.infrastructure.web.flask_routes import create_api_blueprint

# Definición de datos de prueba
MOCK_ORDER_DATA = [
    {"id": "ORD001", "status": "En tránsito", "item": "Medicamento X"},
    {"id": "ORD002", "status": "Entregado", "item": "Suministro Y"}
]
CLIENT_ID_EXISTS = 1
CLIENT_ID_NOT_FOUND = 100
CLIENT_ID_ERROR = 0


class TestFlaskRoutes(unittest.TestCase):
    """
    Clase para probar las rutas de Flask, asegurando que interactúan
    correctamente con el Caso de Uso (simulado con mocks).
    """

    def setUp(self):
        """
        Configura la aplicación Flask y el cliente de prueba antes de cada test.
        """
        self.app = Flask(__name__)
        self.mock_use_case = Mock()  # Creamos un mock del Caso de Uso

        # Usamos la función de fábrica para inyectar el mock en el Blueprint
        self.app.register_blueprint(create_api_blueprint(self.mock_use_case, self.mock_use_case))
        self.client = self.app.test_client()


    # --- Tests de la ruta /track/<client_id> ---

    def test_track_orders_success(self):
        """
        Prueba el escenario de éxito: el Caso de Uso devuelve datos.
        Debe retornar 200 y los datos de las órdenes.
        """
        print(f"Ejecutando test_track_orders_success para ID: {CLIENT_ID_EXISTS}")
        # Configurar el mock para devolver datos de prueba
        self.mock_use_case.execute.return_value = MOCK_ORDER_DATA

        response = self.client.get(f'/track/{CLIENT_ID_EXISTS}')
        response_data = json.loads(response.data)

        # 1. Verificar la llamada al Caso de Uso
        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_EXISTS)

        # 2. Verificar el código de estado y la respuesta
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, MOCK_ORDER_DATA)

    def test_track_orders_not_found(self):
        """
        Prueba el escenario "no hay pedidos": el Caso de Uso devuelve una lista vacía.
        Debe retornar 404 y un mensaje específico.
        """
        print(f"Ejecutando test_track_orders_not_found para ID: {CLIENT_ID_NOT_FOUND}")
        # Configurar el mock para devolver una lista vacía
        self.mock_use_case.execute.return_value = []

        response = self.client.get(f'/track/{CLIENT_ID_NOT_FOUND}')
        response_data = json.loads(response.data)

        # 1. Verificar la llamada al Caso de Uso
        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_NOT_FOUND)

        # 2. Verificar el código de estado y el mensaje
        self.assertEqual(response.status_code, 404)
        self.assertIn("Aún no tienes pedidos registrados", response_data['message'])
        self.assertEqual(response_data['orders'], [])

    def test_track_orders_internal_server_error(self):
        """
        Prueba el escenario de error del sistema: el Caso de Uso lanza una excepción.
        Debe retornar 500 y un mensaje de error genérico.
        """
        print(f"Ejecutando test_track_orders_internal_server_error para ID: {CLIENT_ID_ERROR}")
        # Configurar el mock para lanzar una excepción (simulando un fallo de DB, API externa, etc.)
        self.mock_use_case.execute.side_effect = Exception("Simulated DB connection error")

        response = self.client.get(f'/track/{CLIENT_ID_ERROR}')
        response_data = json.loads(response.data)

        # 1. Verificar la llamada al Caso de Uso
        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_ERROR)

        # 2. Verificar el código de estado y el mensaje
        self.assertEqual(response.status_code, 500)
        self.assertIn("No pudimos obtener los pedidos", response_data['message'])


if __name__ == '__main__':
    unittest.main()