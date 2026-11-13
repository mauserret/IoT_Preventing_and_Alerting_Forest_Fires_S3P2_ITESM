import joblib
import pandas as pd
import sqlite3
import time
from datetime import datetime

# Librerías Bot de Telegram
import asyncio
from telegram import Bot

# Parametros iniciales del bot de telegram
TOKEN = ""
CHAT_ID = 

# ─── 1. Cargar Modelo ─────────────────────────────────────────
try:
    modelo = joblib.load('modelo_rf_fuerte.pkl')
except FileNotFoundError:
    print("⚠️ Error: No se encuentra 'modelo_rf_fuerte.pkl'.")
    exit()

"""DEFAULTS = {
    "wind": 4.0, "rain": 0.0, "FFMC": 90.0,
    "DMC": 100.0, "DC": 500.0, "ISI": 9.0
}
"""
# DEFAULTS PARA NUEVAS PRUEBAS
DEFAULTS = {
    "wind": 3.5, "rain": 0.0, "FFMC": 84.0,
    "DMC": 45.0, "DC": 180.0, "ISI": 4.5
}

LAT_DEFAULT, LON_DEFAULT = 20.6736, -103.5608

# ─── 2. Lógica de Riesgo (3 Reglas) ───────────────────────────
def calcular_riesgo_hibrido(temp, humedad, humo_mq2, co2_mq135):
    # Regla 0: Física (Extremos)
    if temp >= 35.0 and humedad <= 25.0:
        prob_ambiental = 0.85
        razon_ambiental = "Regla Física: Calor extremo y sequía"
    else:
        # Regla 1: ML
        entrada = pd.DataFrame([{"temp": temp, "RH": humedad, **DEFAULTS}])
        entrada = entrada[["temp", "RH", "wind", "rain", "FFMC", "DMC", "DC", "ISI"]]
        prob_ambiental = modelo.predict_proba(entrada)[0][1] 
        razon_ambiental = "Evaluación ambiental (ML)"

    # Reglas 2 y 3: Gases
    alerta_humo = humo_mq2 > 500
    alerta_co2 = co2_mq135 > 600

    if alerta_humo or alerta_co2:
        riesgo_final = 1.0
        motivo = []
        if alerta_humo: motivo.append("Humo (MQ-2)")
        if alerta_co2: motivo.append("CO2/VOC (MQ-135)")
        razon = f"Sensor de gas: {', '.join(motivo)}"
    else:
        riesgo_final = prob_ambiental
        razon = razon_ambiental

    if riesgo_final >= 0.85:
        nivel = "CRÍTICO"
    elif riesgo_final >= 0.65:
        nivel = "ALERTA"
    elif riesgo_final >= 0.30:
        nivel = "PRECAUCIÓN"
    else:
        nivel = "NORMAL"

    return {
        "prob_ambiental": round(prob_ambiental, 3),
        "riesgo_final": round(riesgo_final, 3),
        "nivel": nivel,
        "razon": razon
    }

# Funcion para bot de Telegram

async def mensaje_alerta(riesgo):
    if riesgo >= 0.30:
        if riesgo >= 0.85:
            msg = "🚨 ALERTA DE INCENDIO\nSe han detectado niveles críticos en la zona, se requiere de acción inmediata"
        elif riesgo >= 0.65:
            msg = "⚠️ ALERTA\nSe han detectado probabilidades altas de incendio en la zona, se requiere de acciones preventivas"
        else:
            msg = "❕Precaución\nLas condiciones climáticas pueden propiciar un incendio"

        bot = Bot(token=TOKEN)
        async with bot:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=msg
            )
        print("   -> Mensaje enviado correctamente")
    
    
# ─── 3. Base de Datos SQLite ──────────────────────────────────
conn = sqlite3.connect('bosque_simulacion.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS alertas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        temperatura REAL, humedad REAL, nivel_humo INTEGER,
        nivel_co2 INTEGER, nivel_riesgo REAL,
        alerta_activa BOOLEAN,
        latitud REAL, longitud REAL
    )
