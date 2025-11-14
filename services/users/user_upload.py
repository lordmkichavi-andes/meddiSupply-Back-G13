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


def _sync_user_id_sequence(conn, cursor):
    """
    Sincroniza la secuencia de user_id con el máximo valor actual en la tabla.
    Esto previene errores de 'duplicate key' cuando la secuencia está desincronizada.
    """
    try:
        # Obtener el máximo user_id actual
        cursor.execute("SELECT COALESCE(MAX(user_id), 0) AS max_id FROM users.users")
        max_id_result = cursor.fetchone()
        
        # RealDictCursor devuelve dict, cursor normal devuelve tuple
        if isinstance(max_id_result, dict):
            max_id = max_id_result.get('max_id', 0)
        else:
            max_id = max_id_result[0] if max_id_result else 0
        
        # Sincronizar la secuencia
        # setval(sequence, value, true): establece que el último valor usado fue 'value',
        # por lo que el próximo nextval() devolverá 'value + 1'
        # Nota: El nombre de la secuencia es users_users_user_id_seq (con guion bajo, no punto)
        cursor.execute("SELECT setval('users_users_user_id_seq', %s, true)", (max_id,))
        print(f"✅ Secuencia de user_id sincronizada a {max_id}")
    except Exception as e:
        print(f"⚠️  Advertencia: No se pudo sincronizar la secuencia: {str(e)}")
        # No fallar si no se puede sincronizar, continuar con la inserción


def _sync_seller_id_sequence(conn, cursor):
    """
    Sincroniza la secuencia de seller_id con el máximo valor actual en la tabla.
    Esto previene errores de 'duplicate key' cuando la secuencia está desincronizada.
    """
    try:
        # Obtener el máximo seller_id actual
        cursor.execute("SELECT COALESCE(MAX(seller_id), 0) AS max_id FROM users.sellers")
        max_id_result = cursor.fetchone()
        
        if isinstance(max_id_result, dict):
            max_id = max_id_result.get('max_id', 0)
        else:
            max_id = max_id_result[0] if max_id_result else 0
        
        # Sincronizar la secuencia
        # Nota: El nombre real en producción es users.sellers_seller_id_seq (con punto)
        # Probamos sin ::regclass, usando el nombre completo directamente
        cursor.execute("SELECT setval(%s, %s, true)", ('users.sellers_seller_id_seq', max_id))
        print(f"✅ Secuencia de seller_id sincronizada a {max_id}")
    except Exception as e:
        print(f"⚠️  Advertencia: No se pudo sincronizar la secuencia de seller_id: {str(e)}")


def _sync_provider_id_sequence(conn, cursor):
    """
    Sincroniza la secuencia de provider_id con el máximo valor actual en la tabla.
    Esto previene errores de 'duplicate key' cuando la secuencia está desincronizada.
    """
    try:
        # Obtener el máximo provider_id actual
        cursor.execute("SELECT COALESCE(MAX(provider_id), 0) AS max_id FROM products.providers")
        max_id_result = cursor.fetchone()
        
        if isinstance(max_id_result, dict):
            max_id = max_id_result.get('max_id', 0)
        else:
            max_id = max_id_result[0] if max_id_result else 0
        
        # Sincronizar la secuencia
        # Nota: El nombre real en producción es products.providers_provider_id_seq (con punto)
        # Probamos sin ::regclass, usando el nombre completo directamente
        cursor.execute("SELECT setval(%s, %s, true)", ('products.providers_provider_id_seq', max_id))
        print(f"✅ Secuencia de provider_id sincronizada a {max_id}")
    except Exception as e:
        print(f"⚠️  Advertencia: No se pudo sincronizar la secuencia de provider_id: {str(e)}")


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
    allowed_file_types = ['csv', 'xlsx', 'xls', 'json']
    if file_type.lower() not in allowed_file_types:
        file_type = 'csv'
    file_type = file_type[:10]
    
    # Sincronizar secuencia de user_id antes de insertar
    _sync_user_id_sequence(conn, cursor)
    
    # Procesar cada usuario con SAVEPOINT para permitir inserción parcial
    for index, user in enumerate(users_data):
        row_num = index + 1
        savepoint_name = f"sp_user_{index}"
        
        try:
            # Crear SAVEPOINT para esta inserción individual
            cursor.execute(f"SAVEPOINT {savepoint_name}")
            
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
            
            # Liberar SAVEPOINT si todo salió bien
            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            successful_records += 1
            
        except Exception as e:
            # En caso de error, hacer ROLLBACK al SAVEPOINT para continuar con el siguiente usuario
            try:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            except Exception as rollback_error:
                # Si el savepoint no existe o hay otro error, continuar de todas formas
                print(f"⚠️  Advertencia: No se pudo hacer rollback al savepoint: {str(rollback_error)}")
            
            error_msg = f"Fila {row_num}: Error al insertar usuario - {str(e)}"
            print(f"Error insertando usuario {row_num}: {str(e)}")
            processed_errors.append(error_msg)
            failed_records += 1
    
    return successful_records, failed_records, processed_errors, None, warnings


