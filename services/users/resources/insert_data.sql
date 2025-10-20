-- Insertar datos solo si la tabla User está vacía
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM Users LIMIT 1) THEN
        INSERT INTO Users (name, last_name, password, identification, phone, role) VALUES
        ('Carlos', 'Ramírez', 'hashed_pw_001', 'ID-1001', '3001112233', 'CLIENT'),
        ('Laura', 'Gómez', 'hashed_pw_002', 'ID-1002', '3002223344', 'CLIENT' ),
        ('Andrés', 'Martínez', 'hashed_pw_003', 'ID-1003', '3003334455', 'CLIENT'),
        ('Sofía', 'López', 'hashed_pw_004', 'ID-1004', '3004445566', 'CLIENT'),
        ('Julián', 'Torres', 'hashed_pw_005', 'ID-1005', '3005556677', 'CLIENT' ),
        ('Camila', 'Vargas', 'hashed_pw_006', 'ID-1006', '3006667788', 'CLIENT' ),
        ('Daniel', 'Moreno', 'hashed_pw_007', 'ID-1007', '3007778899', 'CLIENT'),
        ('Valentina', 'Ríos', 'hashed_pw_008', 'ID-1008', '3008889900', 'CLIENT' ),
        ('Felipe', 'Castro', 'hashed_pw_009', 'ID-1009', '3009990011', 'CLIENT'),
        ('Natalia', 'Cárdenas', 'hashed_pw_010', 'ID-1010', '3010001122', 'CLIENT');

        -- Insertar clientes asociados
        INSERT INTO Clientes (user_id, nit, balance, perfil)
        VALUES
            (1, '900123456-1', 5000.00, 'Cliente Premium'),
            (2, '900654321-2', 3000.00, 'Cliente Estándar'),
            (3, '900789012-3', 1500.00, 'Cliente Básico');

        RAISE NOTICE 'Datos de prueba insertados correctamente.';
    ELSE
        RAISE NOTICE 'La tabla User ya contiene datos. No se insertaron datos de prueba.';
    END IF;
END $$;
