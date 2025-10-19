-- INSERCIÓN DE DATOS DE PRUEBA
-- Se asume que las tablas Category, Provider, Product y ProductStock
-- ya están definidas, junto con State, Order y OrderLine.
-- Se añade una validación para insertar datos solo si las tablas están vacías.
-- ******************************************************

-- 1. Tablas de Catálogo y Proveedores
------------------------------------------------------

-- Categorías

-- Inserción de estados iniciales (Opcional, pero recomendado para iniciar)
INSERT INTO Category (category_id, name)
SELECT 101, 'Electrónica'
WHERE NOT EXISTS (SELECT 1 FROM Category  WHERE category_id = 101);

INSERT INTO Category (category_id, name)
SELECT 102, 'Ropa'
WHERE NOT EXISTS (SELECT 1 FROM Category WHERE category_id = 102); -- Se usa la misma lógica para todas las categorías si la primera existe

INSERT INTO Category (category_id, name)
SELECT 103, 'Alimentos'
WHERE NOT EXISTS (SELECT 1 FROM Category WHERE category_id = 103);

-- Proveedores
INSERT INTO Provider (provider_id, name)
SELECT 'PROV001', 'TechGlobal S.A.'
WHERE NOT EXISTS (SELECT 1 FROM Provider WHERE provider_id = 'PROV002');

INSERT INTO Provider (provider_id, name)
SELECT 'PROV002', 'FashionCorp Ltd.'
WHERE NOT EXISTS (SELECT 1 FROM Provider WHERE provider_id = 'PROV002');

INSERT INTO Provider (provider_id, name)
SELECT 'PROV003', 'FreshFoods Ltda.'
WHERE NOT EXISTS (SELECT 1 FROM Provider WHERE provider_id = 'PROV003');


-- Productos
-- Se asume que las categorías y proveedores ya existen
INSERT INTO Product (product_id, sku, value, provider_id, category_id, objective_profile)
SELECT 'PROD001', 'SKU-EL-4K', 850.50, 'PROV001', 101, 'Televisor 4K de alta gama.'
WHERE NOT EXISTS (SELECT 1 FROM Product WHERE product_id = 'PROD001');

INSERT INTO Product (product_id, sku, value, provider_id, category_id, objective_profile)
SELECT 'PROD002', 'SKU-CL-TS', 45.99, 'PROV002', 102, 'Camiseta de algodón, talla M.'
WHERE NOT EXISTS (SELECT 1 FROM Product WHERE product_id = 'PROD002');

INSERT INTO Product (product_id, sku, value, provider_id, category_id, objective_profile)
SELECT 'PROD003', 'SKU-AL-APL', 1.20, 'PROV003', 103, 'Manzana Fuji unitaria.'
WHERE NOT EXISTS (SELECT 1 FROM Product WHERE product_id = 'PROD003');

INSERT INTO Warehouse (warehouse_id, name, location) VALUES
('BOD01', 'Bodega Central Norte', 'Calle Falsa 123, Ciudad A'),
('BOD02', 'Mini Centro Sur', 'Avenida Siempre Viva 456, Ciudad B');

INSERT INTO Inventory (product_id, warehouse_id, stock_quantity) VALUES
('PROD001', 'BOD01', 50),
('PROD001', 'BOD02', 10),
('PROD002', 'BOD01', 200),
('PROD003', 'BOD02', 350);



-- Inventario de Producto
INSERT INTO ProductStock (stock_id, product_id, quantity, lote, warehouse_id, country)
SELECT 'STK_001', 'PROD001', 15, 'LOTE-TV-2024', 'WH-NY', 'USA'
WHERE NOT EXISTS (SELECT 1 FROM ProductStock WHERE stock_id = 'STK_001');

INSERT INTO ProductStock (stock_id, product_id, quantity, lote, warehouse_id, country)
SELECT 'STK_002', 'PROD002', 200, 'LOTE-TS-JUL', 'WH-LDN', 'UK'
WHERE NOT EXISTS (SELECT 1 FROM ProductStock WHERE stock_id = 'STK_002');

