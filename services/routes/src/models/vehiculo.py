"""Modelo para vehículos."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Vehiculo:
    """Modelo para vehículos disponibles."""
    id: str
    capacidad: int
    color: str
    etiqueta: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> 'Vehiculo':
        """Crear instancia desde diccionario."""
        return cls(
            id=data['id'],
            capacidad=data['capacidad'],
            color=data['color'],
            etiqueta=data.get('etiqueta')
        )

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            'id': self.id,
            'capacidad': self.capacidad,
            'color': self.color,
            'etiqueta': self.etiqueta
        }
