from flask import Blueprint, jsonify
from ..db import get_vehiculos, get_clientes, get_clientes_by_seller
from ..models import Vehiculo, Cliente
from ..utils.calculate_route import generate_optimized_route

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

@routes_bp.get('/seller/<int:seller_ID>')
def get_seller_daily_routes(seller_ID):
    clients_data = get_clientes_by_seller(seller_ID)

    # 1. Llamar a la función y capturar el resultado
    route_result = generate_optimized_route(clients_data)


    # 2. Retornar el resultado de la ruta
    if route_result and "error" in route_result:
        # Si la función retornó un error
        return jsonify(route_result), 500

    # Si fue exitoso, retornar el resultado de la ruta optimizada
    return jsonify(route_result), 200
    

@routes_bp.get('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200




