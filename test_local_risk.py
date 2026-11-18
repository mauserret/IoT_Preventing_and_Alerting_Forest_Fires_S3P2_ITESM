import risk
import json

# Make sure the terminal prints our test results clearly
print("=== TESTING ZAPOPAN CLIMATE SCORE & RISK LOGIC ===\n")

# Scenario 1: A normal, pleasant day in Zapopan
d1 = {"temperature": 22.0, "humidity": 70.0, "mq2": 200, "mq135": 300, "mq7": 1000, "warm": 1}
res1 = risk.evaluar(d1)
print(f"1. Normal Day (22°C, 70% RH):")
print(f"   Risk Level: {res1['risk_level']} (Risk: {res1['risk']})")
print(f"   Reason:     {res1['risk_reason']}\n")

# Scenario 2: A very hot and dry day (Should trigger the Zapopan local score)
d2 = {"temperature": 34.0, "humidity": 20.0, "mq2": 200, "mq135": 300, "mq7": 1000, "warm": 1}
res2 = risk.evaluar(d2)
print(f"2. Hot & Dry Day (34°C, 20% RH):")
print(f"   Risk Level: {res2['risk_level']} (Risk: {res2['risk']})")
print(f"   Reason:     {res2['risk_reason']}\n")

# Scenario 3: Extreme heat (Should trigger your physical rule)
d3 = {"temperature": 38.0, "humidity": 15.0, "mq2": 200, "mq135": 300, "mq7": 1000, "warm": 1}
res3 = risk.evaluar(d3)
print(f"3. Extreme Heat (38°C, 15% RH):")
print(f"   Risk Level: {res3['risk_level']} (Risk: {res3['risk']})")
print(f"   Reason:     {res3['risk_reason']}\n")

# Scenario 4: Gas alert (Smoke on MQ-2)
d4 = {"temperature": 22.0, "humidity": 70.0, "mq2": 1600, "mq135": 300, "mq7": 1000, "warm": 1}
res4 = risk.evaluar(d4)
print(f"4. Smoke Detected (MQ-2 = 900):")
print(f"   Risk Level: {res4['risk_level']} (Risk: {res4['risk']})")
print(f"   Reason:     {res4['risk_reason']}\n")