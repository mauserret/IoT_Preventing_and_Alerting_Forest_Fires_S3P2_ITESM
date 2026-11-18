import os
from pathlib import Path
from pymongo import MongoClient

def load_env(path):
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())

load_env(Path("/home/rey/collector.env"))

col = MongoClient(
    os.environ["AZ_HOST"],
    username=os.environ["AZ_USER"],
    password=os.environ["AZ_PASS"],
    tls=True,
    authMechanism="SCRAM-SHA-256",
    retryWrites=False
)["forest"]["readings"]

print("documents:", col.count_documents({}))

for d in col.find().sort("ts", -1).limit(3):
    print(d)
