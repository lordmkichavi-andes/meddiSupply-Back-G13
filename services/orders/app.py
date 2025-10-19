from flask import Flask, jsonify
from dotenv import load_dotenv
from src.infrastructure.web.flask_routes import create_api_blueprint
from src.application.use_cases import TrackOrdersUseCase, CreateOrderUseCase
from src.infrastructure.persistence.pg_repository import PgOrderRepository
from src.infrastructure.persistence.db_connector import init_db_pool
from src.infrastructure.persistence.db_initializer import initialize_database
from config import Config
from flask_cors import CORS

load_dotenv()

def create_app():
    """Crea y configura la aplicación Flask usando Arquitectura Limpia."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- Inicialización de BD ---
    try:
        init_db_pool()
        initialize_database()
    except Exception as e:
        print(f"CRITICAL ERROR: Fallo al inicializar la BD. {e}")

    # --- Inyección de dependencias ---
    order_repository = PgOrderRepository()

    track_orders_use_case = TrackOrdersUseCase(order_repository)
    create_order_use_case = CreateOrderUseCase(order_repository)

    # --- Configurar CORS ---
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        }
    })

    # --- Rutas (presentación) ---
    api_bp = create_api_blueprint(track_orders_use_case, create_order_use_case)
    app.register_blueprint(api_bp, url_prefix='/orders')

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok'})
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=8080, debug=False)
