"""Aplicación principal del servicio de reportes."""

from flask import Flask, jsonify
from flask_cors import CORS


def create_app() -> Flask:
    """Crea y configura la aplicación Flask."""
    app = Flask(__name__)
    
    # Configurar CORS
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        }
    })

    # Registro del blueprint de reportes
    from src.blueprints.reports import reports_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')

    return app

app = create_app()


if __name__ == '__main__':
    print("Iniciando servidor de reportes de ventas...")
    print("Endpoints disponibles:")
    print("   GET  /reports/vendors - Lista de vendedores")
    print("   GET  /reports/periods - Períodos disponibles")
    print("   POST /reports/sales-report - Generar reporte")
    print("   POST /reports/sales-report/validate - Validar datos")
    print("   GET  /reports/health - Estado del servidor")
    print("Servidor corriendo en http://localhost:8080")
    
    app.run(host='0.0.0.0', port=8080, debug=False)
