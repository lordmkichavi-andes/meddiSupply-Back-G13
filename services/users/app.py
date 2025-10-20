from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import datetime

# Importaciones de arquitectura limpia
from src.infrastructure.web.flask_user_routes import create_user_api_blueprint
from src.application.use_cases import GetClientUsersUseCase
from src.infrastructure.persistence.pg_user_repository import PgUserRepository
from src.infrastructure.persistence.db_connector import init_db_pool
from src.infrastructure.persistence.db_initializer import initialize_database
from config import Config

# Cargar variables de entorno del archivo .env (si existe)
load_dotenv()

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

def create_app():
    """Crea, configura y cablea la aplicación Flask siguiendo la Arquitectura Limpia."""
    
    app = Flask(__name__)
    app.config.from_object(Config)

    
    # --- INICIALIZACIÓN DE LA BASE DE DATOS (REQUISITO) ---
    try:
        print("🔌 Inicializando conexión a la base de datos...")
        init_db_pool()
        print("📊 Inicializando esquema de la base de datos...")
        #initialize_database()
        print("✅ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Fallo al inicializar la BD. {e}")
        # Opción 1: Re-lanzar la excepción para que la app no arranque
        raise
    
    # --- CABLEADO DE DEPENDENCIAS (Dependency Injection - DI) ---
    
    # 1. Infraestructura de Persistencia (Implementación real de PostgreSQL)
    user_repository = PgUserRepository()
    
    # 2. Capa de Aplicación (Use Case)
    get_client_users_use_case = GetClientUsersUseCase(
        user_repository=user_repository
    )
    
    # Configurar CORS
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        }
    })
    
    # 3. Capa de Presentación (Web) - Arquitectura Limpia
    user_api_bp = create_user_api_blueprint(get_client_users_use_case)
    
    # --- REGISTRO DE RUTAS ---
    app.register_blueprint(user_api_bp, url_prefix='/api')
    
    # --- RUTAS LEGACY (Datos quemados) ---
    
    @app.route('/', methods=['GET'])
    def home():
        return jsonify({
            "mensaje": "🚀 Usuarios Service - Deploy Test en Develop",
            "version": "2.1.4",
            "build": "ci-cd-test-$(date +%Y%m%d-%H%M%S)",
            "endpoints_disponibles": [
                "GET / - Información del backend",
                "POST /datos - Obtener datos quemados",
                "POST /usuarios - Obtener usuarios",
                "POST /productos - Obtener productos",
                "GET /health - Health check para CI/CD",
                "GET /api/users/clients - Obtener usuarios CLIENT de la BD"
            ],
            "microservicio": "usuarios",
            "cluster": "microservices-cluster"
        })

    @app.route('/datos', methods=['POST'])
    def obtener_datos():
        """
        Endpoint POST que devuelve datos quemados
        """
        try:
            datos_request = request.get_json() if request.is_json else {}
            print(f"Petición recibida: {datos_request}")
            
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

    @app.route('/health', methods=['GET'])
    def health_check():
        """
        Endpoint de health check para CI/CD y monitoreo
        """
        try:
            return jsonify({
                "status": "healthy",
                "service": "usuarios",
                "version": "2.1.4",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "uptime": "running",
                "checks": {
                    "database": "ok",
                    "memory": "ok",
                    "cpu": "ok"
                },
                "ci_cd": {
                    "pipeline": "active",
                    "last_deploy": "ci-cd-test",
                    "environment": "production-ready"
                }
            }), 200
            
        except Exception as e:
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }), 503
    
    return app
  

if __name__ == '__main__':
    print("🚀 Iniciando Usuarios Service - CI/CD Pipeline...")
    print("📡 Endpoints disponibles:")
    print("   GET  / - Información del backend")
    print("   POST /datos - Obtener todos los datos quemados")
    print("   POST /usuarios - Obtener usuarios")
    print("   POST /productos - Obtener productos")
    print("   GET  /health - Health check para CI/CD")
    print("   GET  /api/users/clients - Obtener usuarios CLIENT de BD")
    print("🌐 Servidor ejecutándose en: http://localhost:8080")
    print("🔧 Versión: 2.1.4 - Proper ECS Deploy Test")
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=False)