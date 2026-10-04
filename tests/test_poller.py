from datetime import datetime, time as dtime
import pytest
import auth
import poller

POWER_FLOW_JSON = {
    "siteCurrentPowerFlow": {
        "unit": "kW",
        "connections": [{"from": "PV", "to": "Load"}],
        "PV": {"status": "Active", "currentPower": 4.191},
    },
    "_mock": {"source": "mock_server"},
}

OVERVIEW_JSON = {
    "overview": {
        "lastUpdateTime": "2026-09-08 14:56:17",
        "lastDayData": {"energy": 27697.4},
        "currentPower": {"power": 4278.6},
    }
}

ENERGY_JSON = {"energy": {"timeUnit": "HOUR", "unit": "Wh", "values": []}}

BY_PATH = {
    "currentPowerFlow": POWER_FLOW_JSON,
    "overview": OVERVIEW_JSON,
    "energy": ENERGY_JSON,
}

def _payload_for(path):
    return BY_PATH[path.rsplit("/", 1)[-1]]

@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.setenv("SITE_ID", "demo_site_001")
    monkeypatch.setenv("POLL_INTERVAL_MIN", "5")
    monkeypatch.setenv("POLL_INTERVAL_SEC", "")
    monkeypatch.setenv("DAYLIGHT_START", "06:30")
    monkeypatch.setenv("DAYLIGHT_END", "19:30")
    monkeypatch.setenv("RATE_LIMIT_MAX", "280")
    poller.reset_cache()
    yield
    poller.reset_cache()

@pytest.fixture
def calls(monkeypatch):
    """always succeeds, records every call"""
    recorded = []
    def fake_get(path, params=None):
        recorded.append((path, params))
        return (_payload_for(path), True)

    monkeypatch.setattr(auth, "get", fake_get)
    return recorded

@pytest.fixture
def failing(monkeypatch):
    """ok so auth.get succeeds."""
    class Switch:
        ok = True

        def install(self):
            def fake_get(path, params=None):
                if self.ok:
                    return (_payload_for(path), True)
                return (None, False)

            monkeypatch.setattr(auth, "get", fake_get)
            return self

    return Switch().install()

def test_one_cycle_returns_three_endpoints_plus_stale(calls):
    cycle = poller.poll_once()
    assert set(cycle) == {"currentPowerFlow", "overview", "energy", "stale"}
    assert cycle["stale"] is False
    assert len(calls) == 3

def test_raw_json_is_handed_on_unchanged(calls):
    cycle = poller.poll_once()
    assert cycle["currentPowerFlow"]["data"] == POWER_FLOW_JSON
    assert cycle["overview"]["data"] == OVERVIEW_JSON
    assert cycle["energy"]["data"] == ENERGY_JSON

def test_energy_asks_for_hourly_slots(calls):
    poller.poll_once()
    paths = {path: params for path, params in calls}
    assert paths["/site/demo_site_001/energy"] == {"timeUnit": "HOUR"}
    assert paths["/site/demo_site_001/currentPowerFlow"] is None

def test_site_id_comes_from_env(monkeypatch, calls):
    monkeypatch.setenv("SITE_ID", "other_site_999")
    poller.poll_once()
    assert all("other_site_999" in path for path, _ in calls)

def test_every_entry_carries_a_fetched_at(calls):
    cycle = poller.poll_once()
    stamp = cycle["overview"]["fetched_at"]
    assert stamp.endswith("Z")
    datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")

#cache
def test_failure_after_a_good_poll_reserves_the_cache(failing):
    good = poller.poll_once()
    assert good["stale"] is False
    failing.ok = False
    stale = poller.poll_once()
    assert stale is not None, "a cached cycle must still be served"
    assert stale["stale"] is True
    assert stale["currentPowerFlow"]["data"] == POWER_FLOW_JSON
    assert stale["currentPowerFlow"]["stale"] is True

