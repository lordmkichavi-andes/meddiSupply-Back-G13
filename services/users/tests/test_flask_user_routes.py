import unittest
import json
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
# Importar la función del Blueprint
from src.presentation.api import create_user_api_blueprint
# Importar las clases para el mocking de la especificación
from src.application.use_cases import GetClientUsersUseCase
from src.application.register_visit_usecase import RegisterVisitUseCase


# --- Clase de Prueba ---
class TestUserApiBlueprint(unittest.TestCase):

    def setUp(self):
        """
        Configuración inicial antes de cada prueba:
        1. Mockear los Casos de Uso.
        2. Crear la aplicación de Flask y el cliente de pruebas.
        """
        # Mocks para las dependencias (Casos de Uso)
        self.mock_get_client_users_uc = Mock(spec=GetClientUsersUseCase)
        self.mock_register_visit_uc = Mock(spec=RegisterVisitUseCase)

        # Crear el Blueprint inyectando los mocks
        blueprint = create_user_api_blueprint(
            use_case=self.mock_get_client_users_uc,
            register_visit_use_case=self.mock_register_visit_uc
        )

        # Crear una aplicación de prueba de Flask
        from flask import Flask
        self.app = Flask(__name__)
        self.app.register_blueprint(blueprint, url_prefix='/api')  # Usaremos un prefijo para claridad

        # Crear el cliente de prueba para enviar solicitudes HTTP simuladas
        self.client = self.app.test_client()
        self.app.testing = True

        # Definir URLs con el prefijo
        self.clients_url = '/api/clients'
        self.visit_url = '/api/visit'




## ⚡️ Tests para la Ruta GET `/clients`

def test_get_client_users_success(self):
    """Prueba GET /clients: Retorna 200 con la lista de usuarios."""

    mock_users = [{"id": 1, "name": "Cliente A"}, {"id": 2, "name": "Cliente B"}]
    # Simular que el Caso de Uso devuelve datos
    self.mock_get_client_users_uc.execute.return_value = mock_users

    response = self.client.get(self.clients_url)
    data = json.loads(response.data.decode('utf-8'))

    # Verificaciones
    self.assertEqual(response.status_code, 200)
    self.assertEqual(data["clients"], mock_users)
    self.mock_get_client_users_uc.execute.assert_called_once()


def test_get_client_users_not_found(self):
    """Prueba GET /clients: Retorna 404 cuando no hay clientes."""

    # Simular que el Caso de Uso devuelve una lista vacía
    self.mock_get_client_users_uc.execute.return_value = []

    response = self.client.get(self.clients_url)
    data = json.loads(response.data.decode('utf-8'))

    # Verificaciones
    self.assertEqual(response.status_code, 404)
    self.assertIn("No se encontraron", data["message"])
    self.mock_get_client_users_uc.execute.assert_called_once()


def test_get_client_users_internal_error(self):
    """Prueba GET /clients: Retorna 500 cuando el Caso de Uso falla."""

    # Simular una excepción interna del Caso de Uso (ej. error de BD)
    self.mock_get_client_users_uc.execute.side_effect = Exception("Error de conexión al ORM")

    response = self.client.get(self.clients_url)
    data = json.loads(response.data.decode('utf-8'))

    # Verificaciones
    self.assertEqual(response.status_code, 500)
    self.assertIn("No se pudieron obtener", data["message"])
    self.assertIn("Error de conexión al ORM", data["error"])
    self.mock_get_client_users_uc.execute.assert_called_once()




## 🔍 Tests para la Ruta GET `/clients/<seller_id>`

def test_get_client_users_by_seller_success(self):
    """Prueba GET /clients/<seller_id>: Retorna 200 con clientes filtrados."""

    seller_id = 50
    mock_users = [{"id": 3, "name": "Cliente C", "seller_id": seller_id}]
    self.mock_get_client_users_uc.execute_by_seller.return_value = mock_users

    response = self.client.get(f'{self.clients_url}/{seller_id}')
    data = json.loads(response.data.decode('utf-8'))

    # Verificaciones
    self.assertEqual(response.status_code, 200)
    self.assertEqual(data["clients"], mock_users)
    # Verificar que se llamó al método correcto con el argumento correcto
    self.mock_get_client_users_uc.execute_by_seller.assert_called_once_with(seller_id=seller_id)


def test_get_client_users_by_seller_not_found(self):
    """Prueba GET /clients/<seller_id>: Retorna 404 cuando el seller no tiene clientes."""

    seller_id = 99
    self.mock_get_client_users_uc.execute_by_seller.return_value = []

    response = self.client.get(f'{self.clients_url}/{seller_id}')
    data = json.loads(response.data.decode('utf-8'))

    # Verificaciones
    self.assertEqual(response.status_code, 404)
    self.assertIn(f"ID {seller_id}", data["message"])
    self.mock_get_client_users_uc.execute_by_seller.assert_called_once_with(seller_id=seller_id)





## 📝 Tests para la Ruta POST `/visit` (Registro de Visita)

