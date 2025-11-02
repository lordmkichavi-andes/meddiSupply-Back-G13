import unittest
import json
from unittest.mock import MagicMock, patch
from flask import Flask
from datetime import datetime, date, timedelta
import io
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

    def test_upload_evidences_success(self):
        """Prueba la carga exitosa de archivos (código 201)."""
        test_visit_id = 101
        
        # 1. Simular la respuesta del Caso de Uso
        mock_evidences = [
            {'id': 1, 'url': 's3/f1.jpg', 'type': 'photo'},
            {'id': 2, 'url': 's3/f2.mp4', 'type': 'video'}
        ]
        self.mock_get_users_uc.upload_visit_evidences.return_value = mock_evidences
        
        # 2. Simular archivos de subida usando io.BytesIO
        data_files = {
            'files': [
                (io.BytesIO(b"file content A"), 'photo_a.jpg'),
                (io.BytesIO(b"file content B"), 'video_b.mp4')
            ]
        }
        
        # 3. Ejecutar la petición (es crucial usar 'multipart/form-data')
        with self.app.test_client() as client:
            response = client.post(
                f'/clients/visits/{test_visit_id}/evidences',
                data=data_files,
                content_type='multipart/form-data'
            )

        response_data = json.loads(response.data)

        # 4. Asertar el éxito (201 Created)
        self.assertEqual(response.status_code, 201)
        self.assertIn(f"Se subieron 2 evidencias con éxito para la visita {test_visit_id}.", response_data['message'])
        self.assertEqual(len(response_data['evidences']), 2)

        # 5. Asertar la llamada al Caso de Uso
        # No podemos verificar la lista exacta de FileStorage, solo que fue llamado
        self.mock_get_users_uc.upload_visit_evidences.assert_called_once()
        self.assertEqual(self.mock_get_users_uc.upload_visit_evidences.call_args[1]['visit_id'], test_visit_id)


    def test_upload_evidences_no_files(self):
        """Prueba cuando no se adjuntan archivos (código 400)."""
        test_visit_id = 102
        
        # 1. Ejecutar la petición con el campo 'files' vacío o no válido
        data_files = {'files': (io.BytesIO(b''), '')} # Simula un campo vacío
        
        with self.app.test_client() as client:
            response = client.post(
                f'/clients/visits/{test_visit_id}/evidences',
                data=data_files,
                content_type='multipart/form-data'
            )

        response_data = json.loads(response.data)

        # 2. Asertar el error 400
        self.assertEqual(response.status_code, 400)
        self.assertIn("No se adjuntaron archivos para la evidencia.", response_data['message'])

        # 3. Asertar que el Caso de Uso NO fue llamado
        self.mock_get_users_uc.upload_visit_evidences.assert_not_called()


    def test_upload_evidences_visit_not_found(self):
        """Prueba cuando el Caso de Uso lanza ValueError (Visita no existe) (código 404)."""
        test_visit_id = 999
        
        # 1. Simular la excepción ValueError (manejo del 404)
        error_msg = f"La visita con ID {test_visit_id} no existe en el sistema."
        self.mock_get_users_uc.upload_visit_evidences.side_effect = ValueError(error_msg)
        
        data_files = {'files': [(io.BytesIO(b"dummy"), 'dummy.jpg')]}

        # 2. Ejecutar la petición
        with self.app.test_client() as client:
            response = client.post(
                f'/clients/visits/{test_visit_id}/evidences',
                data=data_files,
                content_type='multipart/form-data'
            )

        response_data = json.loads(response.data)

        # 3. Asertar el error 404
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response_data['message'], error_msg)
        
        # 4. Asertar la llamada al Caso de Uso
        self.mock_get_users_uc.upload_visit_evidences.assert_called_once()


    def test_upload_evidences_internal_server_error(self):
        """Prueba cuando el Caso de Uso lanza una excepción genérica (código 500)."""
        test_visit_id = 103
        
        # 1. Simular una excepción genérica (ej. fallo de S3 o DB)
        simulated_exception = "Fallo en el almacenamiento del archivo"
        self.mock_get_users_uc.upload_visit_evidences.side_effect = Exception(simulated_exception)
        
        data_files = {'files': [(io.BytesIO(b"dummy"), 'dummy.jpg')]}

        # 2. Ejecutar la petición
        with self.app.test_client() as client:
            response = client.post(
                f'/clients/visits/{test_visit_id}/evidences',
                data=data_files,
                content_type='multipart/form-data'
            )

        response_data = json.loads(response.data)

        # 3. Asertar el error 500
        self.assertEqual(response.status_code, 500)
        self.assertIn("No se pudieron subir las evidencias. Intenta nuevamente.", response_data['message'])
        self.assertIn(simulated_exception, response_data['error'])
        
        # 4. Asertar la llamada al Caso de Uso
        self.mock_get_users_uc.upload_visit_evidences.assert_called_once()
if __name__ == '__main__':
    unittest.main()