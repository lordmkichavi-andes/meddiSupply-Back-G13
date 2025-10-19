from dataclasses import dataclass

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