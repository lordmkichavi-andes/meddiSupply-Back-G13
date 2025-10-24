-- Creación esquema de Productos
CREATE SCHEMA IF NOT EXISTS products;
CREATE SCHEMA IF NOT EXISTS users;
CREATE SCHEMA IF NOT EXISTS orders;
CREATE SCHEMA IF NOT EXISTS routes;
-- Creación de la tabla 'Category' (Categoría)
-- Esta tabla almacena los tipos de categorías de productos.
 CREATE TABLE IF NOT EXISTS products.Category (
                          category_id INT PRIMARY KEY,
                          name VARCHAR(50) NOT NULL
);

-- Creación de la tabla 'Provider' (Proveedor)
-- Esta tabla se crea para soportar la relación con la tabla 'Product'.
 CREATE TABLE IF NOT EXISTS products.Providers (
                          provider_id SERIAL PRIMARY KEY,
                          name VARCHAR(100) NOT NULL
);

CREATE TABLE products.units (
    unit_id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    symbol VARCHAR(10) NOT NULL,
    type VARCHAR(20) NOT NULL,
    active BOOLEAN DEFAULT true,
    creation_date TIMESTAMP DEFAULT NOW(),
    CONSTRAINT chk_type CHECK (type IN ('peso', 'volumen', 'cantidad', 'longitud', 'area'))
);

-- Creación de la tabla 'Product' (Producto)
-- Almacena la información de los productos, incluyendo su relación con la categoría y el proveedor.
CREATE TABLE products.Products (
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
    FOREIGN KEY (provider_id) REFERENCES products.Providers(provider_id),
    FOREIGN KEY (category_id) REFERENCES products.Category(category_id),
    FOREIGN KEY (unit_id) REFERENCES products.units(unit_id),
    CONSTRAINT chk_estado CHECK (status IN ('activo', 'inactivo', 'suspendido'))
);

CREATE TABLE IF NOT EXISTS products.Warehouses (
    warehouse_id SERIAL PRIMARY KEY, -- Identificador único de la bodega
    name VARCHAR(100) NOT NULL,          -- Nombre de la bodega
    location VARCHAR(255)                -- Ubicación o dirección de la bodega (opcional)
);


-- Creación de la tabla 'ProductStock' (Inventario de Producto)
-- Almacena los registros de inventario para cada producto.
 CREATE TABLE IF NOT EXISTS products.ProductStock (
                              stock_id SERIAL PRIMARY KEY,
                              product_id INTEGER NOT NULL,
                              quantity INT NOT NULL,
                              lote VARCHAR(50) NOT NULL,
                              warehouse_id INTEGER NOT NULL,
                              provider_id INTEGER NOT NULL,
                              country VARCHAR(50) NOT NULL,
                              FOREIGN KEY (product_id) REFERENCES products.Products(product_id),
                              FOREIGN KEY (warehouse_id) REFERENCES products.Warehouses(warehouse_id),
                              FOREIGN KEY (provider_id) REFERENCES products.Providers(provider_id)
);

-- Crear tabla User
CREATE TABLE IF NOT EXISTS users.Users(
    user_id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    password VARCHAR NOT NULL,
    identification VARCHAR UNIQUE NOT NULL,
    phone VARCHAR,
    email     VARCHAR(150),
    active    BOOLEAN DEFAULT TRUE,
    role VARCHAR NOT NULL
);

CREATE TABLE IF NOT EXISTS users.sellers (
    seller_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL, -- Clave foránea 1:1 con users.Users
    zone VARCHAR(100) NOT NULL,      -- Zona de trabajo del vendedor
    -- NOTA: La FK a users.Users está comentada para evitar errores si users.Users no existe.
    FOREIGN KEY (user_id) REFERENCES users.Users(user_id) ON DELETE CASCADE
);