def validate_sellers_data(sellers_data: List[Dict[str, Any]]) -> Tuple[bool, List[str], List[str], List[Dict[str, Any]]]:
    """
    Valida los vendedores antes de insertarlos en la base de datos.
    Similar a validate_users_data pero incluye validación de zona.
    
    Args:
        sellers_data: Lista de diccionarios con vendedores a validar
        
    Returns:
        Tupla: (is_valid: bool, errors: list, warnings: list, validated_sellers: list)
    """
    errors = []
    warnings = []
    validated_sellers = []
    
    # Validar que sea una lista y no esté vacía
    if not isinstance(sellers_data, list):
        errors.append("Los datos deben ser un array de vendedores")
        return False, errors, warnings, validated_sellers
    
    if not sellers_data:
        errors.append("No se recibieron vendedores para procesar")
        return False, errors, warnings, validated_sellers
    
    # Validar correos e identificaciones duplicadas en el archivo
    emails_in_file = {}
    identifications_in_file = {}
    for index, seller in enumerate(sellers_data):
        if isinstance(seller, dict):
            # Validar correo duplicado
            if 'correo' in seller:
                email = str(seller['correo']).strip().lower()
                if email in emails_in_file:
                    errors.append(f"¡Ups! Existen vendedores duplicados, revisa el archivo")
                    return False, errors, warnings, validated_sellers
                emails_in_file[email] = index + 1
            
            # Validar identification duplicada
            identification = seller.get('identificacion') or seller.get('identification')
            if identification:
                identification = str(identification).strip()
                if identification in identifications_in_file:
                    errors.append(f"¡Ups! Existen vendedores duplicados, revisa el archivo")
                    return False, errors, warnings, validated_sellers
                identifications_in_file[identification] = index + 1
    
    # Validar cada vendedor
    for index, seller in enumerate(sellers_data):
        row_num = index + 1
        
        # Verificar que sea un diccionario
        if not isinstance(seller, dict):
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        user_errors = []
        
        # Campos requeridos: nombre, apellido, correo, identificacion, telefono, zona, contraseña
        required_fields = ['nombre', 'apellido', 'correo', 'identificacion', 'telefono', 'zona', 'contraseña']
        for field in required_fields:
            if field not in seller or seller[field] is None or str(seller[field]).strip() == '':
                user_errors.append(f"Campo obligatorio faltante: {field}")
        
        if user_errors:
            errors.extend(user_errors)
            continue
        
        # Validar formato de correo
        email = str(seller['correo']).strip().lower()
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        # Validar fortaleza de contraseña
        password = str(seller['contraseña']).strip()
        is_valid_password, password_error = validate_password_strength(password)
        if not is_valid_password:
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        # Validar zona (no vacía)
        zona = str(seller['zona']).strip()
        if not zona:
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        # Si no hay errores, agregar el vendedor a la lista de validados
        validated_seller = {
            'nombre': str(seller['nombre']).strip(),
            'apellido': str(seller['apellido']).strip(),
            'correo': email,
            'identificacion': str(seller['identificacion']).strip(),
            'telefono': str(seller['telefono']).strip(),
            'zona': zona,
            'contraseña': password,
            'rol': 'SELLER'  # Siempre SELLER para vendedores
        }
        validated_sellers.append(validated_seller)
    
    # Validar correos e identificaciones duplicadas en la base de datos
    if validated_sellers:
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # 1. Validar correos duplicados
            emails_to_check = [s['correo'] for s in validated_sellers]
            if emails_to_check:
                placeholders = ','.join(['%s'] * len(emails_to_check))
                cursor.execute(
                    f"SELECT user_id, email FROM users.users WHERE LOWER(email) IN ({placeholders})",
                    emails_to_check
                )
                existing_emails = cursor.fetchall()
                
                if existing_emails:
                    errors.append("¡Ups! Existen vendedores duplicados, revisa el archivo")
                    validated_sellers = []
            
            # 2. Validar identificaciones duplicadas (solo si no hay error de correos)
            if not errors:
                identifications_to_check = [s['identificacion'] for s in validated_sellers]
                if identifications_to_check:
                    placeholders = ','.join(['%s'] * len(identifications_to_check))
                    cursor.execute(
                        f"SELECT user_id, identification FROM users.users WHERE identification IN ({placeholders})",
                        identifications_to_check
                    )
                    existing_identifications = cursor.fetchall()
                    
                    if existing_identifications:
                        errors.append("¡Ups! Existen vendedores duplicados, revisa el archivo")
                        validated_sellers = []
            
            cursor.close()
            release_connection(conn)
        except Exception as db_error:
            print(f"Error validando en la base de datos: {str(db_error)}")
            errors.append("¡Ups! Hubo un problema, intenta nuevamente en unos minutos")
    
    is_valid = len(errors) == 0 and len(validated_sellers) > 0
    return is_valid, errors, warnings, validated_sellers


