import pytest
from unittest.mock import patch, MagicMock
from src.services.sales_plan_service import SalesPlanService


class TestSalesPlanServiceValidation:
    """Tests para validaciones de SalesPlanService"""
    
    def test_validate_sales_plan_data_missing_fields(self):
        errors = SalesPlanService.validate_sales_plan_data({})
        assert len(errors) >= 1
        assert any('region' in error.lower() for error in errors)
    
    def test_validate_sales_plan_data_invalid_region(self):
        data = {
            'region': 'Invalid',
            'quarter': 'Q1',
            'year': 2025,
            'total_goal': 10,
            'products': []
        }
        errors = SalesPlanService.validate_sales_plan_data(data)
        assert len(errors) > 0
    
    def test_validate_sales_plan_data_invalid_quarter(self):
        data = {
            'region': 'Norte',
            'quarter': 'Q5',
            'year': 2025,
            'total_goal': 10,
            'products': []
        }
        errors = SalesPlanService.validate_sales_plan_data(data)
        assert len(errors) > 0
    
    def test_validate_sales_plan_data_invalid_year(self):
        data = {
            'region': 'Norte',
            'quarter': 'Q1',
            'year': 1900,
            'total_goal': 10,
            'products': []
        }
        errors = SalesPlanService.validate_sales_plan_data(data)
        assert len(errors) > 0
    
    def test_validate_sales_plan_data_invalid_total_goal(self):
        data = {
            'region': 'Norte',
            'quarter': 'Q1',
            'year': 2025,
            'total_goal': -10,
            'products': []
        }
        errors = SalesPlanService.validate_sales_plan_data(data)
        assert len(errors) > 0
    
    def test_validate_sales_plan_data_invalid_product_id(self, monkeypatch):
        data = {
            'region': 'Norte',
            'quarter': 'Q1',
            'year': 2025,
            'total_goal': 10,
            'products': [
                {'product_id': 999, 'individual_goal': 5}
            ]
        }
        
        class DummyClient:
            def get_all_active_products(self):
                return [{'product_id': 1}]
        
        from src.services import sales_plan_service as sps
        monkeypatch.setattr(sps, 'products_client', DummyClient())
        
        errors = SalesPlanService.validate_sales_plan_data(data)
        assert len(errors) > 0
    
    def test_validate_sales_plan_data_invalid_individual_goal(self):
        data = {
            'region': 'Norte',
            'quarter': 'Q1',
            'year': 2025,
            'total_goal': 10,
            'products': [
                {'product_id': 1, 'individual_goal': -5}
            ]
        }
        
        class DummyClient:
            def get_all_active_products(self):
                return [{'product_id': 1}]
        
        with patch('src.services.sales_plan_service.products_client', DummyClient()):
            errors = SalesPlanService.validate_sales_plan_data(data)
            assert len(errors) > 0
    
    def test_validate_sales_plan_data_happy_path(self, monkeypatch):
        data = {
            'region': 'Norte',
            'quarter': 'Q1',
            'year': SalesPlanService.CURRENT_YEAR,
            'total_goal': 10,
            'products': [
                {'product_id': 1, 'individual_goal': 5},
                {'product_id': 2, 'individual_goal': 5}
            ]
        }

        class DummyClient:
            def get_all_active_products(self):
                return [{'product_id': 1}, {'product_id': 2}]

        from src.services import sales_plan_service as sps
        monkeypatch.setattr(sps, 'products_client', DummyClient())

        errors = SalesPlanService.validate_sales_plan_data(data)
        assert errors == []


class TestSalesPlanServiceCalculations:
    """Tests para cálculos de SalesPlanService"""
    
    def test_calculate_total_goal_from_products(self):
        products = [
            {'individual_goal': 1.5},
            {'individual_goal': 2.5},
            {'individual_goal': '3'}
        ]
        total = SalesPlanService.calculate_total_goal_from_products(products)
        assert str(total) == '7.0'
    
    def test_calculate_total_goal_from_products_empty(self):
        total = SalesPlanService.calculate_total_goal_from_products([])
        assert total == 0
    
    def test_validate_total_goal_consistency_no_errors(self):
        data = {
            'products': [{'individual_goal': 2}, {'individual_goal': 3}],
            'total_goal': 5
        }
        errors = SalesPlanService.validate_total_goal_consistency(data)
        assert errors == []


class TestSalesPlanServiceOptions:
    """Tests para opciones de SalesPlanService"""
    
    def test_get_region_options(self):
        regions = SalesPlanService.get_region_options()
        assert len(regions) == 5
        assert any(r['value'] == 'Norte' for r in regions)
        assert any(r['value'] == 'Centro' for r in regions)
        assert any(r['value'] == 'Sur' for r in regions)
        assert any(r['value'] == 'Caribe' for r in regions)
        assert any(r['value'] == 'Pacífico' for r in regions)
    
    def test_get_quarter_options(self):
        quarters = SalesPlanService.get_quarter_options()
        assert len(quarters) == 4
        assert any(q['value'] == 'Q1' for q in quarters)
        assert any(q['value'] == 'Q2' for q in quarters)
        assert any(q['value'] == 'Q3' for q in quarters)
        assert any(q['value'] == 'Q4' for q in quarters)

