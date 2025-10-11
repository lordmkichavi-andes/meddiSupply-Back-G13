"""Modelo para clientes."""

from dataclasses import dataclass


@dataclass
class Cliente:
    """Modelo para clientes/destinos."""
    id: str
    nombre: str
    direccion: str
    latitud: float
    longitud: float
    demanda: int

    @classmethod
    def from_dict(cls, data: dict) -> 'Cliente':
        """Crear instancia desde diccionario."""
        return cls(
            id=data['id'],
            nombre=data['nombre'],
            direccion=data['direccion'],
            latitud=float(data['latitud']),
            longitud=float(data['longitud']),
            demanda=int(data['demanda'])
        )

    def to_dict(self) -> dict:
        """Convertir a diccionario."""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'direccion': self.direccion,
            'latitud': self.latitud,
            'longitud': self.longitud,
            'demanda': self.demanda
        }

    def to_stop(self, order_id: str = None) -> dict:
        """Convertir a formato Stop para rutas."""
        return {
            'id': self.id,
            'name': self.nombre,
            'address': self.direccion,
            'orderId': order_id or self.id,
            'lat': self.latitud,
            'lng': self.longitud
        }
