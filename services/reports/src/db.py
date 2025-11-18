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

def _get_users_service_base_url() -> str:
    """Obtiene la URL base del Users Service desde variables de entorno."""
    return os.getenv('USERS_SERVICE_URL', 'http://MediSu-MediS-5XPY2MhrDivI-109634141.us-east-1.elb.amazonaws.com/')


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
    result = _http_get(url)
    if result:
        products_count = len(result.get('products', []))
        logger.info(f"Plan obtenido por ID {plan_id}: tiene {products_count} productos")
        if products_count > 0:
            logger.info(f"Productos del plan {plan_id}: {[{'product_id': p.get('product_id'), 'individual_goal': p.get('individual_goal')} for p in result.get('products', [])]}")
    else:
        logger.warning(f"No se pudo obtener plan {plan_id} desde {url}")
    return result


def _get_plans_active_by_params(region: str, quarter: str, year: int) -> List[Dict[str, Any]]:
    """Obtiene todos los planes activos que coinciden con los parámetros."""
    base = _get_offer_manager_base_url().rstrip('/')
    url = f"{base}/offers/plans"
    data = _http_get(url, params={"region": region, "quarter": quarter, "year": year})
    if not data:
        logger.warning(f"No se encontraron planes para región={region}, quarter={quarter}, year={year}")
        return []
    
    # Filtrar por quarter/year exactos y solo activos
    if isinstance(data, list):
        filtered = [
            item for item in data
            if str(item.get('quarter')).upper() == str(quarter).upper()
            and int(item.get('year')) == int(year)
            and item.get('is_active') is True
        ]
        return filtered
    elif isinstance(data, dict) and data.get('is_active') is True:
        return [data]
    
    return []