def insert_sellers(sellers_data: List[Dict[str, Any]], conn, cursor, data_string: str, file_name: str = 'json_upload', file_type: str = 'csv') -> Tuple[int, int, List[str], Optional[int], List[str]]:
    """
    Inserta los vendedores validados en la base de datos.
    Crea el usuario en users.users y el registro en users.sellers.
    
    Args:
        sellers_data: Lista de vendedores validados a insertar
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
    allowed_file_types = ['csv', 'xlsx', 'xls', 'json']
    if file_type.lower() not in allowed_file_types:
        file_type = 'csv'
    file_type = file_type[:10]
    
    # Sincronizar secuencias antes de insertar
    _sync_user_id_sequence(conn, cursor)
    _sync_seller_id_sequence(conn, cursor)
    # Hacer commit de la sincronización para que se persista antes de insertar
    conn.commit()
    
    # Procesar cada vendedor con SAVEPOINT para permitir inserción parcial
    for index, seller in enumerate(sellers_data):
        row_num = index + 1
        savepoint_name = f"sp_seller_{index}"
        
        try:
            # Crear SAVEPOINT para esta inserción individual
            cursor.execute(f"SAVEPOINT {savepoint_name}")
            
            name = str(seller['nombre']).strip()
            last_name = str(seller['apellido']).strip()
            identification = str(seller['identificacion']).strip()
            zona = str(seller['zona']).strip()
            
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
                seller['contraseña'],
                identification,
                seller.get('telefono'),
                seller['correo'],
                True,  # active por defecto
                'SELLER'  # Siempre SELLER
            ))
            
            user_result = cursor.fetchone()
            # RealDictCursor devuelve dict, cursor normal devuelve tuple
            if isinstance(user_result, dict):
                user_id = user_result.get('user_id')
            else:
                user_id = user_result[0] if user_result else None
            
            if not user_id:
                raise Exception("No se pudo obtener user_id después de insertar usuario")
            
            # Insertar en users.sellers
            seller_insert = """
                INSERT INTO users.sellers (user_id, zone)
                VALUES (%s, %s)
                RETURNING seller_id
            """
            cursor.execute(seller_insert, (user_id, zona))
            
            seller_result = cursor.fetchone()
            if isinstance(seller_result, dict):
                seller_id = seller_result.get('seller_id')
            else:
                seller_id = seller_result[0] if seller_result else None
            
            if not seller_id:
                raise Exception("No se pudo obtener seller_id después de insertar vendedor")
            
            # Crear usuario en Cognito
            try:
                username = get_username_from_email_or_identification(seller['correo'], identification)
                group_name = map_role_to_cognito_group('SELLER')  # Siempre 'ventas' para vendedores
                
                password_for_cognito = seller['contraseña']
                
                cognito_success, cognito_user_id, cognito_error = create_user_in_cognito(
                    username=username,
                    email=seller['correo'],
                    password=password_for_cognito,
                    group_name=group_name
                )
                
                if not cognito_success:
                    print(f"⚠️  Advertencia: Vendedor insertado en BD pero falló en Cognito: {cognito_error}")
                    warnings.append(f"Fila {row_num}: Vendedor creado en BD pero no en Cognito - {cognito_error}")
                else:
                    print(f"✅ Vendedor creado en Cognito: {username}")
            except Exception as cognito_ex:
                print(f"⚠️  Error creando vendedor en Cognito: {str(cognito_ex)}")
                warnings.append(f"Fila {row_num}: Error creando en Cognito - {str(cognito_ex)}")
            
            # Liberar SAVEPOINT si todo salió bien
            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            successful_records += 1
            print(f"✅ Vendedor insertado: {name} {last_name} (user_id: {user_id}, seller_id: {seller_id}, zona: {zona})")
            
        except Exception as e:
            # En caso de error, hacer ROLLBACK al SAVEPOINT para continuar con el siguiente vendedor
            try:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            except Exception as rollback_error:
                print(f"⚠️  Advertencia: No se pudo hacer rollback al savepoint: {str(rollback_error)}")
            
            error_msg = f"Fila {row_num}: Error al insertar vendedor - {str(e)}"
            print(f"Error insertando vendedor {row_num}: {str(e)}")
            processed_errors.append(error_msg)
            failed_records += 1
    
    return successful_records, failed_records, processed_errors, None, warnings


def validate_providers_data(providers_data: List[Dict[str, Any]]) -> Tuple[bool, List[str], List[str], List[Dict[str, Any]]]:
    """
    Valida los proveedores antes de insertarlos en la base de datos.
    Similar a validate_sellers_data pero incluye validación de nombre_empresa.
    
    Args:
        providers_data: Lista de diccionarios con proveedores a validar
        
    Returns:
        Tupla: (is_valid: bool, errors: list, warnings: list, validated_providers: list)
    """
    errors = []
    warnings = []
    validated_providers = []
    
    # Validar que sea una lista y no esté vacía
    if not isinstance(providers_data, list):
        errors.append("Los datos deben ser un array de proveedores")
        return False, errors, warnings, validated_providers
    
    if not providers_data:
        errors.append("No se recibieron proveedores para procesar")
        return False, errors, warnings, validated_providers
    
    # Validar correos e identificaciones duplicadas en el archivo
    emails_in_file = {}
    identifications_in_file = {}
    for index, provider in enumerate(providers_data):
        if isinstance(provider, dict):
            # Validar correo duplicado
            if 'correo' in provider:
                email = str(provider['correo']).strip().lower()
                if email in emails_in_file:
                    errors.append(f"¡Ups! Existen proveedores duplicados, revisa el archivo")
                    return False, errors, warnings, validated_providers
                emails_in_file[email] = index + 1
            
            # Validar identification duplicada
            identification = provider.get('identificacion') or provider.get('identification')
            if identification:
                identification = str(identification).strip()
                if identification in identifications_in_file:
                    errors.append(f"¡Ups! Existen proveedores duplicados, revisa el archivo")
                    return False, errors, warnings, validated_providers
                identifications_in_file[identification] = index + 1
    
    # Validar cada proveedor
    for index, provider in enumerate(providers_data):
        row_num = index + 1
        
        # Verificar que sea un diccionario
        if not isinstance(provider, dict):
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        user_errors = []
        
        # Campos requeridos: nombre, apellido, correo, identificacion, telefono, nombre_empresa, contraseña
        required_fields = ['nombre', 'apellido', 'correo', 'identificacion', 'telefono', 'nombre_empresa', 'contraseña']
        for field in required_fields:
            if field not in provider or provider[field] is None or str(provider[field]).strip() == '':
                user_errors.append(f"Campo obligatorio faltante: {field}")
        
        if user_errors:
            errors.extend(user_errors)
            continue
        
        # Validar formato de correo
        email = str(provider['correo']).strip().lower()
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(email):
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        # Validar fortaleza de contraseña
        password = str(provider['contraseña']).strip()
        is_valid_password, password_error = validate_password_strength(password)
        if not is_valid_password:
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        # Validar nombre_empresa (no vacío)
        company_name = str(provider['nombre_empresa']).strip()
        if not company_name:
            errors.append("¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente")
            continue
        
        # Si no hay errores, agregar el proveedor a la lista de validados
        validated_provider = {
            'nombre': str(provider['nombre']).strip(),
            'apellido': str(provider['apellido']).strip(),
            'correo': email,
            'identificacion': str(provider['identificacion']).strip(),
            'telefono': str(provider['telefono']).strip(),
            'nombre_empresa': company_name,
            'contraseña': password,
            'rol': 'PROVIDER'  # Siempre PROVIDER para proveedores
        }
        validated_providers.append(validated_provider)
    
    # Validar correos e identificaciones duplicadas en la base de datos
    if validated_providers:
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # 1. Validar correos duplicados
            emails_to_check = [p['correo'] for p in validated_providers]
            if emails_to_check:
                placeholders = ','.join(['%s'] * len(emails_to_check))
                cursor.execute(
                    f"SELECT user_id, email FROM users.users WHERE LOWER(email) IN ({placeholders})",
                    emails_to_check
                )
                existing_emails = cursor.fetchall()
                
                if existing_emails:
                    errors.append("¡Ups! Existen proveedores duplicados, revisa el archivo")
                    validated_providers = []
            
            # 2. Validar identificaciones duplicadas (solo si no hay error de correos)
            if not errors:
                identifications_to_check = [p['identificacion'] for p in validated_providers]
                if identifications_to_check:
                    placeholders = ','.join(['%s'] * len(identifications_to_check))
                    cursor.execute(
                        f"SELECT user_id, identification FROM users.users WHERE identification IN ({placeholders})",
                        identifications_to_check
                    )
                    existing_identifications = cursor.fetchall()
                    
                    if existing_identifications:
                        errors.append("¡Ups! Existen proveedores duplicados, revisa el archivo")
                        validated_providers = []
            
            cursor.close()
            release_connection(conn)
        except Exception as db_error:
            print(f"Error validando en la base de datos: {str(db_error)}")
            errors.append("¡Ups! Hubo un problema, intenta nuevamente en unos minutos")
    
    is_valid = len(errors) == 0 and len(validated_providers) > 0
    return is_valid, errors, warnings, validated_providers


def insert_providers(providers_data: List[Dict[str, Any]], conn, cursor, data_string: str, file_name: str = 'json_upload', file_type: str = 'csv') -> Tuple[int, int, List[str], Optional[int], List[str]]:
    """
    Inserta los proveedores validados en la base de datos.
    Crea el usuario en users.users y el registro en products.Providers (empresa proveedora).
    
    Args:
        providers_data: Lista de proveedores validados a insertar
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
    allowed_file_types = ['csv', 'xlsx', 'xls', 'json']
    if file_type.lower() not in allowed_file_types:
        file_type = 'csv'
    file_type = file_type[:10]
    
    # Sincronizar secuencias antes de insertar
    _sync_user_id_sequence(conn, cursor)
    _sync_provider_id_sequence(conn, cursor)
    # Hacer commit de la sincronización para que se persista antes de insertar
    conn.commit()
    
    # Procesar cada proveedor con SAVEPOINT para permitir inserción parcial
    for index, provider in enumerate(providers_data):
        row_num = index + 1
        savepoint_name = f"sp_provider_{index}"
        
        try:
            # Crear SAVEPOINT para esta inserción individual
            cursor.execute(f"SAVEPOINT {savepoint_name}")
            
            name = str(provider['nombre']).strip()
            last_name = str(provider['apellido']).strip()
            identification = str(provider['identificacion']).strip()
            company_name = str(provider['nombre_empresa']).strip()
            
            # 1. Insertar usuario
            user_insert = """
                INSERT INTO users.users
                (name, last_name, password, identification, phone, email, active, role)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING user_id
            """
            cursor.execute(user_insert, (
                name,
                last_name,
                provider['contraseña'],
                identification,
                provider.get('telefono'),
                provider['correo'],
                True,  # active por defecto
                'PROVIDER'  # Siempre PROVIDER
            ))
            
            user_result = cursor.fetchone()
            # RealDictCursor devuelve dict, cursor normal devuelve tuple
            if isinstance(user_result, dict):
                user_id = user_result.get('user_id')
            else:
                user_id = user_result[0] if user_result else None
            
            if not user_id:
                raise Exception("No se pudo obtener user_id después de insertar usuario")
            
            # 2. Insertar o verificar existencia en products.Providers (nombre de la empresa)
            # Primero verificamos si la empresa proveedora ya existe
            check_provider = """
                SELECT provider_id FROM products.providers 
                WHERE LOWER(name) = LOWER(%s)
                LIMIT 1
            """
            cursor.execute(check_provider, (company_name,))
            existing_provider = cursor.fetchone()
            
            if existing_provider:
                # Si ya existe, usamos el provider_id existente
                if isinstance(existing_provider, dict):
                    company_provider_id = existing_provider.get('provider_id')
                else:
                    company_provider_id = existing_provider[0] if existing_provider else None
                print(f"✅ Empresa proveedora ya existe: {company_name} (provider_id: {company_provider_id})")
            else:
                # Si no existe, la insertamos
                provider_company_insert = """
                    INSERT INTO products.providers (name)
                    VALUES (%s)
                    RETURNING provider_id
                """
                cursor.execute(provider_company_insert, (company_name,))
                
                provider_company_result = cursor.fetchone()
                if isinstance(provider_company_result, dict):
                    company_provider_id = provider_company_result.get('provider_id')
                else:
                    company_provider_id = provider_company_result[0] if provider_company_result else None
                
                if not company_provider_id:
                    raise Exception("No se pudo obtener provider_id después de insertar en products.providers")
                print(f"✅ Empresa proveedora creada: {company_name} (provider_id: {company_provider_id})")
            
            # 3. Crear usuario en Cognito
            try:
                username = get_username_from_email_or_identification(provider['correo'], identification)
                group_name = map_role_to_cognito_group('PROVIDER')  # Siempre 'compras' para proveedores
                
                password_for_cognito = provider['contraseña']
                
                cognito_success, cognito_user_id, cognito_error = create_user_in_cognito(
                    username=username,
                    email=provider['correo'],
                    password=password_for_cognito,
                    group_name=group_name
                )
                
                if not cognito_success:
                    print(f"⚠️  Advertencia: Proveedor insertado en BD pero falló en Cognito: {cognito_error}")
                    warnings.append(f"Fila {row_num}: Proveedor creado en BD pero no en Cognito - {cognito_error}")
                else:
                    print(f"✅ Proveedor creado en Cognito: {username}")
            except Exception as cognito_ex:
                print(f"⚠️  Error creando proveedor en Cognito: {str(cognito_ex)}")
                warnings.append(f"Fila {row_num}: Error creando en Cognito - {str(cognito_ex)}")
            
            # Liberar SAVEPOINT si todo salió bien
            cursor.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            successful_records += 1
            print(f"✅ Proveedor insertado: {name} {last_name} (user_id: {user_id}, empresa_provider_id: {company_provider_id}, empresa: {company_name})")
            
        except Exception as e:
            # En caso de error, hacer ROLLBACK al SAVEPOINT para continuar con el siguiente proveedor
            try:
                cursor.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
            except Exception as rollback_error:
                print(f"⚠️  Advertencia: No se pudo hacer rollback al savepoint: {str(rollback_error)}")
            
            error_msg = f"Fila {row_num}: Error al insertar proveedor - {str(e)}"
            print(f"Error insertando proveedor {row_num}: {str(e)}")
            processed_errors.append(error_msg)
            failed_records += 1
    
    return successful_records, failed_records, processed_errors, None, warnings

