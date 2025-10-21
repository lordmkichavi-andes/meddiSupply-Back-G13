import pytest
from src.domain.entities import Role, User, Client, USER_ROLE_MAP


class TestRole:
    """Tests para la entidad Role"""

    def test_role_creation(self):
        """Test: creación básica de un rol"""
        # Arrange & Act
        role = Role(value="ADMIN", name="Administrador")

        # Assert
        assert role.value == "ADMIN"
        assert role.name == "Administrador"

    def test_role_is_dataclass(self):
        """Test: verificar que Role es un dataclass"""
        role = Role(value="CLIENT", name="Cliente")

        assert hasattr(role, '__dataclass_fields__')
        assert 'value' in role.__dataclass_fields__
        assert 'name' in role.__dataclass_fields__

    def test_role_equality(self):
        """Test: comparación de roles"""
        role1 = Role(value="SELLER", name="Vendedor")
        role2 = Role(value="SELLER", name="Vendedor")
        role3 = Role(value="ADMIN", name="Administrador")

        assert role1 == role2
        assert role1 != role3


class TestUser:
    """Tests para la entidad User"""

    @pytest.fixture
    def sample_user_data(self):
        """Fixture con datos de usuario de ejemplo"""
        return {
            "user_id": "user_123",
            "name": "Juan",
            "last_name": "Pérez",
            "password": "hashed_password_123",
            "identification": "1234567890",
            "phone": "3001234567",
            "role_value": "SELLER"
        }

    def test_user_creation(self, sample_user_data):
        """Test: creación básica de un usuario"""
        # Act
        user = User(**sample_user_data)

        # Assert
        assert user.user_id == "user_123"
        assert user.name == "Juan"
        assert user.last_name == "Pérez"
        assert user.password == "hashed_password_123"
        assert user.identification == "1234567890"
        assert user.phone == "3001234567"
        assert user.role_value == "SELLER"

    def test_user_role_property_admin(self):
        """Test: property role retorna Role correcto para ADMIN"""
        # Arrange
        user = User(
            user_id="1",
            name="Admin",
            last_name="User",
            password="pass",
            identification="123",
            phone="300",
            role_value="ADMIN"
        )

        # Act
        role = user.role

        # Assert
        assert isinstance(role, Role)
        assert role.value == "ADMIN"
        assert role.name == "Administrador"

    def test_user_role_property_supervisor(self):
        """Test: property role retorna Role correcto para SUPERVISOR"""
        # Arrange
        user = User(
            user_id="2",
            name="Super",
            last_name="Visor",
            password="pass",
            identification="456",
            phone="301",
            role_value="SUPERVISOR"
        )

        # Act
        role = user.role

        # Assert
        assert role.value == "SUPERVISOR"
        assert role.name == "Supervisor"

    def test_user_role_property_seller(self):
        """Test: property role retorna Role correcto para SELLER"""
        # Arrange
        user = User(
            user_id="3",
            name="Vendedor",
            last_name="Test",
            password="pass",
            identification="789",
            phone="302",
            role_value="SELLER"
        )

        # Act
        role = user.role

        # Assert
        assert role.value == "SELLER"
        assert role.name == "Vendedor"

    def test_user_role_property_client(self):
        """Test: property role retorna Role correcto para CLIENT"""
        # Arrange
        user = User(
            user_id="4",
            name="Cliente",
            last_name="Test",
            password="pass",
            identification="012",
            phone="303",
            role_value="CLIENT"
        )

        # Act
        role = user.role

        # Assert
        assert role.value == "CLIENT"
        assert role.name == "Cliente"

    def test_user_role_property_unknown_role(self):
        """Test: property role maneja roles desconocidos"""
        # Arrange
        user = User(
            user_id="5",
            name="Unknown",
            last_name="User",
            password="pass",
            identification="345",
            phone="304",
            role_value="UNKNOWN_ROLE"
        )

        # Act
        role = user.role

        # Assert
        assert role.value == "UNKNOWN_ROLE"
        assert role.name == "Desconocido"

    def test_get_user_role_method(self):
        """Test: método get_user_role retorna el rol correcto"""
        # Arrange
        user = User(
            user_id="6",
            name="Test",
            last_name="User",
            password="pass",
            identification="678",
            phone="305",
            role_value="ADMIN"
        )

        # Act
        role = user.get_user_role()

        # Assert
        assert isinstance(role, Role)
        assert role.value == "ADMIN"
        assert role.name == "Administrador"

    def test_get_user_role_method_equals_property(self):
        """Test: método get_user_role retorna lo mismo que property role"""
        # Arrange
        user = User(
            user_id="7",
            name="Test",
            last_name="User",
            password="pass",
            identification="901",
            phone="306",
            role_value="SELLER"
        )

        # Act & Assert
        assert user.get_user_role() == user.role

    def test_user_is_dataclass(self):
        """Test: verificar que User es un dataclass"""
        user = User(
            user_id="8",
            name="Test",
            last_name="User",
            password="pass",
            identification="234",
            phone="307",
            role_value="CLIENT"
        )

        assert hasattr(user, '__dataclass_fields__')
        assert len(user.__dataclass_fields__) == 7

    def test_user_role_property_cached(self):
        """Test: verificar que property role se evalúa cada vez"""
        # Arrange
        user = User(
            user_id="9",
            name="Test",
            last_name="User",
            password="pass",
            identification="567",
            phone="308",
            role_value="ADMIN"
        )

        # Act
        role1 = user.role
        role2 = user.role

        # Assert
        assert role1 == role2
        assert role1.value == role2.value
        assert role1.name == role2.name


