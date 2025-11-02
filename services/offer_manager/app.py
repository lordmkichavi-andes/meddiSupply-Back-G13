from flask import Flask, jsonify
from flask_cors import CORS
import os

def check_environment_variables():
    """Verifica si las variables críticas de entorno están presentes."""
    required_vars = ["GEMINI_API_KEY", "DB_HOST"]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        raise EnvironmentError(
            f"Fallo crítico: El contenedor no puede iniciar. Variables de entorno faltantes: {', '.join(missing)}"
        )

def create_app() -> Flask:
    app = Flask(__name__)
    check_environment_variables()
    # Configurar CORS
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        }
    })

    # Registro del blueprint de dominio "offers"
    from src.blueprints.offers import offers_bp
    app.register_blueprint(offers_bp, url_prefix='/offers')

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok'})

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
