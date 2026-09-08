"""Block 0 verification - the mock SolarEdge server.

Every assertion here traces to a bullet in SKILL.md section 5 Block 0 or to an acceptance
criterion in VPP_C2C_BUILD_MANUAL.md Phase 1. The behaviour they pin down is written up in
docs/block0_contract.md, which is the document Gina codes Blocks 1-3 against.

Randomness is switched off (mock_server.DETERMINISTIC) wherever a test asserts a value, so
a cloud dip can never fail CI. The two tests that DO exercise noise assert on bounds.
"""
from datetime import datetime

import pytest

import mock_server


KEY = "?api_key=mock_key"
SITE = "demo_site_001"

ENDPOINTS = [
    f"/site/{SITE}/currentPowerFlow",
    f"/site/{SITE}/overview",
    f"/site/{SITE}/energy",
    f"/site/{SITE}/powerDetails",
    f"/equipment/{SITE}/list",
]


@pytest.fixture
def client():
    mock_server.app.config["TESTING"] = True
    with mock_server.app.test_client() as c:
        yield c


@pytest.fixture
def frozen(monkeypatch):
    """Freeze the clock and disable noise. Returns a setter."""
    monkeypatch.setattr(mock_server, "DETERMINISTIC", True)

    def _set(hour, minute=0):
        stamp = datetime(2026, 9, 8, hour, minute, 0)
        monkeypatch.setattr(mock_server, "current_time", lambda: stamp)
        return stamp
    return _set


@pytest.fixture(autouse=True)
def fresh_battery(monkeypatch):
    monkeypatch.setattr(mock_server, "battery", mock_server.Battery())


# ---------------------------------------------------------------- auth (Block 1 contract)

def test_missing_api_key_is_401(client):
    assert client.get(f"/site/{SITE}/currentPowerFlow").status_code == 401


def test_empty_api_key_is_401(client):
    assert client.get(f"/site/{SITE}/currentPowerFlow?api_key=").status_code == 401


def test_whitespace_api_key_is_401(client):
    assert client.get(f"/site/{SITE}/currentPowerFlow?api_key=%20%20").status_code == 401


def test_any_non_empty_key_is_accepted(client):
    assert client.get(f"/site/{SITE}/currentPowerFlow?api_key=literally_anything").status_code == 200


@pytest.mark.parametrize("path", ENDPOINTS)
def test_every_endpoint_guards_the_key(client, path):
    assert client.get(path).status_code == 401


# ---------------------------------------------------------------------------- endpoints

@pytest.mark.parametrize("path", ENDPOINTS)
def test_every_endpoint_returns_200_with_a_key(client, path):
    assert client.get(path + KEY).status_code == 200


def test_current_power_flow_shape(client):
    body = client.get(f"/site/{SITE}/currentPowerFlow" + KEY).get_json()
    flow = body["siteCurrentPowerFlow"]
    assert flow["unit"] == "kW"
    for section in ("GRID", "LOAD", "PV", "STORAGE"):
        assert "currentPower" in flow[section]
    assert "chargeLevel" in flow["STORAGE"]
    assert isinstance(flow["connections"], list)


def test_overview_shape(client):
    ov = client.get(f"/site/{SITE}/overview" + KEY).get_json()["overview"]
    assert set(("lifeTimeData", "lastDayData", "currentPower", "lastUpdateTime")) <= set(ov)
    assert ov["lifeTimeData"]["energy"] >= ov["lastDayData"]["energy"]


def test_energy_shape_and_unit(client):
    en = client.get(f"/site/{SITE}/energy" + KEY).get_json()["energy"]
    assert en["unit"] == "Wh"
    assert en["timeUnit"] == "DAY"
    assert len(en["values"]) == 1


def test_energy_hourly_returns_24_slots(client):
    en = client.get(f"/site/{SITE}/energy{KEY}&timeUnit=HOUR").get_json()["energy"]
    assert en["timeUnit"] == "HOUR"
    assert len(en["values"]) == 24


def test_power_details_has_production_and_consumption(client):
    pd = client.get(f"/site/{SITE}/powerDetails" + KEY).get_json()["powerDetails"]
    assert pd["unit"] == "W"
    assert {m["type"] for m in pd["meters"]} == {"Production", "Consumption"}


