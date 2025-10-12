-- Creación de la tabla 'Category' (Categoría)
-- Esta tabla almacena los tipos de categorías de productos.
 CREATE TABLE IF NOT EXISTS Category (
                          category_id INT PRIMARY KEY,
                          name VARCHAR(50) NOT NULL
);

-- Creación de la tabla 'Provider' (Proveedor)
-- Esta tabla se crea para soportar la relación con la tabla 'Product'.
 CREATE TABLE IF NOT EXISTS Provider (
                          provider_id VARCHAR(50) PRIMARY KEY,
                          name VARCHAR(100) NOT NULL
);

-- Creación de la tabla 'Product' (Producto)
-- Almacena la información de los productos, incluyendo su relación con la categoría y el proveedor.
 CREATE TABLE IF NOT EXISTS Product (
                         product_id VARCHAR(50) PRIMARY KEY,
                         sku VARCHAR(50) NOT NULL UNIQUE,
                         value FLOAT NOT NULL,
                         provider_id VARCHAR(50) NOT NULL,
                         category_id INT NOT NULL,
                         objective_profile VARCHAR(255) NOT NULL,
                         FOREIGN KEY (provider_id) REFERENCES Provider(provider_id),
                         FOREIGN KEY (category_id) REFERENCES Category(category_id)
);

-- Creación de la tabla 'ProductStock' (Inventario de Producto)
-- Almacena los registros de inventario para cada producto.
 CREATE TABLE IF NOT EXISTS ProductStock (
                              stock_id VARCHAR(50) PRIMARY KEY,
                              product_id VARCHAR(50) NOT NULL,
                              quantity INT NOT NULL,
                              lote VARCHAR(50) NOT NULL,
                              warehouse_id VARCHAR(50) NOT NULL,
                              country VARCHAR(50) NOT NULL,
                              FOREIGN KEY (product_id) REFERENCES Product(product_id)
);

 CREATE TABLE IF NOT EXISTS State (
                         state_id INT PRIMARY KEY,
                         name VARCHAR(50) NOT NULL UNIQUE
);


-- Creación de la tabla 'Order' (Pedido)
-- Almacena la cabecera del pedido y su información general.
 CREATE TABLE IF NOT EXISTS "Order" (
                          order_id VARCHAR(50) PRIMARY KEY,
                          user_id VARCHAR(50), -- Asumiendo que hay una tabla 'User' o 'Customer' externa
                          creation_date DATE NOT NULL,
                          estimated_delivery_date DATE,
                          current_state_id INT NOT NULL,
                          total_value FLOAT NOT NULL,

                          FOREIGN KEY (current_state_id) REFERENCES State(state_id)
);


-- Creación de la tabla 'OrderLine' (Línea de Pedido / Detalle)
-- Almacena los productos específicos dentro de un pedido, su cantidad y precio en el momento de la compra.
 CREATE TABLE IF NOT EXISTS OrderLine (
                             order_line_id VARCHAR(50) PRIMARY KEY,
                             order_id VARCHAR(50) NOT NULL,
                             product_id VARCHAR(50) NOT NULL,
                             quantity INT NOT NULL,
                             -- Se registra el valor del producto en el momento del pedido para evitar incoherencias futuras
                             value_at_time_of_order FLOAT NOT NULL,

                             FOREIGN KEY (order_id) REFERENCES "Order"(order_id),
                             FOREIGN KEY (product_id) REFERENCES Product(product_id)
);


CREATE INDEX IF NOT EXISTS idx_order_state ON "Order"(current_state_id);
CREATE INDEX IF NOT EXISTS idx_line_order ON OrderLine(order_id);
CREATE INDEX IF NOT EXISTS idx_line_product ON OrderLine(product_id);
-- ******************************************************