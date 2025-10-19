import unittest
import sys
from unittest.mock import Mock
from datetime import datetime, date
from typing import List, Dict, Any

# Aseguramos que los módulos de src se pueden importar
sys.path.append('src')

# Importamos las clases a probar y sus dependencias (interfaces/entidades)
from orders.src.application.use_cases import TrackOrdersUseCase


# Asumimos que OrderRepository y Order son interfaces/entidades, y las simulamos
# para evitar dependencias reales.

# --- Mocks de Entidades y Estructuras de Dominio ---

# Mock para simular la propiedad 'status' (el requisito de negocio)
class MockStatus:
    def __init__(self, name):
        self.name = name


# Mock para simular la Entidad Order
class MockOrder:
    """Simula la entidad de dominio Order con los atributos requeridos."""

    def __init__(self, order_id: str, creation_date: datetime, last_updated_date: datetime,
                 status_id: int, estimated_delivery_date: date | None):
        self.order_id = order_id
        self.creation_date = creation_date
        self.last_updated_date = last_updated_date
        self.status_id = status_id
        self.estimated_delivery_date = estimated_delivery_date

    @property
    def status(self):
        """Simula la lógica de obtener el nombre del estado (como si viniera de un Enum)."""
        if self.status_id == 1:
            return MockStatus("En camino")
        elif self.status_id == 5:
            return MockStatus("Procesando")
        elif self.status_id == 99:
            return MockStatus("Entregado")
        else:
            return MockStatus("Desconocido")


# Definición de datos de prueba (Mock Orders)
TEST_CLIENT_ID = "client_test_id"

# Órdenes de prueba que cubren los requisitos de estado y ordenamiento:
MOCK_ORDERS = [
    # O01: Última actualización MÁS reciente. Status 1 (necesita fecha estimada). Fecha estimada PRESENTE.
    MockOrder(
        order_id="O001",
        creation_date=datetime(2023, 10, 1),
        last_updated_date=datetime(2023, 10, 5, 15, 30, 0),
        status_id=1,
        estimated_delivery_date=datetime(2023, 10, 10, 15, 30)
    ),
    # O02: Última actualización INTERMEDIA. Status 5 (necesita fecha estimada). Fecha estimada AUSENTE.
    MockOrder(
        order_id="O002",
        creation_date=datetime(2023, 10, 3),
        last_updated_date=datetime(2023, 10, 5, 10, 0, 0),
        status_id=5,
        estimated_delivery_date=None
    ),
    # O03: Última actualización MÁS antigua. Status 99 (NO necesita fecha estimada).
    MockOrder(
        order_id="O003",
        creation_date=datetime(2023, 10, 2),
        last_updated_date=datetime(2023, 10, 4, 14, 0, 0),
        status_id=99,
        estimated_delivery_date=datetime(2023, 10, 12, 10, 0, 0)  # La fecha estimada debe ser ignorada
    ),
]


