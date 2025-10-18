"""Modelo para productos."""

from dataclasses import dataclass


@dataclass
class Product:
    """Modelo para productos."""
    id: str
    name: str
    category: str
    price: float
    unit: str

    @classmethod
    def from_dict(cls, data: dict) -> 'Product':
        """Crear instancia desde diccionario."""
        return cls(
            id=data['id'],
            name=data['name'],
            category=data['category'],
            price=float(data['price']),
            unit=data['unit']
        )

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'price': self.price,
            'unit': self.unit
        }

