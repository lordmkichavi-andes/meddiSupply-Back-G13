-- Crear tabla User
CREATE TABLE IF NOT EXISTS Users(
    user_id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    password VARCHAR NOT NULL,
    identification VARCHAR UNIQUE NOT NULL,
    phone VARCHAR,
    role VARCHAR NOT NULL,
    client_id VARCHAR REFERENCES clientes(id)
);


-- Crear tabla Client
CREATE TABLE IF NOT EXISTS Clientes (
    client_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    nit VARCHAR(50) UNIQUE,
    balance DECIMAL(15, 2) DEFAULT 0.00,
    perfil TEXT,
    FOREIGN KEY (user_id) REFERENCES User(user_id) ON DELETE CASCADE
);

-- Crear índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_user_role ON User(role);
CREATE INDEX IF NOT EXISTS idx_client_user_id ON Client(user_id);