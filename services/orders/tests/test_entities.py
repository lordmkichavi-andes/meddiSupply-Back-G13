# Importaciones necesarias para las pruebas
import pytest
from datetime import datetime

# Importamos las entidades del archivo de destino
# Asegúrate de que tu configuración de pytest permite esta importación (python_paths = .)
from src.domain.entities import Order, OrderStatus, ORDER_STATUS_MAP

# 1. Preparación de datos de prueba
# Definimos una fecha base para no tener que crear una en cada test.
MOCK_DATE = datetime(2025, 1, 15, 10, 30, 0)
MOCK_DELIVERY_DATE = datetime(2025, 1, 20, 10, 30, 0)

# 2. Parametrización para probar todos los estados mapeados
# Esto asegura que todos los IDs en ORDER_STATUS_MAP se prueben.
STATUS_TEST_CASES = [
    (status_id, info["name"])
    for status_id, info in ORDER_STATUS_MAP.items()
]


class TestDomainEntities:
    """
    Colección de pruebas unitarias para las entidades Order y OrderStatus.
    """

    def test_order_status_instantiation(self):
        """Verifica que la entidad OrderStatus se instancia correctamente."""
        status = OrderStatus(id=1, name="En camino")
        assert status.id == 1
        assert status.name == "En camino"

    def test_order_instantiation_with_delivery_date(self):
        """Verifica que la entidad Order se instancia correctamente con fecha de entrega."""
        order = Order(
            order_id="ORD-123",
            client_id="1",
            creation_date=MOCK_DATE,
            status_id=3,
            estimated_delivery_date=MOCK_DELIVERY_DATE,
            orders=[]
        )
        assert order.order_id == "ORD-123"
        assert order.status_id == 3
        assert order.estimated_delivery_date == MOCK_DELIVERY_DATE

    def test_order_instantiation_without_delivery_date(self):
        """Verifica que la entidad Order se instancia correctamente sin fecha de entrega (None)."""
        order = Order(
            order_id="ORD-456",
            client_id="1",
            creation_date=MOCK_DATE,
            status_id=1,
            estimated_delivery_date=None,
            orders=[]
        )
        assert order.order_id == "ORD-456"
        assert order.estimated_delivery_date is None

    @pytest.mark.parametrize("status_id, expected_name", STATUS_TEST_CASES)
    def test_order_status_property_returns_correct_status(self, status_id: int, expected_name: str):
        """
        Verifica que la propiedad 'status' mapea correctamente el status_id
        al objeto OrderStatus con el nombre esperado.
        """
        order = Order(
            order_id="ORD-789",
            client_id="1",
            creation_date=MOCK_DATE,
            status_id=status_id,
            orders=[]
        )
        # La propiedad .status debe devolver OrderStatus
        assert isinstance(order.status, OrderStatus)
        # El ID y el nombre deben coincidir con el mapeo
        assert order.status.id == status_id
        assert order.status.name == expected_name

    def test_order_status_property_handles_unknown_id(self):
        """Verifica que la propiedad 'status' maneja IDs no definidos correctamente."""
        UNKNOWN_ID = 99
        order = Order(
            order_id="ORD-000",
            client_id="1",
            creation_date=MOCK_DATE,
            status_id=UNKNOWN_ID,
            orders=[]
        )
        # Debe devolver el ID desconocido y el nombre 'Desconocido'
        assert order.status.id == UNKNOWN_ID
        assert order.status.name == "Desconocido"
