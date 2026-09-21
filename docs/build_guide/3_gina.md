# Gina — REST lane: auth, poller, normalizer, mock-cloud push

You own everything that talks HTTP: the three pull modules (Blocks 1–3) and, in week 7, the mock-cloud push adapter, which is your poller in reverse. Your spec is `docs/block0_contract.md` — **not** the old context skill, which has three errors your code must not inherit (Task 3). Nothing you need is unbuilt; you can start today.

## Step 0 · today

Clone [github.com/sqlhhh/vpp-c2c](https://github.com/sqlhhh/vpp-c2c), `python -m venv .venv`, activate, `pip install -r requirements.txt`, `cp .env.example .env`, `pytest tests/ -v` → `58 passed`. Then in a second terminal `python src/mock_server.py` and open [http://localhost:5000/site/demo_site_001/currentPowerFlow?api_key=x](http://localhost:5000/site/demo_site_001/currentPowerFlow?api_key=x). That JSON is your input for everything below. Work on a branch per task, PR to `main`, CI must be green.

## Task 1 — `src/auth.py` (Block 1) · by 2026-09-27

One function every HTTP call goes through. It adds the key, counts requests, and never raises.

```python
def get(path: str, params: dict | None = None) -> tuple[dict | None, bool]:
    """GET {API_BASE_URL}{path} with api_key added. Returns (json, ok)."""
```

| Rule | Detail |
| --- | --- |
| Key | `API_KEY` from `.env` via `python-dotenv`, sent as the `api_key` query parameter. Never in source |
| Counter | in-memory count of requests today; refuse (return `(None, False)`, log a warning) once it reaches `RATE_LIMIT_MAX` (280); reset at UTC midnight |
| Timeout | `requests.get(..., timeout=10)` |
| 401 | log "bad key", return `(None, False)` |
| 429 | sleep 60 s, retry; then 120 s; then 240 s; then give up with `(None, False)` |
| Any exception | caught, logged, `(None, False)`. One uncaught exception ends the 60-minute soak |

**Worked example:** `get("/site/demo_site_001/overview")` against the running mock returns `({"overview": {...}}, True)`; with `API_KEY=` blank in `.env` it returns `(None, False)` and the log shows the 401.

**Done when:** `pytest tests/test_auth.py` passes with at least: blank key → `(None, False)`; the 281st call in one day is refused without an HTTP request; a mocked 429 produces the 60/120/240 sleep sequence (patch `time.sleep`); a connection error returns `(None, False)` and raises nothing.

## Task 2 — `src/poller.py` (Block 2) · by 2026-10-04

Calls three endpoints on a schedule, keeps the last good answer for each, and hands raw JSON on unchanged.

| Part | Detail |
| --- | --- |
| Schedule | APScheduler, every `POLL_INTERVAL_MIN` (5) minutes, only between `DAYLIGHT_START` and `DAYLIGHT_END` (06:30–19:30 local). `POLL_INTERVAL_SEC` overrides for development |
| Endpoints | `/site/{SITE_ID}/currentPowerFlow`, `/site/{SITE_ID}/overview`, `/site/{SITE_ID}/energy?timeUnit=HOUR` (**HOUR**, not DAY — DAY returns one number, HOUR returns the 24 slots) |
| Cache | `{endpoint: {"data": ..., "fetched_at": utc_iso, "stale": False}}`. When `get()` returns `ok=False`, re-serve the cached entry with `stale: True`. Never hand downstream a `None` |
| Output | `poll_once() -> dict` with the three raw responses plus `stale`, passed to the normalizer unchanged |

**Done when:** `POLL_INTERVAL_SEC=5 python src/poller.py` prints three raw JSON blocks every 5 s against the mock. Kill the mock: the next cycle prints the same data with `stale: true` and the process keeps running. Restart the mock: `stale` goes back to `false`. `pytest tests/test_poller.py` covers the cache path with `get()` patched.

## Task 3 — `src/normalizer.py` (Block 3) · by 2026-10-18

The interoperability engine: SolarEdge's shape in, the 11-field schema of `docs/team1_contract.md` §4 out. When the vendor changes, this table is the file that changes.

**Three rules the old skill gets wrong — code these, not the skill:**

| Rule | What the real API (and the mock) does | What you do |
| --- | --- | --- |
| Sign | `GRID.currentPower` and `STORAGE.currentPower` are **magnitudes, never negative**. Direction is in the `connections` list | `{"from":"GRID","to":"Load"}` → grid **+**; `{"from":"LOAD","to":"Grid"}` → grid **−**; `{"from":"PV","to":"Storage"}` → battery **+** (charging); `{"from":"Storage","to":"Load"}` → battery **−** |
| Units | `currentPowerFlow` power is **kW**; `overview` energy is **Wh** | power × 1000 → W; energy ÷ 1000 → kWh |
| Source | every mock response carries `_mock` | `data_source = "mock"` if `_mock` present, else `"live"` |

**Worked example — real captured input** (`block0_contract.md` §4.1 and §4.2, 2026-09-08 14:56 New York):

```json
{"siteCurrentPowerFlow": {"unit": "kW",
  "connections": [{"from": "PV", "to": "Load"}, {"from": "PV", "to": "Storage"}],
  "GRID": {"status": "Active", "currentPower": 0.0},
  "LOAD": {"status": "Active", "currentPower": 0.493},
  "PV": {"status": "Active", "currentPower": 4.191},
  "STORAGE": {"status": "Active", "currentPower": 3.698, "chargeLevel": 55.0}},
 "_mock": {"source": "mock_server", "site_id": "demo_site_001"}}
```

```json
{"overview": {"lastUpdateTime": "2026-09-08 14:56:17",
  "lifeTimeData": {"energy": 12477697.4}, "lastDayData": {"energy": 27697.4},
  "currentPower": {"power": 4278.6}}}
```

**Expected output** of `normalize(power_flow, overview)`:

```json
{
  "site_id": "demo_site_001",
  "data_source": "mock",
  "utc_timestamp": "2026-09-08T18:56:17Z",
  "stale": false,
  "solar_power_w": 4191.0,
  "battery_power_w": 3698.0,
  "battery_soc_pct": 55.0,
  "grid_power_w": 0.0,
  "load_power_w": 493.0,
  "energy_today_kwh": 27.7,
  "energy_lifetime_kwh": 12477.7
}
```

How each line was produced: PV 4.191 kW × 1000 = 4191.0 W. STORAGE 3.698 kW × 1000, sign **+** because `PV → Storage` is present (charging). GRID magnitude 0.0 and no GRID connection → 0.0. 27697.4 Wh ÷ 1000 = 27.7 kWh (round to 1 decimal). `lastUpdateTime` is New York local (UTC−4 in September) → add 4 h, `Z` suffix. `_mock` present → `mock`.

**Validator:** drop the record and log a warning if any required field is missing, or out of range: `solar_power_w` 0–5700, `battery_soc_pct` 0–100, `grid_power_w` −10000–10000, `load_power_w` 0–20000. If the site has no battery, **omit** `battery_power_w` and `battery_soc_pct` — never publish 0 for something unmeasured.

**Done when:** `pytest tests/test_normalizer.py` passes with at least these fixtures: the example above produces exactly the output above; an input with `{"from":"LOAD","to":"Grid"}` and `GRID.currentPower: 0.302` gives `grid_power_w: -302.0`; a `Storage → Load` input gives a negative `battery_power_w`; `lastDayData.energy: 27697.4` gives `27.7` not `27697.4`; a missing `LOAD` drops the record and the log line appears; a `solar_power_w` of 9000 is dropped.

## Task 4 — Mock-cloud push: mock endpoint + `src/mock_cloud_adapter.py` · by 2026-11-15

This is the second adapter shape (vendor cloud accepts a command) and it uses the same trick as Block 0: our own mock server pretends to be a vendor cloud. Read `docs/command_contract.md` and `src/adapter.py` (Shaoqin, week 1) first.

**4a — add to `src/mock_server.py`** (PR it separately; it touches a frozen file, so update `docs/block0_contract.md` §4 in the same commit):

| Endpoint | Behaviour |
| --- | --- |
| `POST /site/{id}/powerLimit` body `{"limit_pct": 60}` | store it; respond `200 {"accepted": true, "limit_pct": 60}`; outside 0–100 or non-integer → `400`; missing `api_key` → `401` like every other endpoint |
| `GET /site/{id}/powerLimit` | `{"limit_pct": 60}` (default 100) |
| `GET /site/{id}/currentPowerFlow` | PV is now `min(curve, limit_pct% of 5700 W)` — the limit visibly caps the curve |

**4b — `MockCloudAdapter(InverterAdapter)`:**

```python
class MockCloudAdapter(InverterAdapter):
    name = "mock_cloud"
    def pull(self) -> dict:
        return normalize(*poll_once())            # reuse your own Blocks 1-3
    def push(self, command: dict) -> dict:
        r = requests.post(f"{BASE}/site/{SITE_ID}/powerLimit",
                          params={"api_key": KEY},
                          json={"limit_pct": command["value"]}, timeout=10)
        return {"command_id": command["command_id"], "success": r.ok,
                "adapter": self.name, "detail": r.text[:200],
                "completed_at": utc_now_iso()}
```

**Done when:** `pytest tests/test_mock_cloud_adapter.py` passes: `push({... "value": 60})` returns `success: true`; `GET /powerLimit` then reads 60; with `MOCK_DETERMINISTIC=1` and the clock patched to 13:00, `pull()["solar_power_w"] <= 3420.0` (0.6 × 5700); `value: 150` returns `success: false`.

## Who is waiting on you

| Who | For | When |
| --- | --- | --- |
| Matthew | the dict `normalize()` returns — he publishes it as-is | week 3 (until then he uses the JSON in `team1_contract.md` §4 as fake data) |
| Mahedi | real rows in InfluxDB | week 3–4 via Matthew |
| Shaoqin | the swap demo needs `mock_cloud_adapter` | week 10 |

You wait on nobody for Tasks 1–3. Task 4 needs `command_contract.md` and `adapter.py` from Shaoqin (week 1).
