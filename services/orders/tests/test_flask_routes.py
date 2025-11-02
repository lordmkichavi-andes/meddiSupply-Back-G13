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

MOCK_HISTORY_DATA = [
    {"sku": "P001", "name": "Aspirina"},
    {"sku": "P002", "name": "Termómetro"}
]

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
        # Asumimos que track_case y create_case usan el mismo mock para simplificar el setup.
        self.app.register_blueprint(create_api_blueprint(self.mock_use_case, self.mock_use_case, self.mock_use_case, self.mock_use_case))
        self.client = self.app.test_client()

    def tearDown(self):
        """
        Limpia el mock después de cada test. Esto es esencial para que los side_effects 
        y return_values no contaminen otras pruebas.
        """
        self.mock_use_case.reset_mock()


    # --- Tests de la ruta /track/<user_id> ---

    def test_track_orders_success(self):
        """
        Prueba el escenario de éxito: el Caso de Uso devuelve datos.
        Debe retornar 200 y los datos de las órdenes.
        """
        print(f"Ejecutando test_track_orders_success para ID: {CLIENT_ID_EXISTS}")
        # Configurar el mock para devolver datos de prueba
        self.mock_use_case.execute.return_value = MOCK_ORDER_DATA

        # Llamada a la URL corregida (el ID de la constante se usa en la ruta /track/...)
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
        Debe retornar 404 y un mensaje específico (el diccionario JSON).
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
        # El mensaje exacto de la ruta Flask
        self.assertEqual(response_data['message'], "¡Ups! Aún no tienes pedidos registrados.")
        self.assertEqual(response_data['orders'], [])

    def test_track_orders_internal_server_error(self):
        """
        Prueba el escenario de error del sistema: el Caso de Uso lanza una excepción.
        Debe retornar 500 y un mensaje de error genérico (el diccionario JSON).
        """
        print(f"Ejecutando test_track_orders_internal_server_error para ID: {CLIENT_ID_ERROR}")
        # Configurar el mock para lanzar una excepción
        self.mock_use_case.execute.side_effect = Exception("Simulated DB connection error")

        response = self.client.get(f'/track/{CLIENT_ID_ERROR}')
        response_data = json.loads(response.data)

        # 1. Verificar la llamada al Caso de Uso
        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_ERROR)

        # 2. Verificar el código de estado y el mensaje
        self.assertEqual(response.status_code, 500)
        # El mensaje exacto de la ruta Flask
        self.assertEqual(response_data['message'], "¡Ups! No pudimos obtener los pedidos. Intenta nuevamente.")


    def test_get_purchase_history_success(self):
        """
        [GET /history/<id>] Prueba la obtención exitosa del historial de compras.
        """
        self.mock_use_case.execute.return_value = MOCK_HISTORY_DATA

        response = self.client.get(f'/history/{CLIENT_ID_EXISTS}')
        response_data = json.loads(response.data)

        self.mock_use_case.execute.assert_called_once_with(CLIENT_ID_EXISTS)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['products'], MOCK_HISTORY_DATA)
        
        self.mock_use_case.reset_mock()

    def test_get_purchase_history_not_found(self):
        """
        [GET /history/<id>] Prueba cuando el cliente no tiene historial (404).
        """
        self.mock_use_case.execute.return_value = []

        response = self.client.get(f'/history/{CLIENT_ID_NOT_FOUND}')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(json.loads(response.data)['products'], [])
        
        self.mock_use_case.reset_mock()

    def test_get_purchase_history_internal_server_error(self):
        """
        [GET /history/<id>] Prueba cuando el caso de uso lanza un error (500).
        """
        self.mock_use_case.execute.side_effect = Exception("DB error history")

        response = self.client.get(f'/history/{CLIENT_ID_EXISTS}')
        
        self.assertEqual(response.status_code, 500)
        self.assertIn("Error interno del servicio", json.loads(response.data)['message'])
        
        self.mock_use_case.reset_mock()

    def test_get_all_orders_success(self):
        """
        [GET /all] Prueba la obtención exitosa de todas las órdenes.
        """
        self.mock_use_case.execute.return_value = MOCK_ALL_ORDERS_DATA

        response = self.client.get('/all')
        response_data = json.loads(response.data)

        self.mock_use_case.execute.assert_called_once()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['orders'], MOCK_ALL_ORDERS_DATA)
        
        self.mock_use_case.reset_mock()

    def test_get_all_orders_not_found(self):
        """
        [GET /all] Prueba cuando no hay órdenes en el sistema (404).
        """
        self.mock_use_case.execute.return_value = []

        response = self.client.get('/all')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(json.loads(response.data)['orders'], [])
        
        self.mock_use_case.reset_mock()

    def test_create_order_success(self):
        """
        [POST /] Prueba la creación exitosa de una orden.
        """
        self.mock_use_case.execute.return_value = MOCK_CREATED_ORDER 

        response = self.client.post(
            '/',
            data=json.dumps(NEW_ORDER_REQUEST),
            content_type='application/json'
        )
        response_data = json.loads(response.data)

        self.mock_use_case.execute.assert_called_once()
        args, _ = self.mock_use_case.execute.call_args
        
        self.assertIsInstance(args[0], MockOrder)
        self.assertIsInstance(args[1], List)
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response_data['order_id'], MOCK_CREATED_ORDER.order_id)

    def test_create_order_missing_fields(self):
        """
        [POST /] Prueba cuando faltan campos esenciales (400).
        """
        incomplete_request = {"client_id": 4}

        response = self.client.post(
            '/',
            data=json.dumps(incomplete_request),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("client_id and products are required", json.loads(response.data)['error'])
        self.mock_use_case.execute.assert_not_called()

    def test_create_order_internal_server_error(self):
        """
        [POST /] Prueba el escenario de error de base de datos durante la creación (500).
        """
        self.mock_use_case.execute.side_effect = Exception("DB insertion error")

        response = self.client.post(
            '/',
            data=json.dumps(NEW_ORDER_REQUEST),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 500)
        self.assertIn("No pudimos crear el pedido", json.loads(response.data)['message'])

    def test_create_order_success(self):
        self.mock_use_case.execute.return_value = MOCK_CREATED_ORDER 

        response = self.client.post(
            '/',
            data=json.dumps(NEW_ORDER_REQUEST),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        self.mock_use_case.reset_mock()


    def test_create_order_missing_fields(self):
        incomplete_request = {"client_id": 4} # Falta 'products'

        response = self.client.post(
            '/',
            data=json.dumps(incomplete_request),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.mock_use_case.execute.assert_not_called()
        self.mock_use_case.reset_mock()
        
    
    def test_create_order_product_validation_error(self):
        response = self.client.post(
            '/',
            data=json.dumps(INCOMPLETE_PRODUCT_REQUEST),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Each product must have product_id and quantity", json.loads(response.data)['error'])
        self.mock_use_case.execute.assert_not_called()
        self.mock_use_case.reset_mock()


    def test_create_order_internal_server_error(self):
        self.mock_use_case.execute.side_effect = Exception("DB insertion error")

        response = self.client.post(
            '/',
            data=json.dumps(NEW_ORDER_REQUEST),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 500)
        self.mock_use_case.reset_mock()

if __name__ == '__main__':
    unittest.main()
