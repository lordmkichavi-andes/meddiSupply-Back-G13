#!/usr/bin/env python3
"""
Script para consultar usuarios existentes en la base de datos
"""
import psycopg2
import os
import csv
import json

# Configuración de conexión
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5433')
DB_NAME = os.getenv('DB_NAME', 'medisupplydb')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')

try:
    # Conectar a la base de datos
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Consultar usuarios existentes
    query = """
        SELECT 
            user_id,
            name AS nombre,
            last_name AS apellido,
            email AS correo,
            identification AS identificacion,
            phone AS telefono,
            role AS rol
        FROM users.users
        ORDER BY user_id
        LIMIT 10
    """
    
    cursor.execute(query)
    users = cursor.fetchall()
    
    print(f"✅ Encontrados {len(users)} usuarios en la base de datos:")
    print("")
    
    if users:
        # Mostrar usuarios
        for user in users:
            print(f"ID: {user['user_id']}")
            print(f"  Nombre: {user['nombre']} {user['apellido']}")
            print(f"  Correo: {user['correo']}")
            print(f"  Identificación: {user['identificacion']}")
            print(f"  Rol: {user['rol']}")
            print("")
        
        # Generar CSV con usuarios existentes (para probar duplicados)
        csv_file = 'test_users_existentes.csv'
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['nombre', 'apellido', 'correo', 'identificacion', 'telefono', 'rol', 'contraseña'])
            writer.writeheader()
            
            for user in users[:3]:  # Solo los primeros 3 para el CSV
                writer.writerow({
                    'nombre': user['nombre'] or 'Test',
                    'apellido': user['apellido'] or 'Usuario',
                    'correo': user['correo'] or '',
                    'identificacion': user['identificacion'] or '',
                    'telefono': user['telefono'] or '',
                    'rol': user['rol'] or 'CLIENT',
                    'contraseña': 'TestPass123!'  # Contraseña temporal para prueba
                })
        
        print(f"✅ CSV generado: {csv_file}")
        
        # Generar JSON también
        json_file = 'test_users_existentes.json'
        json_users = []
        for user in users[:3]:
            json_users.append({
                'nombre': user['nombre'] or 'Test',
                'apellido': user['apellido'] or 'Usuario',
                'correo': user['correo'] or '',
                'identificacion': user['identificacion'] or '',
                'telefono': user['telefono'] or '',
                'rol': user['rol'] or 'CLIENT',
                'contraseña': 'TestPass123!'
            })
        
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(json_users, f, indent=2, ensure_ascii=False)
        
        print(f"✅ JSON generado: {json_file}")
    else:
        print("⚠️  No se encontraron usuarios en la base de datos")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error al consultar la base de datos: {e}")
    import traceback
    traceback.print_exc()