class TestClient:
    """Tests para la entidad Client"""

    @pytest.fixture
    def sample_client_data(self):
        """Fixture con datos de cliente de ejemplo"""
        return {
            "user_id": "client_123",
            "name": "María",
            "last_name": "González",
            "password": "hashed_password_456",
            "identification": "9876543210",
            "phone": "3109876543",
            "role_value": "CLIENT",
            "nit": "900123456-7",
            "balance": 1500000.50,
            "perfil": "premium",
            "address":'Calle 72 # 10-30, Bogotá',
            "latitude":4.659970,
            "longitude":-74.058370,
            "client_id": 1,
        }

    def test_client_creation(self, sample_client_data):
        """Test: creación básica de un cliente"""
        # Act
        client = Client(**sample_client_data)

        # Assert
        assert client.user_id == "client_123"
        assert client.name == "María"
        assert client.last_name == "González"
        assert client.password == "hashed_password_456"
        assert client.identification == "9876543210"
        assert client.phone == "3109876543"
        assert client.role_value == "CLIENT"
        assert client.nit == "900123456-7"
        assert client.balance == 1500000.50
        assert client.perfil == "premium"
        assert client.address == "Calle 72 # 10-30, Bogotá"
        assert client.latitude == 4.659970
        assert client.longitude == -74.058370
        assert client.client_id == 1

    def test_client_inherits_from_user(self, sample_client_data):
        """Test: Client hereda de User"""
        # Act
        client = Client(**sample_client_data)

        # Assert
        assert isinstance(client, User)
        assert isinstance(client, Client)

    def test_client_has_user_methods(self, sample_client_data):
        """Test: Client tiene acceso a métodos de User"""
        # Act
        client = Client(**sample_client_data)

        # Assert
        assert hasattr(client, 'role')
        assert hasattr(client, 'get_user_role')

    def test_client_role_property(self, sample_client_data):
        """Test: property role funciona en Client"""
        # Act
        client = Client(**sample_client_data)
        role = client.role

        # Assert
        assert isinstance(role, Role)
        assert role.value == "CLIENT"
        assert role.name == "Cliente"

    def test_client_get_user_role_method(self, sample_client_data):
        """Test: método get_user_role funciona en Client"""
        # Act
        client = Client(**sample_client_data)
        role = client.get_user_role()

        # Assert
        assert isinstance(role, Role)
        assert role.value == "CLIENT"
        assert role.name == "Cliente"

    def test_client_with_zero_balance(self):
        """Test: cliente con balance en cero"""
        # Arrange & Act
        client = Client(
            user_id="client_001",
            name="Pedro",
            last_name="Ramírez",
            password="pass",
            identification="111222333",
            phone="3001112233",
            role_value="CLIENT",
            nit="900111222-3",
            balance=0.0,
            perfil="basic",
            address='Calle 72 # 10-30, Bogotá',
            latitude= 4.659970,
            longitude= -74.058370,
            client_id= 1
        )

        # Assert
        assert client.balance == 0.0
        assert isinstance(client.balance, float)

    def test_client_with_negative_balance(self):
        """Test: cliente con balance negativo"""
        # Arrange & Act
        client = Client(
            user_id="client_002",
            name="Ana",
            last_name="López",
            password="pass",
            identification="444555666",
            phone="3004445556",
            role_value="CLIENT",
            nit="900444555-6",
            balance=-5000.0,
            perfil="basic",
            address='Calle 72 # 10-30, Bogotá',
            latitude=4.659970,
            longitude=-74.058370,
            client_id=1
        )

        # Assert
        assert client.balance == -5000.0

    def test_client_with_large_balance(self):
        """Test: cliente con balance muy grande"""
        # Arrange & Act
        client = Client(
            user_id="client_003",
            name="Carlos",
            last_name="Mendoza",
            password="pass",
            identification="777888999",
            phone="3007778889",
            role_value="CLIENT",
            nit="900777888-9",
            balance=999999999.99,
            perfil="vip",
            address='Calle 72 # 10-30, Bogotá',
            latitude=4.659970,
            longitude=-74.058370,
            client_id=1
        )

        # Assert
        assert client.balance == 999999999.99

    def test_client_perfil_types(self):
        """Test: diferentes tipos de perfil de cliente"""
        profiles = ["basic", "premium", "vip", "enterprise"]

        for idx, profile in enumerate(profiles):
            client = Client(
                user_id=f"client_{idx}",
                name="Test",
                last_name="User",
                password="pass",
                identification=f"{idx}",
                phone=f"300{idx}",
                role_value="CLIENT",
                nit=f"900{idx}-{idx}",
                balance=1000.0,
                perfil=profile,
                address='Calle 72 # 10-30, Bogotá',
                latitude=4.659970,
                longitude=-74.058370,
                client_id=1
            )

            assert client.perfil == profile

    def test_client_is_dataclass(self, sample_client_data):
        """Test: verificar que Client es un dataclass"""
        client = Client(**sample_client_data)

        assert hasattr(client, '__dataclass_fields__')
        assert 'nit' in client.__dataclass_fields__
        assert 'balance' in client.__dataclass_fields__
        assert 'perfil' in client.__dataclass_fields__

    def test_client_equality(self):
        """Test: comparación de clientes"""
        client1 = Client(
            user_id="client_eq1",
            name="Test",
            last_name="User",
            password="pass",
            identification="123",
            phone="300",
            role_value="CLIENT",
            nit="900123-4",
            balance=1000.0,
            perfil="basic",
            address='Calle 72 # 10-30, Bogotá',
            latitude=4.659970,
            longitude=-74.058370,
            client_id=1
        )

        client2 = Client(
            user_id="client_eq1",
            name="Test",
            last_name="User",
            password="pass",
            identification="123",
            phone="300",
            role_value="CLIENT",
            nit="900123-4",
            balance=1000.0,
            perfil="basic",
            address='Calle 72 # 10-30, Bogotá',
            latitude=4.659970,
            longitude=-74.058370,
            client_id=1
        )

        client3 = Client(
            user_id="client_eq2",
            name="Different",
            last_name="User",
            password="pass",
            identification="456",
            phone="301",
            role_value="CLIENT",
            nit="900456-7",
            balance=2000.0,
            perfil="premium",
            address='Calle 72 # 10-30, Bogotá',
            latitude=4.659970,
            longitude=-74.058370,
            client_id=1
        )

        assert client1 == client2
        assert client1 != client3


