-- --------------------------------------------------------------------------------
-- SCRIPT DE INSERCIÓN DE DATOS DE PRUEBA (ESQUEMA COMPLETO)
-- --------------------------------------------------------------------------------

-- NOTA: Se asume que los esquemas (products, users, orders, routes, y productos) ya fueron creados.

------------------------------------------------------
-- 1. TABLAS DE UNIDADES Y CATEGORÍAS (products/productos)
------------------------------------------------------

-- PRODUCTS.CATEGORY
INSERT INTO products.Category (category_id, name) VALUES
(1, 'MEDICATION'),
(2, 'SURGICAL_SUPPLIES'),
(3, 'REAGENTS'),
(4, 'EQUIPMENT'),
(5, 'OTHERS');

-- PRODUCTS.PROVIDERS
INSERT INTO products.Providers (provider_id, name) VALUES
(1, 'PharmaGlobal Labs S.A.'),
(2, 'MedSupply Distributors'),
(3, 'TecnoHealth Solutions');

-- PRODUCTOS.UNITS
INSERT INTO products.units (unit_id, name, symbol, type) VALUES
(1, 'Caja', 'Cj', 'cantidad'),
(2, 'Miligramo', 'mg', 'peso'),
(3, 'Mililitro', 'ml', 'volumen'),
(4, 'Unidad', 'u', 'cantidad'),
(5, 'Kit', 'Kit', 'cantidad');

-- PRODUCTS.WAREHOUSES
INSERT INTO products.Warehouses (warehouse_id, name, location) VALUES
(1, 'BODEGA_CENTRAL', 'Calle 100 # 50-20, Bogotá'),
(2, 'BODEGA_OCCIDENTE', 'Carrera 80 # 12-45, Cali');

------------------------------------------------------
-- 2. TABLAS DE USUARIOS Y CLIENTES (users)
------------------------------------------------------

-- USERS.USERS (user_id 1 al 8)
INSERT INTO users.Users (user_id, name, last_name, password, identification, phone, email, role) VALUES
(1, 'Admin', 'Root', 'hash_admin', '10000000', '3001001000', 'admin@medisales.com', 'ADMIN'),
(2, 'Maria', 'Gomez', 'hash_seller1', '20000000', '3102002000', 'maria.gomez@medisales.com', 'SELLER'),
(3, 'Pedro', 'Ramirez', 'hash_seller2', '30000000', '3203003000', 'pedro.ramirez@medisales.com', 'SELLER'),
(4, 'Carlos', 'Lopez', 'hash_client1', '40000000', '3304004000', 'carlos.lopez@client.com', 'CLIENT'),
(5, 'Laura', 'Diaz', 'hash_client2', '50000000', '3405005000', 'laura.diaz@client.com', 'CLIENT'),
(6, 'Ana', 'Rojas', 'hash_client3', '60000000', '3506006000', 'ana.rojas@client.com', 'CLIENT'),
(7, 'Miguel', 'Vargas', 'hash_client4', '70000000', '3607007000', 'miguel.vargas@client.com', 'CLIENT'),
(8, 'Elena', 'Castro', 'hash_client5', '80000000', '3708008000', 'elena.castro@client.com', 'CLIENT');


-- USERS.SELLERS (seller_id 1 y 2)
INSERT INTO users.sellers (seller_id, user_id, zone) VALUES
(1, 2, 'ZONA CENTRO-NORTE'), -- Maria Gomez
(2, 3, 'ZONA SUR-ORIENTE'); -- Pedro Ramirez


-- USERS.CLIENTS (client_id 1 al 5) - ¡COHERENCIA GEOGRÁFICA!
INSERT INTO users.Clients (client_id, user_id, nit, balance, name, seller_id, address, latitude, longitude) VALUES
(1, 4, '400123456-1', 1500.50, 'Farmacia de Barrio A', 1, 'Calle 72 # 10-30, Bogotá', 4.659970, -74.058370), -- Asignado a Seller 1
(2, 5, '500789012-5', 52000.75, 'Hospital Nivel 3 X', 1, 'Carrera 7 # 120-50, Bogotá', 4.697500, -74.037500), -- Asignado a Seller 1
(3, 6, '600111222-3', 15000.00, 'Farmacia Los Olivos Principal', 2, 'Carrera 50 # 8-15, Bogotá', 4.580120, -74.103560), -- Asignado a Seller 2
(4, 7, '700005500-8', 85200.50, 'Centro Médico Especializado D', 2, 'Calle 26 Sur # 78-40, Bogotá', 4.601500, -74.148000), -- Asignado a Seller 2
(5, 8, '800555666-4', 980.25, 'Droguería El Buen Remedio', 2, 'Carrera 15 # 145-80, Bogotá', 4.729100, -74.037100); -- Asignado a Seller 2

