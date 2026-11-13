from risk import evaluar
import config
import json, sqlite3, threading, time
from datetime import datetime, timezone, timedelta
import paho.mqtt.client as mqtt
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

# Secrets come from the environment (collector.env, loaded by systemd)
AZ_HOST = config.secret("AZ_HOST")
AZ_USER = config.secret("AZ_USER")
AZ_PASS = config.secret("AZ_PASS")


def open_db():
    db = sqlite3.connect(config.get()["db_path"], timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS readings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        payload TEXT NOT NULL,
        synced INTEGER NOT NULL DEFAULT 0)""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_synced ON readings(synced, id)")
    db.commit()
    return db


def connect_azure():
    return MongoClient(
        AZ_HOST, username=AZ_USER, password=AZ_PASS, tls=True,
        authMechanism="SCRAM-SHA-256", retryWrites=False,
        serverSelectionTimeoutMS=8000,
    )["forest"]["readings"]


def syncer():
    db = open_db()
    col = None
    while True:
        sync = config.get()["sync"]          # re-read every loop: changes apply without restart
        time.sleep(sync["every_s"])
        try:
            if col is None:
                col = connect_azure()
            while True:
                rows = db.execute(
                    "SELECT id, ts, payload FROM readings WHERE synced=0 ORDER BY id LIMIT ?",
                    (sync["batch"],)).fetchall()
                if not rows:
                    break
                docs = []
                for rid, ts, payload in rows:
                    d = json.loads(payload)
                    d["ts"] = datetime.fromisoformat(ts)
                    d["_id"] = f"{d.get('device', 'dev')}:{ts}"
                    docs.append(d)
                try:
                    col.insert_many(docs, ordered=False)
                except BulkWriteError as e:
                    # code 11000 = already uploaded, fine; anything else is a real error
                    if any(err["code"] != 11000 for err in e.details["writeErrors"]):
                        raise
                ids = [r[0] for r in rows]
                db.execute(
                    f"UPDATE readings SET synced=1 WHERE id IN ({','.join('?' * len(ids))})", ids)
                db.commit()
                print(f"synced {len(ids)} rows", flush=True)
            cutoff = (datetime.now(timezone.utc) - timedelta(days=sync["keep_days"])).isoformat(timespec="milliseconds")
            db.execute("DELETE FROM readings WHERE synced=1 AND ts < ?", (cutoff,))
            db.commit()
        except Exception as e:
            col = None
            print("sync failed, will retry:", type(e).__name__, e, flush=True)


mdb = open_db()


def on_connect(client, userdata, flags, rc, props=None):
    client.subscribe("forest/+/readings")


def on_message(client, userdata, msg):
    try:
        d = json.loads(msg.payload)
    except ValueError:
        return
    try:
        d.update(evaluar(d))
    except Exception as e:
        print("risk failed:", e, flush=True)
    d["schema"] = config.get()["schema"]     # lets dashboard/backfill handle old and new documents
    ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    mdb.execute("INSERT INTO readings(ts, payload) VALUES (?,?)", (ts, json.dumps(d)))
    mdb.commit()
    print("buffered", ts, d.get("risk_level"), flush=True)


threading.Thread(target=syncer, daemon=True).start()
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883)     # if Mosquitto isn't up yet, systemd restarts us
client.loop_forever()
