from typing import List, Any
from src.domain.interfaces import UserRepository
from src.domain.entities import Client
from .db_connector import get_connection, release_connection

import psycopg2


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