------------------------------------------------------
-- 3. TABLAS DE PRODUCTOS (products)
------------------------------------------------------

-- PRODUCTS.PRODUCTS (product_id 1 al 12)
INSERT INTO products.Products (sku, name, value, provider_id, status, category_id, objective_profile, unit_id) VALUES
('MED-001', 'Acetaminofén 500mg', 8.50, 1, 'activo', 1, 'Droguerías, Farmacias', 1),
('MED-002', 'Amoxicilina 250mg/5ml', 12.30, 1, 'activo', 1, 'Pediátrico, Clínicas', 3),
('SURG-001', 'Kit Sutura Desechable', 25.00, 2, 'activo', 2, 'Hospitales, Salas de Cirugía', 5),
('SURG-002', 'Guantes Nitrilo Talla M', 4.99, 2, 'activo', 2, 'Clínicas, Consultorios', 1),
('REAG-001', 'Tiras Reactivas Glucosa', 15.75, 3, 'activo', 3, 'Laboratorios Clínicos', 4),
('EQUIP-001', 'Termómetro Infrarrojo', 45.90, 3, 'activo', 4, 'Clínicas, Hospitales', 4),
('MED-003', 'Ibuprofeno 400mg', 9.50, 1, 'activo', 1, 'General', 1),
('SURG-003', 'Tapabocas N95 (Caja)', 15.00, 2, 'activo', 2, 'Todos', 1),
('REAG-002', 'Medio de Cultivo B-AG', 80.00, 3, 'activo', 3, 'Laboratorios Especializados', 3),
('OTH-001', 'Alcohol Antiséptico 500ml', 3.50, 2, 'activo', 5, 'Todos', 3),
('MED-004', 'Dexametasona 4mg (Ampolla)', 1.50, 1, 'activo', 1, 'Hospitales', 4),
('EQUIP-002', 'Tensiómetro Digital', 55.00, 3, 'activo', 4, 'Consultorios', 4);


-- PRODUCTS.PRODUCTSTOCK (10 registros)
INSERT INTO products.ProductStock (product_id, quantity, lote, warehouse_id, provider_id, country) VALUES
(1, 5000, 'LOTE2025A', 1, 1, 'COL'), (2, 2500, 'LOTE2025B', 1, 1, 'COL'),
(3, 1000, 'LOTE456', 2, 2, 'ECU'), (4, 8000, 'LOTE789', 1, 2, 'PER'),
(5, 300, 'GLU2025', 2, 3, 'COL'), (6, 500, 'TERM2025', 1, 3, 'COL'),
(7, 4500, 'IBU2026', 1, 1, 'COL'), (8, 6000, 'MASC2025', 2, 2, 'COL'),
(11, 1500, 'DEXA2025', 1, 1, 'MEX'), (12, 500, 'TENS2026', 1, 3, 'COL');

------------------------------------------------------
-- 4. TABLAS DE ÓRDENES (orders)
------------------------------------------------------

-- ORDERS.ORDERSSTATE
INSERT INTO orders.OrdersState (state_id, name) VALUES
(1, 'Creado'),
(2, 'En Proceso'),
(3, 'Entregado'),
(4, 'Cancelado');

-- ORDERS.ORDERS (3 registros)
INSERT INTO orders.Orders (order_id, client_id, seller_id, creation_date, last_updated_date, estimated_delivery_date, status_id, total_value) VALUES
(1, 1, 1,'2025-10-15', '2025-10-15', '2025-10-20', 3, 150.50), -- Cliente 1, Entregado
(2, 2, 1,'2025-10-18', '2025-10-19', '2025-10-25', 2, 550.90), -- Cliente 2, En Proceso
(3, 4, 2,'2025-10-23', '2025-10-24', '2025-10-30', 1, 80.00);  -- Cliente 4, Creado

