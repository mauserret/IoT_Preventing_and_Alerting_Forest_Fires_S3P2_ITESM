"""Telegram alerts for the forest node.

Runs as its own service, separate from collector.py. It only READS the local
SQLite buffer, so a problem here can never stop data capture.

Rules (all adjustable in config.json under "alerts", applied without restart):
- Sends a message when risk_level is ALERTA or CRITICO.
- At most one alert per cooldown window, except when the level gets worse
  (ALERTA -> CRITICO is sent immediately).
- Sends one "normalized" message when it goes back below the alert levels.
- Sends one message if no new readings arrive for no_data_minutes.

Secrets come from the environment (collector.env):
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

    python3 alerter.py --test     sends one test message and exits
"""
import json, sqlite3, sys, time, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
import config

TOKEN = config.secret("TELEGRAM_TOKEN")
CHAT_ID = config.secret("TELEGRAM_CHAT_ID")
TZ = ZoneInfo("America/Mexico_City")

RANK = {"SIN_DATOS": 0, "NORMAL": 1, "PRECAUCION": 2, "ALERTA": 3, "CRITICO": 4}
ICON = {"PRECAUCION": "🟡", "ALERTA": "⚠️", "CRITICO": "🔥"}


def send(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    body = json.dumps({"chat_id": CHAT_ID, "text": text}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception as e:
        # the message of these exceptions does not include the URL, so the token is not logged
        print("telegram send failed:", type(e).__name__, e, flush=True)
        return False


def local_time(ts):
    return datetime.fromisoformat(ts).astimezone(TZ).strftime("%d/%m %H:%M:%S")


def describe(ts, d):
    lvl = d.get("risk_level", "?")
    return "\n".join([
        f"{ICON.get(lvl, '')} {lvl} - {d.get('device', '?')}",
        str(d.get("risk_reason", "")),
        f"Temp: {d.get('temperature')} °C   Hum: {d.get('humidity')} %",
        f"MQ-2: {d.get('mq2')}   MQ-135: {d.get('mq135')}   MQ-7: {d.get('mq7')}",
        f"Hora: {local_time(ts)}",
    ])


def main():
    if "--test" in sys.argv:
        ok = send("✅ Prueba de alertas del nodo forestal: si ves esto, Telegram funciona.")
        print("sent" if ok else "FAILED (see message above)")
        return

    db = sqlite3.connect(config.get()["db_path"], timeout=30)
    last_id = db.execute("SELECT COALESCE(MAX(id), 0) FROM readings").fetchone()[0]  # ignore old data
    last_sent_time, last_sent_rank = 0.0, 0
    alerting = False
    last_data_time, no_data_sent = time.time(), False
    print("alerter started, watching from id", last_id, flush=True)
    send("🟢 Alertador iniciado.")

    while True:
        a = config.get()["alerts"]
        time.sleep(a["check_every_s"])
        if not a["enabled"]:
            continue
        min_rank = min(RANK[l] for l in a["levels"])
        now = time.time()

        try:
            rows = db.execute("SELECT id, ts, payload FROM readings WHERE id > ? ORDER BY id",
                              (last_id,)).fetchall()
        except Exception as e:
            print("db read failed:", e, flush=True)
            continue

        if rows:
            last_id = rows[-1][0]
            last_data_time = now
            if no_data_sent and send("✅ Los datos regresaron."):
                no_data_sent = False

            worst = None                      # worst reading in this batch
            for rid, ts, payload in rows:
                d = json.loads(payload)
                r = RANK.get(d.get("risk_level"), 0)
                if worst is None or r > worst[0]:
                    worst = (r, ts, d)
            rank, ts, d = worst

            if rank >= min_rank:
                in_window = (now - last_sent_time) < a["cooldown_s"]
                if (not in_window) or rank > last_sent_rank:
                    if send(describe(ts, d)):
                        last_sent_time, last_sent_rank, alerting = now, rank, True
            elif alerting:
                if send(f"✅ Normalizado: nivel {d.get('risk_level')} a las {local_time(ts)}."):
                    alerting = False

        elif (not no_data_sent) and now - last_data_time > a["no_data_minutes"] * 60:
            if send(f"❌ Sin datos del nodo desde hace {a['no_data_minutes']} minutos "
                    "(revisar hotspot, ESP32 o collector)."):
                no_data_sent = True


if __name__ == "__main__":
    main()

