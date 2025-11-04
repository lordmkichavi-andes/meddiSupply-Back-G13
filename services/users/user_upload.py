"""Funciones para validación e inserción de usuarios vía CSV (HU107)."""

import json
import re
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from src.infrastructure.persistence.db_connector import get_connection, release_connection
import psycopg2.extras
from cognito_service import create_user_in_cognito, map_role_to_cognito_group, get_username_from_email_or_identification

# Roles válidos según el sistema
VALID_ROLES = ['ADMIN', 'SELLER', 'CLIENT']

def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """
    Valida la fortaleza de una contraseña en texto plano (Opción 1: Cognito maneja el hashing).
    
    Args:
        password: Contraseña en texto plano
        
    Returns:
        Tupla: (is_valid: bool, error_message: Optional[str])
        - is_valid: True si la contraseña cumple con los requisitos
        - error_message: Mensaje de error si no cumple (None si es válida)
    
    Requisitos mínimos (pueden ajustarse según política de Cognito):
    - Mínimo 8 caracteres
    - Al menos una mayúscula
    - Al menos una minúscula
    - Al menos un número
    - Al menos un carácter especial
    """
    if not password or len(password.strip()) == 0:
        return False, "La contraseña es obligatoria"
    
    password = password.strip()
    
    # Longitud mínima
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres"
    
    # Verificar complejidad básica
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    errors = []
    if not has_upper:
        errors.append("mayúscula")
    if not has_lower:
        errors.append("minúscula")
    if not has_digit:
        errors.append("número")
    if not has_special:
        errors.append("carácter especial")
    
    if errors:
        return False, f"La contraseña debe contener al menos una {' y una '.join(errors)}"
    
    return True, None


def validate_users_data(users_data: List[Dict[str, Any]]) -> Tuple[bool, List[str], List[str], List[Dict[str, Any]]]:
    """
    Valida los usuarios antes de insertarlos en la base de datos (HU107).
    
    Args:
        users_data: Lista de diccionarios con usuarios a validar
        
    Returns:
        Tupla: (is_valid: bool, errors: list, warnings: list, validated_users: list)
        - is_valid: True si pasa todas las validaciones
        - errors: Lista de errores críticos que bloquean la inserción
        - warnings: Lista de advertencias que no bloquean la inserción
        - validated_users: Lista de usuarios validados (vacía si hay errores)
    """
    errors = []
    warnings = []
    validated_users = []
    
    # Validar que sea una lista y no esté vacía
    if not isinstance(users_data, list):
        errors.append("Los datos deben ser un array de usuarios")
        return False, errors, warnings, validated_users
    
    if not users_data:
        errors.append("No se recibieron usuarios para procesar")
        return False, errors, warnings, validated_users
    
    # Validar correos e identificaciones duplicadas en el archivo
    emails_in_file = {}
    identifications_in_file = {}
    for index, user in enumerate(users_data):
        if isinstance(user, dict):
            # Validar correo duplicado
            if 'correo' in user:
                email = str(user['correo']).strip().lower()
                if email in emails_in_file:
                    errors.append(f"¡Ups! Existen usuarios duplicados, revisa el archivo")
                    return False, errors, warnings, validated_users
                emails_in_file[email] = index + 1
            
            # Validar identification duplicada
            identification = user.get('identification')
            if identification:
                identification = str(identification).strip()
                if identification in identifications_in_file:
                    errors.append(f"¡Ups! Existen usuarios duplicados, revisa el archivo")
                    return False, errors, warnings, validated_users
                identifications_in_file[identification] = index + 1
    
    # Validar cada usuario
    for index, user in enumerate(users_data):
        row_num = index + 1
        
        # Verificar que sea un diccionario
        if not isinstance(user, dict):
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        user_errors = []
        
        # Campos requeridos según HU107: nombre, correo, rol, contraseña encriptada
        required_fields = ['nombre', 'correo', 'rol', 'contraseña']
        for field in required_fields:
            if field not in user or user[field] is None or str(user[field]).strip() == '':
                user_errors.append(f"Campo obligatorio faltante: {field}")
        
        if user_errors:
            errors.extend(user_errors)
            continue
        
        # Validar formato de correo
        email = str(user['correo']).strip().lower()
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        # Validar fortaleza de contraseña (Opción 1: texto plano, Cognito maneja hashing)
        password = str(user['contraseña']).strip()
        is_valid_password, password_error = validate_password_strength(password)
        if not is_valid_password:
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        # Validar rol
        role = str(user['rol']).strip().upper()
        if role not in VALID_ROLES:
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        # Si no hay errores, agregar el usuario a la lista de validados
        validated_user = {
            'nombre': str(user['nombre']).strip(),
            'correo': email,
            'rol': role,
            'contraseña': password,
            'identification': str(user.get('identification', '')).strip() if user.get('identification') else None,
            'phone': str(user.get('phone', '')).strip() if user.get('phone') else None
        }
        validated_users.append(validated_user)
    
    # Validar correos e identificaciones duplicadas en la base de datos
    if validated_users:
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # Preparar identificaciones (generar si no vienen, igual que en insert)
            identifications_to_check = []
            for u in validated_users:
                identification = u.get('identification')
                if not identification:
                    # Si no viene, usar la parte antes del @ del email (igual que en insert)
                    identification = u['correo'].split('@')[0]
                identifications_to_check.append(identification)
            
            # 1. Validar correos duplicados
            emails_to_check = [u['correo'] for u in validated_users]
            if emails_to_check:
                placeholders = ','.join(['%s'] * len(emails_to_check))
                cursor.execute(
                    f"SELECT user_id, email FROM users.users WHERE LOWER(email) IN ({placeholders})",
                    emails_to_check
                )
                existing_emails = cursor.fetchall()
                
                if existing_emails:
                    errors.append("¡Ups! Existen usuarios duplicados, revisa el archivo")
                    validated_users = []
            
            # 2. Validar identificaciones duplicadas (solo si no hay error de correos)
            if not errors and identifications_to_check:
                placeholders = ','.join(['%s'] * len(identifications_to_check))
                cursor.execute(
                    f"SELECT user_id, identification FROM users.users WHERE identification IN ({placeholders})",
                    identifications_to_check
                )
                existing_identifications = cursor.fetchall()
                
                if existing_identifications:
                    errors.append("¡Ups! Existen usuarios duplicados, revisa el archivo")
                    validated_users = []
            
            cursor.close()
            release_connection(conn)
        except Exception as db_error:
            print(f"Error validando en la base de datos: {str(db_error)}")
            errors.append("¡Ups! Hubo un problema, intenta nuevamente en unos minutos")
    
    is_valid = len(errors) == 0 and len(validated_users) > 0
    return is_valid, errors, warnings, validated_users


