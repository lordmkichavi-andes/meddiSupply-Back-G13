# config.py
import os


class Config:
    """Clase base de configuración, con variables de entorno para DB."""

    # Configuración de la aplicación
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-super-secret-key')

    # Configuración de la Base de Datos (PostgreSQL/RDW)
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '5432')
    DB_NAME = os.environ.get('DB_NAME', 'medisupplydb')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'mysecretpassword')

    # Parámetros para la inicialización de la BD
    RUN_DB_INIT_ON_STARTUP = os.environ.get('RUN_DB_INIT_ON_STARTUP', 'True').lower() == 'true'