-- Crear tabla Client
CREATE TABLE IF NOT EXISTS users.Clients (
    client_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    nit VARCHAR(50) UNIQUE,
    balance DECIMAL(15, 2) DEFAULT 0.00,
    name TEXT,
    seller_id INTEGER,
    address VARCHAR(255) NULL,
    latitude DECIMAL(10, 8) NULL,
    longitude DECIMAL(11, 8) NULL,
    FOREIGN KEY (seller_id) REFERENCES users.sellers(seller_id) ON DELETE SET NULL,
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
    FOREIGN KEY (client_id) REFERENCES users.Clients(client_id) ON DELETE RESTRICT,
    FOREIGN KEY (seller_id) REFERENCES users.sellers(seller_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS users.visit_product_suggestions (
    visit_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    PRIMARY KEY (visit_id, product_id),
    FOREIGN KEY (visit_id) REFERENCES users.visits(visit_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products.Products(product_id) ON DELETE RESTRICT
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

 CREATE TABLE IF NOT EXISTS orders.OrdersState (
                         state_id SERIAL PRIMARY KEY,
                         name VARCHAR(50) NOT NULL UNIQUE
);
 CREATE TABLE IF NOT EXISTS orders.Orders(
                          order_id SERIAL PRIMARY KEY,
                          seller_id INTEGER,
                          client_id INTEGER, -- Asumiendo que hay una tabla 'User' o 'Customer' externa
                          creation_date DATE NOT NULL,
                          last_updated_date DATE NOT NULL,
                          estimated_delivery_date DATE,
                          status_id INTEGER NOT NULL,
                          total_value FLOAT NOT NULL,

                          FOREIGN KEY (status_id) REFERENCES orders.OrdersState(state_id),
                          FOREIGN KEY (client_id) REFERENCES users.Clients(client_id),
                          FOREIGN KEY (seller_id) REFERENCES users.sellers(seller_id)
);


-- Creación de la tabla 'OrderLine' (Línea de Pedido / Detalle)
-- Almacena los productos específicos dentro de un pedido, su cantidad y precio en el momento de la compra.
 CREATE TABLE IF NOT EXISTS orders.OrderLines (
                             order_line_id SERIAL PRIMARY KEY,
                             order_id INTEGER NOT NULL,
                             product_id INTEGER NOT NULL,
                             quantity INT NOT NULL,
                             price_unit FLOAT NOT NULL,

                             FOREIGN KEY (order_id) REFERENCES orders.Orders(order_id),
                             FOREIGN KEY (product_id) REFERENCES products.Products(product_id)
);

CREATE TABLE IF NOT EXISTS  routes.vehicles(
    vehicle_id SERIAL PRIMARY KEY,
    capacity INTEGER NOT NULL ,
    color TEXT,
    Plate TEXT,
    label TEXT
);

CREATE TABLE products.product_uploads (
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
    user_id Integer NOT NULL,
    errores TEXT,
    CONSTRAINT chk_tipo_archivo CHECK (file_type IN ('csv', 'xlsx', 'xls')),
    CONSTRAINT chk_estado CHECK (state IN ('procesando', 'completado', 'fallido', 'cancelado')),
    FOREIGN KEY (user_id) REFERENCES  users.Users(user_id)
);

CREATE TABLE products.product_upload_details (
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
    product_id INTEGER NOT NULL,
    FOREIGN KEY (upload_id) REFERENCES products.product_uploads(id),
    FOREIGN KEY (product_id) REFERENCES products.products(product_id),
    CONSTRAINT chk_estado_procesamiento CHECK (status IN ('exitoso', 'fallido', 'advertencia'))
);

CREATE TABLE products.product_history (
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
    FOREIGN KEY (user_id) REFERENCES users.Users(user_id),
    CONSTRAINT chk_tipo_cambio CHECK (change_type IN ('creacion', 'actualizacion', 'eliminacion', 'cambio_estado'))
);

CREATE INDEX IF NOT EXISTS idx_order_state ON orders.Orders(status_id);
CREATE INDEX IF NOT EXISTS idx_line_order ON orders.OrderLines(order_id);
CREATE INDEX IF NOT EXISTS idx_line_product ON orders.OrderLines(product_id);
CREATE INDEX IF NOT EXISTS idx_products_codigo ON products.products(sku);
CREATE INDEX IF NOT EXISTS idx_products_nombre ON products.products(name);
CREATE INDEX IF NOT EXISTS idx_products_categoria ON products.products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_estado ON products.products(status);
CREATE INDEX IF NOT EXISTS idx_products_fecha_creacion ON products.products(creation_date);
CREATE INDEX IF NOT EXISTS idx_upload_details_upload_id ON products.product_upload_details(upload_id);
CREATE INDEX IF NOT EXISTS idx_upload_details_estado ON products.product_upload_details(status);
CREATE INDEX IF NOT EXISTS idx_product_history_producto_id ON products.product_history(product_id);
CREATE INDEX IF NOT EXISTS idx_product_history_fecha ON products.product_history(update_date);