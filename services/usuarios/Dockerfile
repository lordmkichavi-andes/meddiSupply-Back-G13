# Usa imagen compatible con Mac M1/M2 (ARM64) pero fuerza emulación AMD64
FROM --platform=linux/amd64 python:3.9-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia e instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código fuente
COPY . .

# Asegura que el código fuente esté en el path de Python
ENV PYTHONPATH=/app

# Expone el puerto interno del contenedor
EXPOSE 8080

# Comando de inicio del servicio
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