''')
conn.commit()

# ─── 4. Simulación ────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 SIMULACIÓN LOCAL: ML + SQLite + LED (Sin Telegram) 🚀\n")
    
    """ escenarios = [
        {"nombre": "1. Día normal", "temp": 18.0, "humedad": 75.0, "humo": 120, "co2": 150},
        {"nombre": "2. Calor extremo (Regla Física)", "temp": 38.5, "humedad": 15.0, "humo": 150, "co2": 180},
        {"nombre": "3. Fogata (Se dispara MQ-2)", "temp": 22.0, "humedad": 60.0, "humo": 750, "co2": 250},
        {"nombre": "4. Todo normal otra vez", "temp": 20.0, "humedad": 50.0, "humo": 200, "co2": 300},
        {"nombre": "5. Tarde templada estable", "temp": 21.0, "humedad": 48.0, "humo": 140, "co2": 240}  
        ] """
        
    escenarios = [
        # 1. NORMAL (< 0.30) -> LED apagado | NO envía mensaje a Telegram
        {"nombre": "1. Día fresco y húmedo (NORMAL)", "temp": 14.0, "humedad": 80.0, "humo": 110, "co2": 180},

        # 2. PRECAUCIÓN (0.30 - 0.64) -> LED apagado | Envía: ❕Precaución
        {"nombre": "2. Tarde cálida moderada (PRECAUCIÓN)", "temp": 24.5, "humedad": 42.0, "humo": 140, "co2": 220},

        # 3. ALERTA (0.65 - 0.84) -> LED encendido | Envía: ⚠️ ALERTA
        {"nombre": "3. Calor alto y baja humedad (ALERTA)", "temp": 32.5, "humedad": 27.0, "humo": 160, "co2": 260},

        # 4. CRÍTICO por Regla Física (0.85) -> LED encendido | Envía: 🚨 ALERTA DE INCENDIO
        {"nombre": "4. Calor extremo y sequía (CRÍTICO - Física)", "temp": 38.5, "humedad": 15.0, "humo": 150, "co2": 180},

        # 5. CRÍTICO por Sensor de Gas (1.00) -> LED encendido | Envía: 🚨 ALERTA DE INCENDIO
        {"nombre": "5. Presencia de humo/CO2 (CRÍTICO - Sensores)", "temp": 21.0, "humedad": 60.0, "humo": 750, "co2": 680}
    ]

    for esc in escenarios:
        print(f"▶ PROBANDO: {esc['nombre']}")
        print(f"🌡 T:{esc['temp']}°C | 💧 H:{esc['humedad']}% | 💨 Humo:{esc['humo']} | 🌫 CO2:{esc['co2']}")
        
        res = calcular_riesgo_hibrido(esc['temp'], esc['humedad'], esc['humo'], esc['co2'])
        
        # Simulamos el LED
        alerta_activa = res['riesgo_final'] >= 0.65
        if alerta_activa:
            print("💡 [LED ENCENDIDO - SIMULANDO ROCIADORES]")
            # Enviado de mensaje de alerta
        else:
            print("⚫ [LED APAGADO]")

        # Mandar mensajes Bot de Telegram
        if res['nivel'] != "NORMAL":
            asyncio.run(mensaje_alerta(res['riesgo_final']))
            
        # Guardar en SQLite
        cursor.execute('''
            INSERT INTO alertas (temperatura, humedad, nivel_humo, nivel_co2, nivel_riesgo, alerta_activa, latitud, longitud)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (esc['temp'], esc['humedad'], esc['humo'], esc['co2'], res['riesgo_final'], alerta_activa, LAT_DEFAULT, LON_DEFAULT))
        conn.commit()

        print(f"   -> Resultado: {res['nivel']} ({res['riesgo_final']*100:.2f}%)")
        print(f"   -> Motivo: {res['razon']}")
        print(f"   -> Guardado en base de datos.\n")
        time.sleep(1)

    print("✅ Simulación terminada.")
    print("Revisa el archivo 'bosque_simulacion.db' para ver los registros guardados.")