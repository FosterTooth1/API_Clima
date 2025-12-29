from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd
import joblib
import requests
from datetime import datetime
import numpy as np
import os

app = FastAPI()

# Ruta del modelo y clave de API
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "model", "prediccion_clima.pkl")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# Declaración global del modelo
modelo = None

# Cargar el modelo al iniciar la aplicaciónw
@app.on_event("startup")
def load_model():
    global modelo
    try:
        modelo = joblib.load(MODEL_PATH)
        print("Modelo cargado exitosamente!")
    except Exception as e:
        print(f"Error fatal cargando el modelo: {e}")

# Clase para las coordenadas
class Coordenadas(BaseModel):
    lat: float
    lon: float

# Funciones auxiliares
# Cambiar formato de hora "YYYY-MM-DD HH:MM" a minutos desde medianoche
def cambiarFormatoHora(fecha_hora_str):
    dt = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M")
    return dt.hour * 60 + dt.minute

# Cambiar formato de dirección del viento a grados
def cambiarFormatoViento(dir):
    mapa = {"CALM": -1, "N": 0, "NNE": 22.5, "NE": 45, "ENE": 67.5, "E": 90,
            "ESE": 112.5, "SE": 135, "SSE": 157.5, "S": 180, "SSW": 202.5,
            "SW": 225, "WSW": 247.5, "W": 270, "WNW": 292.5, "NW": 315, "NNW": 337.5}
    return mapa.get(dir, -1) # Default -1 si falla

# Endpoint para predecir el clima
@app.post("/predecir")
def predecir_clima(coords: Coordenadas):
    global modelo
    if not modelo:
        raise HTTPException(status_code=500, detail="El modelo no está cargado.")

    lat_f = coords.lat
    lon_f = coords.lon
    location = f"{lat_f},{lon_f}"
    
    # Obtener datos de WeatherAPI
    url = f"https://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={location}&aqi=no"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error conectando a WeatherAPI: {str(e)}")

    # Obtener y transformar datos necesarios
    try:
        hora_API = data['location']['localtime']
        temperatura = data['current']['temp_c']
        puntoRocio = data['current']['dewpoint_c']
        humedad = data['current']['humidity']
        dirViento_API = data['current']['wind_dir']
        velocidadViento = data['current']['wind_kph']
        
        hora_num = cambiarFormatoHora(hora_API)
        dir_viento_num = cambiarFormatoViento(dirViento_API)
        
        # Crear DataFrame para el modelo
        columnas = ['Time', 'Temperature', 'Dew Point', 'Humidity', 'Wind', 'Wind Speed']
        fila_predict = pd.DataFrame([[
            hora_num, temperatura, puntoRocio, humedad, dir_viento_num, velocidadViento
        ]], columns=columnas)
        
    except KeyError as e:
        raise HTTPException(status_code=500, detail=f"Faltan datos en la respuesta de la API: {e}")

    # Realizar la predicción
    condiciones = ['Nublado', 'Considerablemente nublado', 'Despejado', 'Niebla', 'Bruma',
        'Lluvia intensa', 'Tormenta electrica intensa', 'Neblina', 'Lluvia', 'Truenos']
    
    try:
        pred_array = modelo.predict(fila_predict)
        pred_idx = int(pred_array[0])
        
        if 0 <= pred_idx < len(condiciones):
            resultado = condiciones[pred_idx]
        else:
            resultado = f"Indice desconocido: {pred_idx}"
            
        return {
            "ubicacion": data['location']['name'],
            "prediccion": resultado,
            "datos_actuales": {
                "temp": temperatura,
                "humedad": humedad
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la predicción del modelo: {e}")