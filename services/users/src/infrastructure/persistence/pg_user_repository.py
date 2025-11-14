from typing import List, Any, Dict, Optional
from src.domain.interfaces import UserRepository
from src.domain.entities import Client
from .db_connector import get_connection, release_connection
import psycopg2
import sys
import psycopg2.extras
import logging

logger = logging.getLogger(__name__)

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

    def get_recent_evidences_by_client(self, client_id: int) -> List[Dict[str, str]]:
        """
        Obtiene las URLs y tipos de archivos de evidencia visual (media) asociados a las 
        visitas recientes de un cliente.
        
        Retorna una lista de diccionarios con las claves 'url' y 'type'.
        """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 
            
            query = """
            SELECT
                ve.url_file AS url,
                ve.type
            FROM
                users.visual_evidences ve
            JOIN
                users.visits v ON ve.visit_id = v.visit_id
            WHERE
                v.client_id = %s
            ORDER BY
                v.date DESC, ve.evidence_id DESC 
            LIMIT 10;
            """
            
            cursor.execute(query, (client_id,))
            result = cursor.fetchall()
            
            if not result:
                return []

            return [dict(row) for row in result]

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al obtener evidencias del cliente {client_id}: {e}")
            raise Exception("Database error during recent evidences retrieval.")
        finally:
            if conn:
                release_connection(conn)

    def get_recent_purchase_history(self, client_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Recupera el historial reciente (SKU y nombre) de productos comprados por un cliente.
        """
        conn = None
        history = []
        try:
            conn = get_connection()
            cursor = conn.cursor()

            
            query = """
                SELECT DISTINCT ON (p.product_id)
                    p.sku, 
                    p.name
                FROM orders.Orders o
                JOIN orders.OrderLines ol ON o.order_id = ol.order_id
                JOIN products.Products p ON ol.product_id = p.product_id
                WHERE o.client_id = %s
                ORDER BY p.product_id, o.creation_date DESC 
                LIMIT %s;
            """
            
            cursor.execute(query, (client_id, limit))
            
            for row in cursor.fetchall():
                history.append({
                    "sku": row[0],
                    "name": row[1]
                })

            return history

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al recuperar el historial de compras: {e}")
            if conn:
                conn.rollback()
            raise Exception("Database error retrieving purchase history.")
        finally:
            if conn:
                release_connection(conn)

    def save_evidence(self, visit_id: int, url: str, type: str) -> Dict[str, Any]:
        """
        Guarda la información de un archivo de evidencia (URL y tipo) 
        asociada a una visita en la tabla users.visual_evidences.
        """
        conn = None
        new_evidence_id = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # Consulta SQL para insertar la nueva evidencia
            query = """
                INSERT INTO users.visual_evidences (visit_id, url_file, type)
                VALUES (%s, %s, %s)
                RETURNING evidence_id;
            """
            values = (visit_id, url, type.upper()) # Aseguramos que el tipo esté en mayúsculas (si es necesario)

            cursor.execute(query, values)
            
            # Obtenemos el ID de la evidencia recién insertada
            new_evidence_id = cursor.fetchone()[0]
            conn.commit()

            return {
                "evidence_id": new_evidence_id,
                "visit_id": visit_id,
                "url": url,
                "type": type
            }

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error de base de datos al guardar evidencia para visita {visit_id}: {e}")
            raise Exception("Database error during evidence saving.")
        finally:
            if conn:
                release_connection(conn)

    def save_suggestion(
        self, 
        visit_id: int, 
        product_id: int
    ) -> Dict[str, Any]:
        """
        Guarda una sugerencia de producto, asociando el product_id al visit_id 
        en la tabla users.visit_product_suggestions.
        
        Esta tabla no almacena score ni reasoning.
        """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            query = """
                INSERT INTO users.visit_product_suggestions (visit_id, product_id)
                VALUES (%s, %s)
                ON CONFLICT (visit_id, product_id) DO NOTHING;
            """
            values = (visit_id, product_id)

            cursor.execute(query, values)
            conn.commit()
            rows_affected = cursor.rowcount

            return {
                "visit_id": visit_id,
                "product_id": product_id,
                "status": "inserted" if rows_affected > 0 else "already_exists"
            }

        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"Error de base de datos al guardar sugerencia para visita {visit_id}: {e}")
            raise Exception("Database error during suggestion saving.")
        finally:
            if conn:
                release_connection(conn)

    def get_products(self) -> List[Dict[str, Any]]:
        """
        Obtiene el catálogo de productos disponibles (con stock > 0) 
        directamente desde la base de datos PostgreSQL, usando los esquemas actualizados.
        
        Retorna una lista de diccionarios con el detalle del producto.
        """
        conn = None
        products = []
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

            query = """
            SELECT
                p.product_id,
                p.sku,
                p.value,
                p.name,
                p.image_url,
                c.name AS category_name,
                SUM(ps.quantity) AS total_quantity
            FROM 
                products.Products p
            JOIN 
                products.Category c ON p.category_id = c.category_id
            JOIN 
                products.ProductStock ps ON p.product_id = ps.product_id
            WHERE
                ps.quantity > 0
            GROUP BY
                p.product_id, p.sku, p.value, p.name, p.image_url, c.name -- Agrupación completa requerida por PostgreSQL
            ORDER BY
                p.sku;
            """

            cursor.execute(query)
            results = cursor.fetchall()

            # Mapeamos los resultados (DictRow) a una lista de diccionarios Python estándar
            products = [dict(row) for row in results]

            # logger.info(f"Catálogo cargado: {len(products)} productos disponibles.")
            return products

        except psycopg2.Error as e:
            # Aquí puedes registrar el error de DB para debugging
            logger.error(f"ERROR de base de datos al recuperar el catálogo de productos: {e}")
            return []
        except Exception as e:
            # Aquí puedes registrar cualquier otro error inesperado
            logger.error(f"ERROR INESPERADO AL OBTENER CATÁLOGO: {e}")
            return []
        finally:
            if conn:
                release_connection(conn)

    def get_suggestions_by_client(self, client_id: int) -> List[Dict[str, Any]]:
        """
        Recupera el historial de productos sugeridos para un cliente, 
        incluyendo los detalles del producto consultando los esquemas 'users' y 'products'.
        """
        conn = None
        products_data = []
        try:
            conn = get_connection() 
            cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor) 

            query = """
                SELECT DISTINCT
                    p.product_id,
                    p.sku, 
                    p.value, 
                    p.image_url, 
                    p.name,
                    -- Referencia a products.Category
                    pc.name AS category_name,
                    -- Agregamos el stock total de la tabla products.ProductStock
                    COALESCE(SUM(ps.quantity), 0) AS total_quantity 
                FROM 
                    users.visits v
                -- 1. Unir a las sugerencias de producto (users.visit_product_suggestions)
                JOIN 
                    users.visit_product_suggestions vps ON v.visit_id = vps.visit_id
                -- 2. Unir a la tabla maestra de Productos (products.Products)
                JOIN 
                    products.Products p ON vps.product_id = p.product_id
                -- 3. Unir a la tabla de Categorías (products.Category)
                LEFT JOIN 
                    products.Category pc ON p.category_id = pc.category_id
                -- 4. Unir a la tabla de Stock (products.ProductStock)
                LEFT JOIN
                    products.ProductStock ps ON p.product_id = ps.product_id
                WHERE 
                    v.client_id = %s
                GROUP BY
                    p.product_id, p.sku, p.value, p.image_url, p.name, pc.name
                ORDER BY 
                    p.product_id DESC;
            """
            
            cursor.execute(query, (client_id,))
            result = cursor.fetchall()
            
            for row in result:
                products_data.append({
                    'product_id': row['product_id'],
                    'sku': row['sku'],
                    'value': float(row['value']),
                    'image_url': row['image_url'],
                    'name': row['name'],
                    'category_name': row['category_name'],
                    'total_quantity': int(row['total_quantity']) 
                })

            return products_data

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al recuperar sugerencias del cliente {client_id}: {e}")
            raise Exception("Database error retrieving client suggestions.")
        finally:
            if conn:
                release_connection(conn)

    def get_sellers(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los vendedores disponibles.
        Retorna una lista de diccionarios con la información de los vendedores.
        """
        conn = None
        sellers = []
        try:
            conn = get_connection()
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = """
                SELECT
                    s.seller_id AS id,
                    u.name || ' ' || u.last_name AS name,
                    u.email AS email,
                    s.zone AS region,
                    u.active AS active
                FROM
                    users.sellers s
                JOIN
                    users.users u ON s.user_id = u.user_id
                ORDER BY
                    name
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            
            for row in results:
                sellers.append({
                    'id': row['id'],
                    'name': row['name'],
                    'email': row['email'],
                    'region': row['region'],
                    'active': row['active']
                })
            
            return sellers
            
        except psycopg2.Error as e:
            logger.error(f"ERROR de base de datos al recuperar vendedores: {e}")
            raise Exception("Database error retrieving sellers.")
        finally:
            if conn:
                release_connection(conn)
