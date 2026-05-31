#!/usr/bin/env python3
"""
Bench 315 — daily Garmin pull (token-based, with retries).

Logs into Garmin ONCE using email/password, then caches an OAuth token in
~/.garminconnect. Future runs reuse that token (no password login), which avoids
Garmin's rate-limiting (HTTP 429) on cloud IPs. The GitHub Action caches the token
folder between runs.

Env (GitHub Secrets):  GARMIN_EMAIL, GARMIN_PASSWORD
Optional env:          GARMINTOKENS  (token dir; defaults to ~/.garminconnect)
"""
import os, json, time, datetime, sys

EMAIL = os.environ.get("GARMIN_EMAIL")
PASSWORD = os.environ.get("GARMIN_PASSWORD")
TOKENSTORE = os.environ.get("GARMINTOKENS", os.path.expanduser("~/.garminconnect"))

# recovery baselines (used only for the fallback score if Training Readiness is missing)
RHR_BASELINE = 52
SLEEP_TARGET = 8.0

OUT = os.path.join(os.path.dirname(__file__), "data", "today.json")


def color_from(tr, sleep_hrs, rhr):
    if tr is not None:
        return "green" if tr >= 80 else "yellow" if tr >= 60 else "orange" if tr >= 40 else "red"
    s = min(50, (sleep_hrs or 0) / SLEEP_TARGET * 50)
    r = min(50, RHR_BASELINE / rhr * 50) if rhr else 25
    score = round(s + r)
    return "green" if score >= 80 else "yellow" if score >= 60 else "orange" if score >= 40 else "red"


def seed_token_from_secret():
    """If a base64 token secret is provided, unpack it into the token store."""
    b64 = os.environ.get("GARMIN_TOKEN_B64")
    if not b64:
        return
    import base64, io, tarfile
    try:
        os.makedirs(TOKENSTORE, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(base64.b64decode(b64)), mode="r:gz") as t:
            t.extractall(TOKENSTORE)
        print("Seeded token store from secret.")
    except Exception as e:
        print("Could not unpack GARMIN_TOKEN_B64:", e, file=sys.stderr)


def connect():
    """Return a logged-in Garmin client, reusing a cached token when possible."""
    from garminconnect import Garmin

    seed_token_from_secret()

    # 1) try cached token (no password login -> no rate limit)
    if os.path.isdir(TOKENSTORE) and os.listdir(TOKENSTORE):
        try:
            g = Garmin()
            g.login(TOKENSTORE)
            print("Logged in with cached token.")
            return g
        except Exception as e:
            print("Cached token unusable, will do a fresh login:", e, file=sys.stderr)

    # 2) fresh password login, with retries to ride out temporary 429 throttling
    last = None
    for attempt in range(1, 6):
        try:
            g = Garmin(EMAIL, PASSWORD)
            g.login()
            try:
                g.garth.dump(TOKENSTORE)   # save token so tomorrow needs no password login
                print("Saved token to", TOKENSTORE)
            except Exception as e:
                print("Could not save token:", e, file=sys.stderr)
            print(f"Fresh login OK on attempt {attempt}.")
            return g
        except Exception as e:
            last = e
            print(f"Login attempt {attempt} failed: {e}", file=sys.stderr)
            time.sleep(30)
    print("All login attempts failed:", last, file=sys.stderr)
    return None


def main():
    today = datetime.date.today().isoformat()
    data = {"date": today, "tr": None, "sleepHrs": None, "sleepScore": None,
            "restingHR": None, "color": "yellow",
            "fetchedAt": datetime.datetime.utcnow().isoformat() + "Z"}

    if not EMAIL or not PASSWORD:
        print("ERROR: GARMIN_EMAIL / GARMIN_PASSWORD not set", file=sys.stderr)
        _write(data); return

    g = connect()
    if g is not None:
        try:
            tr = g.get_training_readiness(today)
            if isinstance(tr, list) and tr:
                data["tr"] = tr[0].get("score")
            elif isinstance(tr, dict):
                data["tr"] = tr.get("score")
        except Exception as e:
            print("training_readiness unavailable:", e, file=sys.stderr)
        try:
            sleep = g.get_sleep_data(today)
            dto = (sleep or {}).get("dailySleepDTO", {}) or {}
            if dto.get("sleepTimeSeconds"):
                data["sleepHrs"] = round(dto["sleepTimeSeconds"] / 3600, 1)
            score = (dto.get("sleepScores") or {}).get("overall", {}).get("value")
            if score:
                data["sleepScore"] = score
        except Exception as e:
            print("sleep unavailable:", e, file=sys.stderr)
        try:
            rhr = g.get_rhr_day(today)
            vals = (rhr or {}).get("allMetrics", {}).get("metricsMap", {}).get("WELLNESS_RESTING_HEART_RATE", [])
            if vals:
                data["restingHR"] = vals[0].get("value")
        except Exception as e:
            print("resting HR unavailable:", e, file=sys.stderr)

    data["color"] = color_from(data["tr"], data["sleepHrs"], data["restingHR"])
    _write(data)
    print("Wrote", OUT, json.dumps(data))


def _write(data):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2)


if __name__ == "__main__":
    main()