INSERT INTO ProductStock (stock_id, product_id, quantity, lote, warehouse_id, country)
SELECT 'STK_003', 'PROD003', 500, 'LOTE-FR-09', 'WH-SP', 'ESP'
WHERE NOT EXISTS (SELECT 1 FROM ProductStock WHERE stock_id = 'STK_003');
-- 2. Tablas de Pedidos
------------------------------------------------------

-- Estados (La tabla State fue agregada en el otro script, se usa aquí por consistencia)
-- Se asume que el script de creación inserta los estados, pero los reinsertamos con validación para mayor seguridad.
INSERT INTO State (state_id, name)
SELECT 1, 'IN_TRANSIT'
WHERE NOT EXISTS (SELECT 1 FROM State WHERE state_id = 1);
INSERT INTO State (state_id, name)
SELECT 2, 'DELAYED'
WHERE NOT EXISTS (SELECT 1 FROM State WHERE state_id = 2);
INSERT INTO State (state_id, name)
SELECT 3, 'DELIVERED'
WHERE NOT EXISTS (SELECT 1 FROM State WHERE state_id = 3);
INSERT INTO State (state_id, name)
SELECT 4, 'CANCELLED'
WHERE NOT EXISTS (SELECT 1 FROM State WHERE state_id = 4);
INSERT INTO State (state_id, name)
SELECT 5, 'PROCESSING'
WHERE NOT EXISTS (SELECT 1 FROM State WHERE state_id = 5);
INSERT INTO State (state_id, name)
SELECT 6, 'PENDING'
WHERE NOT EXISTS (SELECT 1 FROM State WHERE state_id = 6);

-- Pedidos (Order)
INSERT INTO "Order" (order_id, user_id, creation_date, estimated_delivery_date, current_state_id, total_value)
SELECT 'ORD_2024_001', 'USER_55', '2024-10-01', '2024-10-15', 3, 936.49
WHERE NOT EXISTS (SELECT 1 FROM "Order" WHERE order_id = 'ORD_2024_001');

INSERT INTO "Order" (order_id, user_id, creation_date, estimated_delivery_date, current_state_id, total_value)
SELECT 'ORD_2024_002', 'USER_55', '2024-10-05', '2024-10-20', 1, 122.40
WHERE NOT EXISTS (SELECT 1 FROM "Order" WHERE order_id = 'ORD_2024_002');

INSERT INTO "Order" (order_id, user_id, creation_date, estimated_delivery_date, current_state_id, total_value)
SELECT 'ORD_2024_003', 'USER_66', '2024-10-07', '2024-10-25', 5, 240.00
WHERE NOT EXISTS (SELECT 1 FROM "Order" WHERE order_id = 'ORD_2024_003');


-- Líneas de Pedido (OrderLine)
INSERT INTO OrderLine (order_line_id, order_id, product_id, quantity, value_at_time_of_order)
SELECT 'LINE_001A', 'ORD_2024_001', 'PROD001', 1, 850.50
WHERE NOT EXISTS (SELECT 1 FROM OrderLine WHERE order_line_id = 'LINE_001A');

INSERT INTO OrderLine (order_line_id, order_id, product_id, quantity, value_at_time_of_order)
SELECT 'LINE_001B', 'ORD_2024_001', 'PROD002', 1, 45.99
WHERE NOT EXISTS (SELECT 1 FROM OrderLine WHERE order_line_id = 'LINE_001B');



INSERT INTO OrderLine (order_line_id, order_id, product_id, quantity, value_at_time_of_order)
SELECT 'LINE_002B', 'ORD_2024_002', 'PROD003', 2, 1.20
WHERE NOT EXISTS (SELECT 1 FROM OrderLine WHERE order_line_id = 'LINE_002B');


