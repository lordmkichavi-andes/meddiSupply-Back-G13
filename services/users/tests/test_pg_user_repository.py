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


    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_users_by_seller_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection,
            sample_db_rows
    ):
        """Test: recuperación exitosa de clientes por ID de vendedor."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        # Ajustamos sample_db_rows para que coincida con el SELECT de get_users_by_seller
        # El SELECT de get_users_by_seller tiene un orden diferente de columnas (client_name va antes de nit)
        seller_rows = [
            (
                1, 1, "Juan", "Pérez", "hashed_password_123", "1234567890", "3001234567",
                'CLIENT', "premium", "900123456-7", 1500000.50,
                'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370
            )
        ]
        cursor.fetchall.return_value = seller_rows

        # Act
        result = repository.get_users_by_seller('VEND-001')

        # Assert
        assert len(result) == 1
        assert all(isinstance(user, Client) for user in result)
        assert result[0].name == "Juan"
        assert result[0].perfil == "premium"
        
        # Verificar que se llamó la query correcta
        cursor.execute.assert_called_once()
        call_args = cursor.execute.call_args
        assert "WHERE s.seller_id = %s" in call_args[0][0]
        assert call_args[0][1] == ('VEND-001',)
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
        """Test: no se encuentran clientes para el vendedor especificado."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_users_by_seller("VEND-999")

        # Assert
        assert result == []
        mock_release.assert_called_once_with(conn)
        
    # --- Tests para db_get_client_data (Perfil Enriquecido) ---

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_db_get_client_data_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Obtención exitosa del perfil enriquecido del cliente."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        
        # Simular DictRow (usando un dict normal ya que el cursor mockeado lo maneja)
        mock_data = {
            'client_id': 5, 
            'user_name': 'Carlos', 
            'last_name': 'Gomez', 
            'balance': 50000.00,
            'seller_zone': 'CENTRO'
        }
        cursor.fetchone.return_value = mock_data

        # Act
        result = repository.db_get_client_data(5)

        # Assert
        assert result is not None
        assert result['client_id'] == 5
        assert result['seller_zone'] == 'CENTRO'
        
        # Verificar que se usó DictCursor (solo se verifica la llamada al cursor)
        mock_get_conn.return_value.cursor.assert_called_once_with(
            cursor_factory=psycopg2.extras.DictCursor
        )
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
        """Test: Perfil no encontrado."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = None

        # Act
        result = repository.db_get_client_data(999)

        # Assert
        assert result is None
        mock_release.assert_called_once_with(conn)

    # --- Tests para get_by_id (Retorna dict del cliente) ---
    
    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_by_id_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Obtención exitosa de cliente por client_id."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_data = {
            'client_id': 5, 
            'name': 'Carlos', 
            'balance': 50000.00,
            'seller_zone': 'CENTRO'
        }
        cursor.fetchone.return_value = mock_data

        # Act
        result = repository.get_by_id(5)

        # Assert
        assert result is not None
        assert result['client_id'] == 5
        assert 'seller_zone' in result
        mock_release.assert_called_once_with(conn)

    # --- Tests para get_visit_by_id ---

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_visit_by_id_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Recuperación exitosa de una visita."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_data = {
            'visit_id': 10,
            'seller_id': 20,
            'date': '2025-11-01',
            'client_id': 5
        }
        cursor.fetchone.return_value = mock_data

        # Act
        result = repository.get_visit_by_id(10)

        # Assert
        assert result is not None
        assert result['visit_id'] == 10
        assert result['seller_id'] == 20
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
        """Test: Visita no encontrada."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = None

        # Act
        result = repository.get_visit_by_id(999)

        # Assert
        assert result is None
        mock_release.assert_called_once_with(conn)

    # --- Tests para save_visit ---

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_save_visit_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Guardado exitoso de una nueva visita."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        # Simular el ID retornado después de la inserción
        cursor.fetchone.return_value = (100,) 
        
        visit_data = {
            "client_id": 5, 
            "seller_id": 20, 
            "date": "2025-11-08", 
            "findings": "Todo OK"
        }

        # Act
        result = repository.save_visit(**visit_data)

        # Assert
        assert result['visit_id'] == 100
        assert result['client_id'] == 5
        cursor.execute.assert_called_once()
        conn.commit.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_save_visit_rollback_on_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Rollback en caso de error de base de datos al guardar."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("FK Constraint violation")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.save_visit(5, 20, "2025-11-08", "Test")

        assert str(exc_info.value) == "Database error during visit saving."
        conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(conn)

    # --- Tests para get_recent_evidences_by_client ---

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_evidences_by_client_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Recuperación exitosa de evidencias recientes."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_rows = [
            {'url': 'url1.jpg', 'type': 'IMAGE'}, 
            {'url': 'url2.mp4', 'type': 'VIDEO'}
        ]
        cursor.fetchall.return_value = mock_rows

        # Act
        result = repository.get_recent_evidences_by_client(5)

        # Assert
        assert len(result) == 2
        assert result[0]['url'] == 'url1.jpg'
        cursor.execute.assert_called_once()
        assert 'LIMIT 10' in cursor.execute.call_args[0][0]
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
        """Test: No se encuentran evidencias."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_recent_evidences_by_client(5)

        # Assert
        assert result == []
        mock_release.assert_called_once_with(conn)

    # --- Tests para get_recent_purchase_history ---

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_get_recent_purchase_history_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Recuperación exitosa del historial de compras."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        mock_rows = [
            ('SKU-A', 'Medicina A'), 
            ('SKU-B', 'Medicina B')
        ]
        cursor.fetchall.return_value = mock_rows

        # Act
        result = repository.get_recent_purchase_history(5)

        # Assert
        assert len(result) == 2
        assert result[0]['sku'] == 'SKU-A'
        cursor.execute.assert_called_once()
        assert cursor.execute.call_args[0][1] == (5, 10) # Verifica client_id y limit
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
        """Test: Historial de compras vacío."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchall.return_value = []

        # Act
        result = repository.get_recent_purchase_history(5)

        # Assert
        assert result == []
        mock_release.assert_called_once_with(conn)

    # --- Tests para save_evidence ---

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_save_evidence_success(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Guardado exitoso de evidencia visual."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.fetchone.return_value = (500,) # evidence_id generado

        # Act
        result = repository.save_evidence(10, 'http://url/image.jpg', 'IMAGE')

        # Assert
        assert result['evidence_id'] == 500
        assert result['type'] == 'IMAGE'
        cursor.execute.assert_called_once()
        # Verificar que el tipo de archivo se envía en mayúsculas a la DB
        assert cursor.execute.call_args[0][1][2] == 'IMAGE' 
        conn.commit.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_save_evidence_rollback_on_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Rollback y liberación de conexión en error al guardar evidencia."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("DB error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.save_evidence(10, 'url', 'pdf')

        assert str(exc_info.value) == "Database error during evidence saving."
        conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(conn)

    # --- Tests para save_suggestion ---

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_save_suggestion_inserted(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Guardado exitoso de una sugerencia (INSERTED)."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.rowcount = 1 # 1 fila insertada
        
        # Act
        result = repository.save_suggestion(10, 200)

        # Assert
        assert result['status'] == 'inserted'
        assert result['visit_id'] == 10
        conn.commit.assert_called_once()
        assert 'ON CONFLICT' in cursor.execute.call_args[0][0]
        mock_release.assert_called_once_with(conn)
        
    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_save_suggestion_already_exists(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Sugerencia ya existente (DO NOTHING)."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.rowcount = 0 # 0 filas insertadas (conflicto)
        
        # Act
        result = repository.save_suggestion(10, 200)

        # Assert
        assert result['status'] == 'already_exists'
        conn.commit.assert_called_once()
        mock_release.assert_called_once_with(conn)

    @patch('src.infrastructure.persistence.pg_user_repository.release_connection')
    @patch('src.infrastructure.persistence.pg_user_repository.get_connection')
    def test_save_suggestion_rollback_on_error(
            self,
            mock_get_conn,
            mock_release,
            repository,
            mock_connection
    ):
        """Test: Rollback y liberación de conexión en error al guardar sugerencia."""
        # Arrange
        conn, cursor = mock_connection
        mock_get_conn.return_value = conn
        cursor.execute.side_effect = psycopg2.Error("DB error: FK violation")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            repository.save_suggestion(10, 200)

        assert str(exc_info.value) == "Database error during suggestion saving."
        conn.rollback.assert_called_once()
        mock_release.assert_called_once_with(conn)