class TestUserRoleMap:
    """Tests para el diccionario USER_ROLE_MAP"""

    def test_user_role_map_contains_all_roles(self):
        """Test: USER_ROLE_MAP contiene todos los roles esperados"""
        expected_roles = ["ADMIN", "SUPERVISOR", "SELLER", "CLIENT"]

        for role in expected_roles:
            assert role in USER_ROLE_MAP

    def test_user_role_map_structure(self):
        """Test: cada entrada en USER_ROLE_MAP tiene la estructura correcta"""
        for role_key, role_data in USER_ROLE_MAP.items():
            assert isinstance(role_key, str)
            assert isinstance(role_data, dict)
            assert "name" in role_data
            assert isinstance(role_data["name"], str)

    def test_user_role_map_values(self):
        """Test: valores específicos en USER_ROLE_MAP"""
        assert USER_ROLE_MAP["ADMIN"]["name"] == "Administrador"
        assert USER_ROLE_MAP["SUPERVISOR"]["name"] == "Supervisor"
        assert USER_ROLE_MAP["SELLER"]["name"] == "Vendedor"
        assert USER_ROLE_MAP["CLIENT"]["name"] == "Cliente"

    def test_user_role_map_immutability_intent(self):
        """Test: verificar que USER_ROLE_MAP no se modifica accidentalmente"""
        original_keys = set(USER_ROLE_MAP.keys())
        original_admin_name = USER_ROLE_MAP["ADMIN"]["name"]

        # Simular uso normal
        _ = USER_ROLE_MAP.get("ADMIN", {"name": "Desconocido"})

        # Verificar que no cambió
        assert set(USER_ROLE_MAP.keys()) == original_keys
        assert USER_ROLE_MAP["ADMIN"]["name"] == original_admin_name