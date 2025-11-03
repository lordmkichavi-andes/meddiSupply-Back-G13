import unittest
import json
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify
from datetime import datetime, date, timedelta
import io 

# Importa la función de fábrica desde tu archivo 
from src.infrastructure.web.flask_user_routes import create_user_api_blueprint

# --- Clases de Mock para los Casos de Uso ---

class MockGetClientUsersUseCase(MagicMock):
    pass 

class MockRegisterVisitUseCase(MagicMock):
    pass

# 🛑 NUEVO MOCK PARA EL CASO DE USO DE RECOMENDACIONES 🛑
class MockGenerateRecommendationsUseCase(MagicMock):
    pass

class UserAPITestCase(unittest.TestCase):
    """
    Clase de prueba para las rutas del Blueprint 'api'.
    """

    def setUp(self):
        # 1. Configurar Mocks y Flask App
        self.mock_get_users_uc = MockGetClientUsersUseCase()
        self.mock_register_visit_uc = MockRegisterVisitUseCase()
        # 🛑 Inicializar el nuevo Mock 🛑
        self.mock_recommendations_uc = MockGenerateRecommendationsUseCase()

        # Necesitas una instancia de Flask para montar el Blueprint
        self.app = Flask(__name__)

        # El blueprint se crea con los TRES mocks inyectados
        user_api_bp = create_user_api_blueprint(
            self.mock_get_users_uc,
            self.mock_register_visit_uc,
            # 🛑 ¡CORRECCIÓN DEL TypeError! 🛑
            self.mock_recommendations_uc 
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

    # Función auxiliar para decodificar JSON de forma robusta
    def _get_json(self, response):
        if not response.data:
            return None
        try:
            return json.loads(response.data.decode('utf-8'))
        except json.JSONDecodeError as e:
            self.fail(f"La respuesta no fue JSON. Cuerpo: {response.data.decode('utf-8')} Error: {e}")

    # ----------------------------------------------------------------------
    ## Tests para la ruta POST /recommendations (NUEVOS)
    # ----------------------------------------------------------------------

    def test_post_recommendations_success(self):
        """Prueba la generación exitosa de recomendaciones (código 200)."""
        
        expected_recommendations = [
            {"product_id": 101, "product_sku": "SKU-001", "product_name": "Test Product", "score": 0.9, "reasoning": "High demand"},
        ]
        
        self.mock_recommendations_uc.execute.return_value = {
            "status": "success",
            "recommendations": expected_recommendations
        }
        
        response = self.client.post(
            '/recommendations',
            json={"client_id": 1, "regional_setting": "CO"}
        )

        response_data = self._get_json(response)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data['status'], 'success')
        self.assertEqual(response_data['recommendations'][0]['product_id'], 101)
        
        self.mock_recommendations_uc.execute.assert_called_once_with(
            client_id=1, 
            regional_setting="CO"
        )
    

    def test_post_recommendations_llm_failure(self):
        """Prueba la falla cuando el Caso de Uso lanza una excepción (ej. fallo del LLM) (código 503)."""
        
        # Simular una excepción de servicio externo
        self.mock_recommendations_uc.execute.side_effect = Exception("Fallo en el Agente de Razonamiento (LLM).")
        
        response = self.client.post(
            '/recommendations',
            json={"client_id": 1, "regional_setting": "CO"}
        )

        response_data = self._get_json(response)
        
        self.assertEqual(response.status_code, 503) # 503 Service Unavailable es apropiado para LLM
        self.assertIn("Fallo en el servicio de recomendaciones", response_data['message'])
        self.mock_recommendations_uc.execute.assert_called_once()
        
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
            
        self.mock_get_users_uc.get_user_by_id.side_effect = Exception("DB Connection Lost")

        response = self.client.get(f'/detail/{test_client_id}') 
        
        self.assertEqual(response.status_code, 500)
        
        data = self._get_json(response)
        
        self.assertIsNotNone(data)
        self.assertIn("Error al obtener la información del usuario. Intenta nuevamente.", data['message'])
        self.assertIn("DB Connection Lost", data['error'])
        
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
            
        # Asegura que el mock del Caso de Uso devuelva la data correcta
        self.mock_get_users_uc.upload_visit_evidences.return_value = mock_evidences
        
        # ... (Resto de la preparación y llamada) ...
        
        response = self.client.post( 
            f'/visits/{test_visit_id}/evidences',
            data=data_files,
            content_type='multipart/form-data'
        )

        response_data = self._get_json(response)

        # 🛑 Las aserciones sobre la respuesta HTTP están correctas 🛑
        self.assertEqual(response.status_code, 201)
        self.assertIn(f"Se subieron 2 evidencias con éxito para la visita {test_visit_id}.", response_data['message'])
        self.assertEqual(len(response_data['evidences']), 2)
        
        # 🛑 Aserción correcta sobre la llamada al Caso de Uso 🛑
        self.mock_get_users_uc.upload_visit_evidences.assert_called_once()
        self.assertEqual(self.mock_get_users_uc.upload_visit_evidences.call_args[1]['visit_id'], test_visit_id) 
        
        # El error que ves NO DEBERÍA ESTAR aquí. ¡Revisa tu entorno de test!

    def test_upload_evidences_no_files(self):
        """Prueba cuando no se adjuntan archivos (código 400)."""
        test_visit_id = 102
        
        # En Flask, files no adjuntos es None, pero el cliente de prueba lo envía como campo vacío.
        response = self.client.post(
            f'/visits/{test_visit_id}/evidences',
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
            f'/visits/{test_visit_id}/evidences',
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
            f'/visits/{test_visit_id}/evidences',
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
            f'/visits/{test_visit_id}/evidences',
            data=data_files,
            content_type='multipart/form-data'
        )

        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 404)
        self.assertIn("Error: La visita no existe o el sistema de archivos falló.", response_data['message'])
        self.assertIn(error_msg, response_data['error'])
        self.mock_get_users_uc.upload_visit_evidences.assert_called_once()
        
        # ----------------------------------------------------------------------
        ## Tests para la ruta POST /visit
        # ----------------------------------------------------------------------

    # Usamos patch para simular la fecha/hora actual, lo que es CRÍTICO para validar fechas
    @patch('src.infrastructure.web.flask_user_routes.datetime')
    def test_register_visit_success(self, mock_datetime):
        """Prueba de registro de visita exitoso (código 201)."""

        # 1. Configurar la fecha actual simulada
        mock_now = datetime(2025, 10, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        request_payload = {
            "client_id": 101,
            "seller_id": 202,
            "date": "2025-10-10", 
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
        response_data = self._get_json(response)

        # 3. Asertar la respuesta HTTP
        self.assertEqual(response.status_code, 201)
        self.assertIn("Visita registrada exitosamente.", response_data['message'])
        self.assertEqual(response_data['visit']['client_id'], 101)

        # 4. Asertar que el Caso de Uso fue llamado con los argumentos correctos
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
        response_data = self._get_json(response)

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
        response_data = self._get_json(response)

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
        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 400)
        self.assertIn("La cadena proporcionada no corresponde a un formato de fecha válido.",
                      response_data['message'])
        self.mock_register_visit_uc.execute.assert_not_called()

    @patch('src.infrastructure.web.flask_user_routes.datetime')
    def test_register_visit_future_date(self, mock_datetime):
        """Prueba fecha posterior a la actual (código 400)."""

        mock_now = datetime(2025, 10, 15, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        request_payload = {
            "client_id": 101,
            "seller_id": 202,
            "date": "2025-10-16",  # Fecha futura
            "findings": "Observaciones"
        }

        response = self.client.post(
            '/visit',
            data=json.dumps(request_payload),
            content_type='application/json'
        )
        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 400)
        self.assertIn("La fecha de la visita no puede ser posterior a la fecha actual.", response_data['message'])
        self.mock_register_visit_uc.execute.assert_not_called()

    @patch('src.infrastructure.web.flask_user_routes.datetime')
    def test_register_visit_too_old_date(self, mock_datetime):
        """Prueba fecha anterior a 30 días (código 400)."""

        mock_now = datetime(2025, 10, 31, 10, 0, 0)
        mock_datetime.now.return_value = mock_now

        request_payload = {
            "client_id": 101,
            "seller_id": 202,
            "date": "2025-09-30",  # Fecha anterior a 30 días
            "findings": "Observaciones"
        }

        response = self.client.post(
            '/visit',
            data=json.dumps(request_payload),
            content_type='application/json'
        )
        response_data = self._get_json(response)

        self.assertEqual(response.status_code, 400)
        self.assertIn("La fecha de la visita no puede ser anterior a 30 días.", response_data['message'])
        self.mock_register_visit_uc.execute.assert_not_called()

if __name__ == '__main__':
    unittest.main()