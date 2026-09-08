"""Block 0 sub-unit A - mock SolarEdge monitoring API.

Serves the same URL paths and the same JSON shapes as monitoringapi.solaredge.com,
so Blocks 1-3 can be built and graded with no vendor account and no hardware. Swapping
to the real cloud is one ENV var (see docs/block0_contract.md).

Behaviour is frozen by docs/block0_contract.md. That document - not this file - is the
contract Gina codes against. If you change what an endpoint returns, change the contract
in the same commit.

Run:  python src/mock_server.py
"""

from __future__ import annotations

import math
import os
import random
import threading
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, jsonify, request

# --------------------------------------------------------------------------------------
# Site model. Numbers follow the SolarEdge Home Hub USE5700H we modelled the project on.
# --------------------------------------------------------------------------------------

PEAK_SOLAR_W = 5700.0          # inverter AC nameplate
SOLAR_PEAK_HOUR = 13.0         # bell curve centre - 1:00 PM
SOLAR_SIGMA_H = 2.5            # curve width in hours
SUNRISE_H = 6.5                # 06:30 - hard zero before this
SUNSET_H = 19.5                # 19:30 - hard zero after this

NOISE_PCT = 0.12               # +/-12% reading noise
CLOUD_CHANCE = 0.05            # 5% of readings are a cloud dip
CLOUD_MIN, CLOUD_MAX = 0.30, 0.60   # dip removes 30-60% of output

BATTERY_CAPACITY_WH = 9700.0   # SolarEdge Home Battery
BATTERY_MAX_W = 5000.0         # charge/discharge power limit
BATTERY_SOC_MIN, BATTERY_SOC_MAX = 10.0, 100.0

LIFETIME_BASE_WH = 12_450_000.0     # energy produced before today

SITE_ID = os.getenv("MOCK_SITE_ID", "demo_site_001")

# Set MOCK_DETERMINISTIC=1 to drop noise and cloud dips entirely. CI and the Block 1-3
# integration checks use this so a flaky random dip can never fail a test.
DETERMINISTIC = os.getenv("MOCK_DETERMINISTIC", "0") == "1"

app = Flask(__name__)
_lock = threading.Lock()
_started_at = time.time()
_request_count = 0


def current_time() -> datetime:
    """Wall clock, in one place so tests can monkeypatch it."""
    return datetime.now()


# --------------------------------------------------------------------------------------
# Physics
# --------------------------------------------------------------------------------------

def _hour_of_day(now: datetime) -> float:
    return now.hour + now.minute / 60.0 + now.second / 3600.0


def solar_power_w(now: datetime, rng: random.Random | None = None) -> float:
    """Gaussian bell centred on 1 PM, hard-zeroed outside the active window.

    Noise and cloud dips are applied only when a generator is supplied and
    DETERMINISTIC is off, so the underlying curve stays assertable.
    """
    h = _hour_of_day(now)
    if h < SUNRISE_H or h > SUNSET_H:
        return 0.0

    base = PEAK_SOLAR_W * math.exp(-((h - SOLAR_PEAK_HOUR) ** 2) / (2 * SOLAR_SIGMA_H ** 2))

    if rng is not None and not DETERMINISTIC:
        base *= 1.0 + rng.uniform(-NOISE_PCT, NOISE_PCT)
        if rng.random() < CLOUD_CHANCE:
            base *= 1.0 - rng.uniform(CLOUD_MIN, CLOUD_MAX)

    return max(0.0, round(base, 1))


def load_power_w(now: datetime, rng: random.Random | None = None) -> float:
    """Household consumption: a 450 W floor plus morning and evening bumps."""
    h = _hour_of_day(now)
    base = 450.0
    base += 900.0 * math.exp(-((h - 7.5) ** 2) / (2 * 1.2 ** 2))    # morning
    base += 1400.0 * math.exp(-((h - 19.0) ** 2) / (2 * 1.8 ** 2))  # evening

    if rng is not None and not DETERMINISTIC:
        base *= 1.0 + rng.uniform(-NOISE_PCT, NOISE_PCT)

    return max(0.0, round(base, 1))


