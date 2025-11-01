"""Blueprint para ofertas/planes de venta."""

from flask import Blueprint, jsonify, request
from src.db import (
    get_products, 
    create_sales_plan, 
    get_sales_plans, 
    get_sales_plan_products,
    get_sales_plan_by_id,
)
from src.models import SalesPlan, SalesPlanProduct, Product
from src.services.sales_plan_service import SalesPlanService

offers_bp = Blueprint('offer_manager', __name__)


@offers_bp.get('/products')
def get_products_endpoint():
    """Obtener lista de productos para el selector."""
    try:
        products_data = get_products()
        products = [Product.from_dict(product) for product in products_data]
        return jsonify([product.to_dict() for product in products]), 200
    except Exception as e:
        return jsonify({"message": f"Error obteniendo productos: {str(e)}"}), 500


@offers_bp.get('/regions')
def get_regions_endpoint():
    """Obtener lista de regiones disponibles."""
    regions = SalesPlanService.get_region_options()
    return jsonify(regions), 200


@offers_bp.get('/quarters')
def get_quarters_endpoint():
    """Obtener lista de trimestres disponibles."""
    quarters = SalesPlanService.get_quarter_options()
    return jsonify(quarters), 200


@offers_bp.post('/plans')
def create_sales_plan_endpoint():
    """Crear un nuevo plan de venta."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"message": "Datos requeridos"}), 400
        
        # Validar datos usando el servicio
        validation_errors = SalesPlanService.validate_sales_plan_data(data)
        
        if validation_errors:
            return jsonify({
                "message": "Errores de validación",
                "errors": validation_errors
            }), 400
        
        # Validar consistencia de meta total
        consistency_errors = SalesPlanService.validate_total_goal_consistency(data)
        if consistency_errors:
            return jsonify({
                "message": "Errores de consistencia",
                "errors": consistency_errors
            }), 400
        
        # Crear el plan
        plan_data = {
            'region': data['region'],
            'quarter': data['quarter'],
            'year': data['year'],
            'total_goal': data['total_goal'],
            'created_by': data.get('created_by', 1),  # Por defecto admin
            'products': data['products']
        }
        
        plan_id = create_sales_plan(plan_data)
        
        if plan_id:
            return jsonify({
                "message": "¡Plan de venta creado exitosamente!",
                "plan_id": plan_id
            }), 201
        else:
            return jsonify({
                "message": "¡Ups! Hubo un problema al crear el plan. Intenta nuevamente en unos minutos"
            }), 500
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error creando plan de venta: {str(e)}", exc_info=True)
        return jsonify({
            "message": "¡Ups! Hubo un problema al crear el plan. Intenta nuevamente en unos minutos"
        }), 500


@offers_bp.get('/plans')
def get_sales_plans_endpoint():
    """Obtener planes de venta."""
    try:
        region = request.args.get('region', type=str)
        
        plans_data = get_sales_plans(region=region)
        plans = [SalesPlan.from_dict(plan) for plan in plans_data]
        
        return jsonify([plan.to_dict() for plan in plans]), 200
    except Exception as e:
        return jsonify({"message": f"Error obteniendo planes: {str(e)}"}), 500


@offers_bp.get('/plans/<int:plan_id>')
def get_sales_plan_endpoint(plan_id):
    """Obtener un plan de venta específico con sus productos."""
    try:
        # Obtener el plan directamente desde la base de datos
        plan_data = get_sales_plan_by_id(plan_id)
        if not plan_data:
            return jsonify({"message": "Plan no encontrado"}), 404

        # Obtener los productos del plan
        products_data = get_sales_plan_products(plan_id)
        plan_data['products'] = products_data

        plan = SalesPlan.from_dict(plan_data)
        return jsonify(plan.to_dict()), 200
        
    except Exception as e:
        return jsonify({"message": f"Error obteniendo plan: {str(e)}"}), 500


@offers_bp.get('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200

