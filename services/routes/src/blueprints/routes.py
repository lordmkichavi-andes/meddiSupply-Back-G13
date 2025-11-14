import random
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
    # El número de clientes a visitar es aleatorio, pero no puede exceder el total disponible.
    num_clientes_a_visitar =  4

    # 4. Seleccionar aleatoriamente el subconjunto de clientes
    # random.sample garantiza la selección sin reemplazo
    clientes_seleccionados = clients_data if len(clients_data) < 4 else random.sample(clients_data, num_clientes_a_visitar)

    # 1. Llamar a la función y capturar el resultado
    route_result = generate_optimized_route(clientes_seleccionados)


    # 2. Retornar el resultado de la ruta
    if route_result and "error" in route_result:
        # Si la función retornó un error
        return jsonify({
            "visits": route_result[:-1],
            "number_visits": len(route_result[:-1]),
        }), 500

    # Si fue exitoso, retornar el resultado de la ruta optimizada
    return jsonify({
            "visits": route_result[:-1],
            "number_visits": len(route_result[:-1]),
        }), 200
    

@routes_bp.get('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200




