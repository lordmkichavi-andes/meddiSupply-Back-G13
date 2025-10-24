# src/infrastructure/persistence/pg_repository.py
from typing import List
import random

from datetime import datetime
from src.domain.interfaces import OrderRepository
from src.domain.entities import Order, OrderItem
from .db_connector import get_connection, release_connection

import psycopg2


class PgOrderRepository(OrderRepository):
    """
    Implementación concreta que se conecta a PostgreSQL (RDW)
    para obtener los datos.
    """

    def get_orders_by_client_id(self, client_id: int) -> List[Order]:
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
                    o.status_id,
                    o.total_value,
                    o.last_updated_date
                                                             -- En un sistema real, necesitarías una tabla de histórico o un campo dedicado
                FROM orders.orders o
                WHERE o.client_id = %s
                GROUP BY o.order_id, o.creation_date, o.estimated_delivery_date, o.status_id, o.total_value
                ORDER BY o.creation_date DESC;
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
                    client_id=client_id,
                    order_id=order_id,
                    creation_date=creation_date,
                    status_id=status_id,
                    estimated_delivery_date=estimated_delivery_date,
                    last_updated_date=last_updated_date,
                    order_value=total_value,
                    orders=[]
                ))

            return orders

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al recuperar pedidos: {e}")
            if conn:
                conn.rollback()
                # En lugar de retornar vacío, lanzamos una excepción para que el controlador la maneje
            raise Exception("Database error during order retrieval.")
        finally:
            if conn:
                release_connection(conn)

    def insert_order(self, order: Order, order_items: List[OrderItem]) -> Order:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO orders.orders (client_id, creation_date, last_updated_date, status_id, estimated_delivery_date, total_value)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING order_id
                """,
                (
                    order.client_id,
                    order.creation_date or datetime.now(),
                    order.creation_date or datetime.now(),
                    order.status_id,
                    order.estimated_delivery_date,
                    order.order_value
                )
            )
            order_id = cur.fetchone()[0]
            order.order_id = order_id

            if order_items:
                items_to_insert = []
                for item in order_items:
                    items_to_insert.append((
                        order_id,
                        item.product_id,
                        item.quantity,
                        item.price_unit,
                    ))
                
                sql_insert_items = """
                    INSERT INTO orders.OrderLines (order_id, product_id, quantity, price_unit )
                    VALUES (%s, %s, %s,%s);
                """
                
                cur.executemany(sql_insert_items, items_to_insert)
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            raise e 
            
        finally:
            cur.close()
            if conn:
                release_connection(conn)
        return order