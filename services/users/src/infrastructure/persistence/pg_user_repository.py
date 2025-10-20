from typing import List, Dict, Any
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
                    u.name,
                    u.last_name,
                    u.password,
                    u.identification,
                    u.phone,
                    u.role,
                    c.nit,
                    c.balance,
                    c.perfil
                FROM Users u
                INNER JOIN Clientes c ON u.user_id = c.user_id
                WHERE u.role IN (%s)
                ORDER BY u.name ASC;
            """

            # Ejecutamos la consulta
            cursor.execute(query, (role,))

            for row in cursor.fetchall():
                (
                    user_id,
                    name,
                    last_name,
                    password,
                    identification,
                    phone,
                    role_value,
                    nit,
                    balance,
                    perfil
                ) = row

                # Mapeo a la entidad del dominio
                users.append(Client(
                    user_id=user_id,
                    name=name,
                    last_name=last_name,
                    password=password,
                    identification=identification,
                    phone=phone,
                    role_value=role_value,
                    nit=nit,
                    balance=balance,
                    perfil=perfil
                ))

            return users

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al recuperar usuarios: {e}")
            raise Exception("Database error during user retrieval.")
        finally:
            if conn:
                release_connection(conn)

    def save_visit(self, visit_data: Dict[str, Any]):
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
                INSERT INTO Visits (client_id, seller_id, visit_date, findings)
                VALUES (%s, %s, %s, %s)
                RETURNING visit_id;
            """

            # Los valores se toman del diccionario visit_data
            values = (
                visit_data['client_id'],
                visit_data['seller_id'],
                visit_data['date'],  # La fecha ya viene validada como objeto date o similar
                visit_data['findings']
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
                "client_id": visit_data['client_id'],
                "seller_id": visit_data['seller_id'],
                "date": visit_data['date'],
                "findings": visit_data['findings']
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