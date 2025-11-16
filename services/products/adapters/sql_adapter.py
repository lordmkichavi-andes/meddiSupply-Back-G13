import psycopg2
from psycopg2.extras import RealDictCursor, register_uuid
from typing import List, Optional, Dict
from repositories.product_repository import ProductRepository
from domain.models import Product
from config import Config
import logging

logger = logging.getLogger(__name__)

class PostgreSQLProductAdapter(ProductRepository):
    """Implementación del repositorio de productos para PostgreSQL (RDS)."""

    def _get_connection(self):
        """Método helper para establecer la conexión a PostgreSQL y devolver un cursor de diccionario."""
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        # Usamos RealDictCursor para obtener resultados como diccionarios (nombre de columna: valor),
        # similar a sqlite3.Row.
        return conn, conn.cursor(cursor_factory=RealDictCursor)

    # -------------------------------------------------------------
    # Implementación de get_available_products
    # -------------------------------------------------------------
    def get_available_products(self) -> List[Product]:
        conn, cursor = self._get_connection()

        query = '''
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
            p.product_id, p.sku, p.value, c.name -- PostgreSQL requiere agrupar por todas las columnas no agregadas
        ORDER BY
            p.sku;
        '''

        try:
            cursor.execute(query)
            results = cursor.fetchall()

            products = [
                Product(
                    product_id=row['product_id'],
                    sku=row['sku'],
                    value=row['value'],
                    name=row['name'],
                    image_url=row['image_url'],
                    category_name=row['category_name'],
                    total_quantity=row['total_quantity']
                ) for row in results
            ]

            return products

        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------
    # Implementación de get_product_by_id
    # -------------------------------------------------------------
    def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Obtiene un producto por su ID."""
        conn, cursor = self._get_connection()

        query = '''
        SELECT 
            p.product_id,
            p.sku,
            p.value,
            p.name,
            p.image_url,
            c.name AS category_name,
            SUM(ps.quantity) AS total_quantity
        FROM 
            products.Product p
        JOIN 
            products.Category c ON p.category_id = c.category_id
        JOIN 
            products.ProductStock ps ON p.product_id = ps.product_id
        WHERE
            p.product_id = %s -- 💡 Cambio de ? a %s para psycopg2
        GROUP BY
            p.product_id, p.sku, p.value, c.name
        ORDER BY
            p.sku;
        '''

        try:
            # 💡 Pasar los parámetros como una tupla (product_id,)
            cursor.execute(query, (product_id,))
            row = cursor.fetchone()

            if row:
                # 💡 Corregir mapeo de campos, usando nombres de columna (diccionario)
                return Product(
                    product_id=row['product_id'],
                    sku=row['sku'],
                    value=row['value'],
                    name=row['name'],
                    image_url=row['image_url'],
                    category_name=row['category_name'],
                    total_quantity=row['total_quantity']
                )
            return None

        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------------------
    # Implementación de update_product
    # -------------------------------------------------------------
    def update_product(self, product_id: int, price: float, stock: int, warehouse: int) -> None:
        """
        Actualiza el precio y el stock de un producto por su ID.
        Si el producto no existe, se asume que la operación no es válida y no se hace nada.
        """
        conn, cursor = self._get_connection()
        queryProduct =  """
                 UPDATE products.Product
                    SET value = %s
                    WHERE product_id = %s;
                 """


        queryStock =  """
                         UPDATE products.ProductStock
                            SET quantity =  %s
                            WHERE product_id =  %s 
                            AND warehouse_id =  %s;
                         """


        cursor.execute(queryProduct, (price, product_id,))
        cursor.execute(queryStock, (stock, product_id, warehouse, ))
        conn.commit()
        conn.close()

    def update_product_quantities(self, products: list) -> int:
        conn, cursor = self._get_connection()
        updated_products = 0

        for product in products:
            product_id = product["product_id"]
            discount = product["quantity"]

            logger.info(f"➡️ Procesando product_id={product_id}, descuento={discount}")

            # 1. Obtener provider_id principal del producto
            cursor.execute("SELECT provider_id FROM products.Products WHERE product_id = %s;", (product_id,))
            row = cursor.fetchone()
            if not row:
                logger.warning(f"No se encontró provider_id para product_id={product_id}")
                continue
            main_provider_id = row['provider_id']
            logger.info(f"   Provider principal={main_provider_id}")

            # 2. Obtener todas las filas de stock del producto (sin filtrar por provider)
            cursor.execute("""
                SELECT stock_id, quantity, provider_id
                FROM products.ProductStock
                WHERE product_id = %s
                ORDER BY provider_id, stock_id;
            """, (product_id,))
            rows = cursor.fetchall()
            logger.info(f"   Filas encontradas: {rows}")

            remaining = discount

            # 3. Agrupar filas por provider_id
            providers = {}
            for r in rows:
                providers.setdefault(r['provider_id'], []).append(r)

            # 4. Ordenar: primero el provider principal, luego los demás
            ordered_providers = [main_provider_id] + [pid for pid in providers if pid != main_provider_id]

            # 5. Descontar escalonado
            for pid in ordered_providers:
                for r in providers[pid]:
                    stock_id = r['stock_id']
                    current_qty = r['quantity']
                    logger.info(f"   Revisando stock_id={stock_id}, provider_id={pid}, qty_actual={current_qty}, remaining={remaining}")

                    if remaining <= 0:
                        break

                    if current_qty >= remaining:
                        new_qty = current_qty - remaining
                        cursor.execute("""
                            UPDATE products.ProductStock
                            SET quantity = %s
                            WHERE stock_id = %s;
                        """, (new_qty, stock_id))
                        logger.info(f"   ✅ Actualizado stock_id={stock_id} a {new_qty}")
                        remaining = 0
                    else:
                        cursor.execute("""
                            UPDATE products.ProductStock
                            SET quantity = 0
                            WHERE stock_id = %s;
                        """, (stock_id,))
                        logger.info(f"   ❌ Vaciado stock_id={stock_id}, antes tenía {current_qty}")
                        remaining -= current_qty

                if remaining <= 0:
                    break

            updated_products += 1

        conn.commit()
        cursor.close()
        conn.close()
        logger.info("✔️ Commit realizado")

        return updated_products

