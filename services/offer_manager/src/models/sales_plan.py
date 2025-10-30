"""Modelos para planes de venta."""

from dataclasses import dataclass
from typing import List, Optional
from decimal import Decimal


@dataclass
class SalesPlanProduct:
    """Modelo para productos en un plan de venta."""
    product_id: int
    individual_goal: Decimal
    product_name: Optional[str] = None
    sku: Optional[str] = None
    product_value: Optional[Decimal] = None
    unit_name: Optional[str] = None
    unit_symbol: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'SalesPlanProduct':
        """Crear instancia desde diccionario."""
        return cls(
            product_id=data['product_id'],
            individual_goal=Decimal(str(data['individual_goal'])),
            product_name=data.get('product_name'),
            sku=data.get('sku'),
            product_value=Decimal(str(data['product_value'])) if data.get('product_value') else None,
            unit_name=data.get('unit_name'),
            unit_symbol=data.get('unit_symbol')
        )

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            'product_id': self.product_id,
            'individual_goal': float(self.individual_goal),
            'product_name': self.product_name,
            'sku': self.sku,
            'product_value': float(self.product_value) if self.product_value else None,
            'unit_name': self.unit_name,
            'unit_symbol': self.unit_symbol
        }


@dataclass
class SalesPlan:
    """Modelo para planes de venta."""
    plan_id: Optional[int]
    region: str
    quarter: str
    year: int
    total_goal: Decimal
    is_active: bool = True
    creation_date: Optional[str] = None
    created_by: Optional[int] = None
    products: List[SalesPlanProduct] = None

    def __post_init__(self):
        if self.products is None:
            self.products = []

    @classmethod
    def from_dict(cls, data: dict) -> 'SalesPlan':
        """Crear instancia desde diccionario."""
        products = []
        if 'products' in data and data['products']:
            products = [SalesPlanProduct.from_dict(p) for p in data['products']]
        
        return cls(
            plan_id=data.get('plan_id'),
            region=data['region'],
            quarter=data['quarter'],
            year=data['year'],
            total_goal=Decimal(str(data['total_goal'])),
            is_active=data.get('is_active', True),
            creation_date=data.get('creation_date'),
            created_by=data.get('created_by'),
            products=products
        )

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            'plan_id': self.plan_id,
            'region': self.region,
            'quarter': self.quarter,
            'year': self.year,
            'total_goal': float(self.total_goal),
            'is_active': self.is_active,
            'creation_date': self.creation_date,
            'created_by': self.created_by,
            'products': [p.to_dict() for p in self.products] if self.products else []
        }

    def calculate_total_goal(self) -> Decimal:
        """Calcula la meta total basada en los productos."""
        if not self.products:
            return Decimal('0')
        return sum(p.individual_goal for p in self.products)
