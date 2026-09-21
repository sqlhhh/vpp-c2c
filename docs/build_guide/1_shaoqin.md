# Shaoqin — PM: contracts, adapter interface, integration

You write the two contracts everyone else codes against, then run the two gates (soak, swap demo). Six tasks, in order.

## Task 1 — `docs/command_contract.md` · by 2026-09-27

The push equivalent of `block0_contract.md`. Matthew, Gina and Mahedi all build against it, so it ships before any push code. Keep the vocabulary to one command in v1.

**The command (dashboard → originator → adapter):**

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

**The result (adapter → originator → InfluxDB `commands` measurement):**

```json
{
  "command_id": "c3f1a2b4-7d9e-4c8a-9f01-2b3c4d5e6f70",
  "success": true,
  "adapter": "mock_cloud",
  "detail": "limit_pct=60 accepted",
  "completed_at": "2026-11-10T19:05:01Z"
}
```

**Safety gate — write these into the contract as rules, not suggestions:**

| Rule | Value |
| --- | --- |
| Whitelist | `set_power_limit_pct` only in v1. `set_mode` and `on_off` are listed as "reserved, not implemented" |
| Clamp | `value` is an integer 0–100; anything else is rejected before it reaches an adapter |
| Dry run | `DRY_RUN=1` is the default in `.env.example`. The originator logs the command and returns `success: true, detail: "dry_run"` without calling `push()` |
| Audit | Every command and its result is written to InfluxDB measurement `commands`, dry run or not |
| Real hardware | No adapter writes to a physical inverter until a lab technician signs off in writing. Grid-tied inverters need live AC and anti-islanding is in play |

## Task 2 — `src/adapter.py` + `src/adapter_factory.py` · by 2026-09-27

About 60 lines total. This is the single swap point; nothing else in the repo may import a vendor module.

```python
# src/adapter.py
from abc import ABC, abstractmethod

class InverterAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def pull(self) -> dict:
        """Return one reading in the 11-field schema of team1_contract.md section 4."""

    @abstractmethod
    def push(self, command: dict) -> dict:
        """Accept a command_contract.md command; return a command_contract.md result."""
```

```python
# src/adapter_factory.py
import os

def get_adapter():
    vendor = os.getenv("INVERTER_VENDOR", "mock_cloud")
    if vendor == "mock_cloud":
        from mock_cloud_adapter import MockCloudAdapter; return MockCloudAdapter()
    if vendor == "bridge":
        from bridge_adapter import BridgeAdapter; return BridgeAdapter()
    if vendor == "sma":
        from sma_adapter import SmaAdapter; return SmaAdapter()
    raise ValueError(f"unknown INVERTER_VENDOR={vendor}")
```

Also add `INVERTER_VENDOR=mock_cloud` and `DRY_RUN=1` to `.env.example`, and a `src/victron_adapter.py` that subclasses `InverterAdapter` and raises `NotImplementedError` in both methods, with a docstring saying why (VRM MQTT shape, not built, no account).

**Done when:** `pytest tests/test_adapter_factory.py` passes: each of the three `INVERTER_VENDOR` values returns the right class, an unknown value raises, `victron` raises `NotImplementedError` on `push`.

## Task 3 — Fix the stale documents · by 2026-09-27

Teammates will read these and act on them, so they must stop contradicting the contracts.

- `vpp-c2c-context/SKILL.md` §5 Block 3: rewrite the field map with the three corrections from `block0_contract.md` §6 (unsigned magnitudes + `connections`, Wh → kWh, `timeUnit=HOUR`).
- Every "23 tests" → "58 tests" (`SKILL.md` §5, §17 F8; build manual Phases 0, 1, 10).
- `SKILL.md` §6 roles → the table on the Pipeline & Assignments tab.
- `SKILL.md` §7 "Selected SI" → "decided after the professor's answer; modelled platform is SolarEdge".

## Task 4 — Purchases and outside asks · by 2026-10-04

| Ask | To whom | Why now |
| --- | --- | --- |
| Raspberry Pi 4 (4 GB) + USB-RS485 adapter + 5 V 3 A supply | professor / budget | Team 2 builds its own Pi for push. Matthew needs it by week 7 |
| Which inverter, one unit or two, will it be commissioned in the vendor portal | professor | our pull path returns nothing without a commissioned site ID |
| SMA sandbox reply | forward from Ali | decides whether the SMA stretch adapter happens |
| Team 1 | their lead | tell them Team 2's Pi is a separate unit that only *writes*; theirs only *reads*. Add one line to `team1_contract.md` |

## Task 5 — Weekly checkpoints · every week

- **Ali, 15 minutes, same day each week.** Open his tab together. He shows the file for the current task; you tick it or send him back with one concrete fix. He does not start the next task until the current one is ticked.
- Everyone else: one message per week — what shipped, what is blocked. Unblock within 24 h.
- MS Project: add the push phase (about 12 tasks: contract, interface, mock endpoint, mock-cloud adapter, originator, Pi bridge, register map, slider, history panel, swap demo, evidence, runbook).

## Task 6 — Run the two gates

| Gate | When | Pass condition |
| --- | --- | --- |
| Pull soak | week 5–6, by 2026-11-01 | `MOCK_DETERMINISTIC=1`, full chain mock → Grafana runs 60 min with no manual intervention; `/health` `request_count` grows by 12 ± 1; no `stale: true`; Ali's evidence log complete |
| Swap demo | week 10, by 2026-11-29 | same `curl POST /command` with `INVERTER_VENDOR=mock_cloud` then `=bridge`, both results `success: true` in the `commands` measurement, mock register and mock endpoint both read 60 |

## Who is waiting on you

Matthew (Task 1 and 2, week 1), Gina (Task 2 for the adapter base class, week 7), Mahedi (Task 1 for the command shape, week 8), Ali (Task 5, every week).
