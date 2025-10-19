-- Crear tabla User
CREATE TABLE IF NOT EXISTS User(
    user_id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    identification VARCHAR(50) UNIQUE NOT NULL,
    phone VARCHAR(20),
    role VARCHAR(20) NOT NULL CHECK (role IN ('CLIENT', 'ADMIN', 'OPERATOR'))
);

-- Crear tabla Client
CREATE TABLE IF NOT EXISTS Client (
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