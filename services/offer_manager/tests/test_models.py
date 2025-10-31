import pytest
from src.models.product import Product
from src.models.sales_plan import SalesPlan, SalesPlanProduct


class TestProductModel:
    """Tests para el modelo Product"""
    
    def test_product_from_dict(self):
        data = {
            'product_id': 1,
            'sku': 'SKU-001',
            'name': 'Producto Test',
            'value': 100.0,
            'objective_profile': 'Test Profile',
            'unit_name': 'Caja',
            'unit_symbol': 'Cj',
            'category_name': 'MEDICATION'
        }
        product = Product.from_dict(data)
        assert product.product_id == 1
        assert product.sku == 'SKU-001'
        assert product.name == 'Producto Test'
        assert product.value == 100.0
        assert product.objective_profile == 'Test Profile'
    
    def test_product_to_dict(self):
        from decimal import Decimal
        product = Product(
            product_id=1,
            sku='SKU-001',
            name='Producto Test',
            value=Decimal('100.0'),
            objective_profile='Test Profile',
            unit_name='Caja',
            unit_symbol='Cj',
            category_name='MEDICATION'
        )
        data = product.to_dict()
        assert data['product_id'] == 1
        assert data['sku'] == 'SKU-001'
        assert data['value'] == 100.0
        assert data['objective_profile'] == 'Test Profile'


class TestSalesPlanModel:
    """Tests para el modelo SalesPlan"""
    
    def test_sales_plan_from_dict(self):
        data = {
            'plan_id': 1,
            'region': 'Norte',
            'quarter': 'Q1',
            'year': 2025,
            'total_goal': 100.0,
            'is_active': True,
            'creation_date': '2025-01-01',
            'created_by': 1
        }
        plan = SalesPlan.from_dict(data)
        assert plan.plan_id == 1
        assert plan.region == 'Norte'
        assert plan.quarter == 'Q1'
        assert plan.year == 2025
        assert plan.total_goal == 100.0
    
    def test_sales_plan_to_dict(self):
        plan = SalesPlan(
            plan_id=1,
            region='Centro',
            quarter='Q2',
            year=2025,
            total_goal=200.0,
            is_active=True,
            creation_date='2025-01-01',
            created_by=1
        )
        data = plan.to_dict()
        assert data['plan_id'] == 1
        assert data['region'] == 'Centro'
        assert data['total_goal'] == 200.0


class TestSalesPlanProductModel:
    """Tests para el modelo SalesPlanProduct"""
    
    def test_sales_plan_product_from_dict(self):
        from decimal import Decimal
        data = {
            'product_id': 100,
            'individual_goal': 50.0,
            'sku': 'SKU-100',
            'product_name': 'Prod 100',
            'product_value': 25.0,
            'unit_name': 'Caja',
            'unit_symbol': 'Cj'
        }
        product = SalesPlanProduct.from_dict(data)
        assert product.product_id == 100
        assert product.individual_goal == Decimal('50.0')
        assert product.sku == 'SKU-100'
        assert product.product_name == 'Prod 100'
    
    def test_sales_plan_product_to_dict(self):
        from decimal import Decimal
        product = SalesPlanProduct(
            product_id=100,
            individual_goal=Decimal('50.0'),
            sku='SKU-100',
            product_name='Prod 100',
            product_value=Decimal('25.0'),
            unit_name='Caja',
            unit_symbol='Cj'
        )
        data = product.to_dict()
        assert data['product_id'] == 100
        assert data['individual_goal'] == 50.0
        assert data['sku'] == 'SKU-100'

