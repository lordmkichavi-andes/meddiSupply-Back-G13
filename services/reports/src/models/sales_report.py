"""Modelo para reportes de ventas."""

from dataclasses import dataclass
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class ProductSale:
    """Modelo para ventas de productos individuales."""
    nombre: str
    ventas: float
    cantidad: int

    @classmethod
    def from_dict(cls, data: dict) -> 'ProductSale':
        """Crear instancia desde diccionario."""
        return cls(
            nombre=data['nombre'],
            ventas=float(data['ventas']),
            cantidad=int(data['cantidad'])
        )

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            'nombre': self.nombre,
            'ventas': self.ventas,
            'cantidad': self.cantidad
        }


@dataclass
class SalesReport:
    """Modelo para reporte de ventas."""
    ventas_totales: float
    pedidos: int
    productos: List[ProductSale]
    grafico: List[int]
    periodo: str
    vendor_id: str = None
    period_type: str = None
    generated_at: str = None

    @classmethod
    def from_dict(cls, data: dict, vendor_id: str = None, period_type: str = None) -> 'SalesReport':
        """Crear instancia desde diccionario."""
        productos = [ProductSale.from_dict(p) for p in data.get('productos', [])]
        
        return cls(
            ventas_totales=float(data['ventasTotales']),
            pedidos=int(data['pedidos']),
            productos=productos,
            grafico=data.get('grafico', []),
            periodo=data['periodo'],
            vendor_id=vendor_id,
            period_type=period_type,
            generated_at=datetime.now().isoformat()
        )

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            'ventasTotales': self.ventas_totales,
            'pedidos': self.pedidos,
            'productos': [product.to_dict() for product in self.productos],
            'grafico': self.grafico,
            'periodo': self.periodo,
            'vendor_id': self.vendor_id,
            'period_type': self.period_type,
            'generated_at': self.generated_at
        }