def test_stale_entry_keeps_the_original_fetched_at(failing):
    first = poller.poll_once()
    original = first["overview"]["fetched_at"]
    failing.ok = False
    stale = poller.poll_once()
    assert stale["overview"]["fetched_at"] == original

def test_cache_recovers_when_the_source_comes_back(failing):
    poller.poll_once()
    failing.ok = False
    assert poller.poll_once()["stale"] is True
    failing.ok = True
    assert poller.poll_once()["stale"] is False

def test_cold_start_with_nothing_cached_returns_none(failing):
    failing.ok = False
    assert poller.poll_once() is None

def test_cold_start_does_not_poison_the_cache(failing):
    failing.ok = False
    assert poller.poll_once() is None
    failing.ok = True
    cycle = poller.poll_once()
    assert cycle["stale"] is False

def test_one_failed_endpoint_marks_the_whole_cycle_stale(monkeypatch):
    poller.reset_cache()

    def all_good(path, params=None):
        return (_payload_for(path), True)

    monkeypatch.setattr(auth, "get", all_good)
    poller.poll_once()

    def overview_only_fails(path, params=None):
        if path.endswith("overview"):
            return (None, False)
        return (_payload_for(path), True)

    monkeypatch.setattr(auth, "get", overview_only_fails)
    cycle = poller.poll_once()
    assert cycle["stale"] is True
    assert cycle["overview"]["stale"] is True
    assert cycle["currentPowerFlow"]["stale"] is False

def test_poll_once_never_hands_down_a_none_payload(failing):
    poller.poll_once()
    failing.ok = False
    cycle = poller.poll_once()
    for name in ("currentPowerFlow", "overview", "energy"):
        assert cycle[name]["data"] is not None

def test_daylight_window_edges():
    assert poller.is_daylight(datetime(2026, 10, 4, 6, 30)) is True
    assert poller.is_daylight(datetime(2026, 10, 4, 19, 30)) is True
    assert poller.is_daylight(datetime(2026, 10, 4, 6, 29)) is False
    assert poller.is_daylight(datetime(2026, 10, 4, 22, 0)) is False

def test_daylight_window_is_configurable(monkeypatch):
    monkeypatch.setenv("DAYLIGHT_START", "05:00")
    monkeypatch.setenv("DAYLIGHT_END", "21:00")
    assert poller.is_daylight(datetime(2026, 10, 4, 20, 0)) is True

def test_unparseable_window_falls_back_to_defaults(monkeypatch):
    monkeypatch.setenv("DAYLIGHT_START", "not a time")
    assert poller.is_daylight(datetime(2026, 10, 4, 12, 0)) is True
    assert poller.is_daylight(datetime(2026, 10, 4, 3, 0)) is False

#budget
def test_blank_dev_override_uses_the_production_cadence():
    assert poller.interval_seconds() == (300, False)

def test_dev_override_wins_and_is_flagged(monkeypatch):
    monkeypatch.setenv("POLL_INTERVAL_SEC", "5")
    assert poller.interval_seconds() == (5, True)

def test_garbage_dev_override_is_ignored(monkeypatch):
    monkeypatch.setenv("POLL_INTERVAL_SEC", "soon")
    assert poller.interval_seconds() == (300, False)

def test_budget_estimate_exceeds_the_cap_at_default_settings():
    #13 h window / 5 min = 156 cycles x 3 endpoints
    assert poller.daily_request_estimate() == 468
    assert poller.daily_request_estimate() > poller.rate_limit()

def test_budget_estimate_is_skipped_under_the_dev_override(monkeypatch):
    monkeypatch.setenv("POLL_INTERVAL_SEC", "5")
    assert poller.daily_request_estimate() == 0

def test_missing_rate_limit_falls_back(monkeypatch):
    monkeypatch.delenv("RATE_LIMIT_MAX", raising=False)
    assert poller.rate_limit() == 280