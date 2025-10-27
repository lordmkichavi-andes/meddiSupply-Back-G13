-- Script SQL simplificado para el servicio de productos
-- Crear esquemas
CREATE SCHEMA IF NOT EXISTS products;
CREATE SCHEMA IF NOT EXISTS users;

-- Crear tabla de categorías
CREATE TABLE IF NOT EXISTS products.category (
    category_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL
);

-- Crear tabla de proveedores
CREATE TABLE IF NOT EXISTS products.providers (
    provider_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

-- Crear tabla de unidades
CREATE TABLE IF NOT EXISTS products.units (
    unit_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    symbol VARCHAR(10) NOT NULL,
    type VARCHAR(20) NOT NULL,
    active BOOLEAN DEFAULT true,
    creation_date TIMESTAMP DEFAULT NOW()
);

-- Crear tabla de bodegas
CREATE TABLE IF NOT EXISTS products.warehouses (
    warehouse_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(255)
);

-- Crear tabla de productos
CREATE TABLE IF NOT EXISTS products.products (
    product_id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    value FLOAT NOT NULL,
    image_url VARCHAR(255),
    provider_id INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'activo',
    category_id INTEGER NOT NULL,
    objective_profile VARCHAR(255) NOT NULL,
    unit_id INTEGER NOT NULL,
    creation_date TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (provider_id) REFERENCES products.providers(provider_id),
    FOREIGN KEY (category_id) REFERENCES products.category(category_id),
    FOREIGN KEY (unit_id) REFERENCES products.units(unit_id)
);

-- Crear tabla de stock de productos
CREATE TABLE IF NOT EXISTS products.productstock (
    stock_id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    quantity INT NOT NULL,
    lote VARCHAR(50) NOT NULL,
    warehouse_id INTEGER NOT NULL,
    provider_id INTEGER NOT NULL,
    country VARCHAR(50) NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products.products(product_id),
    FOREIGN KEY (warehouse_id) REFERENCES products.warehouses(warehouse_id),
    FOREIGN KEY (provider_id) REFERENCES products.providers(provider_id)
);

-- Crear tabla de usuarios
CREATE TABLE IF NOT EXISTS users.users (
    user_id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    password VARCHAR NOT NULL,
    identification VARCHAR UNIQUE NOT NULL,
    phone VARCHAR,
    email VARCHAR(150),
    active BOOLEAN DEFAULT TRUE,
    role VARCHAR NOT NULL
);

-- Crear tabla de uploads de productos
CREATE TABLE IF NOT EXISTS products.product_uploads (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(10) NOT NULL,
    file_size BIGINT NOT NULL,
    total_records INTEGER NOT NULL,
    successful_records INTEGER NOT NULL DEFAULT 0,
    failed_records INTEGER NOT NULL DEFAULT 0,
    state VARCHAR(20) NOT NULL DEFAULT 'procesando',
    start_date TIMESTAMP DEFAULT NOW(),
    end_date TIMESTAMP,
    user_id INTEGER NOT NULL,
    errores TEXT,
    FOREIGN KEY (user_id) REFERENCES users.users(user_id)
);

-- Crear tabla de detalles de upload
CREATE TABLE IF NOT EXISTS products.product_upload_details (
    id SERIAL PRIMARY KEY,
    upload_id INTEGER NOT NULL,
    row_id INTEGER NOT NULL,
    code VARCHAR(50),
    name VARCHAR(200),
    descroption TEXT,
    price FLOAT,
    category VARCHAR(100),
    minimum_stock INTEGER,
    measure_unit VARCHAR(50),
    status VARCHAR(20) NOT NULL,
    errors TEXT,
    product_id INTEGER,
    FOREIGN KEY (upload_id) REFERENCES products.product_uploads(id),
    FOREIGN KEY (product_id) REFERENCES products.products(product_id)
);

-- Crear tabla de historial de productos
CREATE TABLE IF NOT EXISTS products.product_history (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    previous_value FLOAT,
    new_value FLOAT,
    change_type VARCHAR(20) NOT NULL,
    update_date TIMESTAMP DEFAULT NOW(),
    user_id INTEGER NOT NULL,
    upload_id INTEGER,
    FOREIGN KEY (product_id) REFERENCES products.products(product_id),
    FOREIGN KEY (upload_id) REFERENCES products.product_uploads(id),
    FOREIGN KEY (user_id) REFERENCES users.users(user_id)
);

-- Insertar datos básicos
INSERT INTO products.category (category_id, name) VALUES
(1, 'MEDICATION'),
(2, 'SURGICAL_SUPPLIES'),
(3, 'REAGENTS'),
(4, 'EQUIPMENT'),
(5, 'OTHERS')
ON CONFLICT (category_id) DO NOTHING;

INSERT INTO products.providers (provider_id, name) VALUES
(1, 'PharmaGlobal Labs S.A.'),
(2, 'MedSupply Distributors'),
(3, 'TecnoHealth Solutions')
ON CONFLICT (provider_id) DO NOTHING;

INSERT INTO products.units (unit_id, name, symbol, type) VALUES
(1, 'Caja', 'Cj', 'cantidad'),
(2, 'Miligramo', 'mg', 'peso'),
(3, 'Mililitro', 'ml', 'volumen'),
(4, 'Unidad', 'u', 'cantidad'),
(5, 'Kit', 'Kit', 'cantidad')
ON CONFLICT (unit_id) DO NOTHING;

INSERT INTO products.warehouses (warehouse_id, name, location) VALUES
(1, 'BODEGA_CENTRAL', 'Calle 100 # 50-20, Bogotá'),
(2, 'BODEGA_OCCIDENTE', 'Carrera 80 # 12-45, Cali')
ON CONFLICT (warehouse_id) DO NOTHING;

INSERT INTO users.users (user_id, name, last_name, password, identification, phone, email, role) VALUES
(1, 'Admin', 'Root', 'hash_admin', '10000000', '3001001000', 'admin@medisales.com', 'ADMIN')
ON CONFLICT (user_id) DO NOTHING;
