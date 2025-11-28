FROM python:3.9-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar archivos de la aplicación
COPY prediccion_clima.pkl .
COPY API_Logisticlima.py .

# Exponer el puerto 8080
EXPOSE 8080

# Comando para iniciar la app
CMD ["uvicorn", "API_Logisticlima:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]