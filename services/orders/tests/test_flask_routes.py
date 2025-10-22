import unittest
import json
from unittest.mock import Mock, patch
from flask import Flask, jsonify # Asegúrate de importar jsonify en tu código real
# Importamos la función de fábrica desde la infraestructura
from orders.src.infrastructure.web.flask_routes import create_api_blueprint

# Definición de datos de prueba
MOCK_ORDER_DATA = [
    {"id": "ORD001", "status": "En tránsito", "item": "Medicamento X"},
    {"id": "ORD002", "status": "Entregado", "item": "Suministro Y"}
]
CLIENT_ID_EXISTS = "client_123"
CLIENT_ID_NOT_FOUND = "client_404"
CLIENT_ID_ERROR = "client_error"


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
        # Asumiendo que track_case es el primer argumento, como en la ruta.
        # Si tienes otro use case (create_use_case), asegúrate de que ambos
        # estén bien inyectados si es necesario, o usa None si no se usa.
        self.app.register_blueprint(create_api_blueprint(self.mock_use_case, self.mock_use_case))
        self.client = self.app.test_client()

    def tearDown(self):
        """
        Limpia el mock después de cada test para asegurar la independencia.
        Esto es CRUCIAL para evitar la contaminación de return_value/side_effect
        entre tests que usan el mismo mock.
        """
        self.mock_use_case.reset_mock()


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
        # La función de Flask devuelve directamente la lista de órdenes en este caso
        self.assertEqual(response_data, MOCK_ORDER_DATA)

    def test_track_orders_not_found(self):
        """
        Prueba el escenario "no hay pedidos": el Caso de Uso devuelve una lista vacía.
        Debe retornar 404 y un mensaje específico (que tu función devuelve).
        """
        print(f"Ejecutando test_track_orders_not_found para ID: {CLIENT_ID_NOT_FOUND}")
        # Configurar el mock para devolver una lista vacía
        self.mock_use_case.execute.return_value = []

        response = self.client.get(f'/track/{CLIENT_ID_NOT_FOUND}')
        response_data = json.loads(response.data) # -> Ahora el response es JSON (el dict)

        # 1. Verificar la llamada al Caso de Uso
        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_NOT_FOUND)

        # 2. Verificar el código de estado y el mensaje
        self.assertEqual(response.status_code, 404)
        # La función de Flask devuelve un diccionario con 'message' y 'orders'
        self.assertIn("Aún no tienes pedidos registrados", response_data['message'])
        self.assertEqual(response_data['orders'], [])

    def test_track_orders_internal_server_error(self):
        """
        Prueba el escenario de error del sistema: el Caso de Uso lanza una excepción.
        Debe retornar 500 y un mensaje de error genérico.
        """
        print(f"Ejecutando test_track_orders_internal_server_error para ID: {CLIENT_ID_ERROR}")
        # Configurar el mock para lanzar una excepción
        self.mock_use_case.execute.side_effect = Exception("Simulated DB connection error")

        response = self.client.get(f'/track/{CLIENT_ID_ERROR}')
        response_data = json.loads(response.data) # -> Ahora el response es JSON (el dict)

        # 1. Verificar la llamada al Caso de Uso
        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_ERROR)

        # 2. Verificar el código de estado y el mensaje
        self.assertEqual(response.status_code, 500)
        # La función de Flask devuelve un diccionario con 'message'
        self.assertIn("No pudimos obtener los pedidos. Intenta nuevamente", response_data['message'])