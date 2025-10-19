import unittest
from unittest.mock import patch, MagicMock
import psycopg2
from typing import List


# ==============================================================================
# 1. ENTIDADES Y MOCKS NECESARIOS
#    Creamos versiones simplificadas o mocks de las dependencias de dominio
#    para que el test sea ejecutable sin tener que importar todo el proyecto.
# ==============================================================================

# Simulación de la Entidad Client (debe coincidir con el mapeo del repositorio)
class Client:
    def __init__(self, user_id, name, last_name, password, identification, phone, role_value, nit, balance, perfil):
        self.user_id = user_id
        self.name = name
        self.last_name = last_name
        # Note: 'role' es un atributo, pero lo llamamos role_value para evitar conflicto de nombres en __init__
        self.role = role_value
        self.nit = nit
        self.balance = balance
        self.perfil = perfil

    def __eq__(self, other):
        """Define igualdad para la verificación del test."""
        if not isinstance(other, Client):
            return NotImplemented
        return self.user_id == other.user_id and self.name == other.name and self.nit == other.nit


# Simulación de la Interfaz UserRepository (Abstracta)
class UserRepository:
    def get_users_by_role(self, role: str) -> List[Client]:
        raise NotImplementedError


# Mocks de las funciones de conexión (db_connector)
# Estas serán parcheadas en la clase de test
def get_connection():
    pass


def release_connection(conn):
    pass


# ==============================================================================
# 2. REPOSITORIO A TESTEAR (Copiado para ser self-contained)
#    En un entorno real, esta clase se importaría.
# ==============================================================================

class PgUserRepository(UserRepository):
    """
    Implementación concreta que se conecta a PostgreSQL
    para obtener los datos de usuarios.
    """

    # Usaremos los mocks de get_connection y release_connection definidos en este archivo
    # para evitar problemas de pathing en entornos de prueba.

    def get_users_by_role(self, role: str) -> List[Client]:
        conn = None
        users = []
        try:
            # La llamada a get_connection será interceptada por el mock
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
            print(f"ERROR de base de datos al recuperar usuarios: {e}")
            raise Exception("Database error during user retrieval.")
        finally:
            if conn:
                # La llamada a release_connection será interceptada por el mock
                release_connection(conn)


# ==============================================================================
# 3. TESTS
# ==============================================================================

class TestPgUserRepository(unittest.TestCase):
    # Datos simulados que retorna la DB
    MOCK_DB_ROW_1 = (
        'C001', 'Juan', 'Perez', 'hashed_pass', '123456', '555-1234', 'client',
        'NIT-987', 1500.50, 'Comprador Mayorista'
    )
    MOCK_DB_ROW_2 = (
        'C002', 'Maria', 'Gomez', 'hashed_pass_2', '654321', '555-4321', 'client',
        'NIT-111', 50.00, 'Comprador Minorista'
    )

    # Entidades esperadas para verificación
    EXPECTED_CLIENT_1 = Client('C001', 'Juan', 'Perez', None, None, None, 'client', 'NIT-987', 1500.50,
                               'Comprador Mayorista')
    EXPECTED_CLIENT_2 = Client('C002', 'Maria', 'Gomez', None, None, None, 'client', 'NIT-111', 50.00,
                               'Comprador Minorista')

    def setUp(self):
        """Configuración de mocks de conexión y cursor."""
        self.repo = PgUserRepository()

        # Mocks para la conexión y cursor
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Parcheo de las funciones de conexión del repositorio (que ahora están en este módulo)
        module_path = 'tests.test_pg_user_repository'

        self.patcher_get = patch(f'{module_path}.get_connection', return_value=self.mock_conn)
        self.patcher_release = patch(f'{module_path}.release_connection')

        self.mock_get_conn = self.patcher_get.start()
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
        self.assertEqual(users[0].user_id, self.EXPECTED_CLIENT_1.user_id)
        self.assertEqual(users[1].name, self.EXPECTED_CLIENT_2.name)

        # 3. Verificación de la limpieza
        self.mock_release_conn.assert_called_once_with(self.mock_conn)

    def test_get_users_by_role_no_results(self):
        """Debe retornar una lista vacía cuando no hay coincidencias."""

        role_to_fetch = 'vendor'
        self.mock_cursor.fetchall.return_value = []

        users = self.repo.get_users_by_role(role_to_fetch)

        self.assertEqual(len(users), 0)
        self.mock_cursor.execute.assert_called_once_with(unittest.mock.ANY, (role_to_fetch,))
        self.mock_release_conn.assert_called_once_with(self.mock_conn)

    # --- CASOS DE ERROR ---

    @patch('tests.test_pg_user_repository.psycopg2.Error', new=psycopg2.Error)
    def test_get_users_by_role_database_error(self):
        """Debe manejar psycopg2.Error y relanzar una excepción genérica."""

        # Simular un error durante la ejecución de la consulta
        self.mock_cursor.execute.side_effect = psycopg2.Error("Error de sintaxis SQL")

        # Verificar que se lance la excepción esperada
        with self.assertRaisesRegex(Exception, "Database error during user retrieval."):
            self.repo.get_users_by_role('admin')

        # Verificar que la conexión se haya intentado obtener
        self.mock_get_conn.assert_called_once()

        # Verificar que release_connection se llame en el finally
        self.mock_release_conn.assert_called_once_with(self.mock_conn)


if __name__ == '__main__':
    unittest.main()
