"""
🔐 Módulo de autorización para reportes de supervisor
=====================================================
Control de acceso granular para reportes de ventas por vendedor
"""

import jwt
import logging
from functools import wraps
from flask import request, jsonify
from datetime import datetime
import json

logger = logging.getLogger(__name__)

def require_supervisor_role(f):
    """
    Decorador que requiere rol de supervisor para generar reportes de ventas por vendedor.
    Solo usuarios con grupo 'admin' pueden acceder (equivalente a supervisor).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # 1. Obtener token del header Authorization
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                log_audit_event(
                    action='ACCESS_DENIED',
                    reason='Missing or invalid Authorization header',
                    user_id='unknown',
                    endpoint=request.endpoint,
                    ip_address=request.remote_addr
                )
                return jsonify({
                    'success': False,
                    'message': 'Token de autorización requerido',
                    'error_type': 'unauthorized'
                }), 401
            
            # 2. Extraer token JWT
            token = auth_header[7:]  # Remover 'Bearer '
            
            # 3. Decodificar token (sin verificar firma para pruebas)
            try:
                # Decodificar payload del JWT
                payload_part = token.split('.')[1]
                # Agregar padding si es necesario
                missing = (-len(payload_part)) % 4
                if missing:
                    payload_part += '=' * missing
                
                import base64
                payload = json.loads(base64.urlsafe_b64decode(payload_part))
                
            except Exception as e:
                log_audit_event(
                    action='ACCESS_DENIED',
                    reason=f'Invalid JWT token: {str(e)}',
                    user_id='unknown',
                    endpoint=request.endpoint,
                    ip_address=request.remote_addr
                )
                return jsonify({
                    'success': False,
                    'message': 'Token inválido',
                    'error_type': 'invalid_token'
                }), 401
            
            # 4. Verificar grupos de Cognito
            cognito_groups = payload.get('cognito:groups', [])
            user_id = payload.get('sub', 'unknown')
            
            # 5. Validar que el usuario tenga rol de supervisor (admin)
            if 'admin' not in cognito_groups:
                log_audit_event(
                    action='ACCESS_DENIED',
                    reason=f'User not in supervisor role. Groups: {cognito_groups}',
                    user_id=user_id,
                    endpoint=request.endpoint,
                    ip_address=request.remote_addr,
                    cognito_groups=cognito_groups
                )
                return jsonify({
                    'success': False,
                    'message': 'Acceso denegado: Solo supervisores pueden generar reportes de ventas por vendedor',
                    'error_type': 'insufficient_privileges'
                }), 403
            
            # 6. Log de acceso autorizado
            log_audit_event(
                action='ACCESS_GRANTED',
                reason='User has supervisor role (admin)',
                user_id=user_id,
                endpoint=request.endpoint,
                ip_address=request.remote_addr,
                cognito_groups=cognito_groups
            )
            
            # 7. Agregar información del usuario al contexto
            request.user_context = {
                'user_id': user_id,
                'cognito_groups': cognito_groups,
                'is_supervisor': True
            }
            
            return f(*args, **kwargs)
            
        except Exception as e:
            log_audit_event(
                action='ACCESS_ERROR',
                reason=f'Authorization error: {str(e)}',
                user_id='unknown',
                endpoint=request.endpoint,
                ip_address=request.remote_addr
            )
            return jsonify({
                'success': False,
                'message': 'Error de autorización',
                'error_type': 'authorization_error'
            }), 500
    
    return decorated_function

def log_audit_event(action, reason, user_id, endpoint, ip_address, cognito_groups=None):
    """
    Registra evento de auditoría para trazabilidad completa.
    Cumple con el ASR: "registrar el intento en logs de auditoría para trazabilidad"
    """
    audit_event = {
        'timestamp': datetime.now().isoformat(),
        'service': 'reports',
        'action': action,
        'reason': reason,
        'user_id': user_id,
        'endpoint': endpoint,
        'ip_address': ip_address,
        'cognito_groups': cognito_groups,
        'user_agent': request.headers.get('User-Agent', 'unknown'),
        'request_id': request.headers.get('X-Request-Id', 'unknown')
    }
    
    # Log estructurado para CloudWatch
    logger.info(f"AUDIT_EVENT: {json.dumps(audit_event)}")
    
    # Log detallado para debugging
    if action == 'ACCESS_DENIED':
        logger.warning(f"🚫 ACCESS DENIED - User: {user_id}, Endpoint: {endpoint}, Reason: {reason}")
    elif action == 'ACCESS_GRANTED':
        logger.info(f"✅ ACCESS GRANTED - User: {user_id}, Endpoint: {endpoint}")
    elif action == 'ACCESS_ERROR':
        logger.error(f"❌ ACCESS ERROR - User: {user_id}, Endpoint: {endpoint}, Error: {reason}")

def log_report_generation(user_id, vendor_id, period, success=True, error_message=None):
    """
    Registra la generación de reportes de ventas por vendedor.
    Cumple con el ASR: "registrar el intento en logs de auditoría para trazabilidad"
    """
    audit_event = {
        'timestamp': datetime.now().isoformat(),
        'service': 'reports',
        'action': 'REPORT_GENERATION',
        'user_id': user_id,
        'vendor_id': vendor_id,
        'period': period,
        'success': success,
        'error_message': error_message,
        'ip_address': request.remote_addr,
        'endpoint': '/reports/sales-report'
    }
    
    # Log estructurado para CloudWatch
    logger.info(f"REPORT_AUDIT: {json.dumps(audit_event)}")
    
    # Log detallado
    if success:
        logger.info(f"📊 REPORT GENERATED - User: {user_id}, Vendor: {vendor_id}, Period: {period}")
    else:
        logger.warning(f"📊 REPORT FAILED - User: {user_id}, Vendor: {vendor_id}, Period: {period}, Error: {error_message}")
