"""Rise-over-baseline gas detection (pure Python, no ML libraries).

Idea: a fire makes a FAST, LARGE rise. A sensor warming up after power-on decays
downward, and a room slowly filling with breath/humidity drifts upward slowly.
So instead of one fixed number, each sensor is compared with its own median over
the last window_min minutes.

A reading counts as "over" when BOTH are true:
    value > baseline * ratio          (relative rise)
    value - baseline > min_delta      (absolute rise, ignores noise on low baselines)
An alert needs `confirm` consecutive over-readings.

Over-readings are NOT added to the baseline (so a long fire cannot raise its own
baseline), but after freeze_max_min minutes of staying over, the new level is
accepted as the new normal.

While a device reports warm=0 (it just powered on), its history is cleared and
nothing is learned or judged.
"""
import statistics
from collections import deque

SENSORS = ("mq2", "mq135", "mq7")
NAMES = {"mq2": "Humo (MQ-2)", "mq135": "CO2/VOC (MQ-135)", "mq7": "CO (MQ-7)"}


class RiseDetector:
    def __init__(self):
        self.hist = {}    # device -> sensor -> deque[(time, value)]
        self.streak = {}  # device -> sensor -> consecutive over-readings
        self.since = {}   # device -> sensor -> time the current streak began

    def reset(self, dev):
        for store in (self.hist, self.streak, self.since):
            store.pop(dev, None)

    def update(self, dev, d, now, cfg):
        """Feed one reading. Returns (alerts, bases).

        alerts: list of (sensor, value, baseline) that are risen and confirmed
        bases:  {sensor: baseline} for sensors with enough history
        """
        r = cfg["rise"]
        alerts, bases = [], {}
        if not d.get("warm", 1):
            self.reset(dev)
            return alerts, bases

        window = r["window_min"] * 60
        hist = self.hist.setdefault(dev, {})
        streak = self.streak.setdefault(dev, {})
        since = self.since.setdefault(dev, {})

        for s in SENSORS:
            v = d.get(s)
            if v is None:
                continue
            h = hist.setdefault(s, deque())
            # While a rise is being held out of the baseline, keep the pre-rise history
            # (otherwise it ages out and the alert would vanish while the fire still burns).
            # Pruning resumes once the rise ends or is accepted as the new normal.
            t0 = since.get(s)
            if t0 is None or (now - t0) > r["freeze_max_min"] * 60:
                while h and h[0][0] < now - window:
                    h.popleft()

            base = None
            if len(h) >= r["min_samples"] and now - h[0][0] >= r["min_history_min"] * 60:
                base = statistics.median([x for _, x in h])
                bases[s] = round(base)

            over = (base is not None
                    and v > base * r["ratio"][s]
                    and v - base > r["min_delta"][s])

            if over:
                streak[s] = streak.get(s, 0) + 1
                if since.get(s) is None:
                    since[s] = now
                learn = (now - since[s]) > r["freeze_max_min"] * 60
            else:
                streak[s] = 0
                since[s] = None
                learn = True

            if learn:
                h.append((now, v))
            if over and streak[s] >= r["confirm"]:
                alerts.append((s, v, base))
        return alerts, bases
