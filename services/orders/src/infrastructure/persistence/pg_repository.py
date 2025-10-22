# src/infrastructure/persistence/pg_repository.py
from typing import List
from datetime import datetime
from src.domain.interfaces import OrderRepository
from src.domain.entities import Order
from .db_connector import get_connection, release_connection

import psycopg2


class PgOrderRepository(OrderRepository):
    """
    Implementación concreta que se conecta a PostgreSQL (RDW)
    para obtener los datos.
    """

    def get_orders_by_client_id(self, client_id: str) -> List[Order]:
        """
        Recupera pedidos de la base de datos para el cliente dado.
        """
        conn = None
        orders = []
        try:
            conn = get_connection()
            cursor = conn.cursor()

            # NOTA: En una aplicación real, se usaría un ORM como SQLAlchemy para
            # evitar la inyección SQL (SQL Injection). Usamos f-string para simplificar,
            # pero en producción se deben usar parámetros de consulta.

            # Adaptamos la consulta a la estructura de las tablas creadas
            query = f"""
                SELECT
                    o.order_id,
                    o.creation_date,
                    o.estimated_delivery_date,
                    o.current_state_id,
                    o.total_value,
                    MAX(o.creation_date) AS last_updated_date -- Usamos creation_date como proxy de last_updated_date
                                                             -- En un sistema real, necesitarías una tabla de histórico o un campo dedicado
                FROM "Order" o
                WHERE o.user_id = %s
                GROUP BY o.order_id, o.creation_date, o.estimated_delivery_date, o.current_state_id, o.total_value
                ORDER BY last_updated_date DESC;
            """

            # Ejecutamos la consulta
            cursor.execute(query, (client_id,))

            for row in cursor.fetchall():
                (
                    order_id,
                    creation_date,
                    estimated_delivery_date,
                    status_id,
                    total_value,
                    last_updated_date
                ) = row

                # Mapeo a la entidad del dominio
                orders.append(Order(
                    order_id=order_id,
                    creation_date=creation_date,
                    last_updated_date=last_updated_date or creation_date,  # Usamos la fecha de la DB
                    status_id=status_id,
                    estimated_delivery_date=estimated_delivery_date
                ))

            return orders

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al recuperar pedidos: {e}")
            # En lugar de retornar vacío, lanzamos una excepción para que el controlador la maneje
            raise Exception("Database error during order retrieval.")
        finally:
            if conn:
                release_connection(conn)

    def insert_order(self, order: Order) -> Order:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO "Order" (user_id, creation_date, last_updated_date, status_id, estimated_delivery_date)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING order_id
            """,
            (
                order.client_id,
                order.creation_date or datetime.now(),
                order.last_updated_date or datetime.now(),
                order.status_id,
                order.estimated_delivery_date
            )
        )
        order_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        order.order_id = order_id
        return order

