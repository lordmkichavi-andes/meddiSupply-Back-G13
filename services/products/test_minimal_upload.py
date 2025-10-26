#!/usr/bin/env python3
"""
Prueba mínima para la funcionalidad de carga de productos desde plantilla.
"""

import requests
import pandas as pd
import io

BASE_URL = "http://localhost:8080"

def test_download_template():
    """Prueba la descarga de plantilla."""
    print("🔽 Probando descarga de plantilla...")
    response = requests.get(f"{BASE_URL}/products/template/download")
    
    if response.status_code == 200:
        print("✅ Plantilla descargada exitosamente")
        return True
    else:
        print(f"❌ Error: {response.status_code}")
        return False

def test_upload_valid_csv():
    """Prueba carga de CSV válido."""
    print("⬆️ Probando carga de CSV válido...")
    
    # Crear CSV válido
    data = {
        'sku': ['TEST001', 'TEST002'],
        'name': ['Producto Test 1', 'Producto Test 2'],
        'value': [100.50, 250.75],
        'category_name': ['Electrónicos', 'Ropa'],
        'quantity': [10, 5],
        'warehouse_id': [1, 1],
        'image_url': ['https://example.com/test1.jpg', 'https://example.com/test2.jpg']
    }
    
    df = pd.DataFrame(data)
    csv_content = df.to_csv(index=False)
    
    files = {'file': ('test.csv', csv_content, 'text/csv')}
    response = requests.post(f"{BASE_URL}/products/upload", files=files)
    
    if response.status_code == 200:
        print("✅ CSV válido cargado exitosamente")
        print(f"📊 Respuesta: {response.json()}")
        return True
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"📄 Respuesta: {response.text}")
        return False

def test_upload_invalid_format():
    """Prueba carga de archivo con formato inválido."""
    print("⬆️ Probando carga de archivo con formato inválido...")
    
    files = {'file': ('test.txt', 'contenido de prueba', 'text/plain')}
    response = requests.post(f"{BASE_URL}/products/upload", files=files)
    
    if response.status_code == 400:
        print("✅ Formato inválido rechazado correctamente")
        print(f"📄 Respuesta: {response.json()}")
        return True
    else:
        print(f"❌ Error: {response.status_code}")
        return False

def main():
    """Función principal de prueba."""
    print("🚀 Pruebas mínimas de carga de productos")
    print("=" * 50)
    
    # 1. Descargar plantilla
    test_download_template()
    print()
    
    # 2. Cargar CSV válido
    test_upload_valid_csv()
    print()
    
    # 3. Probar formato inválido
    test_upload_invalid_format()
    print()
    
    print("✅ Pruebas completadas")

if __name__ == "__main__":
    main()
