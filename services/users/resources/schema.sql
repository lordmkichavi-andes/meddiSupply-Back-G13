-- Crear tabla User
CREATE TABLE IF NOT EXISTS Users(
    user_id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    password VARCHAR NOT NULL,
    identification VARCHAR UNIQUE NOT NULL,
    phone VARCHAR,
    role VARCHAR NOT NULL
);


-- Crear tabla Client
CREATE TABLE IF NOT EXISTS Clientes (
    client_id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL,
    nit VARCHAR(50) UNIQUE,
    balance DECIMAL(15, 2) DEFAULT 0.00,
    perfil TEXT,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

