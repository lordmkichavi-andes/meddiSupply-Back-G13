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
                 client_id, nit):
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


# Datos simulados
MOCK_USERS: List[MockUser] = [
    MockUser("U001", "Ana", "Gómez", "pass123", "123456789", "3001234567", MockRole("CLIENT"),
             'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370, 1,"900111222-3"),
    MockUser("U002", "Luis", "Pérez", "pass456", "987654321", "3019876543", MockRole("CLIENT"),
             'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370, 2, "900111222-3")
]


class TestGetClientUsersUseCase(unittest.TestCase):
    """
    Pruebas unitarias para el Caso de Uso GetClientUsersUseCase.
    """

    def setUp(self):
        self.mock_repository = Mock()
        self.use_case = GetClientUsersUseCase(self.mock_repository)

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
            latitude=10.0, longitude=-20.0, client_id=10, nit="900111222-3"
        )
        mock_user_2 = MockUser(
            user_id=2, name="Bob", last_name="Johnson", password="hashed2",
            identification="67890", phone="555-5678", role=mock_role, address="456 Oak Ave",
            latitude=11.0, longitude=-21.0, client_id=11,nit="900111222-3"
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
            "user_id": 1,
            "client_id": 10,
            "name": "Alice",
            "last_name": "Smith",
            "password": "hashed",
            "identification": "12345",
            "phone": "555-1234",
            "address": "123 Main St",
            "latitude": 10.0,
            "longitude": -20.0,
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


if __name__ == '__main__':
    unittest.main()
