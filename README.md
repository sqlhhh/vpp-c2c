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

| Block | What | Owner | File |
|---|---|---|---|
| 0 | Mock SolarEdge cloud (Flask, `localhost:5000`) | Shaoqin + Ali | `src/mock_server.py` |
| 1 | Authentication + rate limiting | Gina | `src/auth.py` |
| 2 | Polling engine (5-min schedule) | Gina | `src/poller.py` |
| 3 | Normalizer — vendor JSON → standard schema | Gina | `src/normalizer.py` |
| 4 | MQTT publisher (QoS 1, TLS) | Matthew | `src/mqtt_publisher.py` |
| 5 | AWS IoT Core → InfluxDB → Grafana | Matthew + Mahedi | `src/mqtt_to_influx.py` |
| — | Entry point chaining all of the above | Shaoqin | `src/pipeline.py` |

**Success criterion:** the full chain runs for **60 continuous minutes without manual
intervention**.

## Quick start

```bash
git clone <this repo>
cd vpp-c2c
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in values; never commit this file
pytest tests/ -v
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

- **Team handbook** (what/why/how per block, schedule, who does what):
  https://claude.ai/code/artifact/c738fe06-ff6b-464a-beb3-e1d4631714b6
- **Build manual** — `VPP_C2C_BUILD_MANUAL.md`, Phases 0–10 with acceptance criteria
- **Context skill** — `vpp-c2c-context` v2, authoritative over the binder
