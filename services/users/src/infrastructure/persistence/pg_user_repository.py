from typing import List, Any, Dict, Optional
from src.domain.interfaces import UserRepository
from src.domain.entities import Client
from .db_connector import get_connection, release_connection
import psycopg2
import sys
import psycopg2.extras

class PgUserRepository(UserRepository):
    """
    Implementación concreta que se conecta a PostgreSQL
    para obtener los datos de usuarios.
    """

    def get_users_by_role(self, role: str) -> List[Client]:
        """
        Recupera usuarios de la base de datos filtrados por rol.
        """
        conn = None
        users = []
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Consulta para obtener usuarios CLIENT con sus atributos específicos
            query = """
             SELECT
                    u.user_id,
                    c.client_id,
                    u.name,
                    u.last_name,
                    u.password,
                    u.identification,
                    u.phone,
                    u.role,
                    c.nit,
                    c.balance,
                    c.name AS client_name,
                    c.address,
                    c.latitude,
                    c.longitude
                FROM users.Users u
                INNER JOIN users.Clients c ON u.user_id = c.user_id
                WHERE u.role IN (%s)
                ORDER BY u.name ASC;
            """

            # Ejecutamos la consulta
            cursor.execute(query, (role,))

            for row in cursor.fetchall():
                (
                    user_id,
                    client_id,
                    name,
                    last_name,
                    password,
                    identification,
                    phone,
                    role_value,
                    nit,
                    balance,
                    client_name,
                    address,
                    latitude,
                    longitude
                ) = row

                # Mapeo a la entidad del dominio
                users.append(Client(
                    user_id=user_id,
                    client_id=client_id,
                    name=name,
                    last_name=last_name,
                    password=password,
                    identification=identification,
                    phone=phone,
                    role_value=role_value,
                    nit=nit,
                    balance=balance,
                    perfil=client_name,
                    address = address,
                    latitude=latitude,
                    longitude=longitude
                ))

            return users

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al recuperar usuarios: {e}")
            raise Exception("Database error during user retrieval.")
        finally:
            if conn:
                release_connection(conn)

    def get_users_by_seller(self, seller_id: str) -> List[Client]:
        """
        Recupera usuarios de la base de datos filtrados por rol.
        """
        conn = None
        users = []
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Consulta para obtener usuarios CLIENT con sus atributos específicos
            query = """
                SELECT
                   u.user_id,
                   c.client_id,           -- Agregamos el ID del cliente
                   u.name,
                   u.last_name,
                   u.password,            -- Considera si realmente necesitas la contraseña en esta consulta
                   u.identification,
                   u.phone,
                   u.role,
                   c.name AS client_name,
                   c.nit,
                   c.balance,
                   c.address,
                   c.latitude,
                   c.longitude
               FROM users.Users u
               INNER JOIN users.Clients c ON u.user_id = c.user_id
               -- Unimos con la tabla Seller para filtrar por el vendedor
               INNER JOIN users.sellers s ON c.seller_id = s.seller_id
               -- El filtro ahora busca por el ID del vendedor, no por el rol.
               WHERE s.seller_id = %s
               ORDER BY u.name ASC;
               """

            # Ejecutamos la consulta
            cursor.execute(query, (seller_id,))

            for row in cursor.fetchall():
                (
                    user_id,
                    client_id,
                    name,
                    last_name,
                    password,
                    identification,
                    phone,
                    role_value,
                    client_name,
                    nit,
                    balance,
                    address,
                    latitude,
                    longitude
                ) = row

                # Mapeo a la entidad del dominio
                users.append(Client(
                    user_id=user_id,
                    client_id=client_id,
                    name=name,
                    last_name=last_name,
                    password=password,
                    identification=identification,
                    phone=phone,
                    role_value=role_value,
                    nit=nit,
                    balance=balance,
                    perfil=client_name,
                    address=address,
                    latitude=latitude,
                    longitude=longitude
                ))

            return users

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al recuperar usuarios: {e}")
            raise Exception("Database error during user retrieval.")
        finally:
            if conn:
                release_connection(conn)

    def db_get_client_data(self, client_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene el perfil enriquecido del cliente (Users, Clients, Sellers) 
        en formato de diccionario para el motor de recomendaciones.
        """
        conn = None
        try:
            conn = get_connection()
            # Usamos DictCursor para retornar un diccionario por columna, que es 
            # lo que se espera para el perfil enriquecido de recomendaciones.
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            query = """
            SELECT
                c.client_id, 
                u.name AS user_name, 
                u.last_name, 
                u.email,
                c.balance, 
                c.address, 
                c.latitude, 
                c.longitude,
                s.zone AS seller_zone  
            FROM
                users.Clients c
            JOIN users.Users u ON c.user_id = u.user_id
            LEFT JOIN users.sellers s ON c.seller_id = s.seller_id
            WHERE c.client_id = %s;
            """

            # Ejecutamos la consulta
            cursor.execute(query, (client_id,))
            result = cursor.fetchone()
            
            if result:
                # Convertimos el DictRow de psycopg2 a un dict estándar de Python
                return dict(result)
            else:
                return None

        except psycopg2.Error as e:
            # Capturamos errores de la base de datos
            print(f"ERROR de base de datos al obtener perfil del cliente {client_id}: {e}")
            raise Exception("Database error during client profile retrieval.")
        except Exception as e:
            # Capturamos cualquier otro error inesperado (p. ej., conexión)
            print(f"ERROR INESPERADO AL OBTENER PERFIL: {e}", file=sys.stderr, flush=True)
            raise Exception("ERROR inesperado al obtener perfil del cliente {client_id}: {e}")
        finally:
            # 🚨 Liberamos la conexión
            if conn:
                release_connection(conn)

    def get_by_id(self, client_id: int) -> Optional[Dict[str, Any]]:
        """
        Retorna un cliente por su client_id
        """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            query = """
                SELECT c.*, u.name, u.last_name, u.email, u.phone, s.zone AS seller_zone
                FROM users.Clients c
                JOIN users.Users u ON c.user_id = u.user_id
                LEFT JOIN users.sellers s ON c.seller_id = s.seller_id
                WHERE c.client_id = %s;
            """
            cursor.execute(query, (client_id,))
            result = cursor.fetchone()
            return dict(result) if result else None

        except psycopg2.Error as e:
            print(f"ERROR al obtener cliente {client_id}: {e}")
            raise
        finally:
            if conn:
                release_connection(conn)

    def get_visit_by_id(self, visit_id: int) -> Optional[Dict[str, Any]]:
        """
        Recupera una visita por su ID desde la base de datos, usando las columnas de tu DDL.
        """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            query = """
                SELECT 
                    visit_id, 
                    seller_id, 
                    date,       
                    findings,    
                    client_id    
                FROM users.visits 
                WHERE visit_id = %s;
            """
            
            cursor.execute(query, (visit_id,))
            result = cursor.fetchone()
            
            return dict(result) if result else None

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al obtener la visita {visit_id}: {e}")
            raise Exception(f"Database error during visit retrieval for ID {visit_id}.") from e
        
        finally:
            if conn:
                release_connection(conn)
    
    def save_evidence(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Guarda un registro de evidencia visual en la tabla users.visual_evidences.
        """
        conn = None
        try:
            conn = get_connection()
            # Usamos DictCursor para retornar el registro insertado
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            # Query para insertar en users.visual_evidences
            query = """
                INSERT INTO users.visual_evidences (visit_id, type, url_file, description)
                VALUES (%s, %s, %s, %s)
                RETURNING evidence_id, type, url_file, description, visit_id;
            """
            
            # Ejecutamos la inserción usando los datos del diccionario
            cursor.execute(query, (
                data['visit_id'],
                data['type'],
                data['url_file'],
                data.get('description', None) 
            ))
            
            conn.commit()
            
            result = cursor.fetchone()
            # Retorna el registro de la evidencia, incluyendo el nuevo evidence_id
            return dict(result)

        except psycopg2.Error as e:
            # Si la inserción falla (ej. FK constraint por visit_id, error de tipo de dato)
            print(f"ERROR de base de datos al guardar evidencia para visit_id {data.get('visit_id')}: {e}")
            raise Exception("Database error during evidence saving.") from e
        
    def save_visit(self, client_id: int, seller_id: int, date: str, findings: str):
        """
        Guarda la información de una nueva visita en la base de datos.
        :param visit_data: Diccionario con client_id, seller_id, date y findings.
        :return: Una instancia de la Visita recién creada con su visit_id.
        """
        conn = None
        new_visit_id = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Consulta SQL para insertar la nueva visita
            # RETURNING visit_id es crucial para obtener el ID generado automáticamente
            query = """
                INSERT INTO users.Visits (client_id, seller_id, date, findings)
                VALUES (%s, %s, %s, %s)
                RETURNING visit_id;
            """

            # Los valores se toman del diccionario visit_data
            values = (
                client_id,
                seller_id,
                date,  # La fecha ya viene validada como objeto date o similar
                findings,
            )

            # 1. Ejecutamos la inserción
            cursor.execute(query, values)

            # 2. Obtenemos el ID de la visita recién insertada
            new_visit_id = cursor.fetchone()[0]

            # 3. Confirmamos la transacción
            conn.commit()

            # 4. Creamos y devolvemos el objeto de dominio (Visita)
            # Asumiendo que existe una clase 'Visit' para mapear el registro.
            # Si no tienes una clase, simplemente devuelve el diccionario con el ID:
            return {
                "visit_id": new_visit_id,
                "client_id": client_id,
                "seller_id": seller_id,
                "date": date,
                "findings": findings,
            }
            # Si tienes una clase Visit, sería:
            # return Visit(visit_id=new_visit_id, client_id=..., seller_id=..., findings=...)

        except psycopg2.Error as e:
            # Si hay un error, revertimos cualquier cambio
            if conn:
                conn.rollback()
            print(f"ERROR de base de datos al guardar visita: {e}")
            # Relanzar una excepción genérica de dominio/aplicación para aislar la capa
            raise Exception("Database error during visit saving.")
        finally:
            if conn:
                release_connection(conn)