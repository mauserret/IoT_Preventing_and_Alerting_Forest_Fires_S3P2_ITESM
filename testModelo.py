import joblib
import pandas as pd
import numpy as np
import time

# ─── Cargar el modelo fuerte ───────────────────────────────────
try:
    modelo = joblib.load('modelo_rf_fuerte.pkl')
except FileNotFoundError:
    print("⚠️ Error: No se encuentra 'modelo_rf_fuerte.pkl'. Ejecuta el script de entrenamiento primero.")
    exit()

# ─── Valores por defecto para variables no medidas ─────────────
DEFAULTS = {
    "wind": 4.0,
    "rain": 0.0,
    "FFMC": 90.0,
    "DMC": 100.0,
    "DC": 500.0,
    "ISI": 9.0
}

# Coordenadas aproximadas del Bosque La Primavera
LAT_DEFAULT = 20.6736
LON_DEFAULT = -103.5608

def calcular_riesgo_hibrido(temp, humedad, humo_mq2, co2_mq135):
    """
    Calcula el riesgo combinando el modelo de ML, reglas físicas y sensores de gas.
    """
    # ── REGLA 0: Sentido Común Físico (Condiciones Extremas) ──
    # Si hace demasiado calor y hay muy poca humedad, el riesgo es alto por defecto,
    # sin importar lo que diga el modelo de ML (evita fallos por extrapolación).
    if temp >= 35.0 and humedad <= 25.0:
        prob_ambiental = 0.85  # Forzamos un 85% de riesgo ambiental
        razon_ambiental = "Regla Física: Calor extremo y sequía (T>=35 y HR<=25)"
    else:
        # ── Regla 1: Modelo Ambiental (Machine Learning) ──────────
        entrada = pd.DataFrame([{
            "temp": temp,
            "RH": humedad,
            **DEFAULTS
        }])
        entrada = entrada[["temp", "RH", "wind", "rain", "FFMC", "DMC", "DC", "ISI"]]
        prob_ambiental = modelo.predict_proba(entrada)[0][1] 
        razon_ambiental = "Evaluación ambiental (ML)"

    # ── Regla 2: Detección de Humo (MQ-2) ────────────────────
    UMBRAL_HUMO = 500
    alerta_humo = humo_mq2 > UMBRAL_HUMO

    # ── Regla 3: Detección de CO2/VOC (MQ-135) ────────────────
    UMBRAL_CO2 = 600
    alerta_co2 = co2_mq135 > UMBRAL_CO2

    # ── Fusión de las Reglas ────────────────────────────────
    if alerta_humo or alerta_co2:
        riesgo_final = 1.0
        motivo = []
        if alerta_humo: motivo.append("Humo (MQ-2)")
        if alerta_co2: motivo.append("CO2/VOC (MQ-135)")
        razon = f"Alerta crítica por sensor de gas: {', '.join(motivo)}"
    else:
        riesgo_final = prob_ambiental
        razon = razon_ambiental

    # ── Clasificación ─────────────────────────────────────────
    if riesgo_final >= 0.75:
        nivel = "CRÍTICO 🔴"
    elif riesgo_final >= 0.50:
        nivel = "ALERTA 🟠"
    elif riesgo_final >= 0.30:
        nivel = "PRECAUCIÓN 🟡"
    else:
        nivel = "NORMAL 🟢"

    return {
        "prob_ambiental": round(prob_ambiental, 3),
        "alerta_humo": alerta_humo,
        "alerta_co2": alerta_co2,
        "riesgo_final": round(riesgo_final, 3),
        "nivel": nivel,
        "razon": razon
    }

# ─── Batería de Pruebas Automatizada ──────────────────────────
if __name__ == "__main__":
    print("🌲 SIMULADOR AUTOMATIZADO - BOSQUE LA PRIMAVERA 🌲\n")
    
    escenarios = [
        {
            "nombre": "1. Día fresco y húmedo (Todo normal)",
            "temp": 18.0, "humedad": 75.0, "humo": 120, "co2": 150
        },
        {
            "nombre": "2. Calor extremo y sequía (Riesgo Ambiental ML)",
            "temp": 38.5, "humedad": 15.0, "humo": 150, "co2": 180
        },
        {
            "nombre": "3. Fogata oculta (Se dispara MQ-2)",
            "temp": 22.0, "humedad": 60.0, "humo": 750, "co2": 250
        },
        {
            "nombre": "4. Combustión invisible (Se dispara MQ-135)",
            "temp": 24.0, "humedad": 50.0, "humo": 200, "co2": 700
        },
        {
            "nombre": "5. Incendio Forestal (Todo mal)",
            "temp": 40.0, "humedad": 10.0, "humo": 900, "co2": 850
        }
    ]

    for i, esc in enumerate(escenarios):
        print(f"▶ PROBANDO ESCENARIO: {esc['nombre']}")
        print(f"📍 Ubicación: ({LAT_DEFAULT}, {LON_DEFAULT})")
        print(f"🌡 Temp: {esc['temp']}°C | 💧 Humedad: {esc['humedad']}% | 💨 Humo: {esc['humo']} | 🌫 CO2: {esc['co2']}")
        
        resultado = calcular_riesgo_hibrido(esc['temp'], esc['humedad'], esc['humo'], esc['co2'])
        
        print("-" * 50)
        print(f"🔹 Prob. Ambiental (ML): {resultado['prob_ambiental']*100:.1f}%")
        print(f"🔸 Alerta por Humo: {'SÍ' if resultado['alerta_humo'] else 'NO'}")
        print(f"🔸 Alerta por CO2: {'SÍ' if resultado['alerta_co2'] else 'NO'}")
        print("-" * 50)
        print(f"🚨 RIESGO FINAL: {resultado['riesgo_final']*100:.1f}% - {resultado['nivel']}")
        print(f"📝 Razón: {resultado['razon']}")
        print("=" * 50 + "\n")
        
        time.sleep(1)
        
    print("✅ Pruebas finalizadas. Listo para la demostración.")