"""Modelo para vendedores."""

from dataclasses import dataclass


@dataclass
class Vendor:
    """Modelo para vendedores."""
    id: str
    name: str
    email: str
    region: str
    active: bool

    @classmethod
    def from_dict(cls, data: dict) -> 'Vendor':
        """Crear instancia desde diccionario."""
        return cls(
            id=data['id'],
            name=data['name'],
            email=data['email'],
            region=data['region'],
            active=data['active']
        )

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'region': self.region,
            'active': self.active
        }
