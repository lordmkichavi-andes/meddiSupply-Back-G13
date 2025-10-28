from flask import Flask, jsonify
from flask_cors import CORS

# Updated for CI/CD pipeline testing


def create_app() -> Flask:
    app = Flask(__name__)
    
    # Configurar CORS
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        }
    })

    # Registro del blueprint de dominio "routes"
    from src.blueprints.routes import routes_bp
    app.register_blueprint(routes_bp, url_prefix='/routes')

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({'status': 'ok'})

    return app


app = create_app()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