class Battery:
    """SOC integrated over real elapsed time from the solar surplus/deficit."""

    def __init__(self, soc_pct: float = 55.0) -> None:
        self.soc_pct = soc_pct
        self.power_w = 0.0          # + charging, - discharging
        self._last_update: datetime | None = None

    def update(self, now: datetime, solar_w: float, load_w: float) -> None:
        surplus_w = solar_w - load_w

        if surplus_w >= 0:
            headroom = BATTERY_SOC_MAX - self.soc_pct
            self.power_w = 0.0 if headroom <= 0 else min(surplus_w, BATTERY_MAX_W)
        else:
            reserve = self.soc_pct - BATTERY_SOC_MIN
            self.power_w = 0.0 if reserve <= 0 else -min(-surplus_w, BATTERY_MAX_W)

        if self._last_update is not None:
            elapsed_h = (now - self._last_update).total_seconds() / 3600.0
            if elapsed_h > 0:
                delta_wh = self.power_w * elapsed_h
                self.soc_pct += delta_wh / BATTERY_CAPACITY_WH * 100.0
                self.soc_pct = max(BATTERY_SOC_MIN, min(BATTERY_SOC_MAX, self.soc_pct))

        self._last_update = now


battery = Battery()


def grid_power_w(solar_w: float, load_w: float, battery_w: float) -> float:
    """Positive = importing from the grid, negative = exporting to it."""
    return round(load_w + battery_w - solar_w, 1)


def _daily_production_wh(now: datetime) -> float:
    """Energy generated so far today, integrating the clean curve hour by hour."""
    total = 0.0
    h_now = _hour_of_day(now)
    hour = SUNRISE_H
    while hour < min(h_now, SUNSET_H):
        step = min(0.25, min(h_now, SUNSET_H) - hour)
        mid = now.replace(hour=int(hour + step / 2), minute=int(((hour + step / 2) % 1) * 60),
                          second=0, microsecond=0)
        total += solar_power_w(mid) * step
        hour += 0.25
    return round(total, 1)


# --------------------------------------------------------------------------------------
# Plumbing
# --------------------------------------------------------------------------------------

def _mock_tag() -> dict:
    return {"source": "mock_server", "site_id": SITE_ID}


