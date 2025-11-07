from typing import List, Dict, Any
from datetime import datetime, date
from src.domain.interfaces import OrderRepository
from src.domain.entities import Order, OrderItem
from .db_connector import get_connection, release_connection 

import psycopg2
from psycopg2 import extras 

class PgOrderRepository(OrderRepository):
    """
    Implementación concreta que se conecta a PostgreSQL (RDW)
    para obtener y persistir datos de Órdenes usando psycopg2.
    """

    def insert_order(self, order: Order, order_items: List[OrderItem]) -> Order:
        """
        Inserta una nueva orden (cabecera y líneas) en una transacción.
        """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            order_sql = """
                INSERT INTO orders.Orders (seller_id, client_id, creation_date, last_updated_date, estimated_delivery_date, status_id, total_value)
                VALUES (%s, %s, CURRENT_DATE, CURRENT_DATE, %s, %s, %s)
                RETURNING order_id;
            """

            cursor.execute(order_sql, (
                order.seller_id, 
                order.client_id, 
                order.estimated_delivery_date, 
                order.status_id, 
                order.order_value
            ))
            
            new_order_id = cursor.fetchone()[0]
            order.order_id = new_order_id 

            lines_insert_sql = """
                INSERT INTO orders.OrderLines (order_id, product_id, quantity, price_unit)
                VALUES (%s, %s, %s, %s);
            """
            lines_data = [
                (new_order_id, item.product_id, item.quantity, item.price_unit)
                for item in order_items
            ]
            
            psycopg2.extras.execute_batch(cursor, lines_insert_sql, lines_data)

            conn.commit()
            return order

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al insertar orden: {e}")
            if conn:
                conn.rollback() 
            raise Exception("Database error during order insertion.")
        finally:
            if conn:
                release_connection(conn)

    def get_orders_by_client_id(self, client_id: int) -> List[Order]:
        """
        Recupera todas las órdenes para un cliente específico.
        """
        conn = None
        orders = []
        try:
            conn = get_connection()
            cursor = conn.cursor() 
            
            sql_query = """
                SELECT 
                    order_id, client_id, creation_date, 
                    last_updated_date, estimated_delivery_date, status_id, total_value 
                FROM orders.Orders
                WHERE client_id = %s
                ORDER BY creation_date DESC;
            """
            cursor.execute(sql_query, (client_id,))
            
            for row in cursor.fetchall():
                order = Order(
                    order_id=row[0],
                    client_id=row[1],
                    creation_date=row[2],
                    last_updated_date=row[3],
                    estimated_delivery_date=row[4],
                    status_id=row[5],
                    order_value=row[6],
                    items = []
                )
                orders.append(order)
                
            return orders

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al obtener órdenes por cliente: {e}")
            if conn:
                conn.rollback()
            raise Exception("Database error during order retrieval by client.")
        finally:
            if conn:
                release_connection(conn)

    def get_all_orders_with_details(self) -> List[Dict[str, Any]]:
        """
        Ejecuta la consulta SQL real para obtener TODAS las órdenes con sus productos detallados.
        """
        conn = None
        orders_map = {}
        try:
            conn = get_connection()
            cursor = conn.cursor()

            sql_query = """
                SELECT 
                    o.order_id, o.client_id, o.creation_date, o.total_value,
                    ol.quantity, ol.price_unit,
                    p.sku, p.name AS product_name
                FROM orders.Orders o
                JOIN orders.OrderLines ol ON o.order_id = ol.order_id
                JOIN products.Products p ON ol.product_id = p.product_id
                ORDER BY o.creation_date DESC, o.order_id;
            """
            
            cursor.execute(sql_query)
            
            column_names = [desc[0] for desc in cursor.description]
            result_rows = cursor.fetchall()
            
            for row_tuple in result_rows:
                row = dict(zip(column_names, row_tuple))
                order_id = row['order_id']
                
                if order_id not in orders_map:
                    orders_map[order_id] = {
                        "order_id": order_id,
                        "client_id": row['client_id'],
                        "creation_date": row['creation_date'].isoformat() if isinstance(row['creation_date'], (datetime, date)) else str(row['creation_date']),
                        "total_value": float(row['total_value']),
                        "lines": []
                    }
                
                orders_map[order_id]['lines'].append({
                    "sku": row['sku'],
                    "name": row['product_name'],
                    "quantity": row['quantity'],
                    "price_unit": float(row['price_unit'])
                })
                
            return list(orders_map.values())

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al consultar todas las órdenes: {e}")
            if conn:
                conn.rollback()
            raise Exception("Database error during all orders retrieval.")
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

    def get_order_with_details_by_id(self, order_id: int) -> Order:
        """
                Ejecuta la consulta SQL real para obtener TODAS las órdenes con sus productos detallados.
                """
        conn = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            sql_query = """
                        SELECT 
                        o.order_id, 
                        o.client_id, 
                        o.creation_date, 
                        o.total_value,
                        o.last_updated_date, 
                        o.estimated_delivery_date, 
                        o.status_id,
                        c.address AS client_address,
                        uc.name||' '||uc.last_name AS client_name,
                        us.name||' '||us.last_name AS seller_name,
                        o.seller_id,
                        ol.quantity, 
                        ol.price_unit,
                        p.product_id, 
                        p.sku, 
                        p.name AS product_name
                    FROM orders.Orders o
                    JOIN orders.OrderLines ol ON o.order_id = ol.order_id
                    JOIN products.Products p ON ol.product_id = p.product_id
                    JOIN users.Clients c ON o.client_id = c.client_id
                    JOIN users.Users uc ON c.user_id = uc.user_id
                    JOIN users.sellers s ON o.seller_id = s.seller_id
                    JOIN users.Users us ON s.user_id = us.user_id
                    WHERE o.order_id = %s
                    ORDER BY o.creation_date DESC, o.order_id;
                    """

            cursor.execute(sql_query, (order_id,))

            column_names = [desc[0] for desc in cursor.description]
            result_rows = cursor.fetchall()
            order_lines = []


            for row_tuple in result_rows:
                row = dict(zip(column_names, row_tuple))
                order_lines.append(OrderItem(
                    sku=row['sku'],
                    name=row['product_name'],
                    quantity=row['quantity'],
                    price_unit=float(row['price_unit']),
                    product_id=row['product_id'],
                ))
            order = Order(
                order_id=order_id,
                client_id=result_rows[0][1],
                creation_date=result_rows[0][2].isoformat(),
                order_value=float(result_rows[0][3]),
                last_updated_date=result_rows[0][4].isoformat(),
                estimated_delivery_date=result_rows[0][5].isoformat(),
                status_id=result_rows[0][6],
                address = result_rows[0][7],
                client_name = result_rows[0][8],
                seller_name = result_rows[0][9],
                seller_id = result_rows[0][10],
                items=order_lines
            )



            return order

        except psycopg2.Error as e:
            print(f"ERROR de base de datos al consultar todas las órdenes: {e}")
            if conn:
                conn.rollback()
            raise Exception("Database error during all orders retrieval.")
        finally:
            if conn:
                release_connection(conn)
