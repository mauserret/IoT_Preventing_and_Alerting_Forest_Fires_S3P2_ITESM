import os
from pymongo import MongoClient
col = MongoClient(os.environ["AZ_HOST"],
      username=os.environ["AZ_USER"], 
      password=os.environ["AZ_PASS"], 
      tls=True, authMechanism="SCRAM-SHA-256", retryWrites=False)["forest"]["readings"]
print("documents:", col.count_documents({}))
for d in col.find().sort("ts", -1).limit(3):
    print(d)
