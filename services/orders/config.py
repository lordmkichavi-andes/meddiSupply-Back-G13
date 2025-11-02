# config.py
import os


class Config:
    """Clase base de configuración, con variables de entorno para DB."""
    # Configuración de la Base de Datos (PostgreSQL/RDW)
    DB_HOST = os.environ.get('DB_HOST', 'host.docker.internal')
    DB_PORT = os.environ.get('DB_PORT', '5440')
    DB_NAME = os.environ.get('DB_NAME', 'offer_manager_db')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
    # Parámetros para la inicialización de la BD
    RUN_DB_INIT_ON_STARTUP = os.environ.get('RUN_DB_INIT_ON_STARTUP', 'False').lower() == 'true'
