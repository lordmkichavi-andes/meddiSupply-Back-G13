-- Insertar datos solo si la tabla User está vacía
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM User LIMIT 1) THEN
        -- Insertar usuarios de prueba
        INSERT INTO User (name, last_name, password, identification, phone, role)
        VALUES 
            ('Juan', 'Pérez', 'hashed_password_123', '12345678', '555-0001', 'CLIENT'),
            ('María', 'García', 'hashed_password_456', '87654321', '555-0002', 'CLIENT'),
            ('Carlos', 'López', 'hashed_password_789', '11223344', '555-0003', 'CLIENT'),
            ('Admin', 'Sistema', 'admin_hashed_pass', '00000000', '555-0000', 'ADMIN');

        -- Insertar clientes asociados
        INSERT INTO Client (user_id, nit, balance, perfil)
        VALUES 
            (1, '900123456-1', 5000.00, 'Cliente Premium'),
            (2, '900654321-2', 3000.00, 'Cliente Estándar'),
            (3, '900789012-3', 1500.00, 'Cliente Básico');

        RAISE NOTICE 'Datos de prueba insertados correctamente.';
    ELSE
        RAISE NOTICE 'La tabla User ya contiene datos. No se insertaron datos de prueba.';
    END IF;
END $$;