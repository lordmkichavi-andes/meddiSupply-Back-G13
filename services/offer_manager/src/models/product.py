"""Modelo para productos."""

from dataclasses import dataclass
from typing import Optional
from decimal import Decimal


@dataclass
class Product:
    """Modelo para productos."""
    product_id: int
    sku: str
    name: str
    value: Decimal
    objective_profile: str
    unit_name: str
    unit_symbol: str
    category_name: str

    @classmethod
    def from_dict(cls, data: dict) -> 'Product':
        """Crear instancia desde diccionario."""
        return cls(
            product_id=data['product_id'],
            sku=data['sku'],
            name=data['name'],
            value=Decimal(str(data['value'])),
            objective_profile=data['objective_profile'],
            unit_name=data['unit_name'],
            unit_symbol=data['unit_symbol'],
            category_name=data['category_name']
        )

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            'product_id': self.product_id,
            'sku': self.sku,
            'name': self.name,
            'value': float(self.value),
            'objective_profile': self.objective_profile,
            'unit_name': self.unit_name,
            'unit_symbol': self.unit_symbol,
            'category_name': self.category_name
        }
