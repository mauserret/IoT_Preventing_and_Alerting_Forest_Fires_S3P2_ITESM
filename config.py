"""Shared settings loader for collector.py and risk.py.

- Non-secret settings live in config.json and are re-read automatically when the
  file changes (no restart needed for thresholds, levels or sync settings).
- Secrets (Azure host/user/password) come from environment variables, loaded by
  systemd from /home/rey/collector.env.
"""
import json, os

CONFIG_PATH = os.environ.get("FOREST_CONFIG", "/home/rey/config.json")

DEFAULTS = {
    "schema": 1,
    # Absolute SAFETY NET only (very high counts). The sensitive rule is "rise" below.
    "gas_thresholds": {"mq2": 800, "mq135": 1000, "mq7": 2800},
    # Alert when a sensor rises well above its own recent median (see gasrise.py)
    "rise": {
        "enabled": True,
        "window_min": 60,          # baseline = median of the last 60 min
        "min_history_min": 15,     # need this much history before judging
        "min_samples": 10,
        "confirm": 2,              # consecutive over-readings needed
        "freeze_max_min": 60,      # after this long over, accept it as the new normal
        "ratio": {"mq2": 1.5, "mq135": 1.5, "mq7": 1.5},
        "min_delta": {"mq2": 100, "mq135": 120, "mq7": 300},
    },
    "levels": {"critico": 0.85, "alerta": 0.65, "precaucion": 0.30},
    "physical_rule": {"temp_min": 35.0, "rh_max": 25.0, "risk": 0.85},
    "model": {
        "path": "/home/rey/modelo_rf_fuerte.pkl",
        "defaults": {"wind": 4.0, "rain": 0.0, "FFMC": 90.0, "DMC": 100.0, "DC": 500.0, "ISI": 9.0},
    },
    "sync": {"every_s": 30, "batch": 500, "keep_days": 7},
    "alerts": {
        "enabled": True,
        "levels": ["ALERTA", "CRITICO"],
        "cooldown_s": 600,
        "check_every_s": 5,
        "no_data_minutes": 10,
    },
    "db_path": "/home/rey/buffer.db",
}

_cache = {"mtime": None, "data": DEFAULTS}


def _merge(base, extra):
    out = dict(base)
    for k, v in extra.items():
        out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def get():
    """Current settings. Keeps the last good version if the file is broken."""
    try:
        m = os.path.getmtime(CONFIG_PATH)
        if m != _cache["mtime"]:
            with open(CONFIG_PATH) as f:
                _cache["data"] = _merge(DEFAULTS, json.load(f))
            _cache["mtime"] = m
            print("config loaded from", CONFIG_PATH)
    except FileNotFoundError:
        pass  # use defaults
    except Exception as e:
        _cache["mtime"] = None
        print("config error, keeping previous settings:", e)
    return _cache["data"]


def secret(name):
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"Missing environment variable {name} (see collector.env)")
    return v