-- ORDERS.ORDERLINES (5 registros)
INSERT INTO orders.OrderLines (order_id, product_id, quantity, price_unit) VALUES
(1, 1, 100, 8.50), (1, 4, 10, 4.99),
(2, 3, 20, 25.00), (2, 2, 15, 12.30),
(3, 7, 5, 9.50);

------------------------------------------------------
-- 5. TABLAS DE VISITAS (users)
------------------------------------------------------

-- USERS.VISITS (6 registros - La tabla no incluye route_id en el esquema dado)
INSERT INTO users.visits (visit_id, seller_id, date, findings, client_id) VALUES
(1, 1, '2025-11-05', 'El cliente necesita más stock de antibióticos.', 1), -- Seller 1 (Maria), Client 1
(2, 1, '2025-11-05', 'El cliente está evaluando la compra de nuevos equipos.', 2), -- Seller 1 (Maria), Client 2
(3, 2, '2025-11-05', 'Contacto inicial. Necesita material promocional.', 3), -- Seller 2 (Pedro), Client 3
(4, 2, '2025-11-06', 'Revisión de inventario y saldo pendiente.', 4), -- Seller 2 (Pedro), Client 4
(5, 1, '2025-11-07', 'Seguimiento de orden 1. Presentar nuevo producto.', 1), -- Seller 1 (Maria), Client 1
(6, 2, '2025-11-07', 'Muestra del nuevo Tapabocas N95.', 5); -- Seller 2 (Pedro), Client 5

-- USERS.VISIT_PRODUCT_SUGGESTIONS
INSERT INTO users.visit_product_suggestions (visit_id, product_id) VALUES
(1, 5), (1, 2), -- Visita 1: Sugerir Tiras Reactivas y Amoxicilina
(2, 6), -- Visita 2: Sugerir Termómetro Infrarrojo Digital
(3, 8), -- Visita 3: Sugerir Tapabocas N95
(5, 12); -- Visita 5: Sugerir Tensiómetro Digital

-- USERS.VISUAL_EVIDENCES
INSERT INTO users.visual_evidences (type, url_file, description, visit_id) VALUES
('PHOTO', 'https://storage.example.com/visit/1/photo_01.jpg', 'Foto de estantería.', 1),
('NOTE', 'https://storage.example.com/visit/1/audio_01.mp3', 'Nota de voz sobre necesidad de stock.', 1),
('PHOTO', 'https://storage.example.com/visit/4/photo_01.jpg', 'Fachada del centro médico.', 4);

------------------------------------------------------
-- 6. TABLAS DE RUTAS Y VEHÍCULOS (routes)
------------------------------------------------------

-- ROUTES.VEHICLES (2 registros)
INSERT INTO routes.vehicles (vehicle_id, capacity, color, Plate, label) VALUES
(1, 500, 'Blanco', 'XYZ123', 'Furgoneta 1'),
(2, 200, 'Gris', 'ABC789', 'Moto Express');

------------------------------------------------------
-- 7. TABLAS DE CARGAS Y HISTORIAL (products)
------------------------------------------------------

-- PRODUCTS.PRODUCT_UPLOADS (Simulación de una carga de inventario masiva por el ADMIN user_id 1)
INSERT INTO products.product_uploads (id, file_name, file_type, file_size, total_records, successful_records, failed_records, state, user_id) VALUES
(1, 'inventario_inicial_2025.csv', 'csv', 512000, 15, 12, 3, 'completado', 1);

-- PRODUCTS.PRODUCT_HISTORY (Simulación de creación de 3 productos)
-- Nota: user_id es INTEGER, aunque la columna de la tabla lo defina como VARCHAR(100)
INSERT INTO products.product_history (product_id, previous_value, new_value, change_type, user_id, upload_id) VALUES
(1, NULL, 8.50, 'creacion', 1, 1),
(2, NULL, 12.30, 'creacion', 1, 1),
(3, NULL, 25.00, 'creacion', 1, 1);

-- PRODUCTS.PRODUCT_UPLOAD_DETAILS (Detalle de un registro fallido)
INSERT INTO products.product_upload_details (upload_id, row_id, code, name, price, category, minimum_stock, measure_unit, status, errors, product_id) VALUES
(1, 1, 'MED-000', 'Producto Duplicado', 10.00, 'MEDICATION', 50, 'Caja', 'fallido', 'SKU ya existe en el sistema.', 1);
