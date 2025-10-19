# app.py
from flask import Flask, jsonify
from dotenv import load_dotenv  # Necesario para cargar variables de entorno
from src.infrastructure.web.flask_routes import create_api_blueprint
from src.application.use_cases import TrackOrdersUseCase
from src.infrastructure.persistence.pg_repository import PgOrderRepository
from src.infrastructure.persistence.db_connector import init_db_pool
from src.infrastructure.persistence.db_initializer import initialize_database
from config import Config
from flask_cors import CORS


# Cargar variables de entorno del archivo .env (si existe)
load_dotenv()


def create_app():
    """Crea, configura y cablea la aplicación Flask siguiendo la Arquitectura Limpia."""

    app = Flask(__name__)
    app.config.from_object(Config)

    # --- INICIALIZACIÓN DE LA BASE DE DATOS (REQUISITO) ---
    # 1. Inicializa el pool de conexiones.
    try:
        try:
            init_db_pool()
            initialize_database()
        except Exception as e:
            print(f"CRITICAL ERROR: Fallo al inicializar la BD. {e}")
            pass  # <--- ¡El problema! El pool está roto, pero la app sigue.
    except Exception as e:
        # En un entorno de producción, esto debería ser un error fatal que detiene el servicio
        print(f"CRITICAL ERROR: Fallo al inicializar la BD. {e}")
        # Se permite que la aplicación continúe, pero las peticiones fallarán.
        pass

    # --- CABLEADO DE DEPENDENCIAS (Dependency Injection - DI) ---

    # 1. Infraestructura de Persistencia (Implementación real de PostgreSQL)
    order_repository = PgOrderRepository()

    # 2. Capa de Aplicación (Use Case)
    track_orders_use_case = TrackOrdersUseCase(
        order_repository=order_repository
    )
    # Configurar CORS
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        }
    })

    # 3. Capa de Presentación (Web)
    api_bp = create_api_blueprint(track_orders_use_case, create_order_use_case)
    app.register_blueprint(api_bp, url_prefix='/orders')

    # --- Ruta de control ---
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok'})
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=False)