class TestTrackOrdersUseCase(unittest.TestCase):
    """
    Pruebas unitarias para el Caso de Uso TrackOrdersUseCase.
    """

    def setUp(self):
        """Configura el Mock del Repositorio y el Caso de Uso."""
        self.mock_repository = Mock()
        self.use_case = TrackOrdersUseCase(self.mock_repository)

    # --- Escenario de Éxito Completo ---

    def test_execute_success_and_formatting(self):
        """
        Verifica que la lógica de negocio se aplica correctamente:
        1. Ordenamiento por last_updated_date DESC.
        2. Formato de fechas.
        3. Lógica condicional de fecha estimada (status_id 1 y 5).
        """
        print("Ejecutando test_execute_success_and_formatting...")

        # 1. Configurar el Mock del repositorio para devolver datos
        self.mock_repository.get_orders_by_client_id.return_value = MOCK_ORDERS

        # 2. Ejecutar el caso de uso
        result = self.use_case.execute(TEST_CLIENT_ID)

        # 3. Verificar llamada al repositorio
        self.mock_repository.get_orders_by_client_id.assert_called_once_with(TEST_CLIENT_ID)

        # 4. Verificar Ordenamiento (O01, O02, O03)
        self.assertEqual(result[0]['numero_pedido'], "O001", "Debe estar ordenado por last_updated_date descendente.")
        self.assertEqual(result[1]['numero_pedido'], "O002", "Debe estar ordenado por last_updated_date descendente.")
        self.assertEqual(result[2]['numero_pedido'], "O003", "Debe estar ordenado por last_updated_date descendente.")

        # 5. Verificar Formato y Reglas (O01) - Status 1, Fecha Presente
        self.assertEqual(result[0]['estado_nombre'], "En camino")
        self.assertEqual(result[0]['fecha_creacion'], "2023-10-01")
        self.assertEqual(result[0]['fecha_ultima_actualizacion'], "2023-10-05 15:30:00")
        self.assertEqual(result[0]['fecha_entrega_estimada'], "2023-10-10 15:30")

        # 6. Verificar Formato y Reglas (O02) - Status 5, Fecha Ausente
        self.assertEqual(result[1]['estado_nombre'], "Procesando")
        self.assertEqual(result[1]['fecha_entrega_estimada'], "Entrega pendiente de programación",
                         "Debe mostrar mensaje de programación pendiente si la fecha es None.")

        # 7. Verificar Formato y Reglas (O03) - Status 99, Fecha NO Necesaria
        self.assertEqual(result[2]['estado_nombre'], "Entregado")
        self.assertIsNone(result[2]['fecha_entrega_estimada'],
                          "Debe ser None para estados que no son 1 o 5.")

    # --- Escenario de No Pedidos ---

    def test_execute_no_orders_found(self):
        """
        Verifica que retorna una lista vacía si el repositorio no devuelve pedidos.
        """
        print("Ejecutando test_execute_no_orders_found...")

        # 1. Configurar el Mock para devolver una lista vacía
        self.mock_repository.get_orders_by_client_id.return_value = []

        # 2. Ejecutar
        result = self.use_case.execute(TEST_CLIENT_ID)

        # 3. Verificar el resultado
        self.assertEqual(result, [])
        self.mock_repository.get_orders_by_client_id.assert_called_once_with(TEST_CLIENT_ID)

    # --- Escenario de Fallo del Repositorio ---

    def test_execute_repository_failure(self):
        """
        Verifica que si el repositorio lanza una excepción, esta se propaga
        hacia el nivel superior (el controlador Flask).
        """
        print("Ejecutando test_execute_repository_failure...")

        # 1. Configurar el Mock para lanzar una excepción
        MOCK_ERROR = Exception("Database connection failed")
        self.mock_repository.get_orders_by_client_id.side_effect = MOCK_ERROR

        # 2. Verificar que el caso de uso lanza la misma excepción
        with self.assertRaises(Exception) as context:
            self.use_case.execute(TEST_CLIENT_ID)

        self.assertEqual(str(context.exception), "Database connection failed")
        self.mock_repository.get_orders_by_client_id.assert_called_once_with(TEST_CLIENT_ID)

class TestCreateOrderUseCase(unittest.TestCase):
    """
    Pruebas unitarias para el Caso de Uso CreateOrderUseCase.
    """

    def setUp(self):
        self.mock_repository = Mock()
        self.use_case = CreateOrderUseCase(self.mock_repository)

    def test_execute_repository_failure(self):
        """
        Verifica que si el repositorio lanza una excepción, esta se propaga.
        """
        mock_order = Mock()
        self.mock_repository.insert_order.side_effect = Exception("Insert failed")

        with self.assertRaises(Exception) as context:
            self.use_case.execute(mock_order)

        self.assertEqual(str(context.exception), "Insert failed")
        self.mock_repository.insert_order.assert_called_once_with(mock_order)
        
if __name__ == '__main__':
    unittest.main()