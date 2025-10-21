import unittest
import json
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
# Importar la función a probar y las clases/interfaces necesarias para el mocking
from src.presentation.api import create_user_api_blueprint
# Asumimos que los use cases están en estas rutas para el spec
from src.application.use_cases import GetClientUsersUseCase
from src.application.register_visit_usecase import RegisterVisitUseCase


# --- Clase de Prueba ---
class TestUserApiBlueprint(unittest.TestCase):

    def setUp(self):
        """
        Configuración inicial antes de cada prueba.
        Crea Mocks para los casos de uso y la aplicación de prueba de Flask.
        """
        # Mocks para las dependencias (Casos de Uso)
        self.mock_get_client_users_uc = Mock(spec=GetClientUsersUseCase)
        self.mock_register_visit_uc = Mock(spec=RegisterVisitUseCase)

        # 1. Crear el Blueprint inyectando los mocks
        blueprint = create_user_api_blueprint(
            use_case=self.mock_get_client_users_uc,
            register_visit_use_case=self.mock_register_visit_uc
        )

        # 2. Crear una aplicación de prueba de Flask
        self.app = MagicMock()  # Usamos MagicMock para simular la app
        self.app.register_blueprint(blueprint)  # Registrar el Blueprint en la app mockeada

        # 3. Crear el cliente de prueba de Flask
        # Esto permite enviar solicitudes HTTP simuladas
        self.client = self.app.test_client()

        # 4. Configurar la aplicación de prueba (necesario para la funcionalidad de Flask)
        self.app.testing = True

    # -----------------------------------------------
    #              Tests para la ruta GET /clients
    # -----------------------------------------------

    def test_get_client_users_success(self):
        """
        Prueba la ruta GET /clients cuando el Caso de Uso devuelve datos.
        Debe retornar 200 y la lista de clientes.
        """
        print("\n--- Ejecutando test_get_client_users_success ---")

        # Datos de retorno simulados
        mock_users = [{"id": 1, "name": "Cliente A"}, {"id": 2, "name": "Cliente B"}]
        self.mock_get_client_users_uc.execute.return_value = mock_users

        # Enviar la solicitud de prueba
        response = self.client.get('/clients')
        data = json.loads(response.data.decode('utf-8'))

        # Verificaciones
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["clients"], mock_users)
        self.mock_get_client_users_uc.execute.assert_called_once()
        print("Obtención de clientes exitosa verificada (código 200).")

    def test_get_client_users_not_found(self):
        """
        Prueba la ruta GET /clients cuando el Caso de Uso no devuelve datos.
        Debe retornar 404.
        """
        print("\n--- Ejecutando test_get_client_users_not_found ---")

        # Simular que no hay clientes
        self.mock_get_client_users_uc.execute.return_value = []

        # Enviar la solicitud de prueba
        response = self.client.get('/clients')
        data = json.loads(response.data.decode('utf-8'))

        # Verificaciones
        self.assertEqual(response.status_code, 404)
        self.assertEqual(data["message"], "No se encontraron usuarios con rol CLIENT.")
        print("No se encontraron clientes verificado (código 404).")

    # -----------------------------------------------
    #        Tests para la ruta GET /clients/<seller_id>
    # -----------------------------------------------

    def test_get_client_users_by_seller_success(self):
        """
        Prueba la ruta GET /clients/<seller_id> cuando se encuentran clientes.
        Debe retornar 200 y los clientes filtrados.
        """
        print("\n--- Ejecutando test_get_client_users_by_seller_success ---")

        seller_id = 50
        mock_users = [{"id": 3, "name": "Cliente C", "seller_id": seller_id}]

        # Simular el retorno del Caso de Uso filtrado
        self.mock_get_client_users_uc.execute_by_seller.return_value = mock_users

        # Enviar la solicitud de prueba
        response = self.client.get(f'/clients/{seller_id}')
        data = json.loads(response.data.decode('utf-8'))

        # Verificaciones
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["clients"], mock_users)
        # Verificar que se llamó al método correcto con el argumento correcto
        self.mock_get_client_users_uc.execute_by_seller.assert_called_once_with(seller_id=seller_id)
        print(f"Obtención de clientes por seller_id {seller_id} exitosa verificada.")

    # -----------------------------------------------
    #              Tests para la ruta POST /visit
    # -----------------------------------------------

    def test_register_visit_success(self):
        """
        Prueba la ruta POST /visit con datos válidos.
        Debe retornar 201 y los detalles de la visita.
        """
        print("\n--- Ejecutando test_register_visit_success ---")

        today = datetime.now().strftime("%Y-%m-%d")  # Fecha de hoy para que pase la validación

        # Datos de entrada para la petición
        valid_payload = {
            "client_id": 10,
            "seller_id": 20,
            "date": today,
            "findings": "Todo excelente."
        }

        # Simular la respuesta del Caso de Uso (que contiene la visita guardada)
        mock_visit_data = {"id": 100, **valid_payload}
        self.mock_register_visit_uc.execute.return_value = {
            "message": "Visita registrada con éxito en la base de datos.",
            "visit": mock_visit_data
        }

        # Enviar la solicitud POST
        response = self.client.post(
            '/visit',
            data=json.dumps(valid_payload),
            content_type='application/json'
        )
        data = json.loads(response.data.decode('utf-8'))

        # Verificaciones
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data["message"], "Visita registrada exitosamente.")
        self.assertEqual(data["visit"]["id"], 100)

        # Verificar que el Caso de Uso fue llamado (nota: el CU recibe un objeto date)
        self.mock_register_visit_uc.execute.assert_called_once()
        print("Registro de visita exitoso verificado (código 201).")

    def test_register_visit_missing_fields(self):
        """
        Prueba la validación de campos requeridos faltantes.
        Debe retornar 400.
        """
        print("\n--- Ejecutando test_register_visit_missing_fields ---")

        # Payload donde falta 'findings'
        invalid_payload = {
            "client_id": 10,
            "seller_id": 20,
            "date": "2025-10-21",
        }

        response = self.client.post(
            '/visit',
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        data = json.loads(response.data.decode('utf-8'))

        # Verificaciones
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["message"], "Faltan campos requeridos.")
        self.assertIn("findings", data["missing"])
        # Verificar que el Caso de Uso *no* fue llamado
        self.mock_register_visit_uc.execute.assert_not_called()
        print("Validación de campos faltantes verificada (código 400).")

    def test_register_visit_invalid_date_format(self):
        """
        Prueba la validación de formato de fecha incorrecto.
        Debe retornar 400.
        """
        print("\n--- Ejecutando test_register_visit_invalid_date_format ---")

        # Fecha con formato incorrecto que parser.parse no puede manejar
        invalid_payload = {
            "client_id": 10,
            "seller_id": 20,
            "date": "no-es-una-fecha",
            "findings": "Test."
        }

        response = self.client.post(
            '/visit',
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        data = json.loads(response.data.decode('utf-8'))

        # Verificaciones
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["message"], "La cadena proporcionada no corresponde a un formato de fecha válido.")
        self.mock_register_visit_uc.execute.assert_not_called()
        print("Validación de formato de fecha inválido verificada (código 400).")

    def test_register_visit_future_date(self):
        """
        Prueba la validación de fecha futura.
        Debe retornar 400.
        """
        print("\n--- Ejecutando test_register_visit_future_date ---")

        # Fecha en el futuro (+1 día)
        future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        invalid_payload = {
            "client_id": 10,
            "seller_id": 20,
            "date": future_date,
            "findings": "Test."
        }

        response = self.client.post(
            '/visit',
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        data = json.loads(response.data.decode('utf-8'))

        # Verificaciones
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["message"], "La fecha de la visita no puede ser posterior a la fecha actual.")
        self.mock_register_visit_uc.execute.assert_not_called()
        print("Validación de fecha futura verificada (código 400).")

    def test_register_visit_old_date(self):
        """
        Prueba la validación de fecha demasiado antigua (más de 30 días).
        Debe retornar 400.
        """
        print("\n--- Ejecutando test_register_visit_old_date ---")

        # Fecha hace 31 días
        old_date = (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d")

        invalid_payload = {
            "client_id": 10,
            "seller_id": 20,
            "date": old_date,
            "findings": "Test."
        }

        response = self.client.post(
            '/visit',
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        data = json.loads(response.data.decode('utf-8'))

        # Verificaciones
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data["message"], "La fecha de la visita no puede ser anterior a 30 días.")
        self.mock_register_visit_uc.execute.assert_not_called()
        print("Validación de fecha antigua verificada (código 400).")

    def test_register_visit_use_case_exception(self):
        """
        Prueba el manejo de excepciones cuando el Caso de Uso falla.
        Debe retornar 500.
        """
        print("\n--- Ejecutando test_register_visit_use_case_exception ---")

        today = datetime.now().strftime("%Y-%m-%d")

        valid_payload = {
            "client_id": 10,
            "seller_id": 20,
            "date": today,
            "findings": "Test."
        }

        # Simular una excepción lanzada por el Caso de Uso (ej. error de base de datos)
        self.mock_register_visit_uc.execute.side_effect = Exception("Error de conexión a BD")

        response = self.client.post(
            '/visit',
            data=json.dumps(valid_payload),
            content_type='application/json'
        )
        data = json.loads(response.data.decode('utf-8'))

        # Verificaciones
        self.assertEqual(response.status_code, 500)
        self.assertEqual(data["message"], "No se pudo registrar la visita. Intenta nuevamente.")
        self.assertIn("Error de conexión a BD", data["error"])
        print("Manejo de excepción del Caso de Uso verificado (código 500).")


# --- Ejecución del archivo de prueba ---
if __name__ == '__main__':
    unittest.main()