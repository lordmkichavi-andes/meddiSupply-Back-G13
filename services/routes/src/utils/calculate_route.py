import math
import requests
import json
from typing import List, Tuple, Optional, Dict, Any
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# --------------------------------------------------------------------------------
# CONFIGURACIÓN CRÍTICA
# --------------------------------------------------------------------------------
# ⚠️ REEMPLAZA ESTE VALOR CON TU CLAVE REAL DE GOOGLE MAPS API
# Asegúrate de que la "Distance Matrix API" esté habilitada.
GOOGLE_API_KEY = "TU_CLAVE_DE_API_AQUI"


# --------------------------------------------------------------------------------


# --------------------------------------------------------------------------------
# 1. FUNCIÓN PARA SIMULAR LA MATRIZ DE TIEMPOS DE VIAJE (Fallback)
# --------------------------------------------------------------------------------

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia Haversine (distancia en línea recta).
    Usado solo si la llamada a la API falla o no se configura la clave.
    Retorna la distancia en kilómetros.
    """
    R = 6371  # Radio de la Tierra en kilómetros
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(
        d_lon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def create_time_matrix(coordinates: List[Tuple[float, float]]) -> List[List[int]]:
    """
    Crea la matriz de "tiempos" de viaje (costos) entre todos los pares de puntos
    utilizando la API de Google Maps o un fallback de simulación.
    """
    if not coordinates:
        return []

    num_points = len(coordinates)

    # ------------------------------------------------------------------
    # --- 1. LÓGICA DE TIEMPO REAL (INTEGRACIÓN API GOOGLE MAPS) ---
    # ------------------------------------------------------------------
    if GOOGLE_API_KEY != "TU_CLAVE_DE_API_AQUI":
        try:
            print("INFO: Intentando obtener matriz de tiempos real de Google Maps...")

            base_url = "https://maps.googleapis.com/maps/api/distancematrix/json"

            # Formato requerido: "lat1,lon1|lat2,lon2|..."
            coord_strings = [f"{lat},{lon}" for lat, lon in coordinates]
            origins = "|".join(coord_strings)
            destinations = "|".join(coord_strings)

            params = {
                "origins": origins,
                "destinations": destinations,
                "key": GOOGLE_API_KEY,
                "mode": "driving",
                # Opcional: Para incluir tráfico en tiempo real
                # "departure_time": "now",
                "units": "metric"
            }

            response = requests.get(base_url, params=params)
            data = response.json()

            if data.get("status") == "OK":
                time_matrix_real = []
                for i, row in enumerate(data['rows']):
                    time_matrix_real_row = []
                    for element in row['elements']:
                        # Duración del viaje en segundos
                        if element['status'] == 'OK':
                            duration_seconds = element['duration']['value']
                            # Convertir a minutos (entero)
                            time_minutes = int(duration_seconds / 60)
                            time_matrix_real_row.append(time_minutes)
                        else:
                            # Si no se pudo calcular una ruta (ej. isla o error), usar un tiempo muy alto
                            time_matrix_real_row.append(99999)
                    time_matrix_real.append(time_matrix_real_row)

                print("INFO: Matriz de tiempos REAL obtenida exitosamente.")
                return time_matrix_real

            else:
                print(f"ADVERTENCIA: API falló. Status: {data.get('status')}. Usando simulación Haversine.")

        except requests.exceptions.RequestException as e:
            print(f"ERROR DE CONEXIÓN: {e}. Usando simulación Haversine.")
        except json.JSONDecodeError:
            print("ERROR: Respuesta JSON inválida de la API. Usando simulación Haversine.")
        except Exception as e:
            print(f"ERROR INESPERADO al procesar API: {e}. Usando simulación Haversine.")

    # ------------------------------------------------------------------
    # --- 2. SIMULACIÓN DE TIEMPO (FALLBACK) ---
    # ------------------------------------------------------------------
    if GOOGLE_API_KEY == "TU_CLAVE_DE_API_AQUI":
        print("ADVERTENCIA: Clave API no configurada. Usando simulación Haversine.")

    num_points = len(coordinates)
    time_matrix_simulated = []
    KM_TO_TIME_FACTOR = 2

    for i in range(num_points):
        row = []
        for j in range(num_points):
            if i == j:
                time = 0
            else:
                lat1, lon1 = coordinates[i]
                lat2, lon2 = coordinates[j]
                distance_km = haversine_distance(lat1, lon1, lat2, lon2)
                time_minutes = int(distance_km * KM_TO_TIME_FACTOR)
                time = time_minutes
            row.append(time)
        time_matrix_simulated.append(row)

    return time_matrix_simulated


# --------------------------------------------------------------------------------
# 2. ALGORITMO DE SOLUCIÓN TSP (OR-TOOLS)
# (Permanece sin cambios, utiliza la matriz generada)
# --------------------------------------------------------------------------------

def solve_tsp(coordinates: List[Tuple[float, float]]) -> Optional[Tuple[List[int], int]]:
    """
    Encuentra la ruta más corta (menor tiempo simulado/real) que visita todos los puntos.
    Utiliza el motor de optimización de Google OR-Tools.

    Retorna una tupla con la secuencia de índices de la ruta y el tiempo total (en minutos).
    """
    if len(coordinates) <= 1:
        return None  # No hay ruta que optimizar

    # 1. Crear la matriz de costes (tiempos reales o simulados)
    time_matrix = create_time_matrix(coordinates)
    num_points = len(coordinates)

    # 2. Configurar el Manager de OR-Tools
    # Asume que la ruta debe empezar y terminar en el primer punto (índice 0)
    manager = pywrapcp.RoutingIndexManager(num_points, 1, 0)
    routing = pywrapcp.RoutingModel(manager)

    # 3. Crear el Callback de Distancia/Tiempo
    def distance_callback(from_index, to_index):
        """Retorna el costo (tiempo) entre los nodos."""
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return time_matrix[from_node][to_node]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)

    # 4. Definir la Función de Costo (Arc Cost)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # 5. Configurar el Método de Búsqueda (Heurística)
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 1

    # 6. Resolver el problema
    solution = routing.SolveWithParameters(search_parameters)

    # 7. Procesar la Solución
    if solution:
        index = routing.Start(0)
        route_indices = []

        while not routing.IsEnd(index):
            route_indices.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))

        route_indices.append(manager.IndexToNode(index))
        total_time = solution.ObjectiveValue()

        return route_indices, total_time
    else:
        return None


# --------------------------------------------------------------------------------
# 3. FUNCIÓN PRINCIPAL Y EJECUCIÓN
# --------------------------------------------------------------------------------

def generate_optimized_route(locations: List[Dict]):
    """
    Función principal que recibe una lista de diccionarios de ubicaciones,
    la procesa para encontrar la ruta TSP, y devuelve la lista de ubicaciones
    ordenada por la ruta óptima.

    Retorna la lista de diccionarios (con id, nombre, etc.) ordenada.
    Retorna un diccionario de error en caso de fallo.
    """
    print("--- Optimizador de Ruta (TSP) ---")

    # 1. Parsear y extraer solo las coordenadas (lat, lon) de los diccionarios
    try:
        coordinates_float = []
        for loc in locations:
            # Asumiendo que las claves son 'latitud' y 'longitud'
            lat = float(loc['latitud'])
            lon = float(loc['longitud'])
            coordinates_float.append((lat, lon))
    except (ValueError, KeyError):
        print("\nERROR: Los datos de entrada son inválidos o faltan claves ('latitud', 'longitud').")
        return {
            "error": "Invalid input data: coordinates must be valid numbers and keys 'latitud' and 'longitud' must exist."}

    num_points = len(coordinates_float)

    if num_points == 0:
        print("\nNo se proporcionaron puntos. Ruta vacía.")
        # Devolver un arreglo vacío según la solicitud
        return []
    elif num_points == 1:
        print(f"\nSolo un punto ({coordinates_float[0]}). No hay optimización necesaria.")
        print(f"Ruta: [0] -> [0]. Tiempo Total: 0 minutos.")
        # Devolver el punto de inicio y fin (el mismo punto)
        return [locations[0]]

    print(f"\nPuntos de entrada ({num_points}): {coordinates_float}")

    # 2. Resolver el TSP
    result = solve_tsp(coordinates_float)

    # 3. Procesar y RETORNAR la Solución
    if result:
        route_indices, total_time = result

        # --- LÓGICA DE REORDENAMIENTO: Reordenar la lista ORIGINAL de diccionarios ---
        # Usamos los índices optimizados para seleccionar los elementos de la lista 'locations'
        optimized_locations = [locations[i] for i in route_indices]

        # --- Mostrar resultados (para logs/consola) ---
        print("\n=============================================")
        print("✅ RUTA ÓPTIMA ENCONTRADA")
        print("=============================================")
        print(f"Tiempo Total (Minutos): {total_time}")
        print("\nSecuencia de Visitas (Índices):")
        print(" -> ".join(map(str, route_indices)))
        print("\nRuta Óptima (Diccionarios Ordenados):")

        # Mostrar el ID o Nombre de la ruta para logs
        for i, loc in enumerate(optimized_locations):
            print(f"Punto {route_indices[i]}: ID={loc.get('id', 'N/A')}, Nombre='{loc.get('nombre', 'N/A')}'")

        print("=============================================")

        # Retornar únicamente el arreglo de diccionarios reordenado, como se solicitó.
        return optimized_locations

    else:
        print("\n⚠️ El solver no pudo encontrar una solución. Verifica las dependencias.")
        # Devuelve un diccionario de error para distinguirlo de una respuesta vacía
        return {"error": "Solver could not find a solution or problem is invalid."}
