-- INSERCIÓN DE DATOS DE PRUEBA
-- Se asume que las tablas Category, Provider, Product y ProductStock
-- ya están definidas, junto con State, Order y OrderLine.
-- Se añade una validación para insertar datos solo si las tablas están vacías.
-- ******************************************************

-- 1. Tablas de Catálogo y Proveedores
------------------------------------------------------

-- Categorías

-- Inserción de estados iniciales (Opcional, pero recomendado para iniciar)
INSERT INTO State (state_id, name) VALUES
(1, 'IN_TRANSIT'),
(2, 'DELAYED'),
(3, 'DELIVERED'),
(4, 'CANCELLED'),
(5, 'PROCESSING');

INSERT INTO Category (category_id, name)
SELECT 101, 'Electrónica'
WHERE NOT EXISTS (SELECT 1 FROM Category);

INSERT INTO Category (category_id, name)
SELECT 102, 'Ropa'
WHERE NOT EXISTS (SELECT 1 FROM Category WHERE category_id = 101); -- Se usa la misma lógica para todas las categorías si la primera existe

INSERT INTO Category (category_id, name)
SELECT 103, 'Alimentos'
WHERE NOT EXISTS (SELECT 1 FROM Category WHERE category_id = 101);

-- Proveedores
INSERT INTO Provider (provider_id, name)
SELECT 'PROV001', 'TechGlobal S.A.'
WHERE NOT EXISTS (SELECT 1 FROM Provider);

INSERT INTO Provider (provider_id, name)
SELECT 'PROV002', 'FashionCorp Ltd.'
WHERE NOT EXISTS (SELECT 1 FROM Provider WHERE provider_id = 'PROV001');

INSERT INTO Provider (provider_id, name)
SELECT 'PROV003', 'FreshFoods Ltda.'
WHERE NOT EXISTS (SELECT 1 FROM Provider WHERE provider_id = 'PROV001');


-- Productos
-- Se asume que las categorías y proveedores ya existen
INSERT INTO Product (product_id, sku, value, provider_id, category_id, objective_profile)
SELECT 'PROD_A01', 'SKU-EL-4K', 850.50, 'PROV001', 101, 'Televisor 4K de alta gama.'
WHERE NOT EXISTS (SELECT 1 FROM Product);

INSERT INTO Product (product_id, sku, value, provider_id, category_id, objective_profile)
SELECT 'PROD_B02', 'SKU-CL-TS', 45.99, 'PROV002', 102, 'Camiseta de algodón, talla M.'
WHERE NOT EXISTS (SELECT 1 FROM Product WHERE product_id = 'PROD_A01');

INSERT INTO Product (product_id, sku, value, provider_id, category_id, objective_profile)
SELECT 'PROD_C03', 'SKU-AL-APL', 1.20, 'PROV003', 103, 'Manzana Fuji unitaria.'
WHERE NOT EXISTS (SELECT 1 FROM Product WHERE product_id = 'PROD_A01');

INSERT INTO Product (product_id, sku, value, provider_id, category_id, objective_profile)
SELECT 'PROD_A02', 'SKU-EL-AUD', 120.00, 'PROV001', 101, 'Audífonos inalámbricos con cancelación de ruido.'
WHERE NOT EXISTS (SELECT 1 FROM Product WHERE product_id = 'PROD_A01');

-- Inventario de Producto
INSERT INTO ProductStock (stock_id, product_id, quantity, lote, warehouse_id, country)
SELECT 'STK_001', 'PROD_A01', 15, 'LOTE-TV-2024', 'WH-NY', 'USA'
WHERE NOT EXISTS (SELECT 1 FROM ProductStock);

INSERT INTO ProductStock (stock_id, product_id, quantity, lote, warehouse_id, country)
SELECT 'STK_002', 'PROD_B02', 200, 'LOTE-TS-JUL', 'WH-LDN', 'UK'
WHERE NOT EXISTS (SELECT 1 FROM ProductStock WHERE stock_id = 'STK_001');

INSERT INTO ProductStock (stock_id, product_id, quantity, lote, warehouse_id, country)
SELECT 'STK_003', 'PROD_C03', 500, 'LOTE-FR-09', 'WH-SP', 'ESP'
WHERE NOT EXISTS (SELECT 1 FROM ProductStock WHERE stock_id = 'STK_001');

