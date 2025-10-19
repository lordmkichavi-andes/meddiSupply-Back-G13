import unittest
import sys
from unittest.mock import Mock
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
    def __init__(self, user_id, name, last_name, password, identification, phone, role):
        self.user_id = user_id
        self.name = name
        self.last_name = last_name
        self.password = password
        self.identification = identification
        self.phone = phone
        self.role = role

# Datos simulados
MOCK_USERS: List[MockUser] = [
    MockUser("U001", "Ana", "Gómez", "pass123", "123456789", "3001234567", MockRole("CLIENT")),
    MockUser("U002", "Luis", "Pérez", "pass456", "987654321", "3019876543", MockRole("CLIENT"))
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


if __name__ == '__main__':
    unittest.main()
