"""Conector a base de datos transaccional para el servicio de reportes."""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Any, Optional, List, Dict
import logging
import requests
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class RegionMismatchError(Exception):
    """Excepción cuando la región proporcionada no coincide con la región del vendedor."""
    pass


def get_connection():
    """Obtiene conexión a la base de datos transaccional."""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            port=os.getenv('DB_PORT', 5432),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD'),
            sslmode=os.getenv('DB_SSLMODE', 'require')
        )
        return conn
    except Exception as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        return None


def execute_query(query: str, params = None, fetch_one: bool = False, fetch_all: bool = False) -> Any:
    """Ejecuta una consulta SQL y retorna el resultado."""
    conn = None
    try:
        conn = get_connection()
        if not conn:
            return None
            
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.rowcount
                
    except Exception as e:
        logger.error(f"Error ejecutando consulta: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()


def get_vendors() -> List[Dict[str, Any]]:
    """Obtiene todos los vendedores disponibles."""
    query = """
    SELECT
    s.seller_id AS id, -- ID del vendedor
    u.name || ' ' || u.last_name AS name, -- Nombre y apellido
    u.email AS email,
    s.zone AS region, -- Zona de trabajo del vendedor
    u.active AS active -- Estado de actividad del usuario
    FROM
        users.sellers s
    JOIN
        users.users u ON s.user_id = u.user_id
    ORDER BY
    name
    """
    result = execute_query(query, fetch_all=True)
    return result or []


def get_products() -> List[Dict[str, Any]]:
    """Obtiene todos los productos disponibles."""
    query = """
    SELECT
    p.product_id AS id, -- ID del Producto
    p.name AS name, -- Nombre del Producto
    c.name AS category, -- Nombre de la Categoría
    p.value AS price, -- Precio del Producto (el campo 'value' es el precio en tu esquema)
    u.name AS unit -- Nombre de la Unidad de Medida
    FROM
        products.Products p
    JOIN
        products.Category c ON p.category_id = c.category_id
    JOIN
        products.units u ON p.unit_id = u.unit_id
    ORDER BY
        name
    """
    result = execute_query(query, fetch_all=True)
    return result or []


def get_periods() -> List[Dict[str, str]]:
    """Obtiene los períodos disponibles para reportes."""
    return [
        {'value': 'bimestral', 'label': 'Bimestral'},
        {'value': 'trimestral', 'label': 'Trimestral'},
        {'value': 'semestral', 'label': 'Semestral'},
        {'value': 'anual', 'label': 'Anual'}
    ]


def get_sales_report_data(vendor_id: str, period: str) -> Optional[Dict[str, Any]]:
    """Obtiene datos de ventas para un vendedor y período (HU042)."""
    try:
        # 1) Calcular rango de fechas según periodo
        today = datetime.today().date()

        def start_of_month(d: date) -> date:
            return date(d.year, d.month, 1)

        def quarter_bounds(d: date) -> (date, date):
            q = (d.month - 1) // 3 + 1
            start_month = 3 * (q - 1) + 1
            start = date(d.year, start_month, 1)
            end = (start + relativedelta(months=3)) - relativedelta(days=1)
            return start, end

        period = (period or '').lower()
        if period == 'bimestral':
            period_end = today
            period_start = start_of_month(today - relativedelta(months=1))
            bucket = 'week'
        elif period == 'trimestral':
            period_start, period_end = quarter_bounds(today)
            bucket = 'month'
        elif period == 'semestral':
            period_end = today
            period_start = start_of_month(today - relativedelta(months=5))
            bucket = 'month'
        elif period == 'anual':
            period_start = date(today.year, 1, 1)
            period_end = date(today.year, 12, 31)
            bucket = 'month'
        else:
            # por defecto usar trimestral
            period_start, period_end = quarter_bounds(today)
            bucket = 'month'

        # 2) Totales ventas/pedidos
        sales_query = """
            SELECT
              COUNT(o.order_id)  AS pedidos,
              COALESCE(SUM(o.total_value), 0) AS ventas_totales
            FROM orders.orders o
            WHERE o.status_id = 3
              AND o.seller_id = %s
              AND o.creation_date BETWEEN %s AND %s
        """
        sales_result = execute_query(sales_query, (vendor_id, period_start, period_end), fetch_one=True) or {}

        # 3) Ventas por producto (con nombre)
        products_query = """
            SELECT
              p.name AS nombre,
              SUM(ol.quantity) AS cantidad,
              SUM(ol.quantity * ol.price_unit) AS ventas
            FROM orders.orders o
            JOIN orders.orderlines ol ON ol.order_id = o.order_id
            JOIN products.products p ON p.product_id = ol.product_id
            WHERE o.status_id = 3
              AND o.seller_id = %s
              AND o.creation_date BETWEEN %s AND %s
            GROUP BY p.name
            ORDER BY ventas DESC
        """
        products_result = execute_query(products_query, (vendor_id, period_start, period_end), fetch_all=True) or []

        # 4) Serie temporal (gráfico)
        chart_query = f"""
            SELECT
              DATE_TRUNC('{bucket}', o.creation_date) AS periodo,
              SUM(ol.quantity * ol.price_unit) AS ventas
            FROM orders.orders o
            JOIN orders.orderlines ol ON ol.order_id = o.order_id
            WHERE o.status_id = 3
              AND o.seller_id = %s
              AND o.creation_date BETWEEN %s AND %s
            GROUP BY 1
            ORDER BY 1
        """
        chart_rows = execute_query(chart_query, (vendor_id, period_start, period_end), fetch_all=True) or []

        # 5) Construir respuesta
        data: Dict[str, Any] = {
            'ventas_totales': float(sales_result.get('ventas_totales') or 0),
            'pedidos': int(sales_result.get('pedidos') or 0),
            'period_start': period_start.isoformat(),
            'period_end': period_end.isoformat(),
        }

        data['productos'] = [
            {
                'nombre': row['nombre'],
                'ventas': float(row['ventas'] or 0),
                'cantidad': int(row['cantidad'] or 0)
            }
            for row in products_result
        ]

        # Serie: periodo legible + ventas
        def fmt_period(v: Any) -> str:
            # psycopg2 RealDictCursor devuelve datetime/date; formatear YYYY-MM o YYYY-WW
            try:
                dt = v
                # usar year-week para bucket semana
                if bucket == 'week':
                    return dt.strftime('%Y-%W')
                return dt.strftime('%Y-%m')
            except Exception:
                return str(v)

        data['grafico'] = [
            {
                'periodo': fmt_period(row['periodo']),
                'ventas': float(row['ventas'] or 0)
            }
            for row in chart_rows
        ]

        data['periodo'] = f"{data['period_start']} - {data['period_end']}"
        data['ventasTotales'] = data['ventas_totales']
        return data
    except Exception as e:
        logger.error(f"Error construyendo reporte HU042: {e}")
        return None


def validate_sales_data_availability(vendor_id: str, period: str) -> bool:
    """Valida si existen datos para un vendedor y período específico."""
    # Mapear periodos a los valores de la base de datos
    period_mapping = {
        'bimestral': 'bimonthly',
        'trimestral': 'quarterly', 
        'semestral': 'semiannual',
        'anual': 'annual'
    }
    db_period = period_mapping.get(period, period)
    
    query = """
    SELECT COUNT(*) as count 
    FROM reportes.sales 
    WHERE vendor_id = %s AND period_type = %s
    """
    
    result = execute_query(query, (vendor_id, db_period), fetch_one=True)
    return result['count'] > 0 if result else False


# ==========================
# HU043 - CUMPLIMIENTO METAS
# ==========================

def _get_offer_manager_base_url() -> str:
    """Obtiene la URL base del Offer Manager desde variables de entorno."""
    # Permite configurar en entorno; fallback a localhost 8082 si no está.
    return os.getenv('OFFER_MANAGER_URL', 'http://MediSu-MediS-5XPY2MhrDivI-109634141.us-east-1.elb.amazonaws.com/')


def _get_products_base_url() -> str:
    """Obtiene la URL base del Products MS para enriquecimiento opcional."""
    return os.getenv('PRODUCTS_SERVICE_URL', 'http://MediSu-MediS-5XPY2MhrDivI-109634141.us-east-1.elb.amazonaws.com/')


def _http_get(url: str, params: Dict[str, Any] = None, timeout: int = 10) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(url, params=params, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        logger.warning(f"HTTP GET {url} -> {resp.status_code}")
        return None
    except Exception as e:
        logger.error(f"Error HTTP GET {url}: {e}")
        return None


def _get_plan_by_id(plan_id: int) -> Optional[Dict[str, Any]]:
    base = _get_offer_manager_base_url().rstrip('/')
    url = f"{base}/offers/plans/{plan_id}"
    return _http_get(url)


def _get_plan_by_params(region: str, quarter: str, year: int) -> Optional[Dict[str, Any]]:
    base = _get_offer_manager_base_url().rstrip('/')
    url = f"{base}/offers/plans"
    data = _http_get(url, params={"region": region, "quarter": quarter, "year": year})
    if not data:
        return None
    # Si la respuesta es lista, filtrar por quarter/year exactos y priorizar activo
    if isinstance(data, list):
        filtered = [
            item for item in data
            if str(item.get('quarter')).upper() == str(quarter).upper()
            and int(item.get('year')) == int(year)
        ]
        # Priorizar activo entre los filtrados; si no hay, tomar el primero filtrado
        for item in filtered:
            if item.get('is_active') is True:
                return item
        if filtered:
            return filtered[0]
        # Como último recurso, mantener la lógica previa (activo primero)
        for item in data:
            if item.get('is_active') is True:
                return item
        return data[0] if data else None
    return data


def _quarter_to_dates(quarter: str, year: int) -> Optional[Dict[str, date]]:
    q = quarter.upper()
    if q == 'Q1':
        start = date(year, 1, 1)
    elif q == 'Q2':
        start = date(year, 4, 1)
    elif q == 'Q3':
        start = date(year, 7, 1)
    elif q == 'Q4':
        start = date(year, 10, 1)
    else:
        return None
    end = (start + relativedelta(months=3)) - relativedelta(days=1)
    return {"start": start, "end": end}


def _query_sales_totals(vendor_id: int, start_date: date, end_date: date) -> Optional[Dict[str, Any]]:
    query = """
    SELECT
      COUNT(o.order_id)  AS pedidos,
      COALESCE(SUM(o.total_value), 0) AS ventas_totales
    FROM orders.orders o
    WHERE o.status_id = 3
      AND o.seller_id = %s
      AND o.creation_date BETWEEN %s AND %s
    """
    return execute_query(query, (vendor_id, start_date, end_date), fetch_one=True)


def _query_sales_by_product(vendor_id: int, start_date: date, end_date: date) -> List[Dict[str, Any]]:
    query = """
    SELECT
      ol.product_id,
      SUM(ol.quantity)                 AS cantidad,
      SUM(ol.quantity * ol.price_unit) AS ventas
    FROM orders.orders o
    JOIN orders.orderlines ol ON ol.order_id = o.order_id
    WHERE o.status_id = 3
      AND o.seller_id = %s
      AND o.creation_date BETWEEN %s AND %s
    GROUP BY ol.product_id
    ORDER BY ventas DESC
    """
    rows = execute_query(query, (vendor_id, start_date, end_date), fetch_all=True)
    return rows or []


def _status_from_pct(pct: float) -> str:
    if pct >= 1.0:
        return 'verde'
    if pct >= 0.6:
        return 'amarillo'
    return 'rojo'


def _get_vendor_region(vendor_id: int) -> Optional[str]:
    """Obtiene la región (zone) del vendedor desde la base de datos."""
    query = """
    SELECT s.zone AS region
    FROM users.sellers s
    WHERE s.seller_id = %s
    """
    result = execute_query(query, (vendor_id,), fetch_one=True)
    return result.get('region') if result else None


def get_sales_compliance(vendor_id: int,
                         plan_id: Optional[int] = None,
                         region: Optional[str] = None,
                         quarter: Optional[str] = None,
                         year: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Calcula cumplimiento de metas sin crear nuevas tablas.

    - Obtiene metas desde Offer Manager (por plan_id o por region/quarter/year).
    - Valida que el vendedor pertenezca a la región del plan.
    - Deriva rango de fechas del quarter/year del plan.
    - Consulta ventas totales y por producto en orders.*.
    - Calcula cumplimiento por producto y total.
    """
    # 0) Obtener región del vendedor
    vendor_region = _get_vendor_region(int(vendor_id))
    if not vendor_region:
        logger.warning(f"Vendedor {vendor_id} no encontrado")
        return None
    
    # 1) Obtener plan/meta
    plan = None
    if plan_id is not None:
        plan = _get_plan_by_id(int(plan_id))
        if plan:
            # Si se pasó plan_id, validar que la región coincida
            plan_region = plan.get('region')
            if plan_region and plan_region != vendor_region:
                raise RegionMismatchError(
                    f"El plan {plan_id} pertenece a la región '{plan_region}', "
                    f"pero el vendedor {vendor_id} pertenece a la región '{vendor_region}'. "
                    f"La región del plan debe coincidir con la región del vendedor."
                )
    elif region and quarter and year:
        # Si se proporciona región explícitamente, rechazar si no coincide
        if region != vendor_region:
            raise RegionMismatchError(
                f"La región proporcionada '{region}' no coincide con la región del vendedor '{vendor_region}'. "
                f"El vendedor {vendor_id} pertenece a la región '{vendor_region}'."
            )
        plan = _get_plan_by_params(region, quarter, int(year))
    elif quarter and year:
        # Si no se proporciona región, usar la región del vendedor automáticamente
        plan = _get_plan_by_params(vendor_region, quarter, int(year))
        region = vendor_region
    
    if not plan:
        return None
    
    # Validación final: asegurar que la región del plan coincide con la del vendedor
    plan_region = plan.get('region')
    if plan_region and plan_region != vendor_region:
        raise RegionMismatchError(
            f"El plan encontrado pertenece a la región '{plan_region}', "
            f"pero el vendedor {vendor_id} pertenece a la región '{vendor_region}'. "
            f"La región del plan debe coincidir con la región del vendedor."
        )

    # 2) Derivar fechas del plan
    plan_quarter = plan.get('quarter') or quarter
    plan_year = int(plan.get('year') or (year or 0))
    dates = _quarter_to_dates(plan_quarter, plan_year) if plan_quarter and plan_year else None
    if not dates:
        return None
    start_date = dates['start']
    end_date = dates['end']

    # 3) Ventas reales
    totals = _query_sales_totals(int(vendor_id), start_date, end_date) or {"pedidos": 0, "ventas_totales": 0}
    by_product = _query_sales_by_product(int(vendor_id), start_date, end_date)

    # 4) Metas por producto y total
    # Estructura esperada desde Offer Manager: products: [{product_id, individual_goal}], total_goal
    plan_products = plan.get('products') or plan.get('plan_products') or []
    goals_by_product = {int(p.get('product_id')): float(p.get('individual_goal', 0)) for p in plan_products if p.get('product_id') is not None}
    total_goal = float(plan.get('total_goal') or 0)

    # 5) Calcular cumplimiento por producto
    compliance_products: List[Dict[str, Any]] = []
    sum_sales = 0.0
    for row in by_product:
        pid = int(row['product_id'])
        sales_amount = float(row['ventas'] or 0)
        goal = float(goals_by_product.get(pid, 0))
        sum_sales += sales_amount
        pct = (sales_amount / goal) if goal > 0 else 0.0
        compliance_products.append({
            'product_id': pid,
            'goal': goal,
            'ventas': sales_amount,
            'cumplimiento_pct': pct,
            'status': _status_from_pct(pct)
        })

    # 6) Cumplimiento total
    total_pct = (sum_sales / total_goal) if total_goal > 0 else 0.0
    result = {
        'vendor_id': int(vendor_id),
        'period_start': start_date.isoformat(),
        'period_end': end_date.isoformat(),
        'pedidos': int(totals.get('pedidos') or 0),
        'ventasTotales': float(totals.get('ventas_totales') or 0),
        'total_goal': total_goal,
        'cumplimiento_total_pct': total_pct,
        'status': _status_from_pct(total_pct),
        'detalle_productos': compliance_products
    }

    return result