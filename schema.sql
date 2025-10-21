-- Creación esquema de Productos
CREATE SCHEMA IF NOT EXISTS products;
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS orders;
-- Creación de la tabla 'Category' (Categoría)
-- Esta tabla almacena los tipos de categorías de productos.
 CREATE TABLE IF NOT EXISTS products.Category (
                          category_id INT PRIMARY KEY,
                          name VARCHAR(50) NOT NULL
);

-- Creación de la tabla 'Provider' (Proveedor)
-- Esta tabla se crea para soportar la relación con la tabla 'Product'.
 CREATE TABLE IF NOT EXISTS products.Provider (
                          provider_id SERIAL PRIMARY KEY,
                          name VARCHAR(100) NOT NULL
);

-- Creación de la tabla 'Product' (Producto)
-- Almacena la información de los productos, incluyendo su relación con la categoría y el proveedor.
CREATE TABLE products.Product (
    product_id SERIAL PRIMARY KEY,
    sku VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    value FLOAT NOT NULL,
    image_url VARCHAR(255),
    provider_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    objective_profile VARCHAR(255) NOT NULL,
    FOREIGN KEY (provider_id) REFERENCES products.Provider(provider_id),
    FOREIGN KEY (category_id) REFERENCES products.Category(category_id)
);

CREATE TABLE IF NOT EXISTS products.Warehouse (
    warehouse_id SERIAL PRIMARY KEY, -- Identificador único de la bodega
    name VARCHAR(100) NOT NULL,          -- Nombre de la bodega
    location VARCHAR(255)                -- Ubicación o dirección de la bodega (opcional)
);

CREATE TABLE IF NOT EXISTS products.Inventory (
    product_id SERIAL,
    warehouse_id INTEGER,
    stock_quantity INT NOT NULL DEFAULT 0, -- Cantidad de este producto en esta bodega
    PRIMARY KEY (product_id, warehouse_id), -- La clave primaria compuesta asegura que solo haya una entrada por producto/bodega
    FOREIGN KEY (product_id) REFERENCES products.Product(product_id),
    FOREIGN KEY (warehouse_id) REFERENCES products.Warehouse(warehouse_id)
);

-- Creación de la tabla 'ProductStock' (Inventario de Producto)
-- Almacena los registros de inventario para cada producto.
 CREATE TABLE IF NOT EXISTS products.ProductStock (
                              stock_id SERIAL PRIMARY KEY,
                              product_id INTEGER NOT NULL,
                              quantity INT NOT NULL,
                              lote VARCHAR(50) NOT NULL,
                              warehouse_id INTEGER NOT NULL,
                              country VARCHAR(50) NOT NULL,
                              FOREIGN KEY (product_id) REFERENCES products.Product(product_id),
                              FOREIGN KEY (warehouse_id) REFERENCES products.Warehouse(warehouse_id)
);

 CREATE TABLE IF NOT EXISTS products.State (
                         state_id SERIAL PRIMARY KEY,
                         name VARCHAR(50) NOT NULL UNIQUE
);
-- Crear tabla User


