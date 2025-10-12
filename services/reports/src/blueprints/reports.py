"""Blueprint para endpoints de reportes."""

from flask import Blueprint, jsonify, request
from ..db import (
    get_vendors, 
    get_periods, 
    get_sales_report_data, 
    validate_sales_data_availability
)
from ..models.vendor import Vendor
from ..models.sales_report import SalesReport

reports_bp = Blueprint('reports', __name__)


@reports_bp.get('/vendors')
def get_vendors_endpoint():
    """Obtiene la lista de vendedores disponibles."""
    try:
        vendors_data = get_vendors()
        if not vendors_data:
            return jsonify({
                'success': False,
                'message': 'Error cargando datos de vendedores'
            }), 500
        
        vendors = [Vendor.from_dict(vendor) for vendor in vendors_data]
        
        return jsonify({
            'success': True,
            'data': [vendor.to_dict() for vendor in vendors]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo vendedores: {str(e)}'
        }), 500


@reports_bp.get('/periods')
def get_periods_endpoint():
    """Obtiene los períodos disponibles para reportes."""
    try:
        periods = get_periods()
        return jsonify({
            'success': True,
            'data': periods
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error obteniendo períodos: {str(e)}'
        }), 500


@reports_bp.post('/sales-report')
def generate_sales_report():
    """Genera el reporte de ventas por vendedor y período."""
    try:
        # Obtener datos del request
        data = request.get_json()
        vendor_id = data.get('vendor_id')
        period = data.get('period')
        
        # Validar campos obligatorios
        if not vendor_id or not period:
            return jsonify({
                'success': False,
                'message': 'Campo obligatorio',
                'error_type': 'validation_error'
            }), 400
        
        # Obtener datos del reporte
        report_data = get_sales_report_data(vendor_id, period)
        
        if not report_data:
            return jsonify({
                'success': False,
                'message': '¡Ups! No se encontraron datos para este período',
                'error_type': 'no_data'
            }), 404
        
        # Crear modelo de reporte
        sales_report = SalesReport.from_dict(report_data, vendor_id, period)
        
        return jsonify({
            'success': True,
            'data': sales_report.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': '¡Ups! Hubo un error al generar el reporte. Intenta nuevamente',
            'error_type': 'server_error'
        }), 500


@reports_bp.post('/sales-report/validate')
def validate_sales_data():
    """Valida si existen datos para un vendedor y período específico."""
    try:
        data = request.get_json()
        vendor_id = data.get('vendor_id')
        period = data.get('period')
        
        if not vendor_id or not period:
            return jsonify({
                'success': False,
                'has_data': False,
                'message': 'Campos requeridos no proporcionados'
            }), 400
        
        has_data = validate_sales_data_availability(vendor_id, period)
        
        return jsonify({
            'success': True,
            'has_data': has_data,
            'message': 'Datos disponibles' if has_data else 'No hay datos para este período'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'has_data': False,
            'message': 'Error validando datos'
        }), 500


@reports_bp.get('/health')
def health_check():
    """Endpoint para verificar el estado del servidor."""
    from datetime import datetime
    
    return jsonify({
        'success': True,
        'message': 'Servidor funcionando correctamente',
        'timestamp': datetime.now().isoformat()
    })
