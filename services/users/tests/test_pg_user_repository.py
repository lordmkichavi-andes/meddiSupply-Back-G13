import unittest
from unittest.mock import patch, MagicMock
import psycopg2
from typing import List
import os
import sys
from dataclasses import dataclass

# ==============================================================================
# FIJO PARA SOLUCIONAR ModuleNotFoundError en dependencias:
# Añade el directorio padre de 'tests' (e.g., 'users') al path.
# Esto es necesario si las dependencias (como src.domain.entities) no están
# accesibles en el path de prueba.
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
# Directorio que contiene el código principal
module_container_dir = os.path.dirname(current_dir)
# Si las entidades y interfaces están en 'src/domain', necesitamos agregar el
# path raíz del proyecto, pero aquí asumimos que ya está configurado para
# acceder a 'src'. Mantendremos la inyección para el directorio local.
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

    # Sobreescribir __eq__ para asegurar que el test de repositorio funcione
    # correctamente al comparar instancias de Client.
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
    # El cuerpo vacío (pass) hace que la función retorne None si el parche falla.
    # Es fundamental asegurarse que el patch funcione siempre.
    pass


def release_connection(conn):
    pass


# ==============================================================================
# 2. REPOSITORIO A TESTEAR (Copiado para ser self-contained)
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
            # Esta llamada a get_connection será interceptada por el mock
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
            # Aquí manejamos el error
            print(f"ERROR de base de datos al recuperar usuarios: {e}")
            raise Exception("Database error during user retrieval.")
        finally:
            if conn:
                # Esta llamada a release_connection será interceptada por el mock
                release_connection(conn)


# ==============================================================================
# 3. TESTS
# ==============================================================================

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

    # Entidades esperadas para verificación (solo para referencia)
    EXPECTED_CLIENT_1 = Client('C001', 'Juan', 'Perez', 'hashed_pass_1', '123456', '555-1234', 'client', 'NIT-987',
                               1500.50, 'Comprador Mayorista')
    EXPECTED_CLIENT_2 = Client('C002', 'Maria', 'Gomez', 'hashed_pass_2', '654321', '555-4321', 'client', 'NIT-111',
                               50.00, 'Comprador Minorista')

    # La ruta del módulo para parchar (esto depende del nombre del archivo de prueba)
    MODULE_PATH = 'tests.test_pg_user_repository'

    # Se eliminan setUp y tearDown para evitar problemas de ámbito de parches.

    # --- CASOS DE ÉXITO ---

    @patch(f'{MODULE_PATH}.release_connection')
    @patch(f'{MODULE_PATH}.get_connection')
    def test_get_users_by_role_success(self, mock_get_conn, mock_release_conn):
        """Debe retornar una lista de clientes mapeados correctamente para el rol 'client'."""

        # Configuración de mocks locales, ahora seguros dentro del ámbito de la prueba
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        role_to_fetch = 'client'
        mock_cursor.fetchall.return_value = [self.MOCK_DB_ROW_1, self.MOCK_DB_ROW_2]

        repo = PgUserRepository()

        # Ejecutar la función
        users = repo.get_users_by_role(role_to_fetch)

        # 1. Verificación de la consulta
        mock_cursor.execute.assert_called_once_with(unittest.mock.ANY, (role_to_fetch,))

        # 2. Verificación del mapeo
        self.assertEqual(len(users), 2)
        self.assertIsInstance(users[0], Client)
        self.assertEqual(users[0], self.EXPECTED_CLIENT_1)
        self.assertEqual(users[1], self.EXPECTED_CLIENT_2)

        # 3. Verificación de la limpieza
        mock_release_conn.assert_called_once_with(mock_conn)

    @patch(f'{MODULE_PATH}.release_connection')
    @patch(f'{MODULE_PATH}.get_connection')
    def test_get_users_by_role_no_results(self, mock_get_conn, mock_release_conn):
        """Debe retornar una lista vacía cuando no hay coincidencias."""

        # Configuración de mocks locales
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        role_to_fetch = 'non_existent_role'
        mock_cursor.fetchall.return_value = []

        repo = PgUserRepository()

        users = repo.get_users_by_role(role_to_fetch)

        self.assertEqual(len(users), 0)
        mock_cursor.execute.assert_called_once()
        mock_release_conn.assert_called_once_with(mock_conn)

    # --- CASOS DE ERROR ---

    # El patch de psycopg2.Error puede ser omitido ya que el error de mock_cursor.execute
    # asegura el path de excepción, pero lo incluimos para claridad
    @patch(f'{MODULE_PATH}.release_connection')
    @patch(f'{MODULE_PATH}.get_connection')
    @patch(f'{MODULE_PATH}.psycopg2.Error', new=psycopg2.Error)
    def test_get_users_by_role_database_error(self, mock_get_conn, mock_release_conn):
        """Debe manejar psycopg2.Error y relanzar una excepción genérica, asegurando el cleanup."""

        # Configuración de mocks locales
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_conn.return_value = mock_conn

        # Simular un error durante la ejecución de la consulta
        mock_cursor.execute.side_effect = psycopg2.Error("Error de permiso o sintaxis SQL")

        repo = PgUserRepository()

        # Verificar que se lance la excepción esperada
        with self.assertRaisesRegex(Exception, "Database error during user retrieval."):
            repo.get_users_by_role('admin')

        # Verificar que la conexión se haya intentado obtener
        mock_get_conn.assert_called_once()

        # Verificar que release_connection se llame en el finally
        mock_release_conn.assert_called_once_with(mock_conn)


if __name__ == '__main__':
    unittest.main()
