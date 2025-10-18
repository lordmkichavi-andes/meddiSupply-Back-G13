"""Tests directos para medir cobertura real."""

import pytest
import sys
import os
import importlib.util

# Función para importar módulo desde archivo
def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Importar directamente los módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Importar Vendor
vendor_path = os.path.join(parent_dir, "src", "models", "vendor.py")
Vendor = import_from_file("vendor", vendor_path).Vendor

# Importar Product
product_path = os.path.join(parent_dir, "src", "models", "product.py")
Product = import_from_file("product", product_path).Product

# Importar SalesReport
sales_report_path = os.path.join(parent_dir, "src", "models", "sales_report.py")
SalesReport = import_from_file("sales_report", sales_report_path).SalesReport

class TestDirectVendor:
    """Tests directos para Vendor."""

    def test_vendor_creation_complete(self):
        """Test creación completa de vendor."""
        vendor = Vendor(
            id="v1",
            name="Juan Pérez",
            email="juan@example.com",
            region="Norte",
            active=True
        )
        assert vendor.id == "v1"
        assert vendor.name == "Juan Pérez"
        assert vendor.email == "juan@example.com"
        assert vendor.region == "Norte"
        assert vendor.active is True

    def test_vendor_from_dict_string_conversion(self):
        """Test crear vendor desde diccionario."""
        data = {
            "id": "v2",
            "name": "María García",
            "email": "maria@example.com",
            "region": "Sur",
            "active": False
        }
        vendor = Vendor.from_dict(data)
        assert vendor.id == "v2"
        assert vendor.name == "María García"
        assert vendor.email == "maria@example.com"
        assert vendor.region == "Sur"
        assert vendor.active is False

    def test_vendor_to_dict_complete(self):
        """Test convertir vendor a diccionario."""
        vendor = Vendor(
            id="v3",
            name="Carlos López",
            email="carlos@example.com",
            region="Centro",
            active=True
        )
        result = vendor.to_dict()
        expected = {
            "id": "v3",
            "name": "Carlos López",
            "email": "carlos@example.com",
            "region": "Centro",
            "active": True
        }
        assert result == expected


class TestDirectProduct:
    """Tests directos para Product."""

    def test_product_creation_complete(self):
        """Test creación completa de producto."""
        product = Product(
            id="p1",
            name="Producto A",
            category="Electrónicos",
            price=1500.0,
            unit="unidad"
        )
        assert product.id == "p1"
        assert product.name == "Producto A"
        assert product.category == "Electrónicos"
        assert product.price == 1500.0
        assert product.unit == "unidad"

    def test_product_from_dict_string_conversion(self):
        """Test crear producto desde diccionario."""
        data = {
            "id": "p2",
            "name": "Producto B",
            "category": "Ropa",
            "price": "2500.50",
            "unit": "pieza"
        }
        product = Product.from_dict(data)
        assert product.id == "p2"
        assert product.name == "Producto B"
        assert product.category == "Ropa"
        assert product.price == 2500.50  # Convertido a float
        assert product.unit == "pieza"

    def test_product_to_dict_complete(self):
        """Test convertir producto a diccionario."""
        product = Product(
            id="p3",
            name="Producto C",
            category="Hogar",
            price=3000.75,
            unit="kit"
        )
        result = product.to_dict()
        expected = {
            "id": "p3",
            "name": "Producto C",
            "category": "Hogar",
            "price": 3000.75,
            "unit": "kit"
        }
        assert result == expected


class TestDirectSalesReport:
    """Tests directos para SalesReport."""

    def test_sales_report_creation_complete(self):
        """Test creación completa de reporte de ventas."""
        from datetime import datetime
        
        sales_report = SalesReport(
            ventas_totales=150000.0,
            pedidos=10,
            productos=[],
            grafico=[50000, 100000, 150000],
            periodo="2024-01-01 - 2024-03-31",
            vendor_id="v1",
            period_type="trimestral",
            generated_at=datetime.now().isoformat()
        )
        assert sales_report.ventas_totales == 150000.0
        assert sales_report.pedidos == 10
        assert sales_report.productos == []
        assert sales_report.grafico == [50000, 100000, 150000]
        assert sales_report.periodo == "2024-01-01 - 2024-03-31"
        assert sales_report.vendor_id == "v1"
        assert sales_report.period_type == "trimestral"

    def test_sales_report_from_dict_complete(self):
        """Test crear reporte desde diccionario."""
        data = {
            'ventasTotales': 200000.0,
            'pedidos': 15,
            'productos': [
                {
                    'nombre': 'Producto A',
                    'ventas': 100000.0,
                    'cantidad': 50
                },
                {
                    'nombre': 'Producto B',
                    'ventas': 100000.0,
                    'cantidad': 25
                }
            ],
            'grafico': [60000, 120000, 200000],
            'periodo': '2024-04-01 - 2024-06-30'
        }
        
        sales_report = SalesReport.from_dict(data, "v2", "trimestral")
        
        assert sales_report.ventas_totales == 200000.0
        assert sales_report.pedidos == 15
        assert len(sales_report.productos) == 2
        assert sales_report.productos[0].nombre == "Producto A"
        assert sales_report.productos[0].ventas == 100000.0
        assert sales_report.productos[0].cantidad == 50
        assert sales_report.grafico == [60000, 120000, 200000]
        assert sales_report.periodo == '2024-04-01 - 2024-06-30'
        assert sales_report.vendor_id == "v2"
        assert sales_report.period_type == "trimestral"

    def test_sales_report_to_dict_complete(self):
        """Test convertir reporte a diccionario."""
        from datetime import datetime
        
        sales_report = SalesReport(
            ventas_totales=175000.0,
            pedidos=12,
            productos=[],
            grafico=[70000, 140000, 175000],
            periodo="2024-07-01 - 2024-09-30",
            vendor_id="v3",
            period_type="trimestral"
        )
        
        result = sales_report.to_dict()
        
        assert result['vendor_id'] == "v3"
        assert result['period_type'] == "trimestral"
        assert result['ventasTotales'] == 175000.0
        assert result['pedidos'] == 12
        assert result['productos'] == []
        assert result['grafico'] == [70000, 140000, 175000]
        assert result['periodo'] == "2024-07-01 - 2024-09-30"
        assert 'generated_at' in result
