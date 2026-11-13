import joblib, pandas as pd
import config

FEATURES = ["temp", "RH", "wind", "rain", "FFMC", "DMC", "DC", "ISI"]

_modelo = {"path": None, "obj": None}


def get_model():
    """Loads the model once, and again only if the path in config.json changes."""
    path = config.get()["model"]["path"]
    if path != _modelo["path"]:
        _modelo["path"] = path
        try:
            _modelo["obj"] = joblib.load(path)
        except Exception as e:
            _modelo["obj"] = None
            print("model not loaded:", e)
    return _modelo["obj"]


def nivel(r, levels):
    if r is None:                    return "SIN_DATOS"
    if r >= levels["critico"]:       return "CRITICO"
    if r >= levels["alerta"]:        return "ALERTA"
    if r >= levels["precaucion"]:    return "PRECAUCION"
    return "NORMAL"


def evaluar(d):
    cfg = config.get()
    t, h = d.get("temperature"), d.get("humidity")
    prob, razon = None, "Sin datos ambientales"

    if t is not None and h is not None:
        rule = cfg["physical_rule"]
        modelo = get_model()
        if t >= rule["temp_min"] and h <= rule["rh_max"]:
            prob, razon = rule["risk"], "Regla fisica: calor extremo y sequia"
        elif modelo is not None:
            X = pd.DataFrame([{"temp": t, "RH": h, **cfg["model"]["defaults"]}])[FEATURES]
            prob, razon = float(modelo.predict_proba(X)[0][1]), "Evaluacion ambiental (ML)"

    motivos = []
    if d.get("warm", 1):             # ignore gas while the heaters warm up
        th = cfg["gas_thresholds"]
        if (d.get("mq2") or 0)   > th["mq2"]:   motivos.append("Humo (MQ-2)")
        if (d.get("mq135") or 0) > th["mq135"]: motivos.append("CO2/VOC (MQ-135)")
        if (d.get("mq7") or 0)   > th["mq7"]:   motivos.append("CO (MQ-7)")

    if motivos:
        riesgo, razon = 1.0, "Sensor de gas: " + ", ".join(motivos)
    else:
        riesgo = prob

    return {"risk_env": None if prob is None else round(prob, 3),
            "risk": None if riesgo is None else round(riesgo, 3),
            "risk_level": nivel(riesgo, cfg["levels"]),
            "risk_reason": razon,
            "gas_alert": bool(motivos)}
