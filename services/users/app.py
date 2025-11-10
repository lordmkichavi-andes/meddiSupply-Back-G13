from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import datetime
import logging
import json
import psycopg2.extras

from src.infrastructure.web.flask_user_routes import create_user_api_blueprint
from src.application.use_cases import GetClientUsersUseCase
from src.application.register_visit_usecase import RegisterVisitUseCase

from src.infrastructure.persistence.pg_user_repository import PgUserRepository
from src.infrastructure.persistence.db_connector import init_db_pool, get_connection, release_connection
from src.infrastructure.persistence.db_initializer import initialize_database
from config import Config
from src.services.storage_service import StorageService 
from src.services.recommendation_agent import RecommendationAgent 
from src.application.generate_recommendations_usecase import GenerateRecommendationsUseCase
from user_upload import validate_users_data, insert_users, validate_sellers_data, insert_sellers, validate_providers_data, insert_providers
from login_service import authenticate_user

load_dotenv()

logger = logging.getLogger(__name__)

datos_quemados = {
    "usuarios": [
        {
            "id": 1,
            "nombre": "Juan Pérez",
            "email": "juan.perez@email.com",
            "edad": 28,
            "ciudad": "Madrid"
        },
        {
            "id": 2,
            "nombre": "María García",
            "email": "maria.garcia@email.com",
            "edad": 32,
            "ciudad": "Barcelona"
        },
        {
            "id": 3,
            "nombre": "Carlos López",
            "email": "carlos.lopez@email.com",
            "edad": 25,
            "ciudad": "Valencia"
        }
    ],
    "productos": [
        {
            "id": 1,
            "nombre": "Laptop",
            "precio": 999.99,
            "categoria": "Electrónicos",
            "stock": 15
        },
        {
            "id": 2,
            "nombre": "Mouse",
            "precio": 25.50,
            "categoria": "Accesorios",
            "stock": 50
        },
        {
            "id": 3,
            "nombre": "Teclado",
            "precio": 75.00,
            "categoria": "Accesorios",
            "stock": 30
        }
    ],
    "estadisticas": {
        "total_usuarios": 3,
        "total_productos": 3,
        "ventas_mes_actual": 1250.50,
        "clientes_activos": 2
    }
}

