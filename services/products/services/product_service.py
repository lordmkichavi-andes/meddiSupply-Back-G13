# services/product_service.py
from typing import List, Dict
from repositories.product_repository import ProductRepository
from domain.models import Product

class ProductService:
    def __init__(self, repository: ProductRepository):
        self.repository = repository

    def list_available_products(self) -> List[Product]:
        """Caso de uso: listar todos los productos disponibles."""
        return self.repository.get_available_products()

    def update_product(self, product_id: int, price: float, stock: int, warehouse: int) -> None:
        """Caso de uso: actualizar un producto existente."""
        self.repository.update_product(product_id=product_id, price=price, stock=stock, warehouse=warehouse)

    def update_product_quantities(self, products: List[Dict]) -> int:
        """
        Caso de uso: actualizar únicamente el stock (quantity) de uno o varios productos.
        Recibe una lista de diccionarios con:
          - product_id (int)
          - quantity (int)
        Retorna el número de productos actualizados.
        """
        return self.repository.update_product_quantities(products)