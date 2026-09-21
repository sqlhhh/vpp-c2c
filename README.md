# VPP Cloud-to-Cloud Smart Inverter Integration

[![CI](https://github.com/sqlhhh/vpp-c2c/actions/workflows/ci.yml/badge.svg)](https://github.com/sqlhhh/vpp-c2c/actions/workflows/ci.yml)

CCNY Grove School of Engineering · Senior Design II · Team 2

Every Smart Inverter (SI) manufacturer runs its own cloud with its own API format,
authentication and field names. A VPP operator aggregating thousands of inverters has no
standard interface to any of them. **This pipeline is the translation layer**: it pulls data
from one vendor's cloud over REST, normalizes it to a standard schema, and republishes it to a
neutral broker over MQTT.

> Terminology: this project says **Smart Inverters (SIs)**, never "DERs".
> Our schema is **aligned with** IEEE 2030.5 and SunSpec — it does not *implement* them.

## The pipeline

**Pull** (Blocks 0-5) reads the vendor cloud into the DERMS. **Push** (Block 6 + adapters) sends a
command back through one adapter interface, so the inverter brand can be chosen after the pipeline
is built. Lanes are split by protocol.

| Block | What | Owner | File |
|---|---|---|---|
| 0 | Mock SolarEdge cloud (Flask, `localhost:5000`) | Shaoqin, verified by Ali | `src/mock_server.py` |
| 1 | Authentication + rate limiting | Gina | `src/auth.py` |
| 2 | Polling engine (5-min schedule) | Gina | `src/poller.py` |
| 3 | Normalizer — vendor JSON → standard schema | Gina | `src/normalizer.py` |
| 4 | MQTT publisher (QoS 1, TLS) | Matthew | `src/mqtt_publisher.py` |
| 5 | AWS IoT Core → InfluxDB → Grafana | Matthew (broker, `src/mqtt_to_influx.py`), Mahedi (InfluxDB, Grafana, `web/command.html`) | |
| 6 | Command originator (`POST /command`, safety gate) | Matthew | `src/command_originator.py` |
| — | Adapter interface + `INVERTER_VENDOR` switch | Shaoqin | `src/adapter.py`, `src/adapter_factory.py` |
| — | Bridge adapter: our own Raspberry Pi writes a Modbus register | Matthew | `src/bridge_adapter.py`, `pi/bridge.py`, `pi/mock_inverter.py` |
| — | Mock-cloud adapter: `POST` to our mock server (vendor-cloud shape) | Gina | `src/mock_cloud_adapter.py` |
| — | SMA adapter (stretch, only if the sandbox works) / Victron (stub) | tbd | `src/sma_adapter.py`, `src/victron_adapter.py` |
| — | Register map data, setup page, evidence, demo runbook | Ali | `register_maps/solaredge.json`, `docs/setup.md`, `docs/evidence/` |
| — | Entry point chaining the pull blocks | Shaoqin | `src/pipeline.py` |

**Contracts** (authoritative over any older document, including the context skill):
`docs/block0_contract.md` (what the mock returns), `docs/team1_contract.md` §4 (the 11-field
telemetry schema), `docs/command_contract.md` (the command schema and safety gate).

**Success criteria:** the pull chain runs for **60 continuous minutes without manual
intervention** (week 5-6), then the same command lands through two different adapters by flipping
`INVERTER_VENDOR` (week 10). Due 2026-12-20.

## Quick start

```bash
git clone <this repo>
cd vpp-c2c
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in values; never commit this file
pytest tests/ -v             # 58 passed
```

Python 3.10 or newer. CI runs on 3.10, so that is the version that decides arguments about
whether something works.

## Layout

```
src/      pipeline code, one module per block
tests/    one test file per block, plus repo guards
certs/    AWS IoT certificates - git-ignored, never committed
docs/     block0_contract.md, standards_mapping.md, team1_contract.md,
          runbook.md, evidence/
```

## Rules

1. Nothing merges to `main` without a PR, one review, and green CI.
2. Every block ships with its tests. A block without tests cannot be handed over.
3. Secrets live in `.env` and `certs/`, both git-ignored. `.env.example` documents every
   variable with no real values.
4. Failures are logged, never raised — one uncaught exception ends the 60-minute run.
5. Evidence goes into `docs/evidence/` as it is produced, not at the end.
6. No new dependency without PM sign-off.

## Where the plan lives

- **C2C Pipeline Build Guide** — one tab per person: Step 0, files, a worked example on real
  captured data, "done when", who is waiting on you, dates. This is the task list.
  https://claude.ai/code/artifact/bcab6a99-ab4f-46b6-b772-d7480c8ae393
  (Markdown mirror: `docs/build_guide/`)
- **Team handbook** (background only, superseded for tasks):
  https://claude.ai/code/artifact/c738fe06-ff6b-464a-beb3-e1d4631714b6
- **Build manual** — `VPP_C2C_BUILD_MANUAL.md`, Phases 0–10 with acceptance criteria
- **Context skill** — `vpp-c2c-context` v2, authoritative over the binder; its Block 3 field map
  and "23 tests" are stale — the contracts above win
