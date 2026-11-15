"""Offline tests for gasrise.py (no Pi, no sensors). Run: python3 test_gasrise.py"""
import random
import config
from gasrise import RiseDetector

CFG = config.DEFAULTS
random.seed(1)
STEP = 60          # one reading per minute, like the ESP32 default


def run(det, series, t0=0, dev="esp32-01"):
    """series: list of (mq2, mq135, mq7, warm). Returns the list of alert flags per reading."""
    flags = []
    for i, (a, b, c, w) in enumerate(series):
        al, _ = det.update(dev, {"mq2": a, "mq135": b, "mq7": c, "warm": w}, t0 + i * STEP, CFG)
        flags.append(bool(al))
    return flags


def noisy(n, m2, m135, m7, warm=1):
    return [(m2 + random.gauss(0, 6), m135 + random.gauss(0, 12), m7 + random.gauss(0, 40), warm)
            for _ in range(n)]


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (" - " + detail if detail else ""))
    return ok


results = []

# 1. steady air: no alerts
det = RiseDetector()
f = run(det, noisy(180, 260, 350, 1490))
results.append(check("steady air gives no alerts", not any(f)))

# 2. sudden smoke after a steady hour: alert within 2 readings, and it persists
det = RiseDetector()
pre = noisy(90, 260, 350, 1490)
fire = noisy(15, 900, 700, 2600)
f = run(det, pre + fire)
first = next((i for i, x in enumerate(f) if x), None)
results.append(check("sudden smoke alerts fast", first is not None and first - 90 <= 1,
                     f"first alert {None if first is None else first - 90} reading(s) after onset"))
results.append(check("alert persists while smoke lasts", all(f[90 + 1:90 + 15])))

# 3. a single noisy spike does not alert (confirm = 2)
det = RiseDetector()
series = noisy(90, 260, 350, 1490) + [(900, 700, 2600, 1)] + noisy(10, 260, 350, 1490)
f = run(det, series)
results.append(check("single spike does not alert", not any(f)))

# 4. slow drift (night -> day) never alerts: 175 -> 375 over 6 h
det = RiseDetector()
n = 360
series = [(175 + 200 * i / n + random.gauss(0, 5), 260 + 250 * i / n + random.gauss(0, 10),
           1250 + 700 * i / n + random.gauss(0, 30), 1) for i in range(n)]
f = run(det, series)
results.append(check("slow 6 h drift gives no alerts", not any(f)))

# 5. power-up transient after a restart (warm=0 for 20 min, then decaying from high values)
det = RiseDetector()
pre = noisy(90, 260, 350, 1490)
cold = [(600, 700, 2100, 0)] * 20
import math
decay = [(260 + 340 * math.exp(-i / 18) + random.gauss(0, 5),
          350 + 350 * math.exp(-i / 18) + random.gauss(0, 10),
          1490 + 600 * math.exp(-i / 18) + random.gauss(0, 30), 1) for i in range(60)]
f = run(det, pre + cold + decay)
results.append(check("power-up transient gives no alerts", not any(f[90:])))

# 6. long fire: how long does the alert last before the new level is accepted?
det = RiseDetector()
f = run(det, noisy(90, 260, 350, 1490) + noisy(240, 900, 700, 2600))
last = max(i for i, x in enumerate(f) if x) - 90
results.append(check("long fire alert lasts at least 60 min", last >= 60,
                     f"alerting for about {last} min before accepting the new level"))

# 7. after a cold start there is a quiet period (needs history)
det = RiseDetector()
f = run(det, noisy(10, 260, 350, 1490) + noisy(5, 900, 700, 2600))
results.append(check("no rise alerts before enough history (absolute net covers this)", not any(f)))

print("\n%d/%d passed" % (sum(results), len(results)))
raise SystemExit(0 if all(results) else 1)
