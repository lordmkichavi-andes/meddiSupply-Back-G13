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
