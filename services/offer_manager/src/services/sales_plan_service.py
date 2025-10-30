"""Servicio para validaciones y lógica de negocio de planes de venta."""

from typing import List, Dict, Any, Optional
from decimal import Decimal
from src.clients.products_client import products_client


class SalesPlanService:
    """Servicio para manejo de planes de venta."""
    
    VALID_REGIONS = ['Norte', 'Centro', 'Sur', 'Caribe', 'Pacífico']
    VALID_QUARTERS = ['Q1', 'Q2', 'Q3', 'Q4']
    CURRENT_YEAR = 2025
    
    @classmethod
    def validate_sales_plan_data(cls, data: Dict[str, Any]) -> List[str]:
        """Valida los datos de un plan de venta."""
        errors = []
        
        # Validar campos obligatorios
        required_fields = ['region', 'quarter', 'year', 'total_goal', 'products']
        for field in required_fields:
            if field not in data or data[field] is None:
                errors.append(f"Campo obligatorio: {field}")
        
        if errors:
            return errors
        
        # Validar región
        if not cls._validate_region(data['region']):
            errors.append(f"La región debe ser una de: {', '.join(cls.VALID_REGIONS)}")
        
        # Validar trimestre
        if not cls._validate_quarter(data['quarter']):
            errors.append(f"El trimestre debe ser uno de: {', '.join(cls.VALID_QUARTERS)}")
        
        # Validar año
        if not cls._validate_year(data['year']):
            errors.append(f"El año debe ser {cls.CURRENT_YEAR}")
        
        # Validar meta total
        if not cls._validate_total_goal(data['total_goal']):
            errors.append("La meta total debe ser un número mayor a 0")
        
        # Validar productos
        if not isinstance(data['products'], list) or len(data['products']) == 0:
            errors.append("Debe incluir al menos un producto")
        else:
            product_errors = cls._validate_products(data['products'])
            errors.extend(product_errors)
        
        return errors
    
    @classmethod
    def _validate_region(cls, region: str) -> bool:
        """Valida que la región sea válida."""
        return region in cls.VALID_REGIONS
    
    @classmethod
    def _validate_quarter(cls, quarter: str) -> bool:
        """Valida que el trimestre sea válido."""
        return quarter in cls.VALID_QUARTERS
    
    @classmethod
    def _validate_year(cls, year: int) -> bool:
        """Valida que el año sea válido."""
        return year == cls.CURRENT_YEAR
    
    @classmethod
    def _validate_total_goal(cls, total_goal: Any) -> bool:
        """Valida que la meta total sea válida."""
        try:
            goal = Decimal(str(total_goal))
            return goal > 0
        except (ValueError, TypeError):
            return False
    
    @classmethod
    def _validate_products(cls, products: List[Dict[str, Any]]) -> List[str]:
        """Valida la lista de productos."""
        errors = []
        
        # Obtener productos válidos del microservicio
        try:
            valid_products = products_client.get_all_active_products()
            valid_product_ids = {p['product_id'] for p in valid_products}
        except Exception:
            # Si no se puede conectar al servicio, validar solo estructura básica
            valid_product_ids = set()
        
        for i, product in enumerate(products):
            product_num = i + 1
            
            # Validar campos obligatorios del producto
            if 'product_id' not in product or product['product_id'] is None:
                errors.append(f"El producto {product_num} debe tener un ID válido")
                continue
            
            if 'individual_goal' not in product or product['individual_goal'] is None:
                errors.append(f"El producto {product_num} debe tener una meta individual")
                continue
            
            # Validar que el producto exista
            if product['product_id'] not in valid_product_ids:
                errors.append(f"El producto {product_num} no existe en el catálogo")
                continue
            
            # Validar meta individual
            try:
                individual_goal = Decimal(str(product['individual_goal']))
                if individual_goal <= 0:
                    errors.append(f"La meta del producto {product_num} debe ser mayor a 0")
            except (ValueError, TypeError):
                errors.append(f"La meta del producto {product_num} debe ser un número válido")
        
        return errors
    
    @classmethod
    def calculate_total_goal_from_products(cls, products: List[Dict[str, Any]]) -> Decimal:
        """Calcula la meta total basada en los productos."""
        total = Decimal('0')
        for product in products:
            try:
                individual_goal = Decimal(str(product.get('individual_goal', 0)))
                total += individual_goal
            except (ValueError, TypeError):
                continue
        return total
    
    @classmethod
    def validate_total_goal_consistency(cls, data: Dict[str, Any]) -> List[str]:
        """Valida que la meta total coincida con la suma de metas individuales."""
        errors = []
        
        if 'products' in data and 'total_goal' in data:
            calculated_total = cls.calculate_total_goal_from_products(data['products'])
            provided_total = Decimal(str(data['total_goal']))
            
            # Permitir pequeñas diferencias por redondeo
            tolerance = Decimal('0.01')
            if abs(calculated_total - provided_total) > tolerance:
                errors.append(
                    f"La meta total ({provided_total}) no coincide con la suma de metas individuales ({calculated_total})"
                )
        
        return errors
    
    @classmethod
    def get_region_options(cls) -> List[Dict[str, str]]:
        """Obtiene las opciones de región disponibles."""
        return [{'value': region, 'label': region} for region in cls.VALID_REGIONS]
    
    @classmethod
    def get_quarter_options(cls) -> List[Dict[str, str]]:
        """Obtiene las opciones de trimestre disponibles."""
        quarter_labels = {
            'Q1': 'Q1 - Enero a Marzo',
            'Q2': 'Q2 - Abril a Junio', 
            'Q3': 'Q3 - Julio a Septiembre',
            'Q4': 'Q4 - Octubre a Diciembre'
        }
        return [{'value': quarter, 'label': quarter_labels[quarter]} for quarter in cls.VALID_QUARTERS]