def test_equipment_list_reports_the_inverter(client):
    rep = client.get(f"/equipment/{SITE}/list" + KEY).get_json()["reporters"]
    assert rep["count"] == 1
    assert rep["list"][0]["manufacturer"] == "SolarEdge"


# -------------------------------------------------------------------------- _mock tagging

@pytest.mark.parametrize("path", ENDPOINTS)
def test_mock_tag_on_every_success(client, path):
    assert client.get(path + KEY).get_json()["_mock"]["source"] == "mock_server"


def test_mock_tag_on_the_401(client):
    assert client.get(ENDPOINTS[0]).get_json()["_mock"]["source"] == "mock_server"


def test_mock_tag_on_a_404(client):
    resp = client.get("/site/x/nope" + KEY)
    assert resp.status_code == 404
    assert resp.get_json()["_mock"]["source"] == "mock_server"


# -------------------------------------------------------------- solar curve (Phase 1 criteria)

def test_zero_watts_at_2200():
    """Manual Phase 1 acceptance: 0 W at 22:00."""
    assert mock_server.solar_power_w(datetime(2026, 9, 8, 22, 0)) == 0.0


def test_above_3000_watts_at_1300():
    """Manual Phase 1 acceptance: >3000 W at 13:00."""
    assert mock_server.solar_power_w(datetime(2026, 9, 8, 13, 0)) > 3000.0


def test_zero_before_sunrise():
    assert mock_server.solar_power_w(datetime(2026, 9, 8, 5, 0)) == 0.0


def test_zero_at_0629_nonzero_at_0700():
    assert mock_server.solar_power_w(datetime(2026, 9, 8, 6, 29)) == 0.0
    assert mock_server.solar_power_w(datetime(2026, 9, 8, 7, 0)) > 0.0


def test_zero_after_sunset_nonzero_before():
    assert mock_server.solar_power_w(datetime(2026, 9, 8, 19, 0)) > 0.0
    assert mock_server.solar_power_w(datetime(2026, 9, 8, 20, 0)) == 0.0


def test_peak_is_at_1300():
    hours = range(7, 20)
    powers = {h: mock_server.solar_power_w(datetime(2026, 9, 8, h, 0)) for h in hours}
    assert max(powers, key=powers.get) == 13


def test_curve_rises_into_the_peak_and_falls_after():
    at = lambda h: mock_server.solar_power_w(datetime(2026, 9, 8, h, 0))
    assert at(8) < at(10) < at(12) < at(13)
    assert at(13) > at(15) > at(17) > at(19)


def test_never_exceeds_inverter_nameplate():
    for h in range(24):
        for m in (0, 30):
            assert mock_server.solar_power_w(datetime(2026, 9, 8, h, m)) <= mock_server.PEAK_SOLAR_W


# ------------------------------------------------------------------------ noise and clouds

def test_noise_stays_inside_the_declared_band(monkeypatch):
    """+/-12% noise, and a cloud dip removes at most 60% more."""
    monkeypatch.setattr(mock_server, "DETERMINISTIC", False)
    now = datetime(2026, 9, 8, 13, 0)
    clean = mock_server.solar_power_w(now)
    import random
    samples = [mock_server.solar_power_w(now, random.Random(s)) for s in range(400)]
    assert max(samples) <= clean * (1 + mock_server.NOISE_PCT) + 0.1
    assert min(samples) >= clean * (1 - mock_server.NOISE_PCT) * (1 - mock_server.CLOUD_MAX) - 0.1


def test_a_cloud_dip_actually_occurs_sometimes(monkeypatch):
    monkeypatch.setattr(mock_server, "DETERMINISTIC", False)
    now = datetime(2026, 9, 8, 13, 0)
    clean = mock_server.solar_power_w(now)
    import random
    samples = [mock_server.solar_power_w(now, random.Random(s)) for s in range(400)]
    dips = [s for s in samples if s < clean * (1 - mock_server.NOISE_PCT)]
    assert dips, "no cloud dip in 400 readings - CLOUD_CHANCE is not firing"


def test_deterministic_mode_removes_all_variation(monkeypatch):
    monkeypatch.setattr(mock_server, "DETERMINISTIC", True)
    now = datetime(2026, 9, 8, 13, 0)
    import random
    values = {mock_server.solar_power_w(now, random.Random(s)) for s in range(50)}
    assert len(values) == 1


# ------------------------------------------------------------------------------- battery

