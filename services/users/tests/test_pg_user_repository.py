import unittest
from unittest.mock import patch, MagicMock
import psycopg2
from typing import List
import os
import sys
from dataclasses import dataclass

# ==============================================================================
# FIJO PARA SOLUCIONAR ModuleNotFoundError en dependencias:
# (Este bloque se mantiene, aunque para este archivo autocontenido no es estrictamente necesario)
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
module_container_dir = os.path.dirname(current_dir)
sys.path.insert(0, module_container_dir)
# ==============================================================================

# ==============================================================================
# 1. ENTIDADES Y MOCKS DE CONEXIÓN (Entidades de Dominio Reales)
# ==============================================================================

USER_ROLE_MAP = {
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

    def __eq__(self, other):
        """Define igualdad para la verificación del test."""
        if not isinstance(other, Client):
            return NotImplemented
        # Compara las propiedades heredadas y específicas
        return (self.user_id == other.user_id and
                self.name == other.name and
                self.nit == other.nit)


# Simulación de la Interfaz UserRepository (src.domain.interfaces)
class UserRepository:
    def get_users_by_role(self, role: str) -> List[Client]:
        raise NotImplementedError


# Mocks de las funciones de conexión (.db_connector)
# Estas serán parcheadas en la clase de test para simular su comportamiento
def get_connection():
    """Simulación de la obtención de conexión."""
    pass


def release_connection(conn):
    """Simulación de la liberación de conexión."""
    pass


# ==============================================================================
# 2. REPOSITORIO A TESTEAR
# ==============================================================================

class PgUserRepository(UserRepository):
    """
    Implementación concreta que se conecta a PostgreSQL
    para obtener los datos de usuarios.
    """

    def get_users_by_role(self, role: str) -> List[Client]:
        conn = None
        users = []
        try:
            # Obtiene la conexión (mockeada en el test)
            conn = get_connection()
            cursor = conn.cursor()

            query = """
                SELECT
                    u.user_id,
                    u.name,
                    u.last_name,
                    u.password,
                    u.identification,
                    u.phone,
                    u.role,
                    c.nit,
                    c.balance,
                    c.perfil
                FROM "User" u
                INNER JOIN "Client" c ON u.user_id = c.user_id
                WHERE u.role = %s
                ORDER BY u.name ASC;
            """

            # Ejecutamos la consulta
            cursor.execute(query, (role,))

            for row in cursor.fetchall():
                (
                    user_id,
                    name,
                    last_name,
                    password,
                    identification,
                    phone,
                    role_value,
                    nit,
                    balance,
                    perfil
                ) = row

                # Mapeo a la entidad del dominio
                users.append(Client(
                    user_id=user_id,
                    name=name,
                    last_name=last_name,
                    password=password,
                    identification=identification,
                    phone=phone,
                    role_value=role_value,
                    nit=nit,
                    balance=balance,
                    perfil=perfil
                ))

            return users

        except psycopg2.Error as e:
            # Aquí se maneja el error de DB y se relanza una excepción genérica
            print(f"ERROR de base de datos al recuperar usuarios: {e}")
            raise Exception("Database error during user retrieval.")
        finally:
            if conn:
                # Libera la conexión (mockeada en el test)
                release_connection(conn)


# ==============================================================================
# 3. TESTS (CON CORRECCIÓN DE PATCHING)
# ==============================================================================

# Usamos __name__ para que el path de parcheo funcione correctamente en un archivo autocontenido
MODULE_PATH = __name__


class TestPgUserRepository(unittest.TestCase):
    # Datos simulados que retorna la DB
    MOCK_DB_ROW_1 = (
        'C001', 'Juan', 'Perez', 'hashed_pass_1', '123456', '555-1234', 'client',
        'NIT-987', 1500.50, 'Comprador Mayorista'
    )
    MOCK_DB_ROW_2 = (
        'C002', 'Maria', 'Gomez', 'hashed_pass_2', '654321', '555-4321', 'client',
        'NIT-111', 50.00, 'Comprador Minorista'
    )

    # Entidades esperadas para verificación
    EXPECTED_CLIENT_1 = Client('C001', 'Juan', 'Perez', 'hashed_pass_1', '123456', '555-1234', 'client', 'NIT-987',
                               1500.50, 'Comprador Mayorista')
    EXPECTED_CLIENT_2 = Client('C002', 'Maria', 'Gomez', 'hashed_pass_2', '654321', '555-4321', 'client', 'NIT-111',
                               50.00, 'Comprador Minorista')

    def setUp(self):
        """Configuración de mocks de conexión y cursor."""
        self.repo = PgUserRepository()

        # Mocks para la conexión y cursor
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Parcheo de las funciones de conexión que están en este módulo
        # FIX: Eliminamos 'return_value' del patch() para evitar problemas de scoping
        self.patcher_get = patch(f'{MODULE_PATH}.get_connection')
        self.patcher_release = patch(f'{MODULE_PATH}.release_connection')

        self.mock_get_conn = self.patcher_get.start()
        # EXPLICITLY set the return value on the started mock (More robust)
        self.mock_get_conn.return_value = self.mock_conn

        self.mock_release_conn = self.patcher_release.start()

    def tearDown(self):
        """Limpieza después de cada prueba."""
        self.patcher_get.stop()
        self.patcher_release.stop()

    # --- CASOS DE ÉXITO ---

    def test_get_users_by_role_success(self):
        """Debe retornar una lista de clientes mapeados correctamente para el rol 'client'."""

        role_to_fetch = 'client'
        self.mock_cursor.fetchall.return_value = [self.MOCK_DB_ROW_1, self.MOCK_DB_ROW_2]

        # Ejecutar la función
        users = self.repo.get_users_by_role(role_to_fetch)

        # 1. Verificación de la consulta
        self.mock_cursor.execute.assert_called_once_with(unittest.mock.ANY, (role_to_fetch,))

        # 2. Verificación del mapeo
        self.assertEqual(len(users), 2)
        self.assertIsInstance(users[0], Client)
        self.assertEqual(users[0], self.EXPECTED_CLIENT_1)
        self.assertEqual(users[1], self.EXPECTED_CLIENT_2)

        # 3. Verificación de la limpieza
        self.mock_release_conn.assert_called_once_with(self.mock_conn)

    def test_get_users_by_role_no_results(self):
        """Debe retornar una lista vacía cuando no hay coincidencias."""

        role_to_fetch = 'non_existent_role'
        self.mock_cursor.fetchall.return_value = []

        users = self.repo.get_users_by_role(role_to_fetch)

        self.assertEqual(len(users), 0)
        self.mock_cursor.execute.assert_called_once()
        self.mock_release_conn.assert_called_once_with(self.mock_conn)

    # --- CASOS DE ERROR (CORREGIDO) ---

    def test_get_users_by_role_database_error(self):
        """Debe manejar psycopg2.Error y relanzar una excepción genérica, asegurando el cleanup."""

        # Usar side_effect para simular el error de la DB en el cursor
        self.mock_cursor.execute.side_effect = psycopg2.Error("Error de base de datos simulado")

        # Verificar que se lance la excepción ESPERADA (la que se relanza en el 'except')
        with self.assertRaisesRegex(Exception, "Database error during user retrieval."):
            self.repo.get_users_by_role('admin')

        # Verificar que la conexión se haya intentado obtener
        self.mock_get_conn.assert_called_once()

        # Verificar que release_connection se llame en el 'finally'
        self.mock_release_conn.assert_called_once_with(self.mock_conn)


if __name__ == '__main__':
    # Esto permite ejecutar los tests directamente desde la línea de comandos
    unittest.main()
