from flask import Blueprint, jsonify
from ..db import get_vehiculos, get_clientes
from ..models import Vehiculo, Cliente

routes_bp = Blueprint('routes', __name__)


@routes_bp.get('/vehicles')
def get_vehicles():
    """Obtener lista de vehículos disponibles."""
    try:
        vehicles_data = get_vehiculos()
        vehicles = [Vehiculo.from_dict(vehicle) for vehicle in vehicles_data]
        return jsonify([vehicle.to_dict() for vehicle in vehicles]), 200
    except Exception as e:
        return jsonify({"message": f"Error obteniendo vehículos: {str(e)}"}), 500


@routes_bp.get('/clients')
def get_clients():
    """Obtener lista de clientes."""
    try:
        clients_data = get_clientes()
        clients = [Cliente.from_dict(client) for client in clients_data]
        return jsonify([client.to_dict() for client in clients]), 200
    except Exception as e:
        return jsonify({"message": f"Error obteniendo clientes: {str(e)}"}), 500


@routes_bp.get('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200




