# Block 0 contract — the mock SolarEdge API

**Status:** authoritative · **Frozen:** 2026-09-08 · **Owner:** PM (Shaoqin) · **Verifier:** Ali (Phase 1)

This document, not `src/mock_server.py`, is the contract. Blocks 1–3 are coded against what is
written here. If the server's behaviour and this page ever disagree, this page wins and the code
is the bug.

> **Provenance.** The originally delivered `mock_server.py` and its 23 tests could not be located
> on any machine we have access to (searched 2026-09-08). The server was rebuilt from the spec in
> `SKILL.md` §5 Block 0. **If the original resurfaces, it is judged against this document** — the
> implementation that satisfies this contract stays, the other is deleted rather than merged.
> The suite is now **52 tests** (plus 6 repo-health), not 23; every place that quotes "23 tests"
> needs updating (`SKILL.md` §5/§17 F8, `VPP_C2C_BUILD_MANUAL.md` Phase 0/1, the Phase 10 numbers slide).
> *Resolved 2026-09-26: `docs/SKILL.md` and `docs/VPP_C2C_BUILD_MANUAL.md` now quote 52; the numbers slide is still to do.*

---

## 1. Running it

```bash
python src/mock_server.py            # binds 127.0.0.1:5000
MOCK_PORT=5050 python src/mock_server.py
MOCK_DETERMINISTIC=1 python ...      # no noise, no cloud dips — use this in integration tests
```

| ENV var | Default | Meaning |
|---|---|---|
| `MOCK_PORT` | `5000` | listen port |
| `MOCK_SITE_ID` | `demo_site_001` | site id echoed in `_mock` |
| `MOCK_DETERMINISTIC` | `0` | `1` disables the ±12 % noise and the cloud dips |

## 2. Authentication

Every endpoint **except `/health`** requires a non-empty `api_key` query parameter.
Missing, empty, or whitespace-only → **HTTP 401**. Any other value is accepted (mock mode:
"any non-empty string works", `SKILL.md` §5 Block 1 sub-unit A).

```json
{"String": "Invalid token", "_mock": {"source": "mock_server", "site_id": "demo_site_001"}}
```

## 3. The `_mock` tag

**Every** JSON response carries it — successes, 401s and 404s alike. Block 3 uses it to set
`data_source`. Its absence is how the pipeline can tell it is talking to the real cloud.

```json
"_mock": {"source": "mock_server", "site_id": "demo_site_001"}
```

## 4. Endpoints

All examples below are **real captured responses** from the running server on 2026-09-08 at
14:56 local, not hand-written illustrations.

### 4.1 `GET /site/{siteId}/currentPowerFlow`

The live snapshot. This is the one Block 2 polls every 5 minutes and the one Block 3's field map
is built on.

```json
{
  "siteCurrentPowerFlow": {
    "updateRefreshRate": 3,
    "unit": "kW",
    "connections": [{"from": "PV", "to": "Load"}, {"from": "PV", "to": "Storage"}],
    "GRID":    {"status": "Active", "currentPower": 0.0},
    "LOAD":    {"status": "Active", "currentPower": 0.493},
    "PV":      {"status": "Active", "currentPower": 4.191},
    "STORAGE": {"status": "Active", "currentPower": 3.698, "chargeLevel": 55.0, "critical": false}
  },
  "_mock": {"source": "mock_server", "site_id": "demo_site_001"}
}
```

* `unit` is **kW**. Multiply by 1000 for watts.
* `PV.status` is `"Idle"` when solar is 0, `"Active"` otherwise.
* **`currentPower` values are magnitudes — always ≥ 0. Direction lives in `connections`.**
  See §6.1; this matters.

### 4.2 `GET /site/{siteId}/overview`

```json
{
  "overview": {
    "lastUpdateTime": "2026-09-08 14:56:17",
    "lifeTimeData":  {"energy": 12477697.4, "revenue": 0.0},
    "lastYearData":  {"energy": 4120000.0},
    "lastMonthData": {"energy": 388000.0},
    "lastDayData":   {"energy": 27697.4},
    "currentPower":  {"power": 4278.6},
    "measuredBy": "INVERTER"
  }
}
```

* Energy fields are **Wh**. `currentPower.power` is **W**. Note this differs from §4.1's kW —
  that inconsistency is the real SolarEdge API's, and we reproduce it deliberately. See §6.2.
* `lifeTimeData ≥ lastDayData` always holds (asserted in the suite).

### 4.3 `GET /site/{siteId}/energy`

Accepts `timeUnit` (`DAY` default, or `HOUR`); `startDate`/`endDate` are accepted and ignored.

```json
{"energy": {"timeUnit": "DAY", "unit": "Wh", "measuredBy": "INVERTER",
            "values": [{"date": "2026-09-08 00:00:00", "value": 27697.4}]}}
```

`timeUnit=HOUR` returns exactly 24 slots; hours later than now carry `"value": null`.

### 4.4 `GET /site/{siteId}/powerDetails`

