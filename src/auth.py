from __future__ import annotations
import logging
import os
import time
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

RETRY = (60, 120, 240)
TIMEOUT_SECONDS = 10
DEFAULT_RATE_LIMIT = 280

_request_count = 0
_counter_date = None


def _today_utc():
    return datetime.now(timezone.utc).date()

def _roll_counter() -> None:
    global _request_count, _counter_date
    today = _today_utc()
    if _counter_date != today:
        _counter_date = today
        _request_count = 0

def request_count():
    _roll_counter()
    return _request_count

def reset_counter() -> None:
    global _request_count, _counter_date
    _request_count = 0
    _counter_date = _today_utc()

def _rate_limit():
    try:
        return int(os.getenv("RATE_LIMIT_MAX", ""))
    except (TypeError, ValueError):
        return DEFAULT_RATE_LIMIT

def get(path: str, params: dict | None = None) -> tuple[dict | None, bool]:
    """GET {API_BASE_URL}{path} with api_key added. Returns (JSON, ok)"""
    global _request_count
    base = os.getenv("API_BASE_URL", "").rstrip("/")
    url = f"{base}{path}"
    merged = dict(params or {})
    merged["api_key"] = os.getenv("API_KEY", "")

    for sleep_for in (*RETRY, None):
        _roll_counter()
        limit = _rate_limit()

        if _request_count >= limit:
            log.warning("rate limit has been reached (%d/%d) - refusing GET %s",
                        _request_count, limit, path)
            return (None, False)

        _request_count += 1

        try:
            response = requests.get(url, params=merged, timeout=TIMEOUT_SECONDS)
        except Exception as exc:
            log.error("GET %s failed: %s: %s", path, type(exc).__name__, exc)
            return (None, False)

        if response.status_code == 429:
            if sleep_for is None:
                log.error("GET %s still 429 - stopping", path)
                return (None, False)
            log.warning("GET %s returned 429 - sleeping %ds", path, sleep_for)
            time.sleep(sleep_for)
            continue

        if response.status_code == 401:
            log.error("bad key - GET %s returned 401", path)
            return (None, False)

        if not response.ok:
            log.error("GET %s returned HTTP %d", path, response.status_code)
            return (None, False)

        try:
            return (response.json(), True)
        except ValueError as exc:
            log.error("GET %s returned a non-JSON body: %s", path, exc)
            return (None, False)

    return (None, False)