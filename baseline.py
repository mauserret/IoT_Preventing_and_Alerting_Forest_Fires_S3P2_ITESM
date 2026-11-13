"""Clean-air baseline for the MQ sensors and suggested gas thresholds.

Reads the SQLite buffer (does not touch MQTT or the running collector service).
Only uses readings with warm=1.

Usage:
    python3 baseline.py              # last 15 minutes
    python3 baseline.py --minutes 30
"""
import argparse, json, sqlite3, statistics
from datetime import datetime, timezone, timedelta
import config

SENSORS = ("mq2", "mq135", "mq7")
ADC_USABLE_MAX = 3300      # readings saturate near here after the divider
MIN_SAMPLES = 60           # about 5 minutes at one reading every 5 s

ap = argparse.ArgumentParser()
ap.add_argument("--minutes", type=int, default=15)
args = ap.parse_args()

cutoff = (datetime.now(timezone.utc) - timedelta(minutes=args.minutes)).isoformat(timespec="milliseconds")
db = sqlite3.connect(config.get()["db_path"], timeout=30)
rows = db.execute("SELECT payload FROM readings WHERE ts >= ? ORDER BY id", (cutoff,)).fetchall()

vals = {s: [] for s in SENSORS}
for (p,) in rows:
    d = json.loads(p)
    if not d.get("warm", 1):
        continue
    for s in SENSORS:
        if d.get(s) is not None:
            vals[s].append(d[s])

print(f"Window: last {args.minutes} min, {len(vals['mq2'])} warm readings\n")
if len(vals["mq2"]) < MIN_SAMPLES:
    print(f"Not enough data (need at least {MIN_SAMPLES} warm readings). "
          "Wait longer or check that 'warm' is 1 in recent readings.")
    raise SystemExit(1)

suggest = {}
print(f"{'sensor':7} {'min':>6} {'mean':>8} {'std':>7} {'p99':>6} {'max':>6} {'drift%':>7} {'suggested':>10}")
for s in SENSORS:
    v = sorted(vals[s])
    mean = statistics.fmean(v)
    std = statistics.pstdev(v)
    p99 = v[int(0.99 * (len(v) - 1))]
    raw = vals[s]
    third = max(1, len(raw) // 3)
    first, last = statistics.fmean(raw[:third]), statistics.fmean(raw[-third:])
    drift = 100 * (last - first) / first if first else 0.0
    # well above anything seen in clean air: 50% over the max, or mean + 10 std
    sug = round(max(v[-1] * 1.5, mean + 10 * std))
    suggest[s] = sug
    print(f"{s:7} {v[0]:6} {mean:8.1f} {std:7.1f} {p99:6} {v[-1]:6} {drift:7.1f} {sug:10}")

print()
for s in SENSORS:
    if suggest[s] >= ADC_USABLE_MAX:
        print(f"WARNING {s}: suggested {suggest[s]} is near the ADC limit (~{ADC_USABLE_MAX}). "
              "Baseline is too high for a useful alert, check wiring/divider and burn-in.")
drifting = [s for s in SENSORS if abs(100 * (statistics.fmean(vals[s][-max(1, len(vals[s]) // 3):])
                                             - statistics.fmean(vals[s][:max(1, len(vals[s]) // 3)]))
                                       / max(1e-9, statistics.fmean(vals[s][:max(1, len(vals[s]) // 3)]))) > 10]
if drifting:
    print("NOTE: still drifting more than 10% inside the window:", ", ".join(drifting),
          "(sensor still burning in or warming up; rerun later, thresholds may change).")

print('\nPaste into config.json (replace the "gas_thresholds" block):')
print(json.dumps({"gas_thresholds": suggest}, indent=2))
