import unittest
import json
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify
from datetime import datetime, date, timedelta
import io # Importación necesaria

# Importa la función de fábrica desde tu archivo (asume que tu código se llama 'api.py')
from src.infrastructure.web.flask_user_routes import create_user_api_blueprint

# --- Clases de Mock para los Casos de Uso ---

class MockGetClientUsersUseCase(MagicMock):
    """
    Mock para GetClientUsersUseCase.
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

        # Registrar el Blueprint en la app base (asumimos que la URL base es /clients,
        # aunque el código del blueprint no lo especifica, lo inferimos de los tests GET)
        # 🛑 NOTA IMPORTANTE: El problema del JSONDecodeError sugiere que el blueprint
        # para /visits/<int:visit_id>/evidences no está bajo /clients.
        # Basado en la ruta que falla en POST: /clients/visits/{id}/evidences
        # Lo más probable es que el Blueprint NO se registre con un prefijo. 
        # Si se registrara con prefijo /users, la URL sería /users/visits/{id}/evidences.
        # Asumiendo que el prefijo es implícito y que el fallo está en la decodificación.
        self.app.register_blueprint(user_api_bp) 

        # Crear el cliente de prueba de Flask
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        # Limpiar el contexto de la aplicación después de cada prueba
        self.app_context.pop()

    # Función auxiliar para decodificar JSON de forma robusta
    def _get_json(self, response):
        if not response.data:
            return None
        try:
            return json.loads(response.data.decode('utf-8'))
        except json.JSONDecodeError as e:
            self.fail(f"La respuesta no fue JSON. Cuerpo: {response.data.decode('utf-8')} Error: {e}")

    # ----------------------------------------------------------------------
    ## Tests para la ruta GET /clients
    # ----------------------------------------------------------------------

    def test_get_client_users_success(self):
        """Prueba obtener clientes exitosamente (código 200)."""
        mock_clients = [
            {"id": 1, "name": "Client A"},
            {"id": 2, "name": "Client B"}
        ]
        self.mock_get_users_uc.execute.return_value = mock_clients

        response = self.client.get('/clients')
        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 200)
        self.assertIn('clients', response_data)
        self.assertEqual(len(response_data['clients']), 2)
        self.mock_get_users_uc.execute.assert_called_once()

    def test_get_client_users_not_found(self):
        """Prueba cuando no se encuentran clientes (código 404)."""
        self.mock_get_users_uc.execute.return_value = []

        response = self.client.get('/clients')
        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 404)
        self.assertIn("No se encontraron usuarios con rol CLIENT.", response_data['message'])
        self.mock_get_users_uc.execute.assert_called_once()

    def test_get_client_users_internal_error(self):
        """Prueba cuando el Caso de Uso lanza una excepción (código 500)."""
        self.mock_get_users_uc.execute.side_effect = Exception("Error de base de datos simulado")

        response = self.client.get('/clients')
        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 500)
        self.assertIn("No se pudieron obtener los usuarios. Intenta nuevamente.", response_data['message'])
        self.assertIn("Error de base de datos simulado", response_data['error'])
        self.mock_get_users_uc.execute.assert_called_once()

    # ----------------------------------------------------------------------
    ## Tests para la ruta GET /clients/<int:seller_id>
    # ----------------------------------------------------------------------

    def test_get_client_users_by_seller_success(self):
        """Prueba obtener clientes por vendedor exitosamente (código 200)."""
        seller_id = 42
        mock_clients = [{"id": 3, "name": "Client C"}]

        self.mock_get_users_uc.execute_by_seller.return_value = mock_clients

        response = self.client.get(f'/clients/{seller_id}')
        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 200)
        self.assertIn('clients', response_data)
        self.assertEqual(len(response_data['clients']), 1)
        self.mock_get_users_uc.execute_by_seller.assert_called_once_with(seller_id=seller_id)

    def test_get_client_users_by_seller_not_found(self):
        """Prueba cuando no hay clientes para el vendedor (código 404)."""
        seller_id = 99
        self.mock_get_users_uc.execute_by_seller.return_value = []

        response = self.client.get(f'/clients/{seller_id}')
        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 404)
        self.assertIn(f"No se encontraron clientes asignados al vendedor con ID {seller_id}.", response_data['message'])
        self.mock_get_users_uc.execute_by_seller.assert_called_once()

    # ----------------------------------------------------------------------
    ## Tests para la ruta GET /detail/<int:client_id>
    # ----------------------------------------------------------------------
    
    def test_get_user_by_id_success(self):
        """Prueba la obtención exitosa de un usuario por ID (código 200)."""
        test_client_id = 15
        mock_data = {"client_id": 15, "name": "Test Client"}

        self.mock_get_users_uc.get_user_by_id.return_value = mock_data

        response = self.client.get(f'/detail/{test_client_id}')
        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['client_id'], test_client_id)
        self.mock_get_users_uc.get_user_by_id.assert_called_once_with(client_id=test_client_id)
        
    def test_get_user_by_id_not_found(self):
        """Prueba cuando el usuario no se encuentra (código 404)."""
        test_client_id = 999
        self.mock_get_users_uc.get_user_by_id.return_value = None

        response = self.client.get(f'/detail/{test_client_id}')
        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 404)
        self.assertIn(f"Usuario con ID {test_client_id} no encontrado.", response_data['message'])
        self.mock_get_users_uc.get_user_by_id.assert_called_once_with(client_id=test_client_id)

    def test_get_user_by_id_server_error(self):
        """
        Verifica que la ruta /detail/<id> maneja y retorna correctamente
        un error 500 cuando el Caso de Uso lanza una excepción.
        """
        test_client_id = 999
        
        # 1. Configurar el mock del Caso de Uso para que lance una excepción
        self.mock_get_users_uc.get_user_by_id.side_effect = Exception("DB Connection Lost")

        # 2. Realizar la solicitud HTTP (asumiendo que la ruta es /detail/ directamente)
        response = self.client.get(f'/detail/{test_client_id}') 
        
        # 3. Verificar el estado
        self.assertEqual(response.status_code, 500) # 🛑 CORREGIDO a 500
        
        # 4. Verificar el contenido
        data = self._get_json(response)
        
        self.assertIsNotNone(data)
        self.assertIn("Error al obtener la información del usuario. Intenta nuevamente.", data['message'])
        self.assertIn("DB Connection Lost", data['error'])
        
        # 5. Verificar que el Caso de Uso fue llamado
        self.mock_get_users_uc.get_user_by_id.assert_called_once_with(client_id=test_client_id)


    # ----------------------------------------------------------------------
    ## Tests para la ruta POST /visits/<int:visit_id>/evidences
    # ----------------------------------------------------------------------

    def test_upload_evidences_success(self):
        """Prueba la carga exitosa de archivos (código 201)."""
        test_visit_id = 101
        
        mock_evidences = [
            {'id': 1, 'url': 's3/f1.jpg', 'type': 'photo'},
            {'id': 2, 'url': 's3/f2.mp4', 'type': 'video'}
        ]
        self.mock_get_users_uc.upload_visit_evidences.return_value = mock_evidences
        
        data_files = {
            'files': [
                (io.BytesIO(b"file content A"), 'photo_a.jpg'),
                (io.BytesIO(b"file content B"), 'video_b.mp4')
            ]
        }
        
        # 🛑 Usar la URL que falla: /clients/visits/{id}/evidences
        # Si esta falla, la URL debe ser /visits/{id}/evidences (sin prefijo /clients)
        response = self.client.post( 
            f'/clients/visits/{test_visit_id}/evidences',
            data=data_files,
            content_type='multipart/form-data'
        )

        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 201)
        self.assertIn(f"Se subieron 2 evidencias con éxito para la visita {test_visit_id}.", response_data['message'])
        self.assertEqual(len(response_data['evidences']), 2)
        self.mock_get_users_uc.upload_visit_evidences.assert_called_once()
        self.assertEqual(self.mock_get_users_uc.upload_visit_evidences.call_args[1]['visit_id'], test_visit_id)


    def test_upload_evidences_no_files(self):
        """Prueba cuando no se adjuntan archivos (código 400)."""
        test_visit_id = 102
        
        data_files = {'files': (io.BytesIO(b''), '')} 
        
        response = self.client.post(
            f'/clients/visits/{test_visit_id}/evidences',
            data=data_files,
            content_type='multipart/form-data'
        )

        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 400)
        self.assertIn("No se adjuntaron archivos para la evidencia.", response_data['message'])
        self.mock_get_users_uc.upload_visit_evidences.assert_not_called()


    def test_upload_evidences_visit_not_found(self):
        """Prueba cuando el Caso de Uso lanza ValueError (Visita no existe) (código 404)."""
        test_visit_id = 999
        
        error_msg = f"La visita con ID {test_visit_id} no existe en el sistema."
        self.mock_get_users_uc.upload_visit_evidences.side_effect = ValueError(error_msg)
        
        data_files = {'files': [(io.BytesIO(b"dummy"), 'dummy.jpg')]}

        response = self.client.post(
            f'/clients/visits/{test_visit_id}/evidences',
            data=data_files,
            content_type='multipart/form-data'
        )

        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response_data['message'], error_msg)
        self.mock_get_users_uc.upload_visit_evidences.assert_called_once()


    def test_upload_evidences_internal_server_error(self):
        """Prueba cuando el Caso de Uso lanza una excepción genérica (código 500)."""
        test_visit_id = 103
        
        simulated_exception = "Fallo en el almacenamiento del archivo"
        self.mock_get_users_uc.upload_visit_evidences.side_effect = Exception(simulated_exception)
        
        data_files = {'files': [(io.BytesIO(b"dummy"), 'dummy.jpg')]}

        response = self.client.post(
            f'/clients/visits/{test_visit_id}/evidences',
            data=data_files,
            content_type='multipart/form-data'
        )

        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 500)
        self.assertIn("No se pudieron subir las evidencias. Intenta nuevamente.", response_data['message'])
        self.assertIn(simulated_exception, response_data['error'])
        self.mock_get_users_uc.upload_visit_evidences.assert_called_once()
        
    def test_upload_evidences_file_not_found_error(self):
        """Prueba cuando el Caso de Uso lanza FileNotFoundError (código 404)."""
        test_visit_id = 104
        
        error_msg = "La visita no existe en la base de datos."
        self.mock_get_users_uc.upload_visit_evidences.side_effect = FileNotFoundError(error_msg)
        
        data_files = {'files': [(io.BytesIO(b"dummy"), 'dummy.jpg')]}

        response = self.client.post(
            f'/clients/visits/{test_visit_id}/evidences',
            data=data_files,
            content_type='multipart/form-data'
        )

        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 404)
        self.assertIn("Error: La visita no existe o el sistema de archivos falló.", response_data['message'])
        self.assertIn(error_msg, response_data['error'])
        self.mock_get_users_uc.upload_visit_evidences.assert_called_once()

if __name__ == '__main__':
    unittest.main()