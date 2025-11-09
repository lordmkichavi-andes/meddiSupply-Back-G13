"""Servicio para integración con AWS Cognito."""

import boto3
import os
from typing import Optional, Dict, Any, Tuple
from botocore.exceptions import ClientError

# Configuración de Cognito (desde variables de entorno)
USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID', 'us-east-1_3n4C8QOve')
CLIENT_ID = os.getenv('COGNITO_CLIENT_ID', '113qhpd3hktvupdbhpi5361h90')


def get_cognito_client():
    """Obtiene el cliente de Cognito."""
    return boto3.client('cognito-idp', region_name='us-east-1')


def create_user_in_cognito(username: str, email: str, password: str, group_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Crea un usuario en Cognito y lo asigna a un grupo.
    
    Args:
        username: Nombre de usuario (puede ser email o identificador único)
        email: Correo electrónico del usuario
        password: Contraseña del usuario (texto plano - Cognito la maneja)
        group_name: Nombre del grupo en Cognito (admin, clientes, vendedores, etc.)
        
    Returns:
        Tupla: (success: bool, user_id: Optional[str], error_message: Optional[str])
    """
    cognito = get_cognito_client()
    
    try:
        # 1. Crear usuario en Cognito
        print(f"🛠️  Creando usuario en Cognito: {username}...")
        response = cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=username,
            TemporaryPassword=password,
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': email
                },
                {
                    'Name': 'email_verified',
                    'Value': 'true'
                }
            ],
            MessageAction='SUPPRESS'  # No enviar email de bienvenida
        )
        
        user_id = response['User']['Username']
        print(f"✅ Usuario '{username}' creado en Cognito.")
        
        # 2. Establecer contraseña permanente
        print(f"🔒 Estableciendo contraseña permanente...")
        cognito.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=username,
            Password=password,
            Permanent=True
        )
        print(f"✅ Contraseña establecida permanentemente.")
        
        # 3. Agregar usuario al grupo
        print(f"👤 Agregando usuario al grupo '{group_name}'...")
        cognito.admin_add_user_to_group(
            UserPoolId=USER_POOL_ID,
            Username=username,
            GroupName=group_name
        )
        print(f"✅ Usuario '{username}' agregado a '{group_name}'.")
        
        return True, user_id, None
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UsernameExistsException':
            return False, None, f"El usuario '{username}' ya existe en Cognito"
        elif error_code == 'ResourceNotFoundException':
            return False, None, f"El grupo '{group_name}' no existe en Cognito"
        elif error_code == 'InvalidPasswordException':
            return False, None, "La contraseña no cumple con los requisitos de seguridad"
        else:
            return False, None, f"Error de Cognito: {error_message}"
    except Exception as e:
        print(f"❌ Error general creando usuario en Cognito: {e}")
        return False, None, f"Error inesperado: {str(e)}"


def authenticate_with_cognito(username: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Autentica un usuario con Cognito y obtiene el token de acceso.
    
    Args:
        username: Nombre de usuario o email
        password: Contraseña del usuario
        
    Returns:
        Tupla: (is_authenticated: bool, token_data: Optional[Dict], error_message: Optional[str])
        - is_authenticated: True si la autenticación fue exitosa
        - token_data: Diccionario con access_token, id_token, refresh_token (None si falla)
        - error_message: Mensaje de error según HU37 (None si es exitoso)
    """
    cognito = get_cognito_client()
    
    try:
        # Autenticar con Cognito usando ADMIN_NO_SRP_AUTH
        auth_response = cognito.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password
            }
        )
        
        # Obtener tokens
        auth_result = auth_response['AuthenticationResult']
        token_data = {
            'access_token': auth_result['AccessToken'],
            'id_token': auth_result.get('IdToken'),
            'refresh_token': auth_result.get('RefreshToken'),
            'token_type': auth_result.get('TokenType', 'Bearer'),
            'expires_in': auth_result.get('ExpiresIn', 3600)
        }
        
        return True, token_data, None
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == 'UserNotFoundException':
            return False, None, "¡Ups! El usuario no está registrado"
        elif error_code == 'NotAuthorizedException':
            return False, None, "¡Ups! Credenciales inválidas, por favor intente nuevamente"
        elif error_code == 'UserNotConfirmedException':
            return False, None, "El usuario no está confirmado"
        else:
            return False, None, "¡Ups! Credenciales inválidas, por favor intente nuevamente"
    except Exception as e:
        print(f"❌ Error autenticando con Cognito: {e}")
        return False, None, "¡Ups! Hubo un problema, intenta nuevamente en unos minutos"


def map_role_to_cognito_group(role: str) -> str:
    """
    Mapea el rol de la BD a un grupo de Cognito.
    
    Según authorizer.py (HU37), los grupos válidos en Cognito son:
    - admin: Acceso completo 24/7
    - compras: Horario laboral, red corporativa
    - logistica: Horario extendido para logística
    - ventas: Horario extendido para ventas
    - clientes: Horario comercial, solo Colombia
    
    Args:
        role: Rol del usuario (ADMIN, SELLER, CLIENT)
        
    Returns:
        Nombre del grupo en Cognito
    """
    role_mapping = {
        'ADMIN': 'admin',
        'SELLER': 'ventas',  # Vendedores → grupo 'ventas' en Cognito
        'CLIENT': 'clientes',  # Clientes → grupo 'clientes' en Cognito
        'PROVIDER': 'compras'  # Proveedores → grupo 'compras' en Cognito
    }
    return role_mapping.get(role.upper(), 'clientes')  # Default a 'clientes'


def get_username_from_email_or_identification(email: str, identification: Optional[str] = None) -> str:
    """
    Genera un username para Cognito a partir del email o identification.
    
    NOTA: Si Cognito está configurado con "email alias", el username NO puede ser el email.
    En ese caso, debemos usar identification o generar un username único.
    
    Args:
        email: Correo electrónico
        identification: Identificación del usuario (opcional)
        
    Returns:
        Username para usar en Cognito
    """
    # Si hay identification, usarla como username (más común en Cognito con email alias)
    if identification:
        return identification.strip()
    
    # Si no hay identification, usar la parte antes del @ del email
    # Ejemplo: usuario.cognito.test@test.com -> usuario.cognito.test
    username = email.split('@')[0].lower().strip()
    return username


def global_sign_out(access_token: str) -> Tuple[bool, Optional[str]]:
    """
    Cierra sesión global del usuario usando el AccessToken (invalida refresh tokens).
    """
    cognito = get_cognito_client()
    try:
        cognito.global_sign_out(AccessToken=access_token)
        return True, None
    except ClientError as e:
        msg = e.response['Error']['Message']
        return False, msg
    except Exception as e:
        return False, str(e)


def admin_global_sign_out(username: str) -> Tuple[bool, Optional[str]]:
    """
    Cierra sesión global de un usuario por username (identification), invalida tokens.
    """
    cognito = get_cognito_client()
    try:
        cognito.admin_user_global_sign_out(UserPoolId=USER_POOL_ID, Username=username)
        return True, None
    except ClientError as e:
        msg = e.response['Error']['Message']
        return False, msg
    except Exception as e:
        return False, str(e)

