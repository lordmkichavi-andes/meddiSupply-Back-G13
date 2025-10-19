import unittest
from unittest.mock import patch, MagicMock
import psycopg2
from typing import List
import os
import sys
from dataclasses import dataclass

# ==============================================================================
# FIJO PARA SOLUCIONAR ModuleNotFoundError:
# Añade el directorio padre de 'tests' (e.g., 'users') al path.
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
module_container_dir = os.path.dirname(current_dir)
sys.path.insert(0, module_container_dir)
# ==============================================================================

# ==============================================================================
# 1. ENTIDADES Y MOCKS DE CONEXIÓN
# Se asume que estas son las entidades reales.
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


# Simulación de la Interfaz UserRepository
class UserRepository:
    def get_users_by_role(self, role: str) -> List[Client]:
        raise NotImplementedError


# Mocks de las funciones de conexión (.db_connector)
# Estas deben existir aquí para que el parche las intercepte.
def get_connection():
    pass


def release_connection(conn):
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
            # Aquí ocurre el error si el mock falla
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
            print(f"ERROR de base de datos al recuperar usuarios: {e}")
            raise Exception("Database error during user retrieval.")
        finally:
            if conn:
                release_connection(conn)


# ==============================================================================
# 3. TESTS
# ==============================================================================

class TestPgUserRepository(unittest.TestCase):
    # --- DATOS Y MOCKS GLOBALES DE LA CLASE ---
    MOCK_DB_ROW_1 = (
        'C001', 'Juan', 'Perez', 'hashed_pass_1', '123456', '555-1234', 'client',
        'NIT-987', 1500.50, 'Comprador Mayorista'
    )
    EXPECTED_CLIENT_1 = Client('C001', 'Juan', 'Perez', 'hashed_pass_1', '123456', '555-1234', 'client', 'NIT-987',
                               1500.50, 'Comprador Mayorista')

    # Definición de Mocks de Conexión
    MOCK_CONN = MagicMock()
    MOCK_CURSOR = MagicMock()
    # Aseguramos que el mock de conexión tenga un cursor simulado
    MOCK_CONN.cursor.return_value = MOCK_CURSOR

    # RUTA DE PARCHE: Debe apuntar al módulo actual (tests.test_entities)
    # donde se definen las funciones get_connection y release_connection.
    MODULE_PATH = 'tests.test_entities'

    # ------------------------------------------

    # --- CASOS DE ÉXITO ---

    @patch(f'{MODULE_PATH}.release_connection')
    @patch(f'{MODULE_PATH}.get_connection', return_value=MOCK_CONN)
    def test_get_users_by_role_success(self, mock_get_conn, mock_release_conn):
        """Debe retornar una lista de clientes mapeados correctamente."""

        mock_cursor = self.MOCK_CURSOR
        mock_conn = self.MOCK_CONN
        mock_cursor.fetchall.return_value = [self.MOCK_DB_ROW_1]

        repo = PgUserRepository()
        users = repo.get_users_by_role('client')

        # 1. Verificación de la consulta
        mock_cursor.execute.assert_called_once()

        # 2. Verificación del mapeo
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0], self.EXPECTED_CLIENT_1)

        # 3. Verificación de la limpieza
        mock_release_conn.assert_called_once_with(mock_conn)

    @patch(f'{MODULE_PATH}.release_connection')
    @patch(f'{MODULE_PATH}.get_connection', return_value=MOCK_CONN)
    def test_get_users_by_role_no_results(self, mock_get_conn, mock_release_conn):
        """Debe retornar una lista vacía cuando no hay coincidencias."""

        mock_cursor = self.MOCK_CURSOR
        mock_conn = self.MOCK_CONN
        mock_cursor.fetchall.return_value = []

        repo = PgUserRepository()
        users = repo.get_users_by_role('non_existent_role')

        self.assertEqual(len(users), 0)
        mock_release_conn.assert_called_once_with(mock_conn)

    # --- CASOS DE ERROR ---

    @patch(f'{MODULE_PATH}.release_connection')
    @patch(f'{MODULE_PATH}.get_connection', return_value=MOCK_CONN)
    def test_get_users_by_role_database_error(self, mock_get_conn, mock_release_conn):
        """Debe manejar psycopg2.Error, relanzar una excepción genérica y hacer cleanup."""

        mock_cursor = self.MOCK_CURSOR
        mock_conn = self.MOCK_CONN
        repo = PgUserRepository()

        try:
            # Simular un error durante la ejecución de la consulta
            # Esto hace que el código salte al bloque except
            mock_cursor.execute.side_effect = psycopg2.Error("Error de permiso")

            # Verificar que se lance la excepción esperada
            with self.assertRaisesRegex(Exception, "Database error during user retrieval."):
                repo.get_users_by_role('admin')

            # Verificar que release_connection se llame en el finally
            mock_release_conn.assert_called_once_with(mock_conn)

        finally:
            # Asegurar el restablecimiento del side effect para el resto de las pruebas.
            mock_cursor.execute.side_effect = None


if __name__ == '__main__':
    unittest.main()
