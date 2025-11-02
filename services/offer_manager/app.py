from flask import Flask, jsonify
from flask_cors import CORS

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
