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
('P-PHARMA', 'PharmaGlobal Labs S.A.'),
('P-MEDS', 'MedSupply Distributors'),
('P-TECH', 'TecnoHealth Solutions');

-- PRODUCTS.WAREHOUSE (Bodegas)
INSERT INTO products.Warehouse (name, location) VALUES
('BODEGA_CENTRAL', 'Calle 100 # 50-20, Bogotá'),
('BODEGA_OCCIDENTE', 'Carrera 80 # 12-45, Cali');

-- PRODUCTS.PRODUCT (Productos)
INSERT INTO products.Product (sku, name, value, provider_id, category_id, objective_profile) VALUES
('MED-001', 'Acetaminofén 500mg (Caja x100)', 8.50, 'P-PHARMA', 1, 'Droguerías, Farmacias'),
('MED-002', 'Amoxicilina 250mg/5ml (Frasco)', 12.30, 'P-PHARMA', 1, 'Pediátrico, Clínicas'),
('SURG-001', 'Kit Sutura Desechable', 25.00, 'P-MEDS', 2, 'Hospitales, Salas de Cirugía'),
('SURG-002', 'Guantes Nitrilo Talla M (Caja x50)', 4.99, 'P-MEDS', 2, 'Clínicas, Consultorios'),
('REAG-001', 'Tiras Reactivas Glucosa (Caja x50)', 15.75, 'P-TECH', 3, 'Laboratorios Clínicos'),
('EQUIP-001', 'Termómetro Infrarrojo Digital', 45.90, 'P-TECH', 4, 'Clínicas, Hospitales');

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

-- USERS.CLIENTES (Clientes/Puntos de Venta)
INSERT INTO users.Clientes (user_id, nit, balance, perfil) VALUES
(3, '800123456-1', 1500.50, 'Farmacia de Barrio A'),
(4, '900789012-5', 52000.75, 'Hospital Nivel 3 X');

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
INSERT INTO users.visit_routes (route_id, date, map, estimated_travel_time, seller_data) VALUES
('ROUTE-202511-01', '2025-11-05', 'Ruta Centro-Norte Bogotá', '5 horas', '{"seller_name": "Maria Gomez", "user_id": 2}');

-- USERS.VISITS (Visitas)
INSERT INTO users.visits (user_id, date, place, findings, client_id) VALUES
(2, '2025-11-05', 'Farmacia La Esquina', 'El cliente A (Farmacia A) necesita más stock de antibióticos.', 1),
(2, '2025-11-05', 'Hospital Metropolitano', 'El cliente B (Hospital X) está evaluando la compra de nuevos equipos.', 2),
(2, '2025-11-06', 'Droguería San Pedro', 'Contacto inicial. Necesita material promocional.', 1);

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