def test_soc_rises_on_surplus():
    b = mock_server.Battery(soc_pct=50.0)
    b.update(datetime(2026, 9, 8, 12, 0), solar_w=4000, load_w=600)
    b.update(datetime(2026, 9, 8, 13, 0), solar_w=4000, load_w=600)
    assert b.soc_pct > 50.0


def test_soc_falls_on_deficit():
    b = mock_server.Battery(soc_pct=50.0)
    b.update(datetime(2026, 9, 8, 20, 0), solar_w=0, load_w=1500)
    b.update(datetime(2026, 9, 8, 21, 0), solar_w=0, load_w=1500)
    assert b.soc_pct < 50.0


def test_soc_is_clamped_to_its_limits():
    b = mock_server.Battery(soc_pct=99.0)
    b.update(datetime(2026, 9, 8, 10, 0), solar_w=5000, load_w=0)
    b.update(datetime(2026, 9, 8, 18, 0), solar_w=5000, load_w=0)
    assert b.soc_pct <= mock_server.BATTERY_SOC_MAX

    d = mock_server.Battery(soc_pct=11.0)
    d.update(datetime(2026, 9, 8, 20, 0), solar_w=0, load_w=3000)
    d.update(datetime(2026, 9, 9, 4, 0), solar_w=0, load_w=3000)
    assert d.soc_pct >= mock_server.BATTERY_SOC_MIN


def test_charge_power_is_capped():
    b = mock_server.Battery(soc_pct=50.0)
    b.update(datetime(2026, 9, 8, 13, 0), solar_w=99000, load_w=0)
    assert b.power_w <= mock_server.BATTERY_MAX_W


def test_full_battery_stops_charging():
    b = mock_server.Battery(soc_pct=mock_server.BATTERY_SOC_MAX)
    b.update(datetime(2026, 9, 8, 13, 0), solar_w=5000, load_w=100)
    assert b.power_w == 0.0


def test_sign_convention_charging_positive_discharging_negative():
    b = mock_server.Battery(soc_pct=50.0)
    b.update(datetime(2026, 9, 8, 13, 0), solar_w=4000, load_w=500)
    assert b.power_w > 0
    b2 = mock_server.Battery(soc_pct=50.0)
    b2.update(datetime(2026, 9, 8, 21, 0), solar_w=0, load_w=1200)
    assert b2.power_w < 0


# ---------------------------------------------------------------------------- grid signs

def test_grid_imports_when_load_exceeds_solar():
    assert mock_server.grid_power_w(solar_w=0, load_w=1200, battery_w=0) > 0


def test_grid_exports_when_solar_exceeds_load_and_battery():
    assert mock_server.grid_power_w(solar_w=5000, load_w=500, battery_w=0) < 0


def test_grid_is_load_plus_battery_minus_solar():
    assert mock_server.grid_power_w(solar_w=3000, load_w=1000, battery_w=500) == pytest.approx(-1500)


# -------------------------------------------------------------------------------- health

def test_health_needs_no_api_key(client):
    assert client.get("/health").status_code == 200


def test_health_reports_uptime_and_request_count(client):
    client.get("/health")
    body = client.get("/health").get_json()
    assert body["status"] == "ok"
    assert body["uptime_seconds"] >= 0
    assert body["request_count"] >= 2


# -------------------------------------------------------- units, for the Block 3 field map

def test_power_flow_values_are_kilowatts(client, frozen):
    frozen(13, 0)
    flow = client.get(f"/site/{SITE}/currentPowerFlow" + KEY).get_json()["siteCurrentPowerFlow"]
    clean_kw = mock_server.solar_power_w(datetime(2026, 9, 8, 13, 0)) / 1000.0
    assert flow["PV"]["currentPower"] == pytest.approx(clean_kw, abs=0.01)
    assert flow["PV"]["currentPower"] < 10  # kW, not W


def test_overview_current_power_is_watts(client, frozen):
    frozen(13, 0)
    ov = client.get(f"/site/{SITE}/overview" + KEY).get_json()["overview"]
    assert ov["currentPower"]["power"] > 3000  # W, matching the real SolarEdge overview


def test_battery_charge_level_is_a_percentage(client):
    flow = client.get(f"/site/{SITE}/currentPowerFlow" + KEY).get_json()["siteCurrentPowerFlow"]
    assert 0 <= flow["STORAGE"]["chargeLevel"] <= 100
