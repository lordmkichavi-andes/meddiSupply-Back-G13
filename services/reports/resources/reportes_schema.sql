-- =====================================================
-- ESQUEMA REPORTES PARA HU043 (MVP): CUMPLIMIENTO DE METAS
-- Base de datos: medisupplydb (donde está conectado Reports)
-- Solo tablas indispensables para metas vs ventas
-- =====================================================

CREATE SCHEMA IF NOT EXISTS reportes;

-- =====================================================
-- 1) TABLAS DE VENTAS (Snapshot de datos de Orders)
-- =====================================================

-- Tabla principal de ventas por vendedor y período
CREATE TABLE IF NOT EXISTS reportes.sales (
    id BIGSERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    period_type TEXT NOT NULL CHECK (period_type IN ('bimonthly', 'quarterly', 'semiannual', 'annual')),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_orders INTEGER NOT NULL DEFAULT 0,
    total_sales NUMERIC(14,2) NOT NULL DEFAULT 0,
    generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (vendor_id, period_type, period_start, period_end)
);

CREATE INDEX IF NOT EXISTS idx_sales_vendor_period ON reportes.sales (vendor_id, period_type, period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_sales_period_dates ON reportes.sales (period_start, period_end);

-- Detalle de ventas por producto (snapshot)
CREATE TABLE IF NOT EXISTS reportes.sales_products (
    id BIGSERIAL PRIMARY KEY,
    sale_id BIGINT NOT NULL REFERENCES reportes.sales(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,  -- Snapshot para no depender de joins históricos
    quantity BIGINT NOT NULL DEFAULT 0,
    sales NUMERIC(14,2) NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_sales_products_sale ON reportes.sales_products (sale_id);
CREATE INDEX IF NOT EXISTS idx_sales_products_product ON reportes.sales_products (product_id);

-- 2) TABLAS DE METAS (Snapshot de Offer Manager)

-- Snapshot de planes de venta consumidos desde Offer Manager
CREATE TABLE IF NOT EXISTS reportes.plan_snapshots (
    plan_snapshot_id BIGSERIAL PRIMARY KEY,
    plan_id INTEGER,  -- ID real del plan en offers.sales_plans (referencia externa)
    region TEXT NOT NULL,
    quarter TEXT,  -- Q1, Q2, Q3, Q4
    year INTEGER NOT NULL,
    total_goal NUMERIC(18,2) NOT NULL,
    source_service TEXT DEFAULT 'offer_manager',
    fetched_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_plan_snapshots_region_quarter_year ON reportes.plan_snapshots (region, quarter, year);
CREATE INDEX IF NOT EXISTS idx_plan_snapshots_time ON reportes.plan_snapshots (year, quarter);

-- Detalle de metas por producto del plan (snapshot)
CREATE TABLE IF NOT EXISTS reportes.plan_snapshot_products (
    id BIGSERIAL PRIMARY KEY,
    plan_snapshot_id BIGINT NOT NULL REFERENCES reportes.plan_snapshots(plan_snapshot_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,  -- Snapshot
    individual_goal NUMERIC(18,2) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_plan_snapshot_products_plan ON reportes.plan_snapshot_products (plan_snapshot_id);
CREATE INDEX IF NOT EXISTS idx_plan_snapshot_products_product ON reportes.plan_snapshot_products (product_id);

-- 3) TABLAS DE CUMPLIMIENTO (Resultados calculados HU043)

-- Resultados de cumplimiento por vendedor y período
CREATE TABLE IF NOT EXISTS reportes.compliance_results (
    compliance_id BIGSERIAL PRIMARY KEY,
    vendor_id INTEGER NOT NULL,
    period_type TEXT NOT NULL CHECK (period_type IN ('bimonthly', 'quarterly', 'semiannual', 'annual')),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    plan_snapshot_id BIGINT NOT NULL REFERENCES reportes.plan_snapshots(plan_snapshot_id),
    total_goal NUMERIC(18,2) NOT NULL,
    total_sales NUMERIC(14,2) NOT NULL,
    compliance_pct NUMERIC(5,2) NOT NULL,  -- Porcentaje 0-100
    status TEXT NOT NULL CHECK (status IN ('ok', 'warning', 'alert')),  -- Verde/Amarillo/Rojo
    generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (vendor_id, period_type, period_start, period_end, plan_snapshot_id)
);

CREATE INDEX IF NOT EXISTS idx_compliance_vendor_period ON reportes.compliance_results (vendor_id, period_type, period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_compliance_status ON reportes.compliance_results (status);
CREATE INDEX IF NOT EXISTS idx_compliance_generated_at ON reportes.compliance_results (generated_at DESC);

-- Cumplimiento desglosado por producto
CREATE TABLE IF NOT EXISTS reportes.compliance_products (
    id BIGSERIAL PRIMARY KEY,
    compliance_id BIGINT NOT NULL REFERENCES reportes.compliance_results(compliance_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    goal NUMERIC(18,2) NOT NULL,
    sales NUMERIC(14,2) NOT NULL,
    compliance_pct NUMERIC(5,2) NOT NULL,  -- 0-100
    status TEXT NOT NULL CHECK (status IN ('ok', 'warning', 'alert'))
);

CREATE INDEX IF NOT EXISTS idx_compliance_products_parent ON reportes.compliance_products (compliance_id);
CREATE INDEX IF NOT EXISTS idx_compliance_products_product ON reportes.compliance_products (product_id);
CREATE INDEX IF NOT EXISTS idx_compliance_products_status ON reportes.compliance_products (status);

-- =====================================================
-- COMENTARIOS EXPLICATIVOS
-- =====================================================

COMMENT ON SCHEMA reportes IS 'Esquema para reportes de ventas y cumplimiento de metas. HU042 y HU043.';

COMMENT ON TABLE reportes.sales IS 'Snapshot de ventas agregadas por vendedor y período. Usado para HU042.';
COMMENT ON TABLE reportes.sales_products IS 'Detalle de ventas por producto. Snapshot para evitar joins históricos.';

COMMENT ON TABLE reportes.plan_snapshots IS 'Snapshot de planes de venta consumidos desde Offer Manager. Para HU043.';
COMMENT ON TABLE reportes.plan_snapshot_products IS 'Metas individuales por producto del plan. Snapshot para HU043.';

COMMENT ON TABLE reportes.compliance_results IS 'Resultados calculados de cumplimiento de metas vs ventas. HU043.';
COMMENT ON TABLE reportes.compliance_products IS 'Cumplimiento desglosado por producto. HU043.';

-- Fin de MVP: se omitieron tablas opcionales (gráfico, auditoría) para simplificar

