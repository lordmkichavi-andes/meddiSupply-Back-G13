from flask import Flask, request, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)  # Permite CORS para todas las rutas

# Datos quemados que se devolverán
datos_quemados = {
    "usuarios": [
        {
            "id": 1,
            "nombre": "Juan Pérez",
            "email": "juan.perez@email.com",
            "edad": 28,
            "ciudad": "Madrid"
        },
        {
            "id": 2,
            "nombre": "María García",
            "email": "maria.garcia@email.com",
            "edad": 32,
            "ciudad": "Barcelona"
        },
        {
            "id": 3,
            "nombre": "Carlos López",
            "email": "carlos.lopez@email.com",
            "edad": 25,
            "ciudad": "Valencia"
        }
    ],
    "productos": [
        {
            "id": 1,
            "nombre": "Laptop",
            "precio": 999.99,
            "categoria": "Electrónicos",
            "stock": 15
        },
        {
            "id": 2,
            "nombre": "Mouse",
            "precio": 25.50,
            "categoria": "Accesorios",
            "stock": 50
        },
        {
            "id": 3,
            "nombre": "Teclado",
            "precio": 75.00,
            "categoria": "Accesorios",
            "stock": 30
        }
    ],
    "estadisticas": {
        "total_usuarios": 3,
        "total_productos": 3,
        "ventas_mes_actual": 1250.50,
        "clientes_activos": 2
    }
}

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "mensaje": "Backend Python funcionando correctamente",
        "version": "1.0.0",
        "endpoints_disponibles": [
            "GET / - Información del backend",
            "POST /datos - Obtener datos quemados"
        ]
    })

@app.route('/datos', methods=['POST'])
def obtener_datos():
    """
    Endpoint POST que devuelve datos quemados
    """
    try:
        # Obtener datos del body de la petición (opcional)
        datos_request = request.get_json() if request.is_json else {}
        
        # Log de la petición recibida
        print(f"Petición recibida: {datos_request}")
        
        # Respuesta con los datos quemados
        respuesta = {
            "success": True,
            "mensaje": "Datos obtenidos exitosamente",
            "timestamp": "2024-01-15T10:30:00Z",
            "datos": datos_quemados,
            "peticion_recibida": datos_request
        }
        
        return jsonify(respuesta), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "mensaje": "Error al procesar la petición",
            "error": str(e)
        }), 500

@app.route('/usuarios', methods=['POST'])
def obtener_usuarios():
    """
    Endpoint POST específico para obtener solo usuarios
    """
    try:
        datos_request = request.get_json() if request.is_json else {}
        
        respuesta = {
            "success": True,
            "mensaje": "Usuarios obtenidos exitosamente",
            "usuarios": datos_quemados["usuarios"],
            "total": len(datos_quemados["usuarios"])
        }
        
        return jsonify(respuesta), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "mensaje": "Error al obtener usuarios",
            "error": str(e)
        }), 500

@app.route('/productos', methods=['POST'])
def obtener_productos():
    """
    Endpoint POST específico para obtener solo productos
    """
    try:
        datos_request = request.get_json() if request.is_json else {}
        
        respuesta = {
            "success": True,
            "mensaje": "Productos obtenidos exitosamente",
            "productos": datos_quemados["productos"],
            "total": len(datos_quemados["productos"])
        }
        
        return jsonify(respuesta), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "mensaje": "Error al obtener productos",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask...")
    print("📡 Endpoints disponibles:")
    print("   GET  / - Información del backend")
    print("   POST /datos - Obtener todos los datos quemados")
    print("   POST /usuarios - Obtener usuarios")
    print("   POST /productos - Obtener productos")
    print("🌐 Servidor ejecutándose en: http://localhost:8080")
    
    app.run(debug=True, host='0.0.0.0', port=8080)