def insert_users(users_data: List[Dict[str, Any]], conn, cursor, data_string: str, file_name: str = 'json_upload', file_type: str = 'csv') -> Tuple[int, int, List[str], Optional[int], List[str]]:
    """
    Inserta los usuarios validados en la base de datos.
    
    Args:
        users_data: Lista de usuarios validados a insertar
        conn: Conexión a la base de datos
        cursor: Cursor de la conexión
        data_string: String original de los datos (para file_size)
        file_name: Nombre del archivo (default: 'json_upload')
        file_type: Tipo de archivo - debe ser 'csv' o 'xlsx' (default: 'csv')
        
    Returns:
        Tupla: (successful_records: int, failed_records: int, errors: list, upload_id: Optional[int], warnings: list)
    """
    successful_records = 0
    failed_records = 0
    processed_errors = []
    warnings = []
    
    # Validar file_type
    allowed_file_types = ['csv', 'xlsx', 'xls']
    if file_type.lower() not in allowed_file_types:
        file_type = 'csv'
    file_type = file_type[:10]
    
    # Procesar cada usuario
    for index, user in enumerate(users_data):
        row_num = index + 1
        
        try:
            # Separar nombre completo en name y last_name
            nombre_completo = user.get('nombre', '').strip()
            nombre_partes = nombre_completo.split(maxsplit=1)
            name = nombre_partes[0] if nombre_partes else nombre_completo
            last_name = nombre_partes[1] if len(nombre_partes) > 1 else ''
            
            # Si no hay last_name, usar el mismo name (requerido por schema)
            if not last_name:
                last_name = name
            
            # Obtener identification (requerido, usar email si no viene)
            identification = user.get('identification') or user.get('correo', '').split('@')[0]
            
            # Insertar usuario
            user_insert = """
                INSERT INTO users.users
                (name, last_name, password, identification, phone, email, active, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING user_id
            """
            cursor.execute(user_insert, (
                name,
                last_name,
                user['contraseña'],
                identification,
                user.get('phone'),
                user['correo'],
                True,  # active por defecto
                user['rol']
            ))
            
            user_result = cursor.fetchone()
            # RealDictCursor devuelve dict, cursor normal devuelve tuple
            if isinstance(user_result, dict):
                user_id = user_result.get('user_id')
            else:
                user_id = user_result[0] if user_result else None
            
            # Crear usuario en Cognito (Opción A: Cognito como fuente principal)
            try:
                username = get_username_from_email_or_identification(user['correo'], identification)
                group_name = map_role_to_cognito_group(user['rol'])
                
                # Cognito requiere contraseña en texto plano (Opción 1 implementada)
                password_for_cognito = user['contraseña']  # Ya viene en texto plano, validada
                
                cognito_success, cognito_user_id, cognito_error = create_user_in_cognito(
                    username=username,
                    email=user['correo'],
                    password=password_for_cognito,
                    group_name=group_name
                )
                
                if not cognito_success:
                    # Registrar error pero no bloquear la inserción en BD
                    print(f"⚠️  Advertencia: Usuario insertado en BD pero falló en Cognito: {cognito_error}")
                    warnings.append(f"Fila {row_num}: Usuario creado en BD pero no en Cognito - {cognito_error}")
                else:
                    print(f"✅ Usuario creado en Cognito: {username}")
            except Exception as cognito_ex:
                # Si falla Cognito, registrar pero no bloquear
                print(f"⚠️  Error creando usuario en Cognito: {str(cognito_ex)}")
                warnings.append(f"Fila {row_num}: Error creando en Cognito - {str(cognito_ex)}")
            
            successful_records += 1
            
        except Exception as e:
            error_msg = f"Fila {row_num}: Error al insertar usuario - {str(e)}"
            print(f"Error insertando usuario {row_num}: {str(e)}")
            processed_errors.append(error_msg)
            failed_records += 1
    
    return successful_records, failed_records, processed_errors, None, warnings

