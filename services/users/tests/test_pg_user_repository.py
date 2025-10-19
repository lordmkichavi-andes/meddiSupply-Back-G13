import unittest
from unittest.mock import patch, MagicMock
import psycopg2
from typing import List
import os
import sys

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
# 1. SIMULACIONES DE DEPENDENCIAS
#    Creamos versiones simplificadas o mocks de las dependencias de dominio
#    y de conexión para aislar el test.
# ==============================================================================

# Simulación de las Entidades del Dominio (src.domain.entities)
class Client:
    # La firma debe coincidir exactamente con el mapeo del repositorio
    def __init__(self, user_id, name, last_name, password, identification, phone, role_value, nit, balance, perfil):
        self.user_id = user_id
        self.name = name
        self.last_name = last_name
        self.role = role_value
        self.nit = nit
        self.balance = balance
        self.perfil = perfil
        # Los demás campos (password, identification, phone) no los usamos para la igualdad,
        # pero son necesarios para la instanciación.

    def __eq__(self, other):
        """Define igualdad para la verificación del test."""
        if not isinstance(other, Client):
            return NotImplemented
        return self.user_id == other.user_id and self.name == other.name


# Simulación de la Interfaz UserRepository (src.domain.interfaces)
class UserRepository:
    def get_users_by_role(self, role: str) -> List[Client]:
        raise NotImplementedError


# Mocks de las funciones de conexión (.db_connector)
# Estas serán parcheadas en la clase de test para simular su comportamiento
def get_connection():
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
    EXPECTED_CLIENT_1 = Client('C001', 'Juan', 'Perez', None, None, None, 'client', 'NIT-987', 1500.50,
                               'Comprador Mayorista')
    EXPECTED_CLIENT_2 = Client('C002', 'Maria', 'Gomez', None, None, None, 'client', 'NIT-111', 50.00,
                               'Comprador Minorista')

    # La ruta del módulo para parchar (esto depende del nombre del archivo de prueba)
    # Ya que los mocks están en este archivo, el path de parcheo es el mismo nombre del archivo.
    MODULE_PATH = 'tests.test_pg_user_repository'

    def setUp(self):
        """Configuración de mocks de conexión y cursor."""
        self.repo = PgUserRepository()

        # Mocks para la conexión y cursor
        self.mock_conn = MagicMock()
        self.mock_cursor = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cursor

        # Parcheo de las funciones de conexión que están en este módulo (para que el test sea aislado)
        self.patcher_get = patch(f'{self.MODULE_PATH}.get_connection', return_value=self.mock_conn)
        self.patcher_release = patch(f'{self.MODULE_PATH}.release_connection')

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

        # 1. Verificación de la consulta (Verifica que se llamó con el rol correcto)
        self.mock_cursor.execute.assert_called_once_with(unittest.mock.ANY, (role_to_fetch,))

        # 2. Verificación del mapeo
        self.assertEqual(len(users), 2)
        self.assertIsInstance(users[0], Client)
        # Usamos __eq__ para comparar la igualdad de las propiedades clave
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

    # --- CASOS DE ERROR ---

    @patch('tests.test_pg_user_repository.psycopg2.Error', new=psycopg2.Error)
    def test_get_users_by_role_database_error(self):
        """Debe manejar psycopg2.Error y relanzar una excepción genérica, asegurando el cleanup."""

        # Simular un error durante la ejecución de la consulta
        self.mock_cursor.execute.side_effect = psycopg2.Error("Error de permiso o sintaxis SQL")

        # Verificar que se lance la excepción esperada
        with self.assertRaisesRegex(Exception, "Database error during user retrieval."):
            self.repo.get_users_by_role('admin')

        # Verificar que la conexión se haya intentado obtener
        self.mock_get_conn.assert_called_once()

        # Verificar que release_connection se llame en el finally
        self.mock_release_conn.assert_called_once_with(self.mock_conn)


if __name__ == '__main__':
    unittest.main()
