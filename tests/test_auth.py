import logging
import pytest
import requests
import auth

class FakeResponse:
    def __init__(self, status_code=200, payload=None, body_is_json=True):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self._body_is_json = body_is_json

    @property
    def ok(self):
        return 200 <= self.status_code < 400

    def json(self):
        if not self._body_is_json:
            raise ValueError("Expecting value: line 1 column 1 (char 0)")
        return self._payload

@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    monkeypatch.setenv("API_BASE_URL", "http://127.0.0.1:5000")
    monkeypatch.setenv("API_KEY", "test_key")
    monkeypatch.setenv("RATE_LIMIT_MAX", "280")
    auth.reset_counter()
    yield
    auth.reset_counter()

@pytest.fixture
def calls(monkeypatch):
    recorded = []

    def fake_get(url, params=None, timeout=None):
        recorded.append({"url": url, "params": params, "timeout": timeout})
        return FakeResponse(200, {"overview": {"currentPower": {"power": 4278.6}}})

    monkeypatch.setattr(requests, "get", fake_get)
    return recorded

def test_happy_path_returns_json_and_true(calls):
    data, ok = auth.get("/site/demo_site_001/overview")
    assert ok is True
    assert data["overview"]["currentPower"]["power"] == 4278.6
    assert len(calls) == 1

def test_key_is_attached_and_base_url_joined(calls):
    auth.get("/site/demo_site_001/energy", params={"timeUnit": "HOUR"})
    sent = calls[0]
    assert sent["url"] == "http://127.0.0.1:5000/site/demo_site_001/energy"
    assert sent["params"]["api_key"] == "test_key"
    assert sent["params"]["timeUnit"] == "HOUR"
    assert sent["timeout"] == 10

def test_blank_key_gives_401_and_is_logged(monkeypatch, caplog):
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setattr(requests, "get",
                        lambda url, params=None, timeout=None:
                        FakeResponse(401, {"String": "Invalid token"}))
    with caplog.at_level(logging.ERROR):
        data, ok = auth.get("/site/demo_site_001/overview")
    assert (data, ok) == (None, False)
    assert "401" in caplog.text

def test_call_281_is_refused_without_an_http_request(calls):
    for _ in range(280):
        assert auth.get("/site/demo_site_001/overview")[1] is True
    assert len(calls) == 280
    data, ok = auth.get("/site/demo_site_001/overview")
    assert (data, ok) == (None, False)
    assert len(calls) == 280

def test_counter_resets_after_utc_midnight(calls, monkeypatch):
    for _ in range(280):
        auth.get("/site/demo_site_001/overview")
    assert auth.get("/site/demo_site_001/overview") == (None, False)
    monkeypatch.setattr(auth, "_counter_date", None)
    assert auth.get("/site/demo_site_001/overview")[1] is True
    assert auth.request_count() == 1

def test_429_sleeps_60_then_120_then_240_then_gives_up(monkeypatch):
    slept = []
    monkeypatch.setattr(auth.time, "sleep", slept.append)
    attempts = []

    def always_429(url, params=None, timeout=None):
        attempts.append(url)
        return FakeResponse(429, {"String": "Too many requests"})

    monkeypatch.setattr(requests, "get", always_429)
    data, ok = auth.get("/site/demo_site_001/overview")
    assert (data, ok) == (None, False)
    assert slept == [60, 120, 240]
    assert len(attempts) == 4

def test_429_then_success_returns_the_data(monkeypatch):
    monkeypatch.setattr(auth.time, "sleep", lambda _: None)
    responses = [FakeResponse(429), FakeResponse(200, {"overview": {"ok": True}})]
    monkeypatch.setattr(requests, "get",lambda url, params=None, timeout=None: responses.pop(0))
    data, ok = auth.get("/site/demo_site_001/overview")
    assert ok is True
    assert data == {"overview": {"ok": True}}


def test_connection_error_returns_false_and_raises_nothing(monkeypatch, caplog):
    def dead_socket(url, params=None, timeout=None):
        raise requests.exceptions.ConnectionError("connection refused")
    monkeypatch.setattr(requests, "get", dead_socket)
    with caplog.at_level(logging.ERROR):
        data, ok = auth.get("/site/demo_site_001/overview")
    assert (data, ok) == (None, False)
    assert "ConnectionError" in caplog.text


def test_timeout_returns_false(monkeypatch):
    def too_slow(url, params=None, timeout=None):
        raise requests.exceptions.Timeout("timed out")
    monkeypatch.setattr(requests, "get", too_slow)
    assert auth.get("/site/demo_site_001/overview") == (None, False)

def test_non_json_body_returns_false(monkeypatch):
    monkeypatch.setattr(requests, "get",
                        lambda url, params=None, timeout=None:
                        FakeResponse(200, body_is_json=False))
    assert auth.get("/site/demo_site_001/overview") == (None, False)

def test_404_returns_false(monkeypatch):
    monkeypatch.setattr(requests, "get",
                        lambda url, params=None, timeout=None:
                        FakeResponse(404, {"String": "Not found"}))
    assert auth.get("/site/demo_site_001/nope") == (None, False)