def test_register_visit_success(self):
    """Prueba POST /visit: Retorna 201 al registrar una visita con datos válidos."""

    today_date_str = datetime.now().strftime("%Y-%m-%d")  # Fecha de hoy para que pase
    mock_visit_data = {"id": 100, "date": today_date_str}

    valid_payload = {
        "client_id": 10,
        "seller_id": 20,
        "date": today_date_str,
        "findings": "Todo excelente en la visita de seguimiento."
    }

    # Simular la respuesta del Caso de Uso (que contiene la visita guardada)
    self.mock_register_visit_uc.execute.return_value = {
        "message": "Visita registrada con éxito en la base de datos.",
        "visit": mock_visit_data
    }

    response = self.client.post(
        self.visit_url,
        data=json.dumps(valid_payload),
        content_type='application/json'
    )
    data = json.loads(response.data.decode('utf-8'))

    # Verificaciones
    self.assertEqual(response.status_code, 201)
    self.assertEqual(data["message"], "Visita registrada exitosamente.")
    self.assertEqual(data["visit"]["id"], 100)

    # Verificar que el CU fue llamado con el objeto date (visit_date.date())
    expected_date_arg = datetime.strptime(today_date_str, "%Y-%m-%d").date()
    self.mock_register_visit_uc.execute.assert_called_once_with(
        client_id=10, seller_id=20, date=expected_date_arg, findings=valid_payload["findings"]
    )


# --- Tests de Validación de Datos (Retorno 400) ---

def test_register_visit_missing_fields(self):
    """Prueba POST /visit: Retorna 400 si faltan campos requeridos."""

    invalid_payload = {
        "client_id": 10,
        "seller_id": 20,
        "findings": "Falta la fecha"
    }

    response = self.client.post(
        self.visit_url,
        data=json.dumps(invalid_payload),
        content_type='application/json'
    )
    data = json.loads(response.data.decode('utf-8'))

    self.assertEqual(response.status_code, 400)
    self.assertIn("Faltan campos requeridos.", data["message"])
    self.assertIn("date", data["missing"])
    self.mock_register_visit_uc.execute.assert_not_called()


def test_register_visit_empty_fields(self):
    """Prueba POST /visit: Retorna 400 si algún campo requerido está vacío."""

    invalid_payload = {
        "client_id": 10,
        "seller_id": 20,
        "date": "",  # Campo vacío
        "findings": "Todo bien."
    }

    response = self.client.post(
        self.visit_url,
        data=json.dumps(invalid_payload),
        content_type='application/json'
    )
    data = json.loads(response.data.decode('utf-8'))

    self.assertEqual(response.status_code, 400)
    self.assertIn("Ningún campo puede estar vacío.", data["message"])
    self.mock_register_visit_uc.execute.assert_not_called()


def test_register_visit_invalid_date_format(self):
    """Prueba POST /visit: Retorna 400 si la fecha no es un formato válido."""

    invalid_payload = {
        "client_id": 10,
        "seller_id": 20,
        "date": "21/Octubre/2025",
        "findings": "Test."
    }

    response = self.client.post(
        self.visit_url,
        data=json.dumps(invalid_payload),
        content_type='application/json'
    )
    data = json.loads(response.data.decode('utf-8'))

    self.assertEqual(response.status_code, 400)
    self.assertIn("no corresponde a un formato de fecha válido.", data["message"])
    self.mock_register_visit_uc.execute.assert_not_called()


def test_register_visit_future_date(self):
    """Prueba POST /visit: Retorna 400 si la fecha es posterior a la actual."""

    future_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    invalid_payload = {
        "client_id": 10,
        "seller_id": 20,
        "date": future_date,
        "findings": "Test."
    }

    response = self.client.post(
        self.visit_url,
        data=json.dumps(invalid_payload),
        content_type='application/json'
    )

    self.assertEqual(response.status_code, 400)
    self.assertIn("no puede ser posterior a la fecha actual.", response.get_data(as_text=True))
    self.mock_register_visit_uc.execute.assert_not_called()


def test_register_visit_old_date(self):
    """Prueba POST /visit: Retorna 400 si la fecha es anterior a 30 días."""

    old_date = (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d")

    invalid_payload = {
        "client_id": 10,
        "seller_id": 20,
        "date": old_date,
        "findings": "Test."
    }

    response = self.client.post(
        self.visit_url,
        data=json.dumps(invalid_payload),
        content_type='application/json'
    )

    self.assertEqual(response.status_code, 400)
    self.assertIn("no puede ser anterior a 30 días.", response.get_data(as_text=True))
    self.mock_register_visit_uc.execute.assert_not_called()


def test_register_visit_use_case_exception(self):
    """Prueba POST /visit: Retorna 500 cuando el Caso de Uso falla."""

    today_date_str = datetime.now().strftime("%Y-%m-%d")

    valid_payload = {
        "client_id": 10,
        "seller_id": 20,
        "date": today_date_str,
        "findings": "Test."
    }

    # Simular una excepción lanzada por el Caso de Uso
    self.mock_register_visit_uc.execute.side_effect = Exception("Fallo de la base de datos.")

    response = self.client.post(
        self.visit_url,
        data=json.dumps(valid_payload),
        content_type='application/json'
    )
    data = json.loads(response.data.decode('utf-8'))

    self.assertEqual(response.status_code, 500)
    self.assertIn("No se pudo registrar la visita.", data["message"])
    self.assertIn("Fallo de la base de datos.", data["error"])
    # Aunque falle, el CU debe haber sido llamado
    self.mock_register_visit_uc.execute.assert_called_once()


# --- Ejecución del archivo de prueba ---
if __name__ == '__main__':
    unittest.main()