def create_app():
    """Crea, configura y cablea la aplicación Flask siguiendo la Arquitectura Limpia."""
    
    app = Flask(__name__)
    app.config.from_object(Config)

    
    # --- INICIALIZACIÓN DE LA BASE DE DATOS (REQUISITO) ---
    try:
        print("🔌 Inicializando conexión a la base de datos...")
        init_db_pool()
        print("📊 Inicializando esquema de la base de datos...")
        initialize_database()
        print("✅ Base de datos inicializada correctamente")
    except Exception as e:
        print(f"❌ CRITICAL ERROR: Fallo al inicializar la BD. {e}")
        logger.exception("Fallo crítico al inicializar la BD.")
        raise
    
    # --- CABLEADO DE DEPENDENCIAS (Dependency Injection - DI) ---
    
    # 1. Infraestructura de Persistencia (Implementación real de PostgreSQL)
    user_repository = PgUserRepository()
    
    storage_service = StorageService() 

    get_client_users_use_case = GetClientUsersUseCase(
        user_repository=user_repository,
        storage_service=storage_service 
    )

    register_visit_use_case = RegisterVisitUseCase(
        user_repository=user_repository
    )
    
    # Configurar CORS
    CORS(app, resources={
        r"/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"]
        }
    })
    
    recommendation_agent = RecommendationAgent(
        user_repository=user_repository
    )
    generate_recommendations_uc = GenerateRecommendationsUseCase(
        recommendation_agent=recommendation_agent,
        user_repository=user_repository
    )

    # 3. Capa de Presentación (Web) - Arquitectura Limpia
    user_api_bp = create_user_api_blueprint(
        get_client_users_use_case,
        register_visit_use_case,
        generate_recommendations_uc
    )
    
    # --- REGISTRO DE RUTAS ---
    app.register_blueprint(user_api_bp, url_prefix='/users')
    
    # --- RUTAS LEGACY (Datos quemados) ---
    
    @app.route('/', methods=['GET'])
    def home():
        return jsonify({
            "mensaje": "🚀 Usuarios Service - Deploy Test en Develop",
            "version": "2.1.4",
            "build": "ci-cd-test-$(date +%Y%m%d-%H%M%S)",
            "endpoints_disponibles": [
                "GET / - Información del backend",
                "POST /datos - Obtener datos quemados",
                "POST /usuarios - Obtener usuarios",
                "POST /productos - Obtener productos",
                "GET /health - Health check para CI/CD",
                "GET /users/clients - Obtener usuarios CLIENT de la BD",
                "POST /users/visit - Registra la visita del vendedor",
                "POST /users/upload/validate - Validar usuarios CSV (HU107)",
                "POST /users/upload/insert - Insertar usuarios CSV (HU107)",
                "POST /users/sellers/upload/validate - Validar vendedores CSV",
                "POST /users/sellers/upload/insert - Insertar vendedores CSV",
                "POST /users/providers/upload/validate - Validar proveedores CSV",
                "POST /users/providers/upload/insert - Insertar proveedores CSV",
                "POST /users/login - Iniciar sesión (HU37)"
            ],
            "microservicio": "usuarios",
            "cluster": "microservices-cluster"
        })

    @app.route('/datos', methods=['POST'])
    def obtener_datos():
        """
        Endpoint POST que devuelve datos quemados
        """
        try:
            datos_request = request.get_json() if request.is_json else {}
            print(f"Petición recibida: {datos_request}")
            
            respuesta = {
                "success": True,
                "mensaje": "Datos obtenidos exitosamente",
                "timestamp": "2024-01-15T10:30:00Z",
                "datos": datos_quemados,
                "peticion_recibida": datos_request
            }
            
            return jsonify(respuesta), 200
            
        except Exception as e:
            logger.error("Error al procesar la petición /datos", exc_info=True)
            return jsonify({
                "success": False,
                "mensaje": "Error al procesar la petición",
                "error": str(e)
            }), 500

    @app.route('/usuarios', methods=['POST'])
    def obtener_usuarios():
        """
        Endpoint POST específico para obtener solo usuarios
        """
        try:
            datos_request = request.get_json() if request.is_json else {}
            
            respuesta = {
                "success": True,
                "mensaje": "Usuarios obtenidos exitosamente",
                "usuarios": datos_quemados["usuarios"],
                "total": len(datos_quemados["usuarios"])
            }
            
            return jsonify(respuesta), 200
            
        except Exception as e:
            logger.error("Error al obtener usuarios /usuarios", exc_info=True)
            return jsonify({
                "success": False,
                "mensaje": "Error al obtener usuarios",
                "error": str(e)
            }), 500

    @app.route('/productos', methods=['POST'])
    def obtener_productos():
        """
        Endpoint POST específico para obtener solo productos
        """
        try:
            datos_request = request.get_json() if request.is_json else {}
            
            respuesta = {
                "success": True,
                "mensaje": "Productos obtenidos exitosamente",
                "productos": datos_quemados["productos"],
                "total": len(datos_quemados["productos"])
            }
            
            return jsonify(respuesta), 200
            
        except Exception as e:
            logger.error("Error al obtener productos /productos", exc_info=True)
            return jsonify({
                "success": False,
                "mensaje": "Error al obtener productos",
                "error": str(e)
            }), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        """
        Endpoint de health check para CI/CD y monitoreo
        """
        try:
            return jsonify({
                "status": "healthy",
                "service": "usuarios",
                "version": "2.1.4",
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "uptime": "running",
                "checks": {
                    "database": "ok",
                    "memory": "ok",
                    "cpu": "ok"
                },
                "ci_cd": {
                    "pipeline": "active",
                    "last_deploy": "ci-cd-test",
                    "environment": "production-ready"
                }
            }), 200
            
        except Exception as e:
            logger.error("Error en health check", exc_info=True)
            return jsonify({
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }), 503

    @app.route('/users/debug/sequence', methods=['GET'])
    def debug_sequence():
        """
        Endpoint de diagnóstico para revisar el estado de la secuencia de user_id.
        Útil para diagnosticar problemas de sincronización.
        """
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            # 1. Obtener el máximo user_id en la tabla
            cursor.execute("SELECT COALESCE(MAX(user_id), 0) AS max_id FROM users.users")
            max_id_result = cursor.fetchone()
            max_id = max_id_result['max_id'] if isinstance(max_id_result, dict) else max_id_result[0]
            
            # 2. Obtener el valor actual de la secuencia (sin consumirlo)
            cursor.execute("SELECT last_value, is_called FROM users_users_user_id_seq")
            seq_result = cursor.fetchone()
            last_value = seq_result['last_value'] if isinstance(seq_result, dict) else seq_result[0]
            is_called = seq_result['is_called'] if isinstance(seq_result, dict) else seq_result[1]
            
            # 3. Calcular el próximo valor que usará la secuencia
            if is_called:
                next_value = last_value + 1
            else:
                next_value = last_value
            
            # 4. Intentar sincronizar la secuencia
            try:
                # setval(sequence, value, true): establece que el último valor usado fue 'value',
                # por lo que el próximo nextval() devolverá 'value + 1'
                cursor.execute("SELECT setval('users_users_user_id_seq', %s, true)", (max_id,))
                sync_success = True
                sync_message = f"Secuencia sincronizada a {max_id}, próximo valor será {max_id + 1}"
            except Exception as sync_error:
                sync_success = False
                sync_message = f"Error al sincronizar: {str(sync_error)}"
            
            # 5. Verificar el estado después de la sincronización
            cursor.execute("SELECT last_value, is_called FROM users_users_user_id_seq")
            seq_after_result = cursor.fetchone()
            last_value_after = seq_after_result['last_value'] if isinstance(seq_after_result, dict) else seq_after_result[0]
            is_called_after = seq_after_result['is_called'] if isinstance(seq_after_result, dict) else seq_after_result[1]
            
            if is_called_after:
                next_value_after = last_value_after + 1
            else:
                next_value_after = last_value_after
            
            # 6. Determinar si está sincronizado
            is_synced = (next_value_after == max_id + 1)
            
            release_connection(conn)
            
            return jsonify({
                "status": "ok",
                "sequence_info": {
                    "max_user_id_in_table": max_id,
                    "sequence_last_value": last_value,
                    "sequence_is_called": is_called,
                    "next_value_before_sync": next_value,
                    "next_value_after_sync": next_value_after,
                    "is_synced": is_synced,
                    "sync_success": sync_success,
                    "sync_message": sync_message
                },
                "diagnosis": {
                    "problem": "Secuencia desincronizada" if not is_synced else "Secuencia sincronizada correctamente",
                    "recommendation": f"El próximo user_id será {next_value_after}" if is_synced else f"La secuencia debería estar en {max_id + 1} pero está en {next_value_after}"
                },
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }), 200
            
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            return jsonify({
                "status": "error",
                "error": str(e),
                "traceback": error_trace,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }), 500

    # ==========================
    # HU107 - REGISTRO USUARIOS VÍA CSV
    # ==========================
    
    @app.route('/users/upload/validate', methods=['POST'])
    def validate_users_endpoint():
        """
        Endpoint para validar usuarios sin insertarlos en la base de datos (HU107).
        Solo realiza la validación y retorna el resultado.
        """
        print("=== INICIO VALIDACIÓN DE USUARIOS ===")
        
        try:
            # 1. Validar tamaño del archivo (máximo 5 MB)
            content_length = request.content_length
            if content_length and content_length > 5 * 1024 * 1024:  # 5 MB
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El archivo excede el tamaño permitido (máx. 5 MB).",
                    "total_records": 0,
                    "valid_records": 0,
                    "invalid_records": 0,
                    "errors": ["¡Ups! El archivo excede el tamaño permitido (máx. 5 MB)."],
                    "warnings": []
                }), 400
            
            # 2. Obtener y parsear datos del request
            data_string = request.get_data(as_text=True)

            if not data_string or data_string.strip() == '':
                return jsonify({
                    "success": False,
                    "message": "No se recibieron datos para procesar",
                    "total_records": 0,
                    "valid_records": 0,
                    "invalid_records": 0,
                    "errors": ["No se recibieron datos para procesar"],
                    "warnings": []
                }), 400

            print(f"Datos recibidos como string: {data_string[:200]}...")

            # Limpiar el string
            data_string = data_string.strip()

            # Intentar parsear como JSON
            try:
                users_data = json.loads(data_string)
            except json.JSONDecodeError as e:
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El formato del archivo no es válido",
                    "total_records": 0,
                    "valid_records": 0,
                    "invalid_records": 0,
                    "errors": ["¡Ups! El formato del archivo no es válido"],
                    "warnings": []
                }), 400

            print(f"Usuarios parseados: {len(users_data)}")

            # 3. Validar usuarios
            is_valid, errors, warnings, validated_users = validate_users_data(users_data)

            # Preparar respuesta
            valid_records = len(validated_users)
            invalid_records = len(users_data) - valid_records
            
            # Mensajes según HU107
            if not is_valid:
                if any("duplicados" in e.lower() for e in errors):
                    message = "¡Ups! Existen usuarios duplicados, revisa el archivo"
                else:
                    message = "¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente"
            else:
                message = f"Validación completada: {valid_records} usuarios válidos de {len(users_data)} totales"
            
            response_data = {
                "success": is_valid,
                "message": message,
                "total_records": len(users_data),
                "valid_records": valid_records,
                "invalid_records": invalid_records,
                "errors": errors,
                "warnings": warnings,
                "validated_users": validated_users if is_valid else []
            }
            
            return jsonify(response_data), 200
            
        except Exception as e:
            print(f"ERROR en validación: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                "success": False,
                "message": "¡Ups! Hubo un problema, intenta nuevamente en unos minutos",
                "total_records": len(users_data) if 'users_data' in locals() else 0,
                "valid_records": 0,
                "invalid_records": len(users_data) if 'users_data' in locals() else 0,
                "errors": [f"Error interno: {str(e)}"],
                "warnings": []
            }), 500

    @app.route('/users/upload/insert', methods=['POST'])
    def insert_users_endpoint():
        """
        Endpoint para insertar usuarios validados en la base de datos (HU107).
        Asume que los usuarios ya fueron validados previamente.
        """
        print("=== INICIO INSERCIÓN DE USUARIOS ===")
        conn = None
        cursor = None
        
        try:
            # 1. Validar tamaño del archivo (máximo 5 MB)
            content_length = request.content_length
            if content_length and content_length > 5 * 1024 * 1024:  # 5 MB
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El archivo excede el tamaño permitido (máx. 5 MB).",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["¡Ups! El archivo excede el tamaño permitido (máx. 5 MB)."],
                    "warnings": []
                }), 400
            
            # 2. Obtener y parsear datos del request
            data_string = request.get_data(as_text=True)

            if not data_string or data_string.strip() == '':
                return jsonify({
                    "success": False,
                    "message": "No se recibieron datos para procesar",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["No se recibieron datos para procesar"],
                    "warnings": []
                }), 400

            print(f"Datos recibidos como string: {data_string[:200]}...")

            # Limpiar el string
            data_string = data_string.strip()

            # Intentar parsear como JSON
            try:
                users_data = json.loads(data_string)
            except json.JSONDecodeError as e:
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El formato del archivo no es válido",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["¡Ups! El formato del archivo no es válido"],
                    "warnings": []
                }), 400

            print(f"Usuarios parseados para inserción: {len(users_data)}")

            # 3. Validación rápida básica (estructura mínima)
            if not isinstance(users_data, list) or not users_data:
                return jsonify({
                    "success": False,
                    "message": "Los datos deben ser un array de usuarios no vacío",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["Los datos deben ser un array de usuarios no vacío"],
                    "warnings": []
                }), 400
            
            # 4. Determinar file_name y file_type desde headers o usar defaults
            file_name = request.headers.get('X-File-Name')
            file_type = request.headers.get('X-File-Type', 'csv')
            
            # Validar que file_type sea uno de los valores permitidos
            allowed_file_types = ['csv', 'xlsx', 'xls', 'json']
            if file_type.lower() not in allowed_file_types:
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El formato del archivo no es válido",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["¡Ups! El formato del archivo no es válido"],
                    "warnings": []
                }), 400
            else:
                file_type = file_type.lower()
            
            # Si no hay file_name, usar uno basado en timestamp
            if not file_name:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                file_name = f'users_upload_{timestamp}'
            
            # 5. Conectar a la base de datos e insertar
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            print("Conexión a BD establecida")
            
            # Insertar usuarios
            successful_records, failed_records, processed_errors, upload_id, insert_warnings = insert_users(
                users_data, conn, cursor, data_string, file_name=file_name, file_type=file_type
            )
            
            # Commit de la transacción
            conn.commit()
            print(f"Transacción completada. Exitosos: {successful_records}, Fallidos: {failed_records}")

            # Determinar si fue exitoso
            success = failed_records == 0
            
            if success:
                message = "¡El archivo se ha cargado exitosamente!"
            else:
                message = "¡Ups! Hubo un problema, intenta nuevamente en unos minutos"
            
            return jsonify({
                "success": success,
                "message": message,
                "total_records": len(users_data),
                "successful_records": successful_records,
                "failed_records": failed_records,
                "errors": processed_errors,
                "warnings": insert_warnings
            }), 200 if success else 500
            
        except Exception as e:
            print(f"ERROR en inserción: {str(e)}")
            import traceback
            traceback.print_exc()
            
            if conn:
                conn.rollback()
            
            return jsonify({
                "success": False,
                "message": "¡Ups! Hubo un problema, intenta nuevamente en unos minutos",
                "total_records": len(users_data) if 'users_data' in locals() else 0,
                "successful_records": 0,
                "failed_records": len(users_data) if 'users_data' in locals() else 0,
                "errors": [f"Error interno: {str(e)}"],
                "warnings": []
            }), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                release_connection(conn)

    # ==========================
    # HU37 - INICIAR SESIÓN
    # ==========================
    
    @app.route('/users/login', methods=['POST'])
    def login_endpoint():
        """
        Endpoint para iniciar sesión (HU37).
        Autentica un usuario con correo y contraseña.
        """
        print("=== INICIO LOGIN ===")
        
        try:
            # 1. Obtener datos del request
            data = request.get_json()
            
            if not data:
                return jsonify({
                    "success": False,
                    "message": "Campo obligatorio",
                    "error": "No se recibieron datos"
                }), 400
            
            email = data.get('correo') or data.get('email')
            password = data.get('contraseña') or data.get('password')
            
            # 2. Autenticar usuario
            is_authenticated, user_data, error_message = authenticate_user(email, password)
            
            if not is_authenticated:
                return jsonify({
                    "success": False,
                    "message": error_message
                }), 401
            
            # 3. Login exitoso - Retornar datos del usuario y tokens
            response_data = {
                "success": True,
                "message": "Login exitoso",
                "user": {
                    "user_id": user_data['user_id'],
                    "name": user_data['name'],
                    "last_name": user_data['last_name'],
                    "email": user_data['email'],
                    "role": user_data['role'],
                    "identification": user_data.get('identification'),
                    "phone": user_data.get('phone')
                },
                "role": user_data['role'],
                "tokens": user_data.get('tokens', {})  # Tokens de Cognito
            }
            return jsonify(response_data), 200
            
        except Exception as e:
            print(f"ERROR en login: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                "success": False,
                "message": "¡Ups! Hubo un problema, intenta nuevamente en unos minutos"
            }), 500

    # ==========================
    # HU38 - CERRAR SESIÓN
    # ==========================
    @app.route('/users/logout', methods=['POST'])
    def logout_endpoint():
        """
        Cierre de sesión:
        - Preferente: recibe access_token y ejecuta global_sign_out.
        - Alternativa: recibe identification o correo y ejecuta admin_user_global_sign_out.
        """
        try:
            data = request.get_json(silent=True) or {}
            access_token = data.get('access_token')
            identification = data.get('identification') or data.get('identificacion')
            email = data.get('correo') or data.get('email')

            # 1) Si viene access_token, usar global_sign_out
            if access_token:
                from cognito_service import global_sign_out
                ok, err = global_sign_out(access_token)
                if not ok:
                    return jsonify({"success": False, "message": f"No se pudo cerrar sesión: {err}"}), 400
                return jsonify({"success": True, "message": "Sesión cerrada correctamente"}), 200

            # 2) Si no hay token, intentar por username (identification)
            from cognito_service import admin_global_sign_out
            username = None

            if identification:
                username = str(identification).strip()
            elif email:
                # Buscar identification en BD por correo
                try:
                    conn = get_connection()
                    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    cursor.execute(
                        "SELECT identification FROM users.users WHERE LOWER(email)=LOWER(%s)", (email.strip(),)
                    )
                    row = cursor.fetchone()
                    cursor.close(); release_connection(conn)
                    if row and row.get('identification'):
                        username = str(row['identification']).strip()
                except Exception:
                    try:
                        release_connection(conn)
                    except Exception:
                        pass

            if not username:
                return jsonify({"success": False, "message": "Campo obligatorio: access_token o identification/correo"}), 400

            ok, err = admin_global_sign_out(username)
            if not ok:
                return jsonify({"success": False, "message": f"No se pudo cerrar sesión: {err}"}), 400

            return jsonify({"success": True, "message": "Sesión cerrada correctamente"}), 200

        except Exception:
            return jsonify({"success": False, "message": "¡Ups! Hubo un problema, intenta nuevamente en unos minutos"}), 500
    
    # ==========================
    # REGISTRO DE VENDEDORES
    # ==========================
    
    @app.route('/users/sellers/upload/validate', methods=['POST'])
    def validate_sellers_endpoint():
        """
        Endpoint para validar vendedores sin insertarlos en la base de datos.
        Solo realiza la validación y retorna el resultado.
        """
        print("=== INICIO VALIDACIÓN DE VENDEDORES ===")
        
        try:
            # 1. Validar tamaño del archivo (máximo 5 MB)
            content_length = request.content_length
            if content_length and content_length > 5 * 1024 * 1024:  # 5 MB
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El archivo excede el tamaño permitido (máx. 5 MB).",
                    "total_records": 0,
                    "valid_records": 0,
                    "invalid_records": 0,
                    "errors": ["¡Ups! El archivo excede el tamaño permitido (máx. 5 MB)."],
                    "warnings": []
                }), 400
            
            # 2. Obtener y parsear datos del request
            data_string = request.get_data(as_text=True)

            if not data_string or data_string.strip() == '':
                return jsonify({
                    "success": False,
                    "message": "No se recibieron datos para procesar",
                    "total_records": 0,
                    "valid_records": 0,
                    "invalid_records": 0,
                    "errors": ["No se recibieron datos para procesar"],
                    "warnings": []
                }), 400

            print(f"Datos recibidos como string: {data_string[:200]}...")

            # Limpiar el string
            data_string = data_string.strip()

            # Intentar parsear como JSON
            try:
                sellers_data = json.loads(data_string)
            except json.JSONDecodeError as e:
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El formato del archivo no es válido",
                    "total_records": 0,
                    "valid_records": 0,
                    "invalid_records": 0,
                    "errors": ["¡Ups! El formato del archivo no es válido"],
                    "warnings": []
                }), 400

            print(f"Vendedores parseados: {len(sellers_data)}")

            # 3. Validar vendedores
            is_valid, errors, warnings, validated_sellers = validate_sellers_data(sellers_data)

            # Preparar respuesta
            valid_records = len(validated_sellers)
            invalid_records = len(sellers_data) - valid_records
            
            # Mensajes
            if not is_valid:
                if any("duplicados" in e.lower() for e in errors):
                    message = "¡Ups! Existen vendedores duplicados, revisa el archivo"
                else:
                    message = "¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente"
            else:
                message = f"Validación completada: {valid_records} vendedores válidos de {len(sellers_data)} totales"
            
            response_data = {
                "success": is_valid,
                "message": message,
                "total_records": len(sellers_data),
                "valid_records": valid_records,
                "invalid_records": invalid_records,
                "errors": errors,
                "warnings": warnings,
                "validated_sellers": validated_sellers if is_valid else []
            }
            
            return jsonify(response_data), 200
            
        except Exception as e:
            print(f"ERROR en validación: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                "success": False,
                "message": "¡Ups! Hubo un problema, intenta nuevamente en unos minutos",
                "total_records": len(sellers_data) if 'sellers_data' in locals() else 0,
                "valid_records": 0,
                "invalid_records": len(sellers_data) if 'sellers_data' in locals() else 0,
                "errors": [f"Error interno: {str(e)}"],
                "warnings": []
            }), 500

    @app.route('/users/sellers/upload/insert', methods=['POST'])
    def insert_sellers_endpoint():
        """
        Endpoint para insertar vendedores validados en la base de datos.
        Asume que los vendedores ya fueron validados previamente.
        Crea el usuario en users.users y el registro en users.sellers.
        """
        print("=== INICIO INSERCIÓN DE VENDEDORES ===")
        conn = None
        cursor = None
        
        try:
            # 1. Validar tamaño del archivo (máximo 5 MB)
            content_length = request.content_length
            if content_length and content_length > 5 * 1024 * 1024:  # 5 MB
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El archivo excede el tamaño permitido (máx. 5 MB).",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["¡Ups! El archivo excede el tamaño permitido (máx. 5 MB)."],
                    "warnings": []
                }), 400
            
            # 2. Obtener y parsear datos del request
            data_string = request.get_data(as_text=True)

            if not data_string or data_string.strip() == '':
                return jsonify({
                    "success": False,
                    "message": "No se recibieron datos para procesar",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["No se recibieron datos para procesar"],
                    "warnings": []
                }), 400

            print(f"Datos recibidos como string: {data_string[:200]}...")

            # Limpiar el string
            data_string = data_string.strip()

            # Intentar parsear como JSON
            try:
                sellers_data = json.loads(data_string)
            except json.JSONDecodeError as e:
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El formato del archivo no es válido",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["¡Ups! El formato del archivo no es válido"],
                    "warnings": []
                }), 400

            print(f"Vendedores parseados para inserción: {len(sellers_data)}")

            # 3. Validación rápida básica (estructura mínima)
            if not isinstance(sellers_data, list) or not sellers_data:
                return jsonify({
                    "success": False,
                    "message": "Los datos deben ser un array de vendedores no vacío",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["Los datos deben ser un array de vendedores no vacío"],
                    "warnings": []
                }), 400
            
            # 4. Determinar file_name y file_type desde headers o usar defaults
            file_name = request.headers.get('X-File-Name')
            file_type = request.headers.get('X-File-Type', 'csv')
            
            # Validar que file_type sea uno de los valores permitidos
            allowed_file_types = ['csv', 'xlsx', 'xls', 'json']
            if file_type.lower() not in allowed_file_types:
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El formato del archivo no es válido",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["¡Ups! El formato del archivo no es válido"],
                    "warnings": []
                }), 400
            else:
                file_type = file_type.lower()
            
            # Si no hay file_name, usar uno basado en timestamp
            if not file_name:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                file_name = f'sellers_upload_{timestamp}'
            
            # 5. Conectar a la base de datos e insertar
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            print("Conexión a BD establecida")
            
            # Insertar vendedores
            successful_records, failed_records, processed_errors, upload_id, insert_warnings = insert_sellers(
                sellers_data, conn, cursor, data_string, file_name=file_name, file_type=file_type
            )
            
            # Commit de la transacción
            conn.commit()
            print(f"Transacción completada. Exitosos: {successful_records}, Fallidos: {failed_records}")

            # Determinar si fue exitoso
            success = failed_records == 0
            
            if success:
                message = "¡El archivo se ha cargado exitosamente!"
            else:
                message = "¡Ups! Hubo un problema, intenta nuevamente en unos minutos"
            
            return jsonify({
                "success": success,
                "message": message,
                "total_records": len(sellers_data),
                "successful_records": successful_records,
                "failed_records": failed_records,
                "errors": processed_errors,
                "warnings": insert_warnings
            }), 200 if success else 500
            
        except Exception as e:
            print(f"ERROR en inserción: {str(e)}")
            import traceback
            traceback.print_exc()
            
            if conn:
                conn.rollback()
            
            return jsonify({
                "success": False,
                "message": "¡Ups! Hubo un problema, intenta nuevamente en unos minutos",
                "total_records": len(sellers_data) if 'sellers_data' in locals() else 0,
                "successful_records": 0,
                "failed_records": len(sellers_data) if 'sellers_data' in locals() else 0,
                "errors": [f"Error interno: {str(e)}"],
                "warnings": []
            }), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                release_connection(conn)

    @app.route('/users/providers/upload/validate', methods=['POST'])
    def validate_providers_endpoint():
        """
        Endpoint para validar proveedores antes de insertarlos.
        Valida formato, duplicados y estructura de datos.
        """
        print("=== INICIO VALIDACIÓN DE PROVEEDORES ===")
        
        try:
            # 1. Validar tamaño del archivo (máximo 5 MB)
            content_length = request.content_length
            if content_length and content_length > 5 * 1024 * 1024:  # 5 MB
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El archivo excede el tamaño permitido (máx. 5 MB).",
                    "total_records": 0,
                    "valid_records": 0,
                    "invalid_records": 0,
                    "errors": ["¡Ups! El archivo excede el tamaño permitido (máx. 5 MB)."],
                    "warnings": []
                }), 400
            
            # 2. Obtener y parsear datos del request
            data_string = request.get_data(as_text=True)

            if not data_string or data_string.strip() == '':
                return jsonify({
                    "success": False,
                    "message": "No se recibieron datos para procesar",
                    "total_records": 0,
                    "valid_records": 0,
                    "invalid_records": 0,
                    "errors": ["No se recibieron datos para procesar"],
                    "warnings": []
                }), 400

            print(f"Datos recibidos como string: {data_string[:200]}...")

            # Limpiar el string
            data_string = data_string.strip()

            # Intentar parsear como JSON
            try:
                providers_data = json.loads(data_string)
            except json.JSONDecodeError as e:
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El formato del archivo no es válido",
                    "total_records": 0,
                    "valid_records": 0,
                    "invalid_records": 0,
                    "errors": ["¡Ups! El formato del archivo no es válido"],
                    "warnings": []
                }), 400

            print(f"Proveedores parseados: {len(providers_data)}")

            # 3. Validar proveedores
            is_valid, errors, warnings, validated_providers = validate_providers_data(providers_data)

            # Preparar respuesta
            valid_records = len(validated_providers)
            invalid_records = len(providers_data) - valid_records
            
            # Mensajes
            if not is_valid:
                if any("duplicados" in e.lower() for e in errors):
                    message = "¡Ups! Existen proveedores duplicados, revisa el archivo"
                else:
                    message = "¡Ups! El archivo tiene errores de validación, revisa y sube nuevamente"
            else:
                message = f"Validación completada: {valid_records} proveedores válidos de {len(providers_data)} totales"
            
            response_data = {
                "success": is_valid,
                "message": message,
                "total_records": len(providers_data),
                "valid_records": valid_records,
                "invalid_records": invalid_records,
                "errors": errors,
                "warnings": warnings,
                "validated_providers": validated_providers if is_valid else []
            }
            
            return jsonify(response_data), 200
            
        except Exception as e:
            print(f"ERROR en validación: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return jsonify({
                "success": False,
                "message": "¡Ups! Hubo un problema, intenta nuevamente en unos minutos",
                "total_records": len(providers_data) if 'providers_data' in locals() else 0,
                "valid_records": 0,
                "invalid_records": len(providers_data) if 'providers_data' in locals() else 0,
                "errors": [f"Error interno: {str(e)}"],
                "warnings": []
            }), 500

    @app.route('/users/providers/upload/insert', methods=['POST'])
    def insert_providers_endpoint():
        """
        Endpoint para insertar proveedores validados en la base de datos.
        Asume que los proveedores ya fueron validados previamente.
        Crea el usuario en users.users, el registro en products.Providers y el registro en users.providers.
        """
        print("=== INICIO INSERCIÓN DE PROVEEDORES ===")
        conn = None
        cursor = None
        
        try:
            # 1. Validar tamaño del archivo (máximo 5 MB)
            content_length = request.content_length
            if content_length and content_length > 5 * 1024 * 1024:  # 5 MB
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El archivo excede el tamaño permitido (máx. 5 MB).",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["¡Ups! El archivo excede el tamaño permitido (máx. 5 MB)."],
                    "warnings": []
                }), 400
            
            # 2. Obtener y parsear datos del request
            data_string = request.get_data(as_text=True)

            if not data_string or data_string.strip() == '':
                return jsonify({
                    "success": False,
                    "message": "No se recibieron datos para procesar",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["No se recibieron datos para procesar"],
                    "warnings": []
                }), 400

            print(f"Datos recibidos como string: {data_string[:200]}...")

            # Limpiar el string
            data_string = data_string.strip()

            # Intentar parsear como JSON
            try:
                providers_data = json.loads(data_string)
            except json.JSONDecodeError as e:
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El formato del archivo no es válido",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["¡Ups! El formato del archivo no es válido"],
                    "warnings": []
                }), 400

            print(f"Proveedores parseados para inserción: {len(providers_data)}")

            # 3. Validación rápida básica (estructura mínima)
            if not isinstance(providers_data, list) or not providers_data:
                return jsonify({
                    "success": False,
                    "message": "Los datos deben ser un array de proveedores no vacío",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["Los datos deben ser un array de proveedores no vacío"],
                    "warnings": []
                }), 400
            
            # 4. Determinar file_name y file_type desde headers o usar defaults
            file_name = request.headers.get('X-File-Name')
            file_type = request.headers.get('X-File-Type', 'csv')
            
            # Validar que file_type sea uno de los valores permitidos
            allowed_file_types = ['csv', 'xlsx', 'xls', 'json']
            if file_type.lower() not in allowed_file_types:
                return jsonify({
                    "success": False,
                    "message": "¡Ups! El formato del archivo no es válido",
                    "total_records": 0,
                    "successful_records": 0,
                    "failed_records": 0,
                    "errors": ["¡Ups! El formato del archivo no es válido"],
                    "warnings": []
                }), 400
            else:
                file_type = file_type.lower()
            
            # Si no hay file_name, usar uno basado en timestamp
            if not file_name:
                timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                file_name = f'providers_upload_{timestamp}'
            
            # 5. Conectar a la base de datos e insertar
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            print("Conexión a BD establecida")
            
            # Insertar proveedores
            successful_records, failed_records, processed_errors, upload_id, insert_warnings = insert_providers(
                providers_data, conn, cursor, data_string, file_name=file_name, file_type=file_type
            )
            
            # Commit de la transacción
            conn.commit()
            print(f"Transacción completada. Exitosos: {successful_records}, Fallidos: {failed_records}")

            # Determinar si fue exitoso
            success = failed_records == 0
            
            if success:
                message = "¡El archivo se ha cargado exitosamente!"
            else:
                message = "¡Ups! Hubo un problema, intenta nuevamente en unos minutos"
            
            return jsonify({
                "success": success,
                "message": message,
                "total_records": len(providers_data),
                "successful_records": successful_records,
                "failed_records": failed_records,
                "errors": processed_errors,
                "warnings": insert_warnings
            }), 200 if success else 500
            
        except Exception as e:
            print(f"ERROR en inserción: {str(e)}")
            import traceback
            traceback.print_exc()
            
            if conn:
                conn.rollback()
            
            return jsonify({
                "success": False,
                "message": "¡Ups! Hubo un problema, intenta nuevamente en unos minutos",
                "total_records": len(providers_data) if 'providers_data' in locals() else 0,
                "successful_records": 0,
                "failed_records": len(providers_data) if 'providers_data' in locals() else 0,
                "errors": [f"Error interno: {str(e)}"],
                "warnings": []
            }), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                release_connection(conn)
    
    return app