INSERT INTO ProductStock (stock_id, product_id, quantity, lote, warehouse_id, country)
SELECT 'STK_004', 'PROD_A02', 50, 'LOTE-AUD-V3', 'WH-NY', 'USA'
WHERE NOT EXISTS (SELECT 1 FROM ProductStock WHERE stock_id = 'STK_001');


-- 2. Tablas de Pedidos
------------------------------------------------------

-- Estados (La tabla State fue agregada en el otro script, se usa aquí por consistencia)
-- Se asume que el script de creación inserta los estados, pero los reinsertamos con validación para mayor seguridad.
INSERT INTO State (state_id, name)
SELECT 1, 'IN_TRANSIT'
WHERE NOT EXISTS (SELECT 1 FROM State);
INSERT INTO State (state_id, name)
SELECT 2, 'DELAYED'
WHERE NOT EXISTS (SELECT 1 FROM State WHERE state_id = 1);
INSERT INTO State (state_id, name)
SELECT 3, 'DELIVERED'
WHERE NOT EXISTS (SELECT 1 FROM State WHERE state_id = 1);
INSERT INTO State (state_id, name)
SELECT 4, 'CANCELLED'
WHERE NOT EXISTS (SELECT 1 FROM State WHERE state_id = 1);
INSERT INTO State (state_id, name)
SELECT 5, 'PROCESSING'
WHERE NOT EXISTS (SELECT 1 FROM State WHERE state_id = 1);

-- Pedidos (Order)
INSERT INTO "Order" (order_id, user_id, creation_date, estimated_delivery_date, current_state_id, total_value)
SELECT 'ORD_2024_001', 'USER_55', '2024-10-01', '2024-10-15', 3, 936.49
WHERE NOT EXISTS (SELECT 1 FROM "Order");

INSERT INTO "Order" (order_id, user_id, creation_date, estimated_delivery_date, current_state_id, total_value)
SELECT 'ORD_2024_002', 'USER_55', '2024-10-05', '2024-10-20', 1, 122.40
WHERE NOT EXISTS (SELECT 1 FROM "Order" WHERE order_id = 'ORD_2024_001');

INSERT INTO "Order" (order_id, user_id, creation_date, estimated_delivery_date, current_state_id, total_value)
SELECT 'ORD_2024_003', 'USER_66', '2024-10-07', '2024-10-25', 5, 240.00
WHERE NOT EXISTS (SELECT 1 FROM "Order" WHERE order_id = 'ORD_2024_001');


-- Líneas de Pedido (OrderLine)
INSERT INTO OrderLine (order_line_id, order_id, product_id, quantity, value_at_time_of_order)
SELECT 'LINE_001A', 'ORD_2024_001', 'PROD_A01', 1, 850.50
WHERE NOT EXISTS (SELECT 1 FROM OrderLine);

INSERT INTO OrderLine (order_line_id, order_id, product_id, quantity, value_at_time_of_order)
SELECT 'LINE_001B', 'ORD_2024_001', 'PROD_B02', 1, 45.99
WHERE NOT EXISTS (SELECT 1 FROM OrderLine WHERE order_line_id = 'LINE_001A');

INSERT INTO OrderLine (order_line_id, order_id, product_id, quantity, value_at_time_of_order)
SELECT 'LINE_002A', 'ORD_2024_002', 'PROD_A02', 1, 120.00
WHERE NOT EXISTS (SELECT 1 FROM OrderLine WHERE order_line_id = 'LINE_001A');

INSERT INTO OrderLine (order_line_id, order_id, product_id, quantity, value_at_time_of_order)
SELECT 'LINE_002B', 'ORD_2024_002', 'PROD_C03', 2, 1.20
WHERE NOT EXISTS (SELECT 1 FROM OrderLine WHERE order_line_id = 'LINE_001A');

INSERT INTO OrderLine (order_line_id, order_id, product_id, quantity, value_at_time_of_order)
SELECT 'LINE_003A', 'ORD_2024_003', 'PROD_A02', 2, 120.00
WHERE NOT EXISTS (SELECT 1 FROM OrderLine WHERE order_line_id = 'LINE_001A');
