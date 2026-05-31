#!/usr/bin/env python3
"""
Bench 315 — daily Garmin pull.
Runs once a day (GitHub Action). Logs into Garmin Connect, reads today's
Training Readiness, sleep, and resting HR, computes a readiness color, and
writes data/today.json which the phone web app reads.

Garmin credentials come from environment variables (GitHub Secrets):
  GARMIN_EMAIL, GARMIN_PASSWORD
"""
import os, json, datetime, sys

EMAIL = os.environ.get("GARMIN_EMAIL")
PASSWORD = os.environ.get("GARMIN_PASSWORD")

# your recovery baselines (edit if your normals change)
HRV_BASELINE = 60      # ms
RHR_BASELINE = 52      # bpm
SLEEP_TARGET = 8.0     # hours

OUT = os.path.join(os.path.dirname(__file__), "data", "today.json")


def color_from(tr, sleep_hrs, rhr):
    """Prefer Garmin Training Readiness; else compute from sleep + resting HR."""
    if tr:
        return "green" if tr >= 80 else "yellow" if tr >= 60 else "orange" if tr >= 40 else "red"
    # fallback score /100: sleep 50, resting HR 50
    s = min(50, (sleep_hrs or 0) / SLEEP_TARGET * 50)
    r = min(50, RHR_BASELINE / rhr * 50) if rhr else 25
    score = round(s + r)
    return "green" if score >= 80 else "yellow" if score >= 60 else "orange" if score >= 40 else "red"


def main():
    today = datetime.date.today().isoformat()
    data = {"date": today, "tr": None, "sleepHrs": None, "sleepScore": None,
            "restingHR": None, "color": "yellow",
            "fetchedAt": datetime.datetime.utcnow().isoformat() + "Z"}

    if not EMAIL or not PASSWORD:
        print("ERROR: GARMIN_EMAIL / GARMIN_PASSWORD not set", file=sys.stderr)
        # still write a neutral file so the app keeps working
        _write(data); return

    try:
        from garminconnect import Garmin
        g = Garmin(EMAIL, PASSWORD)
        g.login()

        # Training Readiness (Garmin-proprietary 0-100)
        try:
            tr = g.get_training_readiness(today)
            if isinstance(tr, list) and tr:
                data["tr"] = tr[0].get("score")
            elif isinstance(tr, dict):
                data["tr"] = tr.get("score")
        except Exception as e:
            print("training_readiness unavailable:", e, file=sys.stderr)

        # Sleep
        try:
            sleep = g.get_sleep_data(today)
            dto = (sleep or {}).get("dailySleepDTO", {}) or {}
            secs = dto.get("sleepTimeSeconds")
            if secs:
                data["sleepHrs"] = round(secs / 3600, 1)
            score = (dto.get("sleepScores") or {}).get("overall", {}).get("value")
            if score:
                data["sleepScore"] = score
        except Exception as e:
            print("sleep unavailable:", e, file=sys.stderr)

        # Resting HR
        try:
            rhr = g.get_rhr_day(today)
            metrics = (rhr or {}).get("allMetrics", {}).get("metricsMap", {})
            vals = metrics.get("WELLNESS_RESTING_HEART_RATE", [])
            if vals:
                data["restingHR"] = vals[0].get("value")
        except Exception as e:
            print("resting HR unavailable:", e, file=sys.stderr)

    except Exception as e:
        print("Garmin login/pull failed:", e, file=sys.stderr)

    data["color"] = color_from(data["tr"], data["sleepHrs"], data["restingHR"])
    _write(data)
    print("Wrote", OUT, json.dumps(data))


def _write(data):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
