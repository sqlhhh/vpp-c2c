from __future__ import annotations
import json
import logging
import os
from datetime import datetime, time as dtime, timezone
from dotenv import load_dotenv
import auth

load_dotenv()
log = logging.getLogger(__name__)

POWER_FLOW = "currentPowerFlow"
OVERVIEW = "overview"
ENERGY = "energy"
DEFAULT_RATE_LIMIT = 280

_cache = {}

def reset_cache():
    _cache.clear()

def _endpoints():
    site = os.getenv("SITE_ID", "demo_site_001")
    return {
        POWER_FLOW: (f"/site/{site}/currentPowerFlow", None),
        OVERVIEW: (f"/site/{site}/overview", None),
        ENERGY: (f"/site/{site}/energy", {"timeUnit": "HOUR"}),
    }

def _utc_now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _hhmm(raw, fallback: dtime):
    try:
        return dtime.fromisoformat(raw.strip())
    except (AttributeError, ValueError):
        return fallback

def _window():
    return (
        _hhmm(os.getenv("DAYLIGHT_START"), dtime(6, 30)),
        _hhmm(os.getenv("DAYLIGHT_END"), dtime(19, 30)),
    )

def rate_limit():
    try:
        return int(os.getenv("RATE_LIMIT_MAX", ""))
    except (TypeError, ValueError):
        return DEFAULT_RATE_LIMIT

def is_daylight(now: datetime | None = None):
    start, end = _window()
    return start <= (now or datetime.now()).time() <= end

def interval_seconds():
    raw = (os.getenv("POLL_INTERVAL_SEC") or "").strip()
    if raw:
        try:
            return int(raw), True
        except ValueError:
            log.warning("POLL_INTERVAL_SEC=%r is not a number - ignoring", raw)
    try:
        return int((os.getenv("POLL_INTERVAL_MIN") or "5").strip()) * 60, False
    except ValueError:
        return 300, False


def daily_request_estimate():
    seconds, dev = interval_seconds()
    if dev or seconds <= 0:
        return 0

    start, end = _window()
    day = datetime.min.date()
    window = (datetime.combine(day, end) - datetime.combine(day, start)).total_seconds()
    return int(window // seconds) * len(_endpoints()) if window > 0 else 0


def _entry(name, path, params):
    data, ok = auth.get(path, params)

    if ok:
        return {"data": data, "fetched_at": _utc_now_iso(), "stale": False}

    cached = _cache.get(name)
    if cached is None:
        log.error("%s failed and nothing cached - skipping this cycle", name)
        return None

    log.warning("%s failed - re-serving cache from %s", name, cached["fetched_at"])
    return {**cached, "stale": True}


def poll_once():
    """One cycle- 3 raw outputs & stale flag
    Returns None only on a cold start with nothing cached"""
    endpoints = _endpoints()

    for name, (path, params) in endpoints.items():
        entry = _entry(name, path, params)
        if entry is None:
            return None
        _cache[name] = entry

    cycle = {name: _cache[name] for name in endpoints}
    cycle["stale"] = any(cycle[name]["stale"] for name in endpoints)
    return cycle


def _tick():
    if not interval_seconds()[1] and not is_daylight():
        log.info("outside the daylight window - no poll")
        return

    cycle = poll_once()
    if cycle is None:
        return

    for name in (POWER_FLOW, OVERVIEW, ENERGY):
        print(f"--- {name} (stale={cycle[name]['stale']}) ---")
        print(json.dumps(cycle[name]["data"], indent=2)[:600])
    print(f"=== cycle stale={cycle['stale']} ===\n")


def main():
    from apscheduler.schedulers.blocking import BlockingScheduler
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    seconds, dev = interval_seconds()
    log.info(
        "polling every %ds%s",seconds," (dev override, daylight ignored)" if dev else "",)

    estimate, cap = daily_request_estimate(), rate_limit()
    if estimate > cap:
        log.warning(
            "budget: ~%d requests/day at this cadence vs RATE_LIMIT_MAX=%d - "
            "auth.get will start refusing partway through the day",
            estimate,
            cap,)

    scheduler = BlockingScheduler()
    scheduler.add_job(_tick, "interval", seconds=seconds, next_run_time=datetime.now())
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("stopped")


if __name__ == "__main__":
    main()