CREATE TABLE IF NOT EXISTS users.Users(
    user_id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    password VARCHAR NOT NULL,
    identification VARCHAR UNIQUE NOT NULL,
    phone VARCHAR,
    role VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS users.seller (
    seller_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL, -- Clave foránea 1:1 con users.Users
    zone VARCHAR(100) NOT NULL,      -- Zona de trabajo del vendedor
    -- NOTA: La FK a users.Users está comentada para evitar errores si users.Users no existe.
    FOREIGN KEY (user_id) REFERENCES users.Users(user_id) ON DELETE CASCADE
);



-- Crear tabla Client
CREATE TABLE IF NOT EXISTS users.Clientes (
    client_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    nit VARCHAR(50) UNIQUE,
    balance DECIMAL(15, 2) DEFAULT 0.00,
    perfil TEXT,
    seller_id INTEGER,
    address VARCHAR(255) NULL,
    latitude DECIMAL(10, 8) NULL,
    longitude DECIMAL(11, 8) NULL,
    FOREIGN KEY (seller_id) REFERENCES users.seller(seller_id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users.Users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS users.visits (
    visit_id SERIAL PRIMARY KEY,                       -- Identificador de la visita (visit_id: str)
    seller_id INTEGER NOT NULL,                           -- ID del usuario que realizó la visita (user_id: str)
    date DATE NOT NULL,                              -- Fecha en que se realizó la visita (date: Date)
    place TEXT,                                      -- Lugar o dirección de la visita (place: str)
    findings TEXT,                                   -- Hallazgos o notas de la visita (findings: str)

    -- Nuevo campo para la relación 1:N con Clientes
    client_id INTEGER NOT NULL,
    -- Relaciones
    FOREIGN KEY (client_id) REFERENCES users.Clientes(client_id) ON DELETE RESTRICT,
    FOREIGN KEY (seller_id) REFERENCES users.seller(seller_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS users.visit_product_suggestions (
    visit_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    PRIMARY KEY (visit_id, product_id),
    FOREIGN KEY (visit_id) REFERENCES users.visits(visit_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products.Product(product_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS users.visual_evidences (
    evidence_id SERIAL PRIMARY KEY,                    -- Identificador de la evidencia (evidence_id: str)
    type VARCHAR(100),                               -- Tipo de archivo (ej. 'photo', 'video') (type: str)
    url_file TEXT NOT NULL,                          -- URL del archivo de evidencia (url_file: str)
    description TEXT,                                -- Descripción de la evidencia (description: str)

    -- Clave foránea para la relación con Visit (1:N)
    visit_id INTEGER NOT NULL,
    FOREIGN KEY (visit_id) REFERENCES users.visits(visit_id) ON DELETE CASCADE
);

-- Creación de la tabla 'Order' (Pedido)
-- Almacena la cabecera del pedido y su información general.
 CREATE TABLE IF NOT EXISTS orders."Order" (
                          order_id SERIAL PRIMARY KEY,
                          user_id INTEGER, -- Asumiendo que hay una tabla 'User' o 'Customer' externa
                          creation_date DATE NOT NULL,
                          estimated_delivery_date DATE,
                          current_state_id INTEGER NOT NULL,
                          total_value FLOAT NOT NULL,

                          FOREIGN KEY (current_state_id) REFERENCES products.State(state_id),
                          FOREIGN KEY (user_id) REFERENCES users.Users(user_id)
);


-- Creación de la tabla 'OrderLine' (Línea de Pedido / Detalle)
-- Almacena los productos específicos dentro de un pedido, su cantidad y precio en el momento de la compra.
 CREATE TABLE IF NOT EXISTS orders.OrderLine (
                             order_line_id SERIAL PRIMARY KEY,
                             order_id INTEGER NOT NULL,
                             product_id INTEGER NOT NULL,
                             quantity INT NOT NULL,
                             value_at_time_of_order FLOAT NOT NULL,

                             FOREIGN KEY (order_id) REFERENCES orders."Order"(order_id),
                             FOREIGN KEY (product_id) REFERENCES products.Product(product_id)
);


CREATE INDEX IF NOT EXISTS idx_order_state ON orders."Order"(current_state_id);
CREATE INDEX IF NOT EXISTS idx_line_order ON orders.OrderLine(order_id);
CREATE INDEX IF NOT EXISTS idx_line_product ON orders.OrderLine(product_id);
-- --------------------------------------------------------------------------------
-- SCRIPT DE INSERCIÓN DE DATOS DE PRUEBA (MEDICAMENTOS Y LOGÍSTICA)
-- NOTA: Asume que las tablas con SERIAL PRIMARY KEY se inician en 1.
-- --------------------------------------------------------------------------------

-- --------------------------------------------------------------------------------
-- 1. TABLAS DE PRODUCTOS (products SCHEMA)
-- --------------------------------------------------------------------------------

-- PRODUCTS.CATEGORY (Categorías de la imagen)
INSERT INTO products.Category (category_id, name) VALUES
(1, 'MEDICATION'),
(2, 'SURGICAL_SUPPLIES'),
(3, 'REAGENTS'),
(4, 'EQUIPMENT'),
(5, 'OTHERS');

-- PRODUCTS.PROVIDER (Proveedores)
INSERT INTO products.Provider (provider_id, name) VALUES
(1, 'PharmaGlobal Labs S.A.'),
(2, 'MedSupply Distributors'),
(3, 'TecnoHealth Solutions');

-- PRODUCTS.WAREHOUSE (Bodegas)
INSERT INTO products.Warehouse (name, location) VALUES
('BODEGA_CENTRAL', 'Calle 100 # 50-20, Bogotá'),
('BODEGA_OCCIDENTE', 'Carrera 80 # 12-45, Cali');

-- PRODUCTS.PRODUCT (Productos)
INSERT INTO products.Product (sku, name, value, provider_id, category_id, objective_profile) VALUES
('MED-001', 'Acetaminofén 500mg (Caja x100)', 8.50, 1, 1, 'Droguerías, Farmacias'),
('MED-002', 'Amoxicilina 250mg/5ml (Frasco)', 12.30, 1, 1, 'Pediátrico, Clínicas'),
('SURG-001', 'Kit Sutura Desechable', 25.00, 2, 2, 'Hospitales, Salas de Cirugía'),
('SURG-002', 'Guantes Nitrilo Talla M (Caja x50)', 4.99,2, 2, 'Clínicas, Consultorios'),
('REAG-001', 'Tiras Reactivas Glucosa (Caja x50)', 15.75, 3, 3, 'Laboratorios Clínicos'),
('EQUIP-001', 'Termómetro Infrarrojo Digital', 45.90, 3, 4, 'Clínicas, Hospitales');

-- PRODUCTS.INVENTORY (Inventario en Bodegas)
INSERT INTO products.Inventory (product_id, warehouse_id, stock_quantity) VALUES
(1, 1, 5000),
(2, 1, 2500),
(3, 2, 1000),
(4, 1, 8000),
(5, 2, 300),
(6, 1, 500);

-- PRODUCTS.PRODUCTSTOCK (Stock Detallado)
-- Asumiendo que products.Product.product_id (SERIAL) comienza en 1
INSERT INTO products.ProductStock (product_id, quantity, lote, warehouse_id, country) VALUES
(1, 2500, 'LOTE2025A', 1, 'COL'),
(1, 2500, 'LOTE2025B', 1, 'COL'),
(3, 1000, 'LOTE456', 2, 'ECU'),
(4, 5000, 'LOTE789', 1, 'PER');

-- PRODUCTS.STATE (Estados de Pedido)
INSERT INTO products.State (state_id, name) VALUES
(1, 'Created'),
(2, 'In Progress'),
(3, 'Delivered'),
(4, 'Canceled');

-- --------------------------------------------------------------------------------
-- 2. TABLAS DE USUARIOS Y CLIENTES (users SCHEMA)
-- --------------------------------------------------------------------------------

-- USERS.USERS (Usuarios)
INSERT INTO users.Users (name, last_name, password, identification, phone, role) VALUES
( 'Juan', 'Perez', 'hash123', '10101010', '3001112233', 'ADMIN'),
( 'Maria', 'Gomez', 'hash456', '20202020', '3104445566', 'SELLER'), -- Visitador Médico
( 'Carlos', 'Lopez', 'R7hash', '30303030', '3207778899', 'CLIENT'), -- Dueño Farmacia A
( 'Laura', 'Diaz', 'A9hash', '40404040', '3019990011', 'CLIENT'); -- Gerente Hospital X

-- NUEVO: USERS.SELLER (Vendedores)
INSERT INTO users.seller (user_id, zone) VALUES
(2, 'ZONA CENTRO-NORTE'); -- Maria Gomez (user_id 2) es la vendedora 1

-- USERS.CLIENTES (Clientes/Puntos de Venta) - Modificado para incluir seller_id
INSERT INTO users.Clientes (user_id, nit, balance, perfil, seller_id, address, latitude, longitude) VALUES
(3, '800123456-1', 1500.50, 'Farmacia de Barrio A', 1, 'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370),
(4, '900789012-5', 52000.75, 'Hospital Nivel 3 X', 1, 'Carrera 7 # 120-50, Bogotá', 4.697500, -74.037500),
(7, '850001002-3', 15000.00, 'Farmacia Los Olivos Principal', 1, 'Carrera 50 # 8-15, Bogotá', 4.580120, -74.103560),
(8, '900005500-8', 85200.50, 'Centro Médico Especializado D', 1, 'Calle 26 Sur # 78-40, Bogotá', 4.601500, -74.148000),
(9, '890101010-0', 120000.99, 'Distribuidora Fénix S.A.S.', 1, 'Avenida Boyacá # 60-05, Bogotá', 4.675000, -74.095000),
(10, '800555666-4', 980.25, 'Droguería El Buen Remedio', 1, 'Carrera 15 # 145-80, Bogotá', 4.729100, -74.037100),
(11, '777000111-2', 5500.00, 'Consultorio Pediátrico Luna', 1, 'Calle 53 # 18-95, Bogotá', 4.644100, -74.072000);


-- --------------------------------------------------------------------------------
-- 3. TABLAS DE PEDIDOS (orders SCHEMA)
-- --------------------------------------------------------------------------------

-- ORDERS."ORDER" (Pedidos)
INSERT INTO orders."Order" (user_id, creation_date, estimated_delivery_date, current_state_id, total_value) VALUES
(3, '2025-10-15', '2025-10-20', 3, 150.50), -- Pedido entregado (Cliente Farmacia A)
(4, '2025-10-18', '2025-10-25', 2, 550.90); -- Pedido en progreso (Cliente Hospital X)

-- ORDERS.ORDERLINE (Detalles de Pedido)
-- Pedido 1 (Farmacia A): Acetaminofén y Guantes
INSERT INTO orders.OrderLine (order_id, product_id, quantity, value_at_time_of_order) VALUES
(1, 1, 100, 8.50),
(1, 4, 10, 4.99);

-- Pedido 2 (Hospital X): Kit Sutura y Amoxicilina
INSERT INTO orders.OrderLine (order_id, product_id, quantity, value_at_time_of_order) VALUES
(2, 3, 20, 25.00),
(2, 2, 15, 12.30);

-- --------------------------------------------------------------------------------
-- 4. TABLAS DE LOGÍSTICA Y VISITAS (users SCHEMA)
-- --------------------------------------------------------------------------------

-- USERS.VISIT_ROUTES (Rutas de Venta)
-- INSERT INTO users.visit_routes (route_id, date, map, estimated_travel_time, seller_data) VALUES
-- ('ROUTE-202511-01', '2025-11-05', 'Ruta Centro-Norte Bogotá', '5 horas', '{"seller_name": "Maria Gomez", "user_id": 2}');

-- USERS.VISITS (Visitas)
INSERT INTO users.visits (seller_id, date, place, findings, client_id) VALUES
(1, '2025-11-05', 'Farmacia La Esquina', 'El cliente A (Farmacia A) necesita más stock de antibióticos.', 1),
(1, '2025-11-05', 'Hospital Metropolitano', 'El cliente B (Hospital X) está evaluando la compra de nuevos equipos.', 2),
(1, '2025-11-06', 'Droguería San Pedro', 'Contacto inicial. Necesita material promocional.', 1);

-- USERS.VISIT_PRODUCT_SUGGESTIONS (Sugerencias de Productos en Visitas)
-- Visita 1 (Farmacia A): Sugerir Tiras Reactivas y Amoxicilina
INSERT INTO users.visit_product_suggestions (visit_id, product_id) VALUES
(1, 5), -- Tiras Reactivas Glucosa
(1, 2); -- Amoxicilina

-- Visita 2 (Hospital X): Sugerir Termómetro Infrarrojo
INSERT INTO users.visit_product_suggestions (visit_id, product_id) VALUES
(2, 6); -- Termómetro Infrarrojo Digital

-- USERS.VISUAL_EVIDENCES (Evidencia Visual)
-- Evidencia para la Visita 1
INSERT INTO users.visual_evidences (type, url_file, description, visit_id) VALUES
('PHOTO', 'https://storage.example.com/visit/1/photo_01.jpg', 'Foto de estantería de productos de la competencia.', 1),
('NOTE', 'https://storage.example.com/visit/1/audio_01.mp3', 'Nota de voz sobre la conversación con el dueño.', 1);
