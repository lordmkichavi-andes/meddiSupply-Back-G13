import unittest
import sys
from unittest.mock import Mock, MagicMock
from typing import List

# Aseguramos que los módulos de src se pueden importar
sys.path.append('users/src')

# Importamos el caso de uso a probar
from users.src.application.use_cases import GetClientUsersUseCase


# --- Mocks de Entidades y Estructuras de Dominio ---

class MockRole:
    def __init__(self, value):
        self.value = value


class MockUser:
    """Simula la entidad de dominio User con los atributos requeridos."""

    def __init__(self, user_id, name, last_name, password, identification, phone, role, address, latitude, longitude,
                 client_id, nit, perfil):
        self.user_id = user_id
        self.name = name
        self.last_name = last_name
        self.password = password
        self.nit = nit
        self.identification = identification
        self.phone = phone
        self.role = role
        self.address = address
        self.latitude = latitude
        self.longitude = longitude
        self.client_id = client_id
        self.perfil = perfil


# Datos simulados
MOCK_USERS: List[MockUser] = [
    MockUser("U001", "Ana", "Gómez", "pass123", "123456789", "3001234567", MockRole("CLIENT"),
             'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370, 1,"900111222-3", "La tienda"),
    MockUser("U002", "Luis", "Pérez", "pass456", "987654321", "3019876543", MockRole("CLIENT"),
             'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370, 2, "900111222-3", "La tienda")
]

class MockFileStorage:
    """Simula el objeto werkzeug.datastructures.FileStorage."""
    def __init__(self, filename, mimetype):
        self.filename = filename
        self.mimetype = mimetype
        # El método read() debe ser mockeado por MagicMock para simular lectura de bytes
        self.read = MagicMock(return_value=b'file_content_bytes')

MOCK_VISIT_DATA = {'visit_id': 100, 'client_id': 5, 'date': '2025-10-01'}

class TestGetClientUsersUseCase(unittest.TestCase):
    """
    Pruebas unitarias para el Caso de Uso GetClientUsersUseCase.
    """

    def setUp(self):
        self.mock_repository = Mock()
        self.mock_storage_service = Mock()
        self.use_case = GetClientUsersUseCase(self.mock_repository, self.mock_storage_service)

    def test_execute_returns_formatted_users(self):
        """Verifica que el caso de uso formatea correctamente los usuarios CLIENT."""
        self.mock_repository.get_users_by_role.return_value = MOCK_USERS

        result = self.use_case.execute()

        self.mock_repository.get_users_by_role.assert_called_once_with("CLIENT")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['user_id'], "U001")
        self.assertEqual(result[0]['rol'], "CLIENT")
        self.assertEqual(result[1]['name'], "Luis")

    def test_execute_returns_empty_list_when_no_users(self):
        """Verifica que retorna lista vacía si no hay usuarios CLIENT."""
        self.mock_repository.get_users_by_role.return_value = []

        result = self.use_case.execute()

        self.mock_repository.get_users_by_role.assert_called_once_with("CLIENT")
        self.assertEqual(result, [])

    def test_execute_propagates_repository_exception(self):
        """Verifica que si el repositorio lanza excepción, esta se propaga."""
        self.mock_repository.get_users_by_role.side_effect = Exception("DB error")

        with self.assertRaises(Exception) as context:
            self.use_case.execute()

        self.assertEqual(str(context.exception), "DB error")
        self.mock_repository.get_users_by_role.assert_called_once_with("CLIENT")

    # --- NUEVOS TESTS PARA execute_by_seller (Filtrado por Vendedor) ---

    def test_execute_by_seller_successful(self):
        """Prueba la obtención exitosa de clientes por seller_id y su correcto formato."""
        test_seller_id = 900
        # Usamos MockRole para asegurar que 'rol' tiene el .value correcto
        mock_role = MockRole("CLIENT_ROL")

        # Simulamos las entidades de usuario devueltas por el repositorio usando MockUser
        mock_user_1 = MockUser(
            user_id=1, name="Alice", last_name="Smith", password="hashed",
            identification="12345", phone="555-1234", role=mock_role, address="123 Main St",
            latitude=10.0, longitude=-20.0, client_id=10, nit="900111222-3", perfil="La tienda"
        )
        mock_user_2 = MockUser(
            user_id=2, name="Bob", last_name="Johnson", password="hashed2",
            identification="67890", phone="555-5678", role=mock_role, address="456 Oak Ave",
            latitude=11.0, longitude=-21.0, client_id=11,nit="900111222-3", perfil="La tienda"
        )

        # Mockeamos el método específico para obtener usuarios por vendedor
        self.mock_repository.get_users_by_seller.return_value = [mock_user_1, mock_user_2]

        # Ejecutar el Caso de Uso (asumiendo que el método es execute_by_seller)
        result = self.use_case.execute_by_seller(test_seller_id)

        # 1. Verificar la llamada al repositorio
        self.mock_repository.get_users_by_seller.assert_called_once_with(test_seller_id)

        # 2. Verificar el formato y contenido de la respuesta
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)

        # Verificar que el primer elemento tiene el formato correcto
        self.assertDictEqual(result[0], {
            "address": "123 Main St",
            "client_id": 10,
            "latitude": 10.0,
            "longitude": -20.0,
            "name": "La tienda",
            "nit": "900111222-3",
            "phone": "555-1234",
            "rol": "CLIENT_ROL"
        })

    def test_execute_by_seller_returns_empty_list_when_no_users(self):
        """Prueba que devuelve una lista vacía si no se encuentran clientes para el seller_id."""
        test_seller_id = 901
        self.mock_repository.get_users_by_seller.return_value = []

        result = self.use_case.execute_by_seller(test_seller_id)

        # 1. Verificar la llamada al repositorio
        self.mock_repository.get_users_by_seller.assert_called_once_with(test_seller_id)

        # 2. Verificar que el resultado es una lista vacía
        self.assertIsInstance(result, list)
        self.assertEqual(result, [])

    def test_execute_by_seller_propagates_repository_exception(self):
        """Prueba que si el repositorio falla al obtener clientes, la excepción es propagada."""
        test_seller_id = 902
        # Configurar el mock para que lance una excepción
        self.mock_repository.get_users_by_seller.side_effect = TimeoutError("Database query timed out.")

        # Verificar que la excepción es propagada
        with self.assertRaises(TimeoutError) as cm:
            self.use_case.execute_by_seller(test_seller_id)

        self.mock_repository.get_users_by_seller.assert_called_once_with(test_seller_id)
        self.assertIn("Database query timed out.", str(cm.exception))
        
    def test_upload_evidences_visit_not_found(self):
        """Verifica que lanza ValueError si la visita no existe."""
        test_visit_id = 999
        mock_files = [MockFileStorage(filename="test.jpg", mimetype="image/jpeg")]

        # Mock: la visita no existe
        self.mock_repository.get_visit_by_id.return_value = None

        # ACT & ASSERT
        with self.assertRaises(ValueError) as cm:
            self.use_case.upload_visit_evidences(test_visit_id, mock_files)

        self.assertIn(f"La visita con ID {test_visit_id} no existe", str(cm.exception))
        # No se debe llamar al servicio de almacenamiento ni al guardado
        self.mock_storage_service.upload_file.assert_not_called()
        self.mock_repository.save_evidence.assert_not_called()


    def test_upload_evidences_storage_service_fails(self):
        """Verifica que propaga la excepción si falla la subida a S3."""
        test_visit_id = 100
        mock_file = MockFileStorage(filename="error.png", mimetype="image/png")
        mock_files = [mock_file]
        
        self.mock_repository.get_visit_by_id.return_value = MOCK_VISIT_DATA

        # Mock: La subida a S3 falla
        self.mock_storage_service.upload_file.side_effect = RuntimeError("AWS S3 Connection Timeout")

        # ACT & ASSERT
        with self.assertRaisesRegex(Exception, f"Fallo en el almacenamiento del archivo {mock_file.filename}") as cm:
            self.use_case.upload_visit_evidences(test_visit_id, mock_files)

        # Se llama al repositorio para validar, pero no para guardar
        self.mock_repository.get_visit_by_id.assert_called_once_with(test_visit_id)
        self.mock_storage_service.upload_file.assert_called_once()
        self.mock_repository.save_evidence.assert_not_called()

    def test_get_user_by_id_success(self):
        """Verifica que get_user_by_id llama al repositorio y retorna el perfil."""
        test_client_id = 15
        mock_data = {"client_id": 15, "name": "Test Client"}

        # Configurar el mock para que devuelva datos
        self.mock_repository.db_get_client_data.return_value = mock_data

        # ACT
        result = self.use_case.get_user_by_id(test_client_id)

        # ASSERT
        # 1. Verificar la llamada al repositorio
        self.mock_repository.db_get_client_data.assert_called_once_with(test_client_id)

        # 2. Verificar el resultado
        self.assertEqual(result, mock_data)

    def test_get_user_by_id_not_found(self):
        """Verifica que get_user_by_id retorna None si el repositorio no encuentra datos."""
        test_client_id = 999

        # Configurar el mock para que devuelva None
        self.mock_repository.db_get_client_data.return_value = None

        # ACT
        result = self.use_case.get_user_by_id(test_client_id)

        # ASSERT
        self.mock_repository.db_get_client_data.assert_called_once_with(test_client_id)
        self.assertIsNone(result)

    def test_get_visit_by_id_found(self):
        """Verifica que el método llama al repositorio y retorna la visita."""
        test_visit_id = 150
        # MOCK_VISIT_DATA ya está definido al inicio del archivo
        mock_visit = MOCK_VISIT_DATA 

        # Configurar el mock para que devuelva la data de la visita
        self.mock_repository.get_by_id.return_value = mock_visit

        # ACT
        result = self.use_case.get_visit_by_id(test_visit_id)

        # ASSERT
        # 1. Verificar que se llamó al repositorio con el ID correcto
        self.mock_repository.get_by_id.assert_called_once_with(test_visit_id)

        # 2. Verificar que se retorna la data simulada
        self.assertEqual(result, mock_visit)


    def test_get_visit_by_id_not_found(self):
        """Verifica que retorna None si el repositorio no encuentra la visita."""
        test_visit_id = 999

        # Configurar el mock para que devuelva None
        self.mock_repository.get_by_id.return_value = None

        # ACT
        result = self.use_case.get_visit_by_id(test_visit_id)

        # ASSERT
        self.mock_repository.get_by_id.assert_called_once_with(test_visit_id)
        self.assertIsNone(result)

    def test_get_visit_by_id_propagates_exception(self):
        """Verifica que si el repositorio falla, la excepción se propaga."""
        test_visit_id = 500
        # Configurar el mock para que lance una excepción
        self.mock_repository.get_by_id.side_effect = ConnectionError("DB connection failed")

        # ACT & ASSERT
        with self.assertRaises(ConnectionError) as cm:
            self.use_case.get_visit_by_id(test_visit_id)

        self.mock_repository.get_by_id.assert_called_once_with(test_visit_id)
        self.assertIn("DB connection failed", str(cm.exception))
        
if __name__ == '__main__':
    unittest.main()
