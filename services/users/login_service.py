"""Servicio de autenticación para HU37: Iniciar sesión."""

import re
from typing import Optional, Dict, Any, Tuple
from src.infrastructure.persistence.db_connector import get_connection, release_connection
import psycopg2.extras
from cognito_service import authenticate_with_cognito


def validate_login_data(email: Optional[str], password: str, identification: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Valida los datos de login (correo y contraseña).
    
    Args:
        email: Correo electrónico del usuario
        password: Contraseña del usuario
        
    Returns:
        Tupla: (is_valid: bool, error_message: Optional[str])
        - is_valid: True si los datos son válidos
        - error_message: Mensaje de error si hay problema (None si es válido)
    """
    # Validar campos obligatorios (se permite email O identification)
    if (not email or not email.strip()) and (not identification or not str(identification).strip()):
        return False, "Campo obligatorio"
    
    if not password or not password.strip():
        return False, "Campo obligatorio"
    
    # Validar formato de correo si se proporcionó
    if email and email.strip():
        email = email.strip().lower()
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            return False, "Ingrese un correo válido"
    
    return True, None


def authenticate_user(email: Optional[str], password: str, identification: Optional[str] = None) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Autentica un usuario con correo y contraseña.
    
    Args:
        email: Correo electrónico del usuario
        password: Contraseña del usuario
        
    Returns:
        Tupla: (is_authenticated: bool, user_data: Optional[Dict], error_message: Optional[str])
        - is_authenticated: True si la autenticación fue exitosa
        - user_data: Datos del usuario si es exitoso (None si falla)
        - error_message: Mensaje de error según HU37 (None si es exitoso)
    """
    # Validar datos de entrada
    is_valid, validation_error = validate_login_data(email, password, identification)
    if not is_valid:
        # Los mensajes de validación de formato son para el frontend
        # Si llegan aquí, es porque el backend los validó también
        return False, None, validation_error
    
    # Opción A: Autenticar con Cognito (fuente principal)
    conn = None
    try:
        # 0. Obtener username de Cognito desde BD (para User Pool con email alias)
        # Primero buscamos en BD para obtener el identification que se usa como username
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        user = None
        if email and email.strip():
            cursor.execute(
                "SELECT user_id, name, last_name, email, role, active, identification, phone FROM users.users WHERE LOWER(email) = %s",
                (email.strip().lower(),)
            )
            user = cursor.fetchone()

        # Si no encontró por correo y se proporcionó identificación, buscar por identificación
        if not user and identification:
            cursor.execute(
                "SELECT user_id, name, last_name, email, role, active, identification, phone FROM users.users WHERE identification = %s",
                (str(identification),)
            )
            user = cursor.fetchone()
        
        if not user:
            cursor.close()
            release_connection(conn)
            return False, None, "¡Ups! El usuario no está registrado"
        
        # Verificar si el usuario está activo
        if not user.get('active', True):
            cursor.close()
            release_connection(conn)
            return False, None, "¡Ups! Credenciales inválidas, por favor intente nuevamente"
        
        # Obtener username para Cognito (identification o parte del email)
        from cognito_service import get_username_from_email_or_identification
        cognito_username = get_username_from_email_or_identification(user.get('email'), user.get('identification'))
        
        cursor.close()
        release_connection(conn)
        
        # 1. Autenticar con Cognito usando el username correcto
        is_authenticated, token_data, cognito_error = authenticate_with_cognito(cognito_username, password)
        
        if not is_authenticated:
            return False, None, cognito_error
        
        # 2. Si Cognito autenticó exitosamente, usar datos de BD ya obtenidos
        # Autenticación exitosa: Combinar datos de BD con tokens de Cognito
        user_data = {
            "user_id": user['user_id'],
            "name": user['name'],
            "last_name": user['last_name'],
            "email": user['email'],
            "role": user['role'],
            "identification": user.get('identification'),
            "phone": user.get('phone'),
            "tokens": token_data  # Tokens de Cognito
        }
        
        return True, user_data, None
            
    except Exception as e:
        print(f"Error en autenticación: {str(e)}")
        if conn:
            release_connection(conn)
        return False, None, "¡Ups! Hubo un problema, intenta nuevamente en unos minutos"

