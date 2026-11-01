import json
from datetime import datetime, timezone
from pymongo import MongoClient
import paho.mqtt.client as mqtt

MONGO_URI = ""
col = MongoClient(MONGO_URI)["forest"]["readings"]

def on_connect(client, userdata, flags, rc, props=None):
    client.subscribe("forest/+/readings")

def on_message(client, userdata, msg):
    d = json.loads(msg.payload)
    d["ts"] = datetime.now(timezone.utc)
    col.insert_one(d)
    print("saved", d)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883)
client.loop_forever()