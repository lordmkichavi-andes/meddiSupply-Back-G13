"""Tests directos para medir cobertura real."""

import pytest
import sys
import os
import importlib.util

# Función para importar módulo desde archivo
def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Importar directamente los módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Importar Vehiculo
vehiculo_path = os.path.join(parent_dir, "src", "models", "vehiculo.py")
Vehiculo = import_from_file("vehiculo", vehiculo_path).Vehiculo

# Importar Cliente
cliente_path = os.path.join(parent_dir, "src", "models", "cliente.py")
Cliente = import_from_file("cliente", cliente_path).Cliente


class TestDirectVehiculo:
    """Tests directos para Vehiculo."""

    def test_vehiculo_creation_with_label(self):
        """Test creación con label."""
        vehiculo = Vehiculo(
            id="V001",
            capacidad=100,
            color="rojo",
            etiqueta="refrigerado"
        )
        assert vehiculo.id == "V001"
        assert vehiculo.capacidad == 100
        assert vehiculo.color == "rojo"
        assert vehiculo.etiqueta == "refrigerado"

    def test_vehiculo_creation_without_label(self):
        """Test creación sin label."""
        vehiculo = Vehiculo(
            id="V002",
            capacidad=50,
            color="azul"
        )
        assert vehiculo.id == "V002"
        assert vehiculo.capacidad == 50
        assert vehiculo.color == "azul"
        assert vehiculo.etiqueta is None

    def test_vehiculo_from_dict_with_label(self):
        """Test from_dict con label."""
        data = {
            "vehicle_id": "V003",
            "capacity": 75,
            "color": "verde",
            "label": "normal"
        }
        vehiculo = Vehiculo.from_dict(data)
        assert vehiculo.id == "V003"
        assert vehiculo.capacidad == 75
        assert vehiculo.color == "verde"
        assert vehiculo.etiqueta == "normal"

    def test_vehiculo_from_dict_without_label(self):
        """Test from_dict sin label."""
        data = {
            "vehicle_id": "V004",
            "capacity": 25,
            "color": "amarillo"
        }
        vehiculo = Vehiculo.from_dict(data)
        assert vehiculo.id == "V004"
        assert vehiculo.capacidad == 25
        assert vehiculo.color == "amarillo"
        assert vehiculo.etiqueta is None

    def test_vehiculo_to_dict_complete(self):
        """Test to_dict completo."""
        vehiculo = Vehiculo(
            id="V005",
            capacidad=120,
            color="blanco",
            etiqueta="especial"
        )
        result = vehiculo.to_dict()
        expected = {
            "id": "V005",
            "capacidad": 120,
            "color": "blanco",
            "etiquta": "especial"
        }
        assert result == expected

    def test_vehiculo_to_dict_without_label(self):
        """Test to_dict sin label."""
        vehiculo = Vehiculo(
            id="V006",
            capacidad=80,
            color="gris"
        )
        result = vehiculo.to_dict()
        expected = {
            "id": "V006",
            "capacidad": 80,
            "color": "gris",
            "etiquta": None
        }
        assert result == expected


class TestDirectCliente:
    """Tests directos para Cliente."""

    def test_cliente_creation_complete(self):
        """Test creación completa de cliente."""
        cliente = Cliente(
            id="C001",
            nombre="Hospital Central",
            direccion="Calle 123 #45-67",
            latitud=4.6097100,
            longitud=-74.0817500,
            demanda=50
        )
        assert cliente.id == "C001"
        assert cliente.nombre == "Hospital Central"
        assert cliente.direccion == "Calle 123 #45-67"
        assert cliente.latitud == 4.6097100
        assert cliente.longitud == -74.0817500
        assert cliente.demanda == 50

    def test_cliente_from_dict_string_conversion(self):
        """Test from_dict con conversión de strings."""
        data = {
            "id": "C002",
            "nombre": "Clinica San Rafael",
            "direccion": "Carrera 7 #32-10",
            "latitud": "4.6110000",
            "longitud": "-74.0720000",
            "demanda": "75"
        }
        cliente = Cliente.from_dict(data)
        assert cliente.id == "C002"
        assert cliente.nombre == "Clinica San Rafael"
        assert isinstance(cliente.latitud, float)
        assert isinstance(cliente.longitud, float)
        assert isinstance(cliente.demanda, int)
        assert cliente.latitud == 4.6110000
        assert cliente.longitud == -74.0720000
        assert cliente.demanda == 75

    def test_cliente_to_dict_complete(self):
        """Test to_dict completo."""
        cliente = Cliente(
            id="C003",
            nombre="Centro Medico ABC",
            direccion="Avenida 68 #25-30",
            latitud=4.6200000,
            longitud=-74.0800000,
            demanda=100
        )
        result = cliente.to_dict()
        expected = {
            "id": "C003",
            "nombre": "Centro Medico ABC",
            "direccion": "Avenida 68 #25-30",
            "latitud": 4.6200000,
            "longitud": -74.0800000,
            "demanda": 100
        }
        assert result == expected

    def test_cliente_to_stop_with_order_id(self):
        """Test to_stop con order_id personalizado."""
        cliente = Cliente(
            id="C004",
            nombre="Hospital XYZ",
            direccion="Calle 80 #10-15",
            latitud=4.6300000,
            longitud=-74.0900000,
            demanda=60
        )
        result = cliente.to_stop("ORD123")
        expected = {
            "id": "C004",
            "name": "Hospital XYZ",
            "address": "Calle 80 #10-15",
            "orderId": "ORD123",
            "lat": 4.6300000,
            "lng": -74.0900000
        }
        assert result == expected

    def test_cliente_to_stop_without_order_id(self):
        """Test to_stop sin order_id."""
        cliente = Cliente(
            id="C005",
            nombre="Farmacia 24h",
            direccion="Carrera 15 #93-47",
            latitud=4.6500000,
            longitud=-74.0600000,
            demanda=25
        )
        result = cliente.to_stop()
        expected = {
            "id": "C005",
            "name": "Farmacia 24h",
            "address": "Carrera 15 #93-47",
            "orderId": "C005",  # Usa el id del cliente
            "lat": 4.6500000,
            "lng": -74.0600000
        }
        assert result == expected