app = create_app()

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', '8083'))
    print("🚀 Iniciando Usuarios Service - CI/CD Pipeline...")
    print("📡 Endpoints disponibles:")
    print("   GET  / - Información del backend")
    print("   POST /datos - Obtener todos los datos quemados")
    print("   POST /usuarios - Obtener usuarios")
    print("   POST /productos - Obtener productos")
    print("   GET  /health - Health check para CI/CD")
    print("   GET  /users/clients - Obtener usuarios CLIENT de BD")
    print("   POST /users/visits/<id>/evidences - Subir evidencias")
    print("   POST /users/upload/validate - Validar usuarios CSV (HU107)")
    print("   POST /users/upload/insert - Insertar usuarios CSV (HU107)")
    print("   POST /users/sellers/upload/validate - Validar vendedores CSV")
    print("   POST /users/sellers/upload/insert - Insertar vendedores CSV")
    print("   POST /users/providers/upload/validate - Validar proveedores CSV")
    print("   POST /users/providers/upload/insert - Insertar proveedores CSV")
    print("   POST /users/login - Iniciar sesión (HU37)")
    print(f"🌐 Servidor ejecutándose en: http://localhost:{port}")
    print("🔧 Versión: 2.1.4 - Proper ECS Deploy Test")
    app.run(host='0.0.0.0', port=port, debug=False)
