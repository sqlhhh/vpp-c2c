# Command contract — push from the DERMS to the inverter

**Status:** authoritative · **Frozen:** 2026-09-21 · **Owner:** PM (Shaoqin)

The push equivalent of `block0_contract.md`. The command originator (Block 6, Matthew), every
adapter (Gina, Matthew) and the command page (Mahedi) are coded against this document. If code
and this page disagree, this page wins and the code is the bug. Changing it is a PM-reviewed PR
that updates this file in the same commit.

---

## 1. The path a command takes

```
web/command.html  ──POST /command──▶  command_originator.py  ──push(cmd)──▶  adapter_factory.get_adapter()
     (Mahedi)                              (Matthew)                              │
                                                                                  ├─ bridge      → pi/bridge.py → Modbus write   (Matthew)
                                                                                  ├─ mock_cloud  → POST mock_server /powerLimit   (Gina)
                                                                                  ├─ sma         → GridControl API   (stretch)
                                                                                  └─ victron     → NotImplementedError (stub)
```

Nothing upstream of the adapter ever imports a vendor module. `INVERTER_VENDOR` in `.env` is the
only switch. Proving "any brand fits" = the same `POST /command` succeeds with two different
`INVERTER_VENDOR` values (the week-10 swap demo).

## 2. The command

Emitted by the originator, accepted by every adapter's `push(command)`.

```json
{
  "command_id": "c3f1a2b4-7d9e-4c8a-9f01-2b3c4d5e6f70",
  "command": "set_power_limit_pct",
  "value": 60,
  "site_id": "demo_site_001",
  "requested_at": "2026-11-10T19:05:00Z",
  "dry_run": true
}
```

| Field | Type | Set by | Notes |
|---|---|---|---|
| `command_id` | string, uuid4 | originator | joins the command to its result and to the Pi's ack |
| `command` | string | UI | must be in the whitelist (§4) |
| `value` | integer | UI | meaning depends on `command`; for `set_power_limit_pct`: 0–100, percent of nameplate |
| `site_id` | string | originator, from `.env` `SITE_ID` | same string as the telemetry `site_id` |
| `requested_at` | string, ISO-8601 UTC `Z` | originator | UTC always, same rule as telemetry |
| `dry_run` | bool | originator, from `.env` `DRY_RUN` | true = log only, no adapter call |

## 3. The result

Returned by `push()`, returned by `POST /command`, and written to InfluxDB measurement `commands`.

```json
{
  "command_id": "c3f1a2b4-7d9e-4c8a-9f01-2b3c4d5e6f70",
  "success": true,
  "adapter": "mock_cloud",
  "detail": "limit_pct=60 accepted",
  "completed_at": "2026-11-10T19:05:01Z"
}
```

| Field | Type | Notes |
|---|---|---|
| `success` | bool | true only if the target confirmed the write (HTTP 2xx, or a Modbus read-back equal to the value) |
| `adapter` | string | `bridge` · `mock_cloud` · `sma` · `victron` · `dry_run` |
| `detail` | string ≤ 200 chars | vendor response text, error text, or `dry_run` |
| `completed_at` | ISO-8601 UTC | when the adapter returned, not when the UI clicked |

InfluxDB: measurement `commands`, tags `site_id`, `adapter`, `success`; fields `command`, `value`,
`detail`, `command_id`; time = `completed_at`. Mahedi's history panel reads this.

## 4. Safety gate — rules, not suggestions

| Rule | Value |
|---|---|
| Whitelist | `set_power_limit_pct` only in v1. `set_mode` and `on_off` are reserved names, **not implemented**; the originator returns `400` for them |
| Clamp | `value` must be an integer in 0–100. Anything else → `400` before any adapter is called |
| Dry run | `DRY_RUN=1` is the default in `.env.example`. The originator logs the command, writes it to `commands` with `adapter: "dry_run"`, returns `success: true`, and **does not call `push()`** |
| Audit | Every command and its result is written to `commands`, dry run or not, success or not |
| Timeout | An adapter that has not confirmed within 10 s returns `success: false`, `detail: "timeout"` |
| Real hardware | No adapter writes to a physical inverter until a lab technician has signed off in writing and the sign-off is in `docs/evidence/`. A grid-tied inverter needs live AC; anti-islanding is in play. Until then the Pi talks only to `pi/mock_inverter.py` |
| Rate | at most one command per 5 s from the originator; extra requests → `429` |

## 5. Adapter interface

```python
class InverterAdapter(ABC):
    name: str

    def pull(self) -> dict:
        """One reading in the 11-field schema of team1_contract.md section 4."""

    def push(self, command: dict) -> dict:
        """Accept a section-2 command, return a section-3 result. Never raises."""
```

`adapter_factory.get_adapter()` reads `INVERTER_VENDOR` (`mock_cloud` default · `bridge` · `sma` ·
`victron`) and returns the matching instance. Unknown value → `ValueError` at startup, not at
command time.

## 6. What each adapter does with `set_power_limit_pct`

| Adapter | Target | Write | Confirmation |
|---|---|---|---|
| `mock_cloud` | `POST {API_BASE_URL}/site/{SITE_ID}/powerLimit?api_key=…` body `{"limit_pct": value}` | our mock server stores it and caps `PV.currentPower` at `value %` of 5700 W | HTTP 200 `{"accepted": true, "limit_pct": value}`; `GET …/powerLimit` reads it back |
| `bridge` | publish `solar/site/{site_id}/cmd` (QoS 1), the section-2 JSON | `pi/bridge.py` writes `active_power_limit_pct` from `register_maps/solaredge.json` (enable register first if 0) | ack on `solar/site/{site_id}/cmd/ack` with the same `command_id` and the read-back value, within 10 s |
| `sma` | GridControl schedule command (stretch) | feed-in / active power limit | HTTP 2xx |
| `victron` | — | raises `NotImplementedError` | — |

### 6.1 Mock server additions (Gina, week 7 — update `block0_contract.md` §4 in the same commit)

| Endpoint | Behaviour |
|---|---|
| `POST /site/{id}/powerLimit` body `{"limit_pct": 60}` | store; `200 {"accepted": true, "limit_pct": 60}`; outside 0–100 or non-integer → `400`; missing `api_key` → `401` |
| `GET /site/{id}/powerLimit` | `{"limit_pct": 60}` (default 100) |
| `GET /site/{id}/currentPowerFlow` | `PV.currentPower = min(curve, limit_pct % × 5700 W)` |

### 6.2 Bridge topics (Matthew, week 7–9)

```
solar/site/{site_id}/cmd        originator → Pi   the section-2 command, QoS 1, retain false
solar/site/{site_id}/cmd/ack    Pi → originator   {"command_id", "success", "detail", "completed_at"}
```

Team 2's Pi is a **separate unit from Team 1's Pi**: ours only writes, theirs only reads.

## 7. What the originator exposes

| Route | Purpose |
|---|---|
| `POST /command` `{"command", "value"}` | validate → stamp → dry-run or push → audit → return the section-3 result |
| `GET /commands?limit=20` | last rows of `commands`, newest first, for the history panel |
| `GET /` | serves `web/command.html` so the page and the API share an origin |

Port `5001` (`ORIGINATOR_PORT`), same laptop as the pipeline during the demo.
