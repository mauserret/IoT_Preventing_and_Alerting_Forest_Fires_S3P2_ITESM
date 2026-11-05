import json, sqlite3, threading, time
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from pymongo import MongoClient
from pymongo.errors import BulkWriteError

MONGO_URI = ""
DB_PATH   = ""
SYNC_EVERY, BATCH, KEEP_DAYS = 30, 500, 7

def open_db():
    db = sqlite3.connect(DB_PATH, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS readings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        payload TEXT NOT NULL,
        synced INTEGER NOT NULL DEFAULT 0)""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_synced ON readings(synced, id)")
    db.commit()
    return db

def syncer():
    db = open_db()
    col = None
    while True:
        time.sleep(SYNC_EVERY)
        try:
            if col is None:
                col = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)["forest"]["readings"]
            while True:
                rows = db.execute("SELECT id, ts, payload FROM readings WHERE synced=0 ORDER BY id LIMIT ?", (BATCH,)).fetchall()
                if not rows:
                    break
                docs = []
                for rid, ts, payload in rows:
                    d = json.loads(payload)
                    d["ts"] = datetime.fromisoformat(ts)
                    d["_id"] = f"{d.get('device','dev')}:{ts}"
                    docs.append(d)
                try:
                    col.insert_many(docs, ordered=False)
                except BulkWriteError as e:
                    if any(err["code"] != 11000 for err in e.details["writeErrors"]):
                        raise            # real error; code 11000 = already uploaded, fine
                ids = [r[0] for r in rows]
                db.execute(f"UPDATE readings SET synced=1 WHERE id IN ({','.join('?'*len(ids))})", ids)
                db.commit()
                print(f"synced {len(ids)} rows")
            db.execute("DELETE FROM readings WHERE synced=1 AND ts < datetime('now', ?)", (f"-{KEEP_DAYS} days",))
            db.commit()
        except Exception as e:
            col = None
            print("sync failed, will retry:", type(e).__name__)

mdb = open_db()

def on_connect(client, userdata, flags, rc, props=None):
    client.subscribe("forest/+/readings")

def on_message(client, userdata, msg):
    try:
        json.loads(msg.payload)
    except ValueError:
        return
    ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    mdb.execute("INSERT INTO readings(ts, payload) VALUES (?,?)", (ts, msg.payload.decode()))
    mdb.commit()
    print("buffered", ts)

threading.Thread(target=syncer, daemon=True).start()
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883)
client.loop_forever()
