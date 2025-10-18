#!/bin/bash
# Script para ejecutar tests sin cobertura para el servicio routes

echo "🧪 Ejecutando tests para el servicio routes..."

# Cambiar al directorio del servicio
cd "$(dirname "$0")"

# Ejecutar pytest sin cobertura
python -m pytest tests/ -v --tb=short

echo "✅ Tests completados"