```json
{"powerDetails": {"timeUnit": "QUARTER_OF_AN_HOUR", "unit": "W", "meters": [
  {"type": "Production",  "values": [{"date": "2026-09-08 14:56:17", "value": 4213.9}]},
  {"type": "Consumption", "values": [{"date": "2026-09-08 14:56:17", "value": 527.6}]}]}}
```

Unit is **W** here, unlike §4.1's kW. Again, the real API's inconsistency, reproduced.

### 4.5 `GET /equipment/{siteId}/list`

```json
{"reporters": {"count": 1, "list": [{"name": "Inverter 1", "manufacturer": "SolarEdge",
  "model": "USE5700H-US000BNU4", "serialNumber": "7E1B2C3D-4F"}]}}
```

### 4.6 `GET /health` — ours, not SolarEdge's

No `api_key` required. Added per manual step 1.4 for the Phase 8 soak.

```json
{"status": "ok", "uptime_seconds": 25.9, "request_count": 7,
 "server_time": "2026-09-08 14:56:17", "utc_time": "2026-09-08T18:56:17Z",
 "deterministic": false, "site_id": "demo_site_001"}
```

Unknown paths return **404** with a `_mock` tag.

## 5. The simulated site

| Quantity | Value |
|---|---|
| Inverter nameplate | 5700 W (SolarEdge Home Hub USE5700H) |
| Solar curve | Gaussian, centre **13:00**, sigma = 2.5 h |
| Active window | **06:30 – 19:30**; hard zero outside |
| Reading noise | ±12 % |
| Cloud dip | 5 % of readings lose a further 30–60 % |
| Household load | 450 W floor + morning bump (07:30) + evening bump (19:00) |
| Battery | 9700 Wh, ±5000 W, SOC clamped **10–100 %** |
| Grid | `load + battery − solar`; **+ import, − export** |
| Lifetime baseline | 12 450 000 Wh before today |

Battery SOC integrates the solar surplus/deficit over **real elapsed wall-clock time** between
requests, so a long-running soak shows a genuinely drifting SOC rather than a random walk.

**Phase 1 acceptance, both asserted in the suite:** 0 W at 22:00 · > 3000 W at 13:00.

## 6. Three mismatches between this API and `SKILL.md` §5 Block 3

Found while rebuilding, on 2026-09-08. The mock follows the **real SolarEdge API** in all three
cases, because the project's whole premise is that swapping to the real cloud is one ENV var. That
means **Block 3's spec is what needs the edit — before Gina writes it**, not after.

**Resolved 2026-09-26:** all three are corrected in `docs/SKILL.md` §5 Blocks 2–3 and §8. Kept
here as the reasoning behind the field map.

### 6.1 Grid and battery sign — the one that will silently corrupt the dashboard

`SKILL.md` Block 3 sub-unit A maps `GRID.currentPower → grid_power_w (+ import / − export)` and
`STORAGE.currentPower → battery_power_w (+ charging / − discharging)`, i.e. it expects **signed**
values. The real API — and therefore this mock — returns **unsigned magnitudes** and encodes the
direction in the `connections` array.

Block 3 must derive the sign from `connections`:

| Connection present | Meaning |
|---|---|
| `{"from": "GRID", "to": "Load"}` | importing → `grid_power_w` **positive** |
| `{"from": "LOAD", "to": "Grid"}` | exporting → `grid_power_w` **negative** |
| `{"from": "PV", "to": "Storage"}` | charging → `battery_power_w` **positive** |
| `{"from": "Storage", "to": "Load"}` | discharging → `battery_power_w` **negative** |

Taking `currentPower` at face value yields a dashboard that reports import while the house is
exporting. `SKILL.md` itself calls this sign convention "critical".

### 6.2 Energy units are Wh, not kWh

`SKILL.md` Block 3 sub-unit B says *"Energy values stay in kWh (no conversion needed)."* The real
SolarEdge `overview` and `energy` endpoints return **Wh**. `energy_today_kwh` and
`energy_lifetime_kwh` therefore need **÷ 1000**, not a pass-through, or every energy figure lands
1000x too large.

### 6.3 `/energy?timeUnit=DAY` is not hourly

`SKILL.md` Block 2 sub-unit B describes `/energy?timeUnit=DAY` as *"hourly production slots for the
day"*. `DAY` granularity returns **one** value — the day's total. Block 2 should request
`timeUnit=HOUR` if it actually wants the 24 slots. Both are implemented; pick deliberately.

## 7. What Blocks 1–3 may rely on

1. Paths, JSON shapes and field names above are **frozen**. Changing one changes this document in
   the same commit, and it is a PM-reviewed PR.
2. A response is **always** returned — success, 401 or 404 — never a hang or a bare exception.
   Request timeout on the client side is still Block 1's job (10 s, `SKILL.md` §5 Block 2).
3. `_mock.source == "mock_server"` is present on every response.
4. `MOCK_DETERMINISTIC=1` makes readings exactly repeatable at a given clock time. Use it in any
   test that asserts a value; the mock's own suite does.
5. There is **no rate limit here**. The 300/day cap and the 280 pause are Block 1's to simulate —
   the mock will answer forever.