def require_api_key(view):
    """Block 1 contract: missing or empty api_key is a 401. Any non-empty value passes."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        key = request.args.get("api_key", "")
        if not key.strip():
            return jsonify({
                "String": "Invalid token",
                "_mock": _mock_tag(),
            }), 401
        return view(*args, **kwargs)
    return wrapper


@app.before_request
def _count_request():
    global _request_count
    with _lock:
        _request_count += 1


def _snapshot(now: datetime) -> tuple[float, float, float, float, float]:
    rng = random.Random()
    solar = solar_power_w(now, rng)
    load = load_power_w(now, rng)
    with _lock:
        battery.update(now, solar, load)
        batt_w, soc = battery.power_w, battery.soc_pct
    grid = grid_power_w(solar, load, batt_w)
    return solar, load, batt_w, soc, grid


# --------------------------------------------------------------------------------------
# Endpoints - paths and JSON shapes mirror monitoringapi.solaredge.com
# --------------------------------------------------------------------------------------

@app.route("/site/<site_id>/currentPowerFlow")
@require_api_key
def current_power_flow(site_id: str):
    now = current_time()
    solar, load, batt_w, soc, grid = _snapshot(now)

    connections = []
    if solar > 0:
        connections.append({"from": "PV", "to": "Load"})
    if grid > 0:
        connections.append({"from": "GRID", "to": "Load"})
    elif grid < 0:
        connections.append({"from": "LOAD", "to": "Grid"})
    if batt_w > 0:
        connections.append({"from": "PV", "to": "Storage"})
    elif batt_w < 0:
        connections.append({"from": "Storage", "to": "Load"})

    return jsonify({
        "siteCurrentPowerFlow": {
            "updateRefreshRate": 3,
            "unit": "kW",
            "connections": connections,
            "GRID": {"status": "Active", "currentPower": round(abs(grid) / 1000.0, 3)},
            "LOAD": {"status": "Active", "currentPower": round(load / 1000.0, 3)},
            "PV": {"status": "Active" if solar > 0 else "Idle",
                   "currentPower": round(solar / 1000.0, 3)},
            "STORAGE": {"status": "Active", "currentPower": round(abs(batt_w) / 1000.0, 3),
                        "chargeLevel": round(soc, 1), "critical": False},
        },
        "_mock": _mock_tag(),
    })


@app.route("/site/<site_id>/overview")
@require_api_key
def overview(site_id: str):
    now = current_time()
    solar, _, _, _, _ = _snapshot(now)
    today_wh = _daily_production_wh(now)

    return jsonify({
        "overview": {
            "lastUpdateTime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "lifeTimeData": {"energy": round(LIFETIME_BASE_WH + today_wh, 1), "revenue": 0.0},
            "lastYearData": {"energy": 4_120_000.0},
            "lastMonthData": {"energy": 388_000.0},
            "lastDayData": {"energy": today_wh},
            "currentPower": {"power": solar},
            "measuredBy": "INVERTER",
        },
        "_mock": _mock_tag(),
    })


@app.route("/site/<site_id>/energy")
@require_api_key
def energy(site_id: str):
    now = current_time()
    time_unit = request.args.get("timeUnit", "DAY").upper()

    if time_unit == "HOUR":
        values = []
        for hour in range(24):
            slot = now.replace(hour=hour, minute=30, second=0, microsecond=0)
            produced = solar_power_w(slot) if slot <= now else None
            values.append({
                "date": slot.replace(minute=0).strftime("%Y-%m-%d %H:%M:%S"),
                "value": round(produced, 1) if produced is not None else None,
            })
    else:
        values = [{
            "date": now.strftime("%Y-%m-%d 00:00:00"),
            "value": _daily_production_wh(now),
        }]

    return jsonify({
        "energy": {
            "timeUnit": time_unit,
            "unit": "Wh",
            "measuredBy": "INVERTER",
            "values": values,
        },
        "_mock": _mock_tag(),
    })


@app.route("/site/<site_id>/powerDetails")
@require_api_key
def power_details(site_id: str):
    now = current_time()
    solar, load, _, _, _ = _snapshot(now)
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")

    return jsonify({
        "powerDetails": {
            "timeUnit": "QUARTER_OF_AN_HOUR",
            "unit": "W",
            "meters": [
                {"type": "Production", "values": [{"date": stamp, "value": solar}]},
                {"type": "Consumption", "values": [{"date": stamp, "value": load}]},
            ],
        },
        "_mock": _mock_tag(),
    })


@app.route("/equipment/<site_id>/list")
@require_api_key
def equipment_list(site_id: str):
    return jsonify({
        "reporters": {
            "count": 1,
            "list": [{
                "name": "Inverter 1",
                "manufacturer": "SolarEdge",
                "model": "USE5700H-US000BNU4",
                "serialNumber": "7E1B2C3D-4F",
            }],
        },
        "_mock": _mock_tag(),
    })


@app.route("/health")
def health():
    """Not a SolarEdge endpoint. Ours, for the Phase 8 soak. No api_key required."""
    now = current_time()
    with _lock:
        count = _request_count
    return jsonify({
        "status": "ok",
        "uptime_seconds": round(time.time() - _started_at, 1),
        "request_count": count,
        "server_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "utc_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "deterministic": DETERMINISTIC,
        "site_id": SITE_ID,
        "_mock": _mock_tag(),
    })


@app.errorhandler(404)
def not_found(_err):
    return jsonify({"String": "Not found", "_mock": _mock_tag()}), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.getenv("MOCK_PORT", "5000")), debug=False)
