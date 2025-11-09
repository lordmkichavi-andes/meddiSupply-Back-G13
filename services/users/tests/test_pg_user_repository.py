import pytest
from unittest.mock import Mock, patch
import psycopg2

from src.infrastructure.persistence.pg_user_repository import PgUserRepository
from src.domain.entities import Client


class TestPgUserRepository:
    """Tests unitarios para PgUserRepository"""

    @pytest.fixture
    def repository(self):
        """Fixture que proporciona una instancia del repositorio"""
        return PgUserRepository()

    @pytest.fixture
    def mock_connection(self):
        """Fixture que proporciona una conexión mock"""
        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        return conn, cursor

    @pytest.fixture
    def sample_db_rows(self):
        """Fixture con datos de ejemplo de la base de datos"""
        return [
            (
                1,
                1,
                "Juan",
                "Pérez",
                "hashed_password_123",
                "1234567890",
                "3001234567",
                'CLIENT',
                "900123456-7",
                1500000.50,
                "premium",
                'Calle 72 # 10-30, Bogotá',
                4.659970,
                -74.058370
            ),
            (
                2,
                2,
                "María",
                "González",
                "hashed_password_456",
                "0987654321",
                "3107654321",
                'CLIENT',
                "900654321-1",
                2500000.00,
                "basic",
                'Calle 72 # 10-30, Bogotá',
                4.659970,
                -74.058370
            )
        ]

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection,
            sample_db_rows
    ):
        """Test: recuperación exitosa de usuarios por rol"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = sample_db_rows

        # Act
        result = repository.get_users_by_role('CLIENT')

        # Assert
        assert len(result) == 2
        assert all(isinstance(user, Client) for user in result)

        # Verificar primer usuario
        assert result[0].user_id == 1
        assert result[0].name == "Juan"
        assert result[0].last_name == "Pérez"
        assert result[0].password == "hashed_password_123"
        assert result[0].identification == "1234567890"
        assert result[0].phone == "3001234567"
        assert result[0].role_value == 'CLIENT'
        assert result[0].nit == "900123456-7"
        assert result[0].balance == 1500000.50
        assert result[0].perfil == "premium"

        # Verificar segundo usuario
        assert result[1].user_id == 2
        assert result[1].name == "María"

        # Verificar que se llamó la query correcta
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args
        assert "SELECT" in call_args[0][0]
        assert 'WHERE u.role IN (%s)' in call_args[0][0]
        assert call_args[0][1] == ('CLIENT',)

        # Verificar que se liberó la conexión
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_users_by_seller
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_seller_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: recuperación exitosa de usuarios por seller_id"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        seller_rows = [
            (1, 1, "Juan", "Pérez", "hashed_password_123", "1234567890", "3001234567",
             'CLIENT', "premium", "900123456-7", 1500000.50, 'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370)
        ]
        cursor.fetchall.return_value = seller_rows

        # Act
        result = repository.get_users_by_seller("123")

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], Client)
        assert result[0].user_id == 1
        assert result[0].name == "Juan"
        cursor.execute.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_seller_empty_result(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: no se encuentran usuarios para el seller_id"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_users_by_seller("999")

        # Assert
        assert result == []
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_seller_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: manejo de error de base de datos en get_users_by_seller"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.get_users_by_seller("123")

        assert str(exc_info.value) == "Database error during user retrieval."
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para db_get_client_data
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_db_get_client_data_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa de datos del cliente"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda key: {
            'client_id': 1,
            'user_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'juan@example.com',
            'balance': 1500000.50,
            'address': 'Calle 72 # 10-30',
            'latitude': 4.659970,
            'longitude': -74.058370,
            'seller_zone': 'Zona Norte'
        }[key])
        mock_row.keys.return_value = ['client_id', 'user_name', 'last_name', 'email', 'balance', 'address', 'latitude', 'longitude', 'seller_zone']
        cursor.fetchone.return_value = mock_row

        # Act
        result = repository.db_get_client_data(1)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['client_id'] == 1
        cursor.execute.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_db_get_client_data_not_found(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: cliente no encontrado"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = None

        # Act
        result = repository.db_get_client_data(999)

        # Assert
        assert result is None
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_db_get_client_data_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en db_get_client_data"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.db_get_client_data(1)

        assert "Database error during client profile retrieval" in str(exc_info.value)
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('sys.stderr')
    def test_db_get_client_data_unexpected_error(
            self,
            mock_stderr,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error inesperado en db_get_client_data"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = ValueError("Unexpected error")

        # Act & Assert
        with pytest.raises(Exception):
            repository.db_get_client_data(1)

        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_by_id
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_by_id_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa de visita por ID"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda key: {
            'client_id': 1,
            'name': 'Juan',
            'last_name': 'Pérez'
        }[key])
        mock_row.keys.return_value = ['client_id', 'name', 'last_name']
        cursor.fetchone.return_value = mock_row

        # Act
        result = repository.get_by_id(1)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['client_id'] == 1
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_by_id_not_found(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: visita no encontrada"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = None

        # Act
        result = repository.get_by_id(999)

        # Assert
        assert result is None
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_by_id_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en get_by_id"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(psycopg2.Error):
            repository.get_by_id(1)

        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_visit_by_id
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_visit_by_id_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa de visita por ID"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda key: {
            'visit_id': 1,
            'seller_id': 2,
            'date': '2025-01-15',
            'findings': 'Todo OK',
            'client_id': 3
        }[key])
        mock_row.keys.return_value = ['visit_id', 'seller_id', 'date', 'findings', 'client_id']
        cursor.fetchone.return_value = mock_row

        # Act
        result = repository.get_visit_by_id(1)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['visit_id'] == 1
        assert result['client_id'] == 3
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_visit_by_id_not_found(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: visita no encontrada"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = None

        # Act
        result = repository.get_visit_by_id(999)

        # Assert
        assert result is None
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_visit_by_id_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en get_visit_by_id"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.get_visit_by_id(1)

        assert "Database error during visit retrieval" in str(exc_info.value)
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para save_visit
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_save_visit_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: guardado exitoso de visita"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = (123,)  # visit_id retornado

        # Act
        result = repository.save_visit(
            client_id=1,
            seller_id=2,
            date="2025-01-15",
            findings="Todo OK"
        )

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['visit_id'] == 123
        assert result['client_id'] == 1
        assert result['seller_id'] == 2
        assert result['date'] == "2025-01-15"
        assert result['findings'] == "Todo OK"
        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_save_visit_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en save_visit"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.save_visit(1, 2, "2025-01-15", "Test")

        assert str(exc_info.value) == "Database error during visit saving."
        conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_recent_evidences_by_client
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_evidences_by_client_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa de evidencias recientes"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_row1 = Mock()
        mock_row1.__getitem__ = Mock(side_effect=lambda key: {'url': 'http://example.com/img1.jpg', 'type': 'IMAGE'}[key])
        mock_row1.keys.return_value = ['url', 'type']
        mock_row2 = Mock()
        mock_row2.__getitem__ = Mock(side_effect=lambda key: {'url': 'http://example.com/img2.jpg', 'type': 'VIDEO'}[key])
        mock_row2.keys.return_value = ['url', 'type']
        cursor.fetchall.return_value = [mock_row1, mock_row2]

        # Act
        result = repository.get_recent_evidences_by_client(1)

        # Assert
        assert len(result) == 2
        assert isinstance(result, list)
        assert result[0]['url'] == 'http://example.com/img1.jpg'
        assert result[0]['type'] == 'IMAGE'
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_evidences_by_client_empty(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: no hay evidencias para el cliente"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_recent_evidences_by_client(999)

        # Assert
        assert result == []
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_evidences_by_client_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en get_recent_evidences_by_client"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.get_recent_evidences_by_client(1)

        assert "Database error during recent evidences retrieval" in str(exc_info.value)
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_recent_purchase_history
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_purchase_history_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa del historial de compras"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = [
            ("SKU-001", "Producto 1"),
            ("SKU-002", "Producto 2")
        ]

        # Act
        result = repository.get_recent_purchase_history(1, limit=10)

        # Assert
        assert len(result) == 2
        assert result[0]['sku'] == "SKU-001"
        assert result[0]['name'] == "Producto 1"
        assert result[1]['sku'] == "SKU-002"
        assert result[1]['name'] == "Producto 2"
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_purchase_history_empty(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: no hay historial de compras"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_recent_purchase_history(999, limit=10)

        # Assert
        assert result == []
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_purchase_history_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en get_recent_purchase_history"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.get_recent_purchase_history(1, limit=10)

        assert "Database error retrieving purchase history" in str(exc_info.value)
        conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_products
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_get_products_success(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa del catálogo de productos"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_row1 = Mock()
        mock_row1.__getitem__ = Mock(side_effect=lambda key: {
            'product_id': 1,
            'sku': 'SKU-001',
            'value': 10000,
            'name': 'Producto 1',
            'image_url': 'http://example.com/img1.jpg',
            'category_name': 'Categoría 1',
            'total_quantity': 50
        }[key])
        mock_row1.keys.return_value = ['product_id', 'sku', 'value', 'name', 'image_url', 'category_name', 'total_quantity']
        cursor.fetchall.return_value = [mock_row1]

        # Act
        result = repository.get_products()

        # Assert
        assert len(result) == 1
        assert result[0]['product_id'] == 1
        assert result[0]['sku'] == 'SKU-001'
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_get_products_empty(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: no hay productos disponibles"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_products()

        # Assert
        assert result == []
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_get_products_database_error(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en get_products"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act
        result = repository.get_products()

        # Assert
        assert result == []
        mock_logger.error.assert_called()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_get_products_unexpected_error(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error inesperado en get_products"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = ValueError("Unexpected error")

        # Act
        result = repository.get_products()

        # Assert
        assert result == []
        mock_logger.error.assert_called()
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para save_evidence
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_save_evidence_success(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: guardado exitoso de evidencia"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = (456,)  # evidence_id retornado

        # Act
        result = repository.save_evidence(
            visit_id=123,
            url="http://example.com/evidence.jpg",
            type="image"
        )

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['evidence_id'] == 456
        assert result['visit_id'] == 123
        assert result['url'] == "http://example.com/evidence.jpg"
        assert result['type'] == "image"
        cursor.execute.assert_called_once()
        # Verificar que el tipo se convierte a mayúsculas en la query
        call_args = cursor.execute.call_args
        assert call_args[0][1][2] == "IMAGE"  # type.upper()
        conn.commit.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_save_evidence_database_error(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en save_evidence"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.save_evidence(123, "http://example.com/img.jpg", "image")

        assert str(exc_info.value) == "Database error during evidence saving."
        conn.rollback.assert_called_once()
        mock_logger.error.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_empty_result(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: no se encuentran usuarios con el rol especificado"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_users_by_role("ADMIN")

        # Assert
        assert result == []
        assert isinstance(result, list)
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: manejo de error de base de datos"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Connection failed")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.get_users_by_role('CLIENT')

        assert str(exc_info.value) == "Database error during user retrieval."

        # Verificar que se liberó la conexión incluso con error
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_connection_error(
            self,
            mock_get_conn,
            mock_release,
            repository
    ):
        """Test: error al obtener la conexión"""
        # Arrange
        mock_get_conn.side_effect = Exception("Unable to get connection")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.get_users_by_role('CLIENT')

        assert str(exc_info.value) == "Unable to get connection"

        # No se debe liberar conexión si no se obtuvo
        mock_release.assert_not_called()

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_cursor_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error al crear el cursor"""
        # Arrange
        conn, _ = mock_connection
        mock_get_conn.return_value = conn
        conn.cursor.side_effect = psycopg2.Error("Cursor creation failed")

        # Act & Assert
        with pytest.raises(Exception):
            repository.get_users_by_role('CLIENT')

        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_ordered_by_name(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: verificar que los resultados se ordenan por nombre"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        unordered_rows = [
            (2, "Zoe", "Last", "pass", "123", "phone", 'CLIENT', "nit", 1000, "basic", 'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370,2),
            (1, "Ana", "Last", "pass", "456", "phone", 'CLIENT', "nit", 2000, "premium", 'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370,1),
        ]
        cursor.fetchall.return_value = unordered_rows

        # Act
        result = repository.get_users_by_role('CLIENT')

        # Assert
        # Verificar que la query incluye ORDER BY
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]
        assert "ORDER BY u.name ASC" in query

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_single_user(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: recuperación de un solo usuario"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        single_row = [
            (1, 2, "Carlos", "Ruiz", "pass123", "111222333", "3009876543",
             'CLIENT', "900111222-3", 5000000.75, "vip", 'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370)
        ]
        cursor.fetchall.return_value = single_row

        # Act
        result = repository.get_users_by_role('CLIENT')

        # Assert
        assert len(result) == 1
        assert result[0].name == "Carlos"
        assert result[0].balance == 5000000.75
        assert result[0].perfil == "vip"

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_ensures_connection_release_on_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection,
            sample_db_rows
    ):
        """Test: verificar que la conexión se libera siempre en caso exitoso"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = sample_db_rows

        # Act
        repository.get_users_by_role('CLIENT')

        # Assert
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_query_structure(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: verificar la estructura de la query SQL"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        repository.get_users_by_role('CLIENT')

        # Assert
        cursor.execute.assert_called_once()
        query = cursor.execute.call_args[0][0]

        # Verificar elementos clave de la query
        assert 'FROM users.Users u' in query
        assert 'INNER JOIN users.Clients c ON u.user_id = c.user_id' in query
        assert 'WHERE u.role IN (%s)' in query


    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_multiple_calls(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection,
            sample_db_rows
    ):
        """Test: múltiples llamadas al método funcionan correctamente"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = sample_db_rows

        # Act
        result1 = repository.get_users_by_role('CLIENT')

        # Reset mocks para segunda llamada
        mock_get_conn.reset_mock()
        mock_release.reset_mock()
        cursor.execute.reset_mock()
        cursor.fetchall.reset_mock()

        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = sample_db_rows

        result2 = repository.get_users_by_role('CLIENT')

        # Assert
        assert len(result1) == 2
        assert len(result2) == 2
        assert mock_get_conn.call_count == 1
        assert mock_release.call_count == 1

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_fetchall_called(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection,
            sample_db_rows
    ):
        """Test: verificar que fetchall es llamado correctamente"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = sample_db_rows

        # Act
        repository.get_users_by_role('CLIENT')

        # Assert
        cursor.fetchall.assert_called_once()

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_role_connection_released_after_exception(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: conexión se libera incluso cuando fetchall falla"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.side_effect = psycopg2.Error("Fetch failed")

        # Act & Assert
        with pytest.raises(Exception):
            repository.get_users_by_role('CLIENT')

        # Verificar que se liberó la conexión
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_users_by_seller
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_seller_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: recuperación exitosa de usuarios por seller_id"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        seller_rows = [
            (1, 1, "Juan", "Pérez", "hashed_password_123", "1234567890", "3001234567",
             'CLIENT', "premium", "900123456-7", 1500000.50, 'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370)
        ]
        cursor.fetchall.return_value = seller_rows

        # Act
        result = repository.get_users_by_seller("123")

        # Assert
        assert len(result) == 1
        assert isinstance(result[0], Client)
        assert result[0].user_id == 1
        assert result[0].name == "Juan"
        cursor.execute.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_seller_empty_result(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: no se encuentran usuarios para el seller_id"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_users_by_seller("999")

        # Assert
        assert result == []
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_seller_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: manejo de error de base de datos en get_users_by_seller"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.get_users_by_seller("123")

        assert str(exc_info.value) == "Database error during user retrieval."
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para db_get_client_data
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_db_get_client_data_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa de datos del cliente"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda key: {
            'client_id': 1,
            'user_name': 'Juan',
            'last_name': 'Pérez',
            'email': 'juan@example.com',
            'balance': 1500000.50,
            'address': 'Calle 72 # 10-30',
            'latitude': 4.659970,
            'longitude': -74.058370,
            'seller_zone': 'Zona Norte'
        }[key])
        mock_row.keys.return_value = ['client_id', 'user_name', 'last_name', 'email', 'balance', 'address', 'latitude', 'longitude', 'seller_zone']
        cursor.fetchone.return_value = mock_row

        # Act
        result = repository.db_get_client_data(1)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['client_id'] == 1
        cursor.execute.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_db_get_client_data_not_found(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: cliente no encontrado"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = None

        # Act
        result = repository.db_get_client_data(999)

        # Assert
        assert result is None
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_db_get_client_data_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en db_get_client_data"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.db_get_client_data(1)

        assert "Database error during client profile retrieval" in str(exc_info.value)
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('sys.stderr')
    def test_db_get_client_data_unexpected_error(
            self,
            mock_stderr,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error inesperado en db_get_client_data"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = ValueError("Unexpected error")

        # Act & Assert
        with pytest.raises(Exception):
            repository.db_get_client_data(1)

        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_by_id
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_by_id_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa de visita por ID"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda key: {
            'client_id': 1,
            'name': 'Juan',
            'last_name': 'Pérez'
        }[key])
        mock_row.keys.return_value = ['client_id', 'name', 'last_name']
        cursor.fetchone.return_value = mock_row

        # Act
        result = repository.get_by_id(1)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['client_id'] == 1
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_by_id_not_found(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: visita no encontrada"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = None

        # Act
        result = repository.get_by_id(999)

        # Assert
        assert result is None
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_by_id_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en get_by_id"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(psycopg2.Error):
            repository.get_by_id(1)

        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_visit_by_id
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_visit_by_id_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa de visita por ID"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda key: {
            'visit_id': 1,
            'seller_id': 2,
            'date': '2025-01-15',
            'findings': 'Todo OK',
            'client_id': 3
        }[key])
        mock_row.keys.return_value = ['visit_id', 'seller_id', 'date', 'findings', 'client_id']
        cursor.fetchone.return_value = mock_row

        # Act
        result = repository.get_visit_by_id(1)

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['visit_id'] == 1
        assert result['client_id'] == 3
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_visit_by_id_not_found(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: visita no encontrada"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = None

        # Act
        result = repository.get_visit_by_id(999)

        # Assert
        assert result is None
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_visit_by_id_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en get_visit_by_id"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.get_visit_by_id(1)

        assert "Database error during visit retrieval" in str(exc_info.value)
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para save_visit
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_save_visit_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: guardado exitoso de visita"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = (123,)  # visit_id retornado

        # Act
        result = repository.save_visit(
            client_id=1,
            seller_id=2,
            date="2025-01-15",
            findings="Todo OK"
        )

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['visit_id'] == 123
        assert result['client_id'] == 1
        assert result['seller_id'] == 2
        assert result['date'] == "2025-01-15"
        assert result['findings'] == "Todo OK"
        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_save_visit_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en save_visit"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.save_visit(1, 2, "2025-01-15", "Test")

        assert str(exc_info.value) == "Database error during visit saving."
        conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_recent_evidences_by_client
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_evidences_by_client_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa de evidencias recientes"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_row1 = Mock()
        mock_row1.__getitem__ = Mock(side_effect=lambda key: {'url': 'http://example.com/img1.jpg', 'type': 'IMAGE'}[key])
        mock_row1.keys.return_value = ['url', 'type']
        mock_row2 = Mock()
        mock_row2.__getitem__ = Mock(side_effect=lambda key: {'url': 'http://example.com/img2.jpg', 'type': 'VIDEO'}[key])
        mock_row2.keys.return_value = ['url', 'type']
        cursor.fetchall.return_value = [mock_row1, mock_row2]

        # Act
        result = repository.get_recent_evidences_by_client(1)

        # Assert
        assert len(result) == 2
        assert isinstance(result, list)
        assert result[0]['url'] == 'http://example.com/img1.jpg'
        assert result[0]['type'] == 'IMAGE'
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_evidences_by_client_empty(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: no hay evidencias para el cliente"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_recent_evidences_by_client(999)

        # Assert
        assert result == []
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_evidences_by_client_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en get_recent_evidences_by_client"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.get_recent_evidences_by_client(1)

        assert "Database error during recent evidences retrieval" in str(exc_info.value)
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_recent_purchase_history
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_purchase_history_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa del historial de compras"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = [
            ("SKU-001", "Producto 1"),
            ("SKU-002", "Producto 2")
        ]

        # Act
        result = repository.get_recent_purchase_history(1, limit=10)

        # Assert
        assert len(result) == 2
        assert result[0]['sku'] == "SKU-001"
        assert result[0]['name'] == "Producto 1"
        assert result[1]['sku'] == "SKU-002"
        assert result[1]['name'] == "Producto 2"
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_purchase_history_empty(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: no hay historial de compras"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_recent_purchase_history(999, limit=10)

        # Assert
        assert result == []
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_purchase_history_database_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en get_recent_purchase_history"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.get_recent_purchase_history(1, limit=10)

        assert "Database error retrieving purchase history" in str(exc_info.value)
        conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para get_products
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_get_products_success(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: obtención exitosa del catálogo de productos"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_row1 = Mock()
        mock_row1.__getitem__ = Mock(side_effect=lambda key: {
            'product_id': 1,
            'sku': 'SKU-001',
            'value': 10000,
            'name': 'Producto 1',
            'image_url': 'http://example.com/img1.jpg',
            'category_name': 'Categoría 1',
            'total_quantity': 50
        }[key])
        mock_row1.keys.return_value = ['product_id', 'sku', 'value', 'name', 'image_url', 'category_name', 'total_quantity']
        cursor.fetchall.return_value = [mock_row1]

        # Act
        result = repository.get_products()

        # Assert
        assert len(result) == 1
        assert result[0]['product_id'] == 1
        assert result[0]['sku'] == 'SKU-001'
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_get_products_empty(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: no hay productos disponibles"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_products()

        # Assert
        assert result == []
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_get_products_database_error(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en get_products"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act
        result = repository.get_products()

        # Assert
        assert result == []
        mock_logger.error.assert_called()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_get_products_unexpected_error(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error inesperado en get_products"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = ValueError("Unexpected error")

        # Act
        result = repository.get_products()

        # Assert
        assert result == []
        mock_logger.error.assert_called()
        mock_release.assert_called_once_with(conn)

    # ============================================================================
    # Tests para save_evidence
    # ============================================================================

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_save_evidence_success(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: guardado exitoso de evidencia"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = (456,)  # evidence_id retornado

        # Act
        result = repository.save_evidence(
            visit_id=123,
            url="http://example.com/evidence.jpg",
            type="image"
        )

        # Assert
        assert result is not None
        assert isinstance(result, dict)
        assert result['evidence_id'] == 456
        assert result['visit_id'] == 123
        assert result['url'] == "http://example.com/evidence.jpg"
        assert result['type'] == "image"
        cursor.execute.assert_called_once()
        # Verificar que el tipo se convierte a mayúsculas en la query
        call_args = cursor.execute.call_args
        assert call_args[0][1][2] == "IMAGE"  # type.upper()
        conn.commit.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.logger', create=True)
    def test_save_evidence_database_error(
            self,
            mock_logger,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: error de base de datos en save_evidence"""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("Database error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.save_evidence(123, "http://example.com/img.jpg", "image")

        assert str(exc_info.value) == "Database error during evidence saving."
        conn.rollback.assert_called_once()
        mock_logger.error.assert_called_once()
        mock_release.assert_called_once_with(conn)