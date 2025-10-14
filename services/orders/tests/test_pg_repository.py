import unittest
from unittest.mock import patch, Mock, call
import sys
from datetime import datetime, date
from psycopg2 import Error as Psycopg2Error

# Aseguramos que los módulos de src se pueden importar
sys.path.append('src')

# Importamos las clases a probar y sus dependencias
from src.infrastructure.persistence.pg_repository import PgOrderRepository
from src.domain.entities import Order

# Datos de prueba para simular la respuesta de la base de datos
CLIENT_ID_TEST = "client_abc_789"
MOCK_DB_ROWS = [
    # (order_id, creation_date, estimated_delivery_date, status_id, total_value, last_updated_date)
    ("ORD001", datetime(2023, 10, 15, 10, 0, 0), date(2023, 10, 25), 1, 150.50, datetime(2023, 10, 15, 10, 0, 0)),
    ("ORD002", datetime(2023, 10, 10, 9, 30, 0), date(2023, 10, 20), 3, 220.00, datetime(2023, 10, 10, 9, 30, 0)),
]


class TestPgOrderRepository(unittest.TestCase):
    """
    Pruebas unitarias para PgOrderRepository, mockeando la capa de conexión a la BD.
    """

    def setUp(self):
        """Inicializa el repositorio antes de cada prueba."""
        self.repository = PgOrderRepository()

    def _setup_mocks(self, mock_get_conn, fetchall_return_value):
        """
        Configura los mocks de conexión, cursor y la respuesta de fetchall.
        Retorna la instancia del mock de conexión para verificaciones posteriores.
        """
        mock_conn = Mock()
        mock_cursor = Mock()

        # Configurar el flujo: get_connection -> mock_conn -> cursor -> mock_cursor
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = fetchall_return_value

        return mock_conn, mock_cursor

    # --- Test de Escenario de Éxito ---

    @patch('src.infrastructure.persistence.pg_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_repository.get_connection')
    def test_get_orders_by_client_id_success(self, mock_get_conn, mock_release_conn):
        """
        Verifica que se recuperan los datos, se mapean a entidades Order
        y se liberan las conexiones.
        """
        print("Ejecutando test_get_orders_by_client_id_success...")

        mock_conn, mock_cursor = self._setup_mocks(mock_get_conn, MOCK_DB_ROWS)

        orders = self.repository.get_orders_by_client_id(CLIENT_ID_TEST)

        # 1. Verificar la llamada a execute con la consulta y los parámetros
        expected_query_call = mock_cursor.execute.call_args[0][0].strip().replace('\n', ' ').replace(' ', '')
        expected_query_start = "SELECTo.order_id,o.creation_date,o.estimated_delivery_date,o.current_state_id,o.total_value,MAX(o.creation_date)ASlast_updated_dateFROM\"Order\"oWHEREo.user_id=%sGROUPBYo.order_id,o.creation_date,o.estimated_delivery_date,o.current_state_id,o.total_valueORDERBYlast_updated_dateDESC;"
        self.assertTrue(expected_query_call.startswith(expected_query_start),
                        f"La consulta ejecutada no coincide con el inicio esperado. Ejecutada: {expected_query_call[:100]}...")
        self.assertEqual(mock_cursor.execute.call_args[0][1], (CLIENT_ID_TEST,))

        # 2. Verificar el resultado (que se mapee a la entidad Order)
        self.assertEqual(len(orders), 2)
        self.assertIsInstance(orders[0], Order)
        self.assertEqual(orders[0].order_id, "ORD001")
        self.assertEqual(orders[1].order_id, "ORD002")

        # 3. Verificar que la conexión se obtuvo y se liberó
        mock_get_conn.assert_called_once()
        mock_release_conn.assert_called_once_with(mock_conn)

    # --- Test de Datos No Encontrados ---

    @patch('src.infrastructure.persistence.pg_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_repository.get_connection')
    def test_get_orders_by_client_id_no_results(self, mock_get_conn, mock_release_conn):
        """
        Verifica que retorna una lista vacía si la BD no devuelve filas.
        """
        print("Ejecutando test_get_orders_by_client_id_no_results...")

        mock_conn, _ = self._setup_mocks(mock_get_conn, [])  # Devuelve lista vacía

        orders = self.repository.get_orders_by_client_id(CLIENT_ID_TEST)

        # 1. Verificar el resultado
        self.assertEqual(orders, [])

        # 2. Verificar que la conexión se liberó
        mock_release_conn.assert_called_once_with(mock_conn)

    # --- Test de Error de Base de Datos ---

    @patch('src.infrastructure.persistence.pg_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_repository.get_connection')
    @patch('builtins.print')
    def test_get_orders_by_client_id_db_error(self, mock_print, mock_get_conn, mock_release_conn):
        """
        Verifica que un psycopg2.Error es capturado, se registra el error
        y se relanza como una excepción genérica.
        """
        print("Ejecutando test_get_orders_by_client_id_db_error...")

        mock_conn, mock_cursor = self._setup_mocks(mock_get_conn, [])

        # Configurar el cursor para lanzar un error de BD al ejecutar la consulta
        MOCK_ERROR = Psycopg2Error("Simulated PostgreSQL connection failure")
        mock_cursor.execute.side_effect = MOCK_ERROR

        # 1. Verificar que se lanza la excepción
        with self.assertRaisesRegex(Exception, "Database error during order retrieval."):
            self.repository.get_orders_by_client_id(CLIENT_ID_TEST)

        # 2. Verificar que se registró el error
        mock_print.assert_any_call(f"ERROR de base de datos al recuperar pedidos: {MOCK_ERROR}")

        # 3. Verificar que la conexión se liberó
        mock_release_conn.assert_called_once_with(mock_conn)

    # --- Test de Error al Obtener Conexión ---

    @patch('src.infrastructure.persistence.pg_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_repository.get_connection', side_effect=Exception("Pool error"))
    @patch('builtins.print')
    def test_get_orders_by_client_id_connection_error(self, mock_print, mock_get_conn, mock_release_conn):
        """
        Verifica que si get_connection falla, se propaga la excepción
        y release_connection NO es llamado (ya que conn es None).
        """
        print("Ejecutando test_get_orders_by_client_id_connection_error...")

        # 1. Verificar que se lanza la excepción
        with self.assertRaisesRegex(Exception, "Pool error"):
            self.repository.get_orders_by_client_id(CLIENT_ID_TEST)

        # 2. Verificar que release_connection NO fue llamado
        mock_release_conn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
