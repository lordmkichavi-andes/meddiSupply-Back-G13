import unittest
from dataclasses import dataclass
from typing import Dict, Any

# Importar las clases y el mapa del archivo original
# Asume que las clases están en un archivo llamado 'entities.py'
# Si las clases están en el mismo archivo de prueba, puedes omitir la línea de importación
# from entities import USER_ROLE_MAP, Role, User, Client

# --- Copia las definiciones de tu código aquí si no quieres importarlas ---
USER_ROLE_MAP: Dict[str, Dict[str, Any]] = {
    "ADMIN": {"name": "Administrador"},
    "SUPERVISOR": {"name": "Supervisor"},
    "SELLER": {"name": "Vendedor"},
    "CLIENT": {"name": "Cliente"},
}

@dataclass
class Role:
    """Entidad para el rol de usuario."""
    value: str
    name: str

@dataclass
class User:
    """Entidad central de Usuario."""
    user_id: str
    name: str
    last_name: str
    password: str
    identification: str
    phone: str
    role_value: str

    @property
    def role(self) -> Role:
        """Devuelve el objeto Role mapeado."""
        role_info = USER_ROLE_MAP.get(
            self.role_value,
            {"name": "Desconocido"}
        )
        return Role(self.role_value, role_info["name"])

    def get_user_role(self) -> Role:
        """
        Método del diagrama: retorna el rol del usuario.
        """
        return self.role

@dataclass
class Client(User):
    """Entidad de Cliente con atributos específicos."""
    nit: str
    balance: float
    perfil: str
# --------------------------------------------------------------------------


class TestRole(unittest.TestCase):
    """Pruebas para la entidad Role."""

    def test_role_initialization(self):
        """Verifica que un objeto Role se inicialice correctamente."""
        role = Role(value="ADMIN", name="Administrador")
        self.assertEqual(role.value, "ADMIN")
        self.assertEqual(role.name, "Administrador")

---

class TestUser(unittest.TestCase):
    """Pruebas para la entidad User."""

    def setUp(self):
        """Configura un objeto User base para las pruebas."""
        self.user_data = {
            "user_id": "u123",
            "name": "Juan",
            "last_name": "Pérez",
            "password": "hashed_password",
            "identification": "100000000",
            "phone": "3000000000",
            "role_value": "SELLER",
        }
        self.user = User(**self.user_data)

    def test_user_initialization(self):
        """Verifica que un objeto User se inicialice con todos sus atributos."""
        self.assertEqual(self.user.user_id, "u123")
        self.assertEqual(self.user.name, "Juan")
        self.assertEqual(self.user.role_value, "SELLER")

    def test_user_role_property(self):
        """Verifica que la propiedad 'role' devuelva el objeto Role correcto."""
        role = self.user.role
        self.assertIsInstance(role, Role)
        self.assertEqual(role.value, "SELLER")
        self.assertEqual(role.name, "Vendedor") # Mapeado desde USER_ROLE_MAP

    def test_user_role_property_for_admin(self):
        """Verifica el mapeo correcto para el rol ADMIN."""
        admin_user = User(**{**self.user_data, "role_value": "ADMIN"})
        role = admin_user.role
        self.assertEqual(role.value, "ADMIN")
        self.assertEqual(role.name, "Administrador")

    def test_user_role_unknown(self):
        """Verifica el mapeo a 'Desconocido' para un rol no definido."""
        unknown_user = User(**{**self.user_data, "role_value": "DEV"})
        role = unknown_user.role
        self.assertEqual(role.value, "DEV") # Mantiene el valor original
        self.assertEqual(role.name, "Desconocido") # Usa el nombre por defecto

    def test_get_user_role_method(self):
        """Verifica que el método get_user_role() retorne el rol correcto."""
        role = self.user.get_user_role()
        self.assertIsInstance(role, Role)
        self.assertEqual(role.value, "SELLER")
        self.assertEqual(role.name, "Vendedor")

---

class TestClient(unittest.TestCase):
    """Pruebas para la entidad Client."""

    def setUp(self):
        """Configura un objeto Client base para las pruebas."""
        self.client_data = {
            "user_id": "c456",
            "name": "Ana",
            "last_name": "Gómez",
            "password": "client_password",
            "identification": "200000000",
            "phone": "3100000000",
            "role_value": "CLIENT",
            "nit": "900123456-7",
            "balance": 1500.50,
            "perfil": "Premium",
        }
        self.client = Client(**self.client_data)

    def test_client_initialization(self):
        """Verifica que un objeto Client se inicialice con sus atributos propios."""
        self.assertEqual(self.client.nit, "900123456-7")
        self.assertEqual(self.client.balance, 1500.50)
        self.assertEqual(self.client.perfil, "Premium")

    def test_client_inherits_user_attributes(self):
        """Verifica que Client herede y se inicialice correctamente con los atributos de User."""
        self.assertEqual(self.client.user_id, "c456")
        self.assertEqual(self.client.name, "Ana")

    def test_client_role_property(self):
        """Verifica que Client use correctamente la propiedad de rol heredada."""
        role = self.client.role
        self.assertIsInstance(role, Role)
        self.assertEqual(role.value, "CLIENT")
        self.assertEqual(role.name, "Cliente")

    def test_client_get_user_role_method(self):
        """Verifica que Client use correctamente el método get_user_role() heredado."""
        role = self.client.get_user_role()
        self.assertIsInstance(role, Role)
        self.assertEqual(role.value, "CLIENT")
        self.assertEqual(role.name, "Cliente")

if __name__ == '__main__':
    unittest.main()