def _totalize_plans(plans: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Totaliza múltiples planes activos en un solo plan consolidado.
    
    Retorna un diccionario con el plan totalizado y el número de planes.
    """
    if not plans:
        return None
    
    num_plans = len(plans)
    
    if num_plans == 1:
        # Si solo hay un plan, obtener sus productos y retornarlo
        plan = plans[0]
        if plan.get('plan_id'):
            full_plan = _get_plan_by_id(plan.get('plan_id'))
            if full_plan:
                full_plan['_num_plans_active'] = 1
                return full_plan
        plan['_num_plans_active'] = 1
        return plan
    
    # Totalizar múltiples planes
    logger.info(f"Totalizando {num_plans} planes activos")
    
    # Obtener productos de todos los planes
    all_products = {}  # {product_id: total_goal}
    total_goal_sum = 0.0
    plan_ids = []
    
    for plan in plans:
        plan_id = plan.get('plan_id')
        if plan_id:
            plan_ids.append(plan_id)
            full_plan = _get_plan_by_id(plan_id)
            if full_plan:
                total_goal_sum += float(full_plan.get('total_goal', 0))
                products = full_plan.get('products', [])
                for prod in products:
                    pid = int(prod.get('product_id', 0))
                    goal = float(prod.get('individual_goal', 0))
                    if pid > 0:
                        all_products[pid] = all_products.get(pid, 0.0) + goal
            else:
                # Si no se puede obtener el plan completo, usar el básico
                total_goal_sum += float(plan.get('total_goal', 0))
    
    # Construir plan totalizado
    totalized_plan = {
        'plan_id': plan_ids[0] if plan_ids else None,
        'region': plans[0].get('region'),
        'quarter': plans[0].get('quarter'),
        'year': plans[0].get('year'),
        'total_goal': total_goal_sum,
        'is_active': True,
        'products': [
            {'product_id': pid, 'individual_goal': goal}
            for pid, goal in all_products.items()
        ],
        '_num_plans_active': num_plans
    }
    
    logger.info(f"Plan totalizado: total_goal={total_goal_sum}, productos={len(all_products)}, num_plans={num_plans}")
    return totalized_plan


def _get_plan_by_params(region: str, quarter: str, year: int) -> Optional[Dict[str, Any]]:
    """Obtiene y totaliza todos los planes activos que coinciden con los parámetros."""
    active_plans = _get_plans_active_by_params(region, quarter, year)
    if not active_plans:
        return None
    
    # Totalizar todos los planes activos
    return _totalize_plans(active_plans)


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
    """Calcula el status basado en el porcentaje de cumplimiento (0-1)."""
    if pct >= 1.0:
        return 'verde'
    if pct >= 0.6:
        return 'amarillo'
    return 'rojo'


def _status_from_contribution_pct(contribution_pct: float) -> str:
    """Calcula el status basado en el porcentaje de contribución a la región (0-1).
    
    Umbrales:
    - Verde: >= 0.5 (>= 50% de contribución a la región)
    - Amarillo: >= 0.3 y < 0.5 (>= 30% y < 50%)
    - Rojo: < 0.3 (< 30%)
    """
    if contribution_pct >= 0.5:
        return 'verde'
    if contribution_pct >= 0.3:
        return 'amarillo'
    return 'rojo'


def _normalize_region(region: str) -> str:
    """Normaliza una región para comparación (case-insensitive, sin espacios)."""
    if not region:
        return ""
    return region.strip().upper()


def _get_vendor_region(vendor_id: int) -> Optional[str]:
    """Obtiene la región (zone) del vendedor desde el servicio Users mediante HTTP."""
    base = _get_users_service_base_url().rstrip('/')
    url = f"{base}/users/sellers/{vendor_id}"
    result = _http_get(url)
    if result and result.get('success') and result.get('data'):
        # El endpoint devuelve: {"success": true, "data": {"id": 2, "name": "...", "region": "Norte", ...}}
        return result['data'].get('region')
    logger.warning(f"No se pudo obtener región del vendedor {vendor_id} desde {url}")
    return None


def _get_sellers_by_region(region: str) -> List[int]:
    """Obtiene los seller_ids de todos los vendedores de una región específica."""
    base = _get_users_service_base_url().rstrip('/')
    url = f"{base}/users/sellers"
    result = _http_get(url)
    if not result or not result.get('success') or not result.get('data'):
        logger.warning(f"No se pudieron obtener sellers desde {url}")
        return []
    
    sellers = result.get('data', [])
    seller_ids = []
    region_normalized = _normalize_region(region)
    
    for seller in sellers:
        seller_region = seller.get('region')
        if seller_region and _normalize_region(seller_region) == region_normalized:
            seller_ids.append(int(seller.get('id')))
    
    logger.info(f"Encontrados {len(seller_ids)} sellers en región '{region}': {seller_ids}")
    return seller_ids


def _query_sales_by_region(seller_ids: List[int], start_date: date, end_date: date) -> Optional[Dict[str, Any]]:
    """Consulta las ventas totales de una lista de sellers en un período."""
    if not seller_ids:
        return {"pedidos": 0, "ventas_totales": 0}
    
    # Construir la lista de placeholders para la consulta IN
    placeholders = ','.join(['%s'] * len(seller_ids))
    query = f"""
    SELECT
      COUNT(o.order_id)  AS pedidos,
      COALESCE(SUM(o.total_value), 0) AS ventas_totales
    FROM orders.orders o
    WHERE o.status_id = 3
      AND o.seller_id IN ({placeholders})
      AND o.creation_date BETWEEN %s AND %s
    """
    params = tuple(seller_ids) + (start_date, end_date)
    return execute_query(query, params, fetch_one=True)


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

    # 3) Ventas reales del vendedor
    totals = _query_sales_totals(int(vendor_id), start_date, end_date) or {"pedidos": 0, "ventas_totales": 0}
    by_product = _query_sales_by_product(int(vendor_id), start_date, end_date)

    # 3.1) Ventas por región (suma de todos los vendedores de la región)
    region_seller_ids = _get_sellers_by_region(region)
    region_totals = _query_sales_by_region(region_seller_ids, start_date, end_date) or {"pedidos": 0, "ventas_totales": 0}
    num_sellers_region = len(region_seller_ids) if region_seller_ids else 1

    # 4) Metas por producto y total
    # Estructura esperada desde Offer Manager: products: [{product_id, individual_goal}], total_goal
    plan_products = plan.get('products') or plan.get('plan_products') or []
    num_plans_active = plan.get('_num_plans_active', 1)
    logger.info(f"Plan obtenido - plan_id: {plan.get('plan_id')}, total_goal: {plan.get('total_goal')}, productos en plan: {len(plan_products)}, num_plans: {num_plans_active}")
    logger.info(f"Productos del plan: {plan_products}")
    goals_by_product = {int(p.get('product_id')): float(p.get('individual_goal', 0)) for p in plan_products if p.get('product_id') is not None}
    logger.info(f"Metas por producto mapeadas: {goals_by_product}")
    total_goal = float(plan.get('total_goal') or 0)
    
    # 4.1) Calcular meta individual del vendedor
    # total_goal está en centenas, dividir entre número de sellers
    total_goal_vendor = total_goal / num_sellers_region if num_sellers_region > 0 else total_goal

    # 5) Calcular cumplimiento por producto
    compliance_products: List[Dict[str, Any]] = []
    for row in by_product:
        pid = int(row['product_id'])
        sales_amount = float(row['ventas'] or 0)
        goal = float(goals_by_product.get(pid, 0))
        # Calcular meta individual del producto para el vendedor
        goal_vendor = goal / num_sellers_region if num_sellers_region > 0 and goal > 0 else 0.0
        # Calcular ratio (0-1) para status, pero mostrar como valor absoluto en JSON (1.0 = 100%, 2.1 = 210%)
        pct_ratio = (sales_amount / goal_vendor) if goal_vendor > 0 else 0.0
        pct = pct_ratio  # Mantener formato actual (2.1 = 210%)
        compliance_products.append({
            'product_id': pid,
            'goal': goal,  # Meta compartida del producto
            'goal_vendor': goal_vendor,  # Meta individual del vendedor
            'ventas': sales_amount,
            'cumplimiento_pct': pct,
            'status': _status_from_pct(pct_ratio)  # Usar ratio (0-1) para status
        })

    # 6) Cumplimiento total del vendedor (usando ventasTotales vs meta individual)
    ventas_totales_vendor = float(totals.get('ventas_totales') or 0)
    # Calcular ratio (0-1) para status: (1384.75 / (60.0 * 100)) = 0.2308
    total_pct_ratio = (ventas_totales_vendor / (total_goal_vendor * 100.0)) if total_goal_vendor > 0 else 0.0
    # Mostrar como porcentaje en JSON: 0.2308 * 100 = 23.08
    total_pct = total_pct_ratio * 100

    # 7) Cumplimiento por región (ventas totales de la región vs meta total del plan)
    # Obtener ventas totales de la región para el cálculo
    ventas_region = float(region_totals.get('ventas_totales') or 0)
    # El total_goal es la meta total de la región (suma de todos los planes)
    # Calcular cumplimiento de la región completa comparado con la meta total del plan
    # Ejemplo: (2664.55 / (300.0 * 100)) * 100 = 8.88%
    region_pct_ratio = (ventas_region / (total_goal * 100.0)) if total_goal > 0 else 0.0
    # Mostrar como porcentaje en JSON: 0.0888 * 100 = 8.88
    region_pct = region_pct_ratio * 100

    result = {
        'vendor_id': int(vendor_id),
        'region': region,
        'period_start': start_date.isoformat(),
        'period_end': end_date.isoformat(),
        'pedidos': int(totals.get('pedidos') or 0),
        'ventasTotales': ventas_totales_vendor,
        'ventas_region': ventas_region,
        'total_goal': total_goal,
        'total_goal_vendor': round(total_goal_vendor, 1),
        'num_sellers_region': num_sellers_region,
        'num_plans_active': num_plans_active,
        'cumplimiento_total_pct': round(total_pct, 2),
        'status': _status_from_pct(total_pct_ratio),  # Usar ratio (0-1) para status
        'cumplimiento_region_pct': round(region_pct, 2),
        'status_region': _status_from_pct(region_pct_ratio),  # Cumplimiento de la región vs meta total
        'detalle_productos': compliance_products
    }

    return result