#!/usr/bin/env python3
"""
Script de prueba de rendimiento para consulta de localización de productos en bodega.
Simula 400 usuarios concurrentes consultando la ubicación de productos.
Requisito: La respuesta debe ser en menos de 2 segundos.
"""

import requests
import concurrent.futures
import time
import statistics
import os
from datetime import datetime
from typing import Dict, List, Tuple
import json

# Configuración
BASE_URL = "http://MediSu-MediS-5XPY2MhrDivI-109634141.us-east-1.elb.amazonaws.com"
ENDPOINT = "/products/by-warehouse"
WAREHOUSE_ID = 1  # Bodega a consultar
CONCURRENT_USERS = 400
TIMEOUT_SECONDS = 2  # Requisito: menos de 2 segundos
REQUESTS_PER_USER = 1  # Cada usuario hace 1 consulta

def consultar_localizacion_producto(warehouse_id: int, user_id: int) -> Dict:
    """
    Consulta la localización de productos en una bodega específica.
    
    Retorna información de:
    - sección (section)
    - pasillo (aisle)
    - mueble (shelf)
    - nivel (level)
    - lote
    - vencimiento (expiry_date)
    - cantidad disponible (quantity)
    """
    url = f"{BASE_URL}{ENDPOINT}/{warehouse_id}?include_locations=true"
    
    start_time = time.time()
    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS + 1)
        elapsed_time = time.time() - start_time
        
        result = {
            'user_id': user_id,
            'status_code': response.status_code,
            'response_time': elapsed_time,
            'success': response.status_code == 200,
            'has_data': False,
            'error': None
        }
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('products'):
                result['has_data'] = True
                # Verificar que tenga la información de localización requerida
                first_product = data['products'][0] if data['products'] else {}
                if 'locations' in first_product and len(first_product['locations']) > 0:
                    location = first_product['locations'][0]
                    result['has_location_data'] = all([
                        location.get('section'),
                        location.get('aisle'),
                        location.get('shelf'),
                        location.get('level'),
                        location.get('lote'),
                        location.get('quantity')
                    ])
                    result['location_fields'] = {
                        'section': location.get('section'),
                        'aisle': location.get('aisle'),
                        'shelf': location.get('shelf'),
                        'level': location.get('level'),
                        'lote': location.get('lote'),
                        'expiry_date': location.get('expiry_date'),
                        'quantity': location.get('quantity')
                    }
        else:
            result['error'] = f"HTTP {response.status_code}"
            try:
                error_data = response.json()
                result['error'] = error_data.get('error', result['error'])
            except:
                result['error'] = response.text[:100]
        
        return result
        
    except requests.exceptions.Timeout:
        elapsed_time = time.time() - start_time
        return {
            'user_id': user_id,
            'status_code': 0,
            'response_time': elapsed_time,
            'success': False,
            'has_data': False,
            'error': f'TIMEOUT (> {TIMEOUT_SECONDS + 1}s)',
            'exceeded_threshold': True
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        return {
            'user_id': user_id,
            'status_code': 0,
            'response_time': elapsed_time,
            'success': False,
            'has_data': False,
            'error': str(e),
            'exceeded_threshold': elapsed_time > TIMEOUT_SECONDS
        }


def ejecutar_prueba_concurrente() -> Tuple[List[Dict], Dict]:
    """Ejecuta la prueba con múltiples usuarios concurrentes."""
    print(f"\n{'='*70}")
    print(f"🚀 INICIO DE PRUEBA DE RENDIMIENTO")
    print(f"{'='*70}")
    print(f"📊 Configuración:")
    print(f"   - Usuarios concurrentes: {CONCURRENT_USERS}")
    print(f"   - Endpoint: {BASE_URL}{ENDPOINT}/{WAREHOUSE_ID}")
    print(f"   - Requisito: Respuesta en menos de {TIMEOUT_SECONDS} segundos")
    print(f"   - Consultas por usuario: {REQUESTS_PER_USER}")
    print(f"{'='*70}\n")
    
    start_time = time.time()
    results = []
    
    # Ejecutar requests concurrentes
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        futures = [
            executor.submit(consultar_localizacion_producto, WAREHOUSE_ID, user_id)
            for user_id in range(1, CONCURRENT_USERS + 1)
        ]
        
        print(f"⏳ Ejecutando {CONCURRENT_USERS} consultas concurrentes...")
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            
            # Mostrar progreso cada 50 usuarios
            if len(results) % 50 == 0:
                print(f"   ✓ Procesadas: {len(results)}/{CONCURRENT_USERS}")
    
    total_time = time.time() - start_time
    
    return results, {'total_time': total_time}


def generar_reporte(results: List[Dict], stats: Dict):
    """Genera un reporte detallado de los resultados."""
    # Generar nombre del archivo al inicio para mostrarlo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"performance_report_{timestamp}.json"
    
    total_requests = len(results)
    successful_requests = sum(1 for r in results if r['success'])
    failed_requests = total_requests - successful_requests
    requests_with_data = sum(1 for r in results if r.get('has_data', False))
    requests_with_location = sum(1 for r in results if r.get('has_location_data', False))
    timeouts = sum(1 for r in results if r.get('exceeded_threshold', False) or (r.get('error') and str(r.get('error', '')).startswith('TIMEOUT')))
    
    response_times = [r['response_time'] for r in results if r.get('response_time')]
    
    if response_times:
        min_time = min(response_times)
        max_time = max(response_times)
        avg_time = statistics.mean(response_times)
        median_time = statistics.median(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else max_time
        p99_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else max_time
        requests_under_threshold = sum(1 for t in response_times if t <= TIMEOUT_SECONDS)
        success_rate = (requests_under_threshold / total_requests) * 100
    else:
        min_time = max_time = avg_time = median_time = p95_time = p99_time = 0
        requests_under_threshold = 0
        success_rate = 0
    
    # Errores agrupados
    errors = {}
    for r in results:
        if not r['success'] and r.get('error'):
            error = r['error']
            errors[error] = errors.get(error, 0) + 1
    
    # Generar reporte
    print(f"\n{'='*70}")
    print(f"📈 REPORTE DE RESULTADOS")
    print(f"{'='*70}")
    print(f"\n📄 Archivo de resultados: {report_file}")
    print(f"   (Se guardará al finalizar el reporte)\n")
    print(f"\n⏱️  TIEMPOS DE RESPUESTA (segundos):")
    print(f"   - Mínimo:        {min_time:.3f}s")
    print(f"   - Máximo:        {max_time:.3f}s")
    print(f"   - Promedio:      {avg_time:.3f}s")
    print(f"   - Mediana:       {median_time:.3f}s")
    print(f"   - Percentil 95:  {p95_time:.3f}s")
    print(f"   - Percentil 99:  {p99_time:.3f}s")
    print(f"\n📊 ESTADÍSTICAS DE REQUESTS:")
    print(f"   - Total de requests:        {total_requests}")
    print(f"   - Requests exitosos:        {successful_requests} ({(successful_requests/total_requests)*100:.1f}%)")
    print(f"   - Requests fallidos:         {failed_requests} ({(failed_requests/total_requests)*100:.1f}%)")
    print(f"   - Requests con datos:       {requests_with_data} ({(requests_with_data/total_requests)*100:.1f}%)")
    print(f"   - Requests con ubicación:   {requests_with_location} ({(requests_with_location/total_requests)*100:.1f}%)")
    print(f"   - Timeouts:                  {timeouts} ({(timeouts/total_requests)*100:.1f}%)")
    print(f"\n✅ CUMPLIMIENTO DEL REQUISITO (< {TIMEOUT_SECONDS}s):")
    print(f"   - Requests bajo umbral:     {requests_under_threshold}/{total_requests}")
    print(f"   - Tasa de éxito:            {success_rate:.2f}%")
    
    if success_rate >= 95:
        status = "✅ CUMPLE"
    elif success_rate >= 80:
        status = "⚠️  PARCIALMENTE"
    else:
        status = "❌ NO CUMPLE"
    
    print(f"   - Estado:                    {status}")
    
    if errors:
        print(f"\n❌ ERRORES ENCONTRADOS:")
        for error, count in sorted(errors.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {error}: {count} veces")
    
    print(f"\n⏱️  TIEMPO TOTAL DE EJECUCIÓN: {stats['total_time']:.2f} segundos")
    
    # Ejemplo de datos de localización si hay
    if requests_with_location > 0:
        sample_result = next((r for r in results if r.get('has_location_data', False)), None)
        if sample_result and 'location_fields' in sample_result:
            print(f"\n📦 EJEMPLO DE DATOS DE LOCALIZACIÓN:")
            location = sample_result['location_fields']
            print(f"   - Sección:     {location.get('section', 'N/A')}")
            print(f"   - Pasillo:     {location.get('aisle', 'N/A')}")
            print(f"   - Mueble:      {location.get('shelf', 'N/A')}")
            print(f"   - Nivel:       {location.get('level', 'N/A')}")
            print(f"   - Lote:        {location.get('lote', 'N/A')}")
            print(f"   - Vencimiento: {location.get('expiry_date', 'N/A')}")
            print(f"   - Cantidad:    {location.get('quantity', 'N/A')}")
    
    print(f"\n{'='*70}")
    print(f"🎯 CONCLUSIÓN:")
    if success_rate >= 95:
        print(f"   ✅ El sistema CUMPLE con el requisito de respuesta < {TIMEOUT_SECONDS}s")
        print(f"      para {CONCURRENT_USERS} usuarios concurrentes.")
    elif success_rate >= 80:
        print(f"   ⚠️  El sistema PARCIALMENTE cumple el requisito.")
        print(f"      Se recomienda optimización para mejorar la tasa de éxito.")
    else:
        print(f"   ❌ El sistema NO CUMPLE con el requisito.")
        print(f"      Se requiere optimización urgente.")
    print(f"{'='*70}\n")
    
    # Guardar resultados en JSON
    report_data = {
        'timestamp': datetime.now().isoformat(),
        'configuration': {
            'base_url': BASE_URL,
            'endpoint': f"{ENDPOINT}/{WAREHOUSE_ID}",
            'concurrent_users': CONCURRENT_USERS,
            'timeout_threshold': TIMEOUT_SECONDS
        },
        'statistics': {
            'total_requests': total_requests,
            'successful_requests': successful_requests,
            'failed_requests': failed_requests,
            'requests_with_data': requests_with_data,
            'requests_with_location': requests_with_location,
            'timeouts': timeouts,
            'success_rate': success_rate,
            'response_times': {
                'min': min_time,
                'max': max_time,
                'avg': avg_time,
                'median': median_time,
                'p95': p95_time,
                'p99': p99_time
            }
        },
        'results': results[:10]  # Solo guardar primeros 10 como muestra
    }
    
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"💾 ARCHIVO JSON GENERADO")
    print(f"{'='*70}")
    print(f"📁 Nombre del archivo: {report_file}")
    print(f"📂 Ubicación: {os.path.abspath(report_file)}")
    print(f"📊 Tamaño: {os.path.getsize(report_file) / 1024:.2f} KB")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    try:
        # Ejecutar prueba
        results, stats = ejecutar_prueba_concurrente()
        
        # Generar reporte
        generar_reporte(results, stats)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Prueba interrumpida por el usuario.")
    except Exception as e:
        print(f"\n\n❌ Error durante la ejecución: {str(e)}")
        import traceback
        traceback.print_exc()

