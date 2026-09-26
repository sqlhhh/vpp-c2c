---
name: vpp-c2c-context
description: >
  Master context document for the VPP (Virtual Power Plant) Cloud-to-Cloud
  Solar Smart Inverter Integration Senior Design Project at CCNY. Load this
  skill at the START of every new chat under this project folder. It provides
  the full project background, system architecture, block diagram with
  sub-unit detail, team assignments, deliverables, tech stack, all key
  decisions, SI selection rationale, mock server internals, presentation
  context, interview pitch, and current build status so new chats have
  complete context instantly with zero re-explaining needed.
  ALWAYS use this skill when the user says "continue the project", "what did
  we decide", "remind me of the architecture", "who owns what", "what is our
  stack", "next step", or starts any conversation about cloud-to-cloud,
  SolarEdge API, mock server, MQTT, Smart Inverter, VPP, DERMS, pipeline,
  or senior design project.
---

# VPP — Cloud-to-Cloud Smart Inverter Integration
## Senior Design Project · CCNY Grove School of Engineering
### v2 (2026-07-06) — adds §20 binder-corrections + §21 build-manual pointer; semester structure clarified

**Semester structure (CONFIRMED by PM 2026-07-06):** Two-semester project.
- **Phase 1 — Senior Design I, Spring 2026 (Jan 25 – May 25):** inverter selection, mission
  definition, planning binder. DONE.
- **Phase 2 — Senior Design II, Fall 2026 (Aug 25 – Dec 20):** actual implementation — build the
  pipeline from scratch to working demo. **Final deadline: December 20, 2026.**
- Summer 2026 (now) is an optional head-start window; the 13-week timeline in §11 maps onto the
  Fall semester and any summer work pulls it left.

---

## 1. Project Identity

**Folder name:** VPP (Virtual Power Plant) — used for project folder only.

**Formal title for reports and presentations:**
> "Cloud-Based Middleware for Smart Inverter (SI) Interoperability between Vendor Clouds and VPP DERMS"

**Course:** EE 59868 Senior Design · Spring 2026
**Institution:** The City College of New York, Grove School of Engineering
**Team:** Team 2 — Cloud-to-Cloud (C2C) Integration (5 members)
**Counterpart:** Team 1 — Gateway team (hardware: RS-485, Modbus, Raspberry Pi)
This document covers **Team 2 only**.

**Mandatory terminology (professor's instruction):**
Always say **Smart Inverters (SIs)** — NEVER "DERs" or "DER".
The professor explicitly requires SIs as the correct term throughout.

---

## 2. Problem Statement & Project Objective

**Professor-approved framing:**
> The goal of this project is to address the interoperability problem between
> different vendor Smart Inverters (SIs), each with its own proprietary
> software and vendor-locked cloud server, and an external cloud server
> (VPP DERMS).

**Why interoperability is the core problem:**
Every SI manufacturer — SolarEdge, Fronius, Enphase, SolaX, GoodWe — runs
its own proprietary cloud with its own API format, authentication scheme, and
field names. A VPP DERMS operator aggregating data from thousands of SIs
across multiple vendors has no standard interface. Each vendor is a walled
garden. Our pipeline is the translation layer that breaks open those walls.

**What the pipeline does in one sentence:**
Pulls data from a vendor SI cloud via REST API → normalizes it to a standard
schema → publishes it to a neutral external cloud (VPP DERMS) via MQTT.

**Vendor-agnostic design principle:**
Switching from SolarEdge to any other SI vendor requires ONLY:
1. Swap Block 0 (point to different vendor API URL)
2. Update Block 3 field mappings (different vendor field names)
Nothing else changes. Blocks 1, 2, 4, 5 are 100% vendor-neutral.

---

## 3. The Two Possibilities

**Possibility A — Simulation (primary deliverable, zero hardware needed)**
- Block 0 = Python Flask mock server at `localhost:5000`
- Returns identical JSON to real SolarEdge API
- Solar bell-curve output: 0W at night, peaks ~5700W at solar noon
- Battery SOC rises/falls based on solar vs load balance
- Grid positive = importing, negative = exporting
- ±12% random noise simulates cloud cover; 5% chance of deep 30–60% dip
- 23 automated tests all passing
- This IS the complete, grade-worthy deliverable

**Possibility B — Real inverter (optional stretch goal)**
- Block 0 = `monitoringapi.solaredge.com` with real Site ID + API key
- SolarEdge has NO sandbox, NO demo API, NO test environment — confirmed
- Requires a commissioned SolarEdge installation with a registered site
- Minimum 8 solar panels + 8 SolarEdge power optimizers per string (hard requirement)
- Team 1 owns this hardware dependency — Team 2 is never blocked by it

**The complete switch (3 lines, no code changes):**
```bash
# .env — Possibility A (simulation)     # .env — Possibility B (real inverter)
API_BASE_URL=http://localhost:5000   →  API_BASE_URL=https://monitoringapi.solaredge.com
SITE_ID=demo_site_001               →  SITE_ID=<real_site_id_from_portal>
API_KEY=mock_key                    →  API_KEY=<key_from_Admin_Site_Access>
```

---

## 4. System Architecture — 4 Layers

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 — Physical hardware  (Team 1 ONLY — not Team 2)   │
│  Smart Inverter (SI) → RS-485 cable → USB-RS485 adapter    │
│  → Raspberry Pi 4B (4GB RAM, SixFab 4G LTE modem)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2 — Edge software on Raspberry Pi  (both teams)     │
│  Team 1: pymodbus script reads Modbus registers from SI    │
│  Team 2: REST polling script calls SI vendor cloud API     │
│  Both:   Paho MQTT publisher → same external broker        │
└─────────────────────────────────────────────────────────────┘
         ↑ Team 2 pulls from here        ↓ both publish here
┌──────────────────────┐     ┌───────────────────────────────┐
│  Layer 3             │     │  Layer 4 — External cloud /   │
│  SI Vendor cloud     │     │  VPP DERMS  (Team 2 output)  │
│  (Team 2 scope)      │     │                               │
│  SolarEdge cloud OR  │     │  AWS IoT Core MQTT broker     │
│  localhost:5000 mock │     │  → InfluxDB time-series DB    │
│  REST: /currentPower │     │  → Grafana dashboard          │
│  Flow, /overview,    │     │  ThingSpeak as hot-standby    │
│  /energy, /powerDet- │     │                               │
│  ails, /equipment    │     │  This is the neutral DERMS    │
└──────────────────────┘     └───────────────────────────────┘
```

---

## 5. Block Diagram — All 6 Blocks with Full Sub-unit Detail

### Block 0 — Data Source
**Owner: PM (Shaoqin) + Ali (Person 2)**
**The vendor-specific side — two modes, one ENV var apart**

**Sub-unit A: Mock server (primary)**
- Python Flask app, `localhost:5000`, ~200 lines
- Simulates SolarEdge API — returns identical JSON on same URL paths
- 5 endpoints: `/site/{id}/currentPowerFlow`, `/site/{id}/overview`,
  `/site/{id}/energy`, `/site/{id}/powerDetails`, `/equipment/{id}/list`
- Plus custom `/health` endpoint for pipeline health checks
- Solar output follows a Gaussian bell curve centered at 1:00 PM
- Active hours: 06:30–19:30; zero output outside these hours
- Battery SOC updates based on solar surplus/deficit over elapsed time
- Grid power goes negative when solar exceeds load (export to grid)
- Random ±12% noise; 5% chance of a 30–60% cloud dip per reading
- Auth guard: returns HTTP 401 if `api_key` parameter is missing
- Returns `_mock: {source: "mock_server"}` tag in every response
- **File:** `mock_server.py` — already built and delivered
- **Tests:** `test_mock_server.py` — 52 tests, all passing (full suite 69 as of 2026-09-26; always quote "full suite green", the count grows with every module)

**Sub-unit B: SolarEdge cloud (optional real inverter mode)**
- `monitoringapi.solaredge.com` — best-documented solar API publicly available
- API key generated in 30 seconds: Admin → Site Access → API Access
- Rate limit: 300 requests/day (hard cap) — paused at 280 by Block 1
- Data freshness: 15-minute resolution (inverter uploads every 15 min)
- Cellular modem on the Home Hub means cloud is always connected
- No sandbox — this is why mock server was built

### Block 1 — Authentication Module
**Owner: Gina (Person 3) — reassigned 2026-07-10 (Ali moved to non-coding role)**
**Sits between data source and polling engine; every request passes through here**

**Sub-unit A: API key handler**
- Reads API key from `.env` file via python-dotenv
- Injects as `api_key` URL parameter on every outbound HTTP GET
- In mock mode: any non-empty string works
- In real mode: must be the exact key from SolarEdge monitoring portal
- Key is NEVER hardcoded in source code — security requirement
- If key is missing or empty → returns HTTP 401 immediately

**Sub-unit B: Rate limit tracker**
- Maintains an in-memory counter of daily API requests
- Hard cap: 300 requests/day (SolarEdge limit)
- Pauses polling at 280 — 20-request safety buffer
- Counter resets automatically at UTC midnight
- Logs a warning when within 50 requests of the cap
- In mock mode: counter still runs (realistic behavior)

**Sub-unit C: Error handler**
- Catches HTTP 401 (unauthorized — wrong/expired key)
- Catches HTTP 429 (rate limit exceeded)
- Applies exponential backoff on 429: waits 1 min, 2 min, 4 min before retry
- On any failure: returns last cached valid value from Block 2 cache
- Adds `stale: true` flag so downstream blocks know data is not fresh
- Pipeline NEVER crashes — always returns something valid

### Block 2 — Polling Engine
**Owner: Gina (Person 3)**
**Asks the data source for new data on a regular schedule**

**Sub-unit A: Scheduler**
- Uses APScheduler or Python `schedule` library
- Fires every 5 minutes during daylight (06:30–19:30 local time)
- Completely stops overnight — no wasted rate limit quota on zero-watt readings
- Implemented as a cron job on the Raspberry Pi for production
- Daylight window is configurable via ENV variable

**Sub-unit B: Endpoint caller**
- Makes HTTP GET requests using Python `requests` library
- Three endpoints called per cycle:
  - `/currentPowerFlow` — live snapshot: solar W, grid W, battery W, load W, SOC
  - `/overview` — daily kWh total + lifetime kWh
  - `/energy?timeUnit=HOUR` — 24 hourly production slots for the day, in **Wh**
    (`timeUnit=DAY` returns ONE daily total, not hourly — see `docs/block0_contract.md` §6.3)
- Returns raw JSON exactly as received — no modification at this stage
- Request timeout: 10 seconds (avoids hanging the schedule)

**Sub-unit C: Cache manager**
- Stores last successful response per endpoint in memory (Python dict)
- Key: endpoint name; Value: {data, timestamp, stale: false}
- On poll failure: returns cached value with `stale: true` added
- Prevents Block 3 and downstream from ever receiving null/exception
- Cache is cleared on successful response (always serves freshest valid data)

### Block 3 — Data Normalizer
**Owner: Gina (Person 3) — owns Block 2 AND Block 3**
**The interoperability engine — translates vendor-specific to vendor-neutral**

**Sub-unit A: Field mapper**
SolarEdge-specific → Standard schema:
```
PV.currentPower (kW)             → solar_power_w       ×1000 → W
STORAGE.chargeLevel (%)          → battery_soc_pct     0–100
STORAGE.currentPower (kW, UNSIGNED) → battery_power_w  ×1000, sign from `connections` (+ charging / − discharging)
GRID.currentPower (kW, UNSIGNED)    → grid_power_w     ×1000, sign from `connections` (+ import / − export)
LOAD.currentPower (kW)           → load_power_w        ×1000 → W
overview.lastDayData.energy (Wh) → energy_today_kwh    ÷1000 (resets at local midnight)
overview.lifeTimeData.energy (Wh)→ energy_lifetime_kwh ÷1000 (cumulative)
```
**Sign comes from the `connections` array, never from `currentPower`** (corrected 2026-09-08,
`docs/block0_contract.md` §6.1 — the real API returns unsigned magnitudes):

| Connection present | Meaning |
|---|---|
| `{"from": "GRID", "to": "Load"}` | importing → `grid_power_w` positive |
| `{"from": "LOAD", "to": "Grid"}` | exporting → `grid_power_w` negative |
| `{"from": "PV", "to": "Storage"}` | charging → `battery_power_w` positive |
| `{"from": "Storage", "to": "Load"}` | discharging → `battery_power_w` negative |

Also adds: `utc_timestamp`, `site_id`, `data_source` (mock/live), `stale` flag

**Sub-unit B: Unit scaler**
- `currentPowerFlow` power values arrive in kW → multiply by 1000 → store as W
  (`overview.currentPower.power` is already in W — do not scale it again)
- Grid sign convention enforced from `connections`: positive = importing, negative = exporting
- This sign convention is critical — reading `currentPower` at face value makes the dashboard
  show import while the house exports
- Energy values arrive in **Wh** (`overview`, `energy`) → divide by 1000 → store as kWh

**Sub-unit C: Validator**
- Checks every field for null/missing → drops record, logs warning
- Range checks:
  - `solar_power_w`: 0 to 5700 W (Home Hub rated capacity)
  - `battery_soc_pct`: 0 to 100%
  - `grid_power_w`: ±10000 W (wide range for bidirectional)
  - `load_power_w`: 0 to 20000 W
- Records failing validation are dropped and logged
- All warnings written to `pipeline.log` and printed to console
- pytest tests cover: null fields, out-of-range values, wrong sign convention

### Block 4 — MQTT Publisher
**Owner: Matthew (Person 4)**
**Takes clean normalized JSON and sends to external cloud broker**

**Sub-unit A: Connection manager**
- Library: Eclipse Paho MQTT Python (`paho-mqtt`)
- Protocol: MQTT over TLS, **port 8883** (NOT 1883 — TLS required)
- Broker: AWS IoT Core (primary), ThingSpeak (hot-standby)
- AWS IoT requires 3 certificate files:
  - `certs/AmazonRootCA1.pem` (download from AWS)
  - `certs/device-cert.pem.crt` (from IoT Thing creation)
  - `certs/private.pem.key` (from IoT Thing creation)
- Keepalive: 60 seconds
- Auto-reconnect: on disconnect, waits 5s then reconnects with exponential backoff
- `on_connect` callback confirms connection and logs broker endpoint

**Sub-unit B: Topic router**
```
solar/site/power      ← solar_power_w      (live AC watts)
solar/battery/soc     ← battery_soc_pct   (state of charge %)
solar/grid/power      ← grid_power_w      (import +, export -)
solar/load/power      ← load_power_w      (household watts)
solar/site/energy     ← energy_today_kwh  (daily kWh)
```
- All messages published at QoS 1 (at-least-once delivery guaranteed)
- Broker acknowledges every message receipt
- Topic root `solar/` is configurable via `MQTT_TOPIC_ROOT` in `.env`

**Sub-unit C: Publish loop**
- `json.dumps()` serializes the normalized dict to string
- `client.publish(topic, payload, qos=1)` sends each field to its topic
- `on_publish` callback logs mid (message ID) on successful delivery
- Every publish attempt logged: topic, payload size, success/fail
- Failure to publish: logged, not raised — pipeline continues

### Block 5 — External Cloud + Dashboard
**Owner: Matthew (Person 4) = broker; Mahedi (Person 5) = DB + dashboard (re-split 2026-07-10)**
**The VPP DERMS side — where data lands and is visualized**

**Sub-unit A: MQTT broker**
- AWS IoT Core: free tier = 250,000 messages/month (far more than needed)
- IoT Rule: SQL `SELECT * FROM 'solar/#'` → routes all topics to InfluxDB
- ThingSpeak configured as hot-standby from Week 6 onward
- If AWS IoT Core is down: Block 4 connection manager switches to ThingSpeak
- ThingSpeak: free plan = 3M messages/year, no certs needed (simpler)
- Person 4 owns this sub-unit entirely

**Sub-unit B: Time-series database**
- InfluxDB (local install, free) preferred for Grafana integration
- ThingSpeak as alternative (hosted, simpler, fewer features)
- Each MQTT message → one InfluxDB measurement per field
- Tagged by: `site_id`, `data_source` (mock/live), `utc_timestamp`
- Retention: 30 days for demo purposes
- Grafana connects directly to InfluxDB via InfluxQL or Flux queries
- Person 5 owns this (setup + configuration; Person 4 advises on the IoT Rule hookup)

**Sub-unit C: Web dashboard**
- Grafana preferred (direct InfluxDB data source, no custom JS needed)
- Vue.js as alternative (more flexible, builds on prior semester pattern)
- 6 required panels:
  1. Live solar power chart — time-series, 0–6000W, 5-min refresh
  2. Battery SOC gauge — 0–100%, green >50%, amber 20–50%, red <20%
  3. Grid import/export — positive (red = buying), negative (green = selling)
  4. Household load — watts consumed
  5. Daily energy counter — kWh, resets midnight
  6. Inverter status badge — Active / Idle / Fault
- Dashboard demo sign-off: Mahedi shows PM (Shaoqin), PM approves
- Person 5 owns this sub-unit entirely

---

## 6. Team Members

Split by protocol (PM, 2026-09-20; source of truth = the "Pipeline & Assignments" tab of the
C2C Pipeline Build Guide doc). Supersedes the 2026-07-10 block-based split.

| Person | Lane | Files | Waiting on |
|---|---|---|---|
| **Shaoqin** | PM — contracts, repo, integration, gates | `docs/command_contract.md`, `src/adapter.py`, `src/adapter_factory.py`; purchases; weekly Ali checkpoint; pull soak + swap demo | nobody |
| **Gina** | REST (pull + mock-cloud push) | `src/auth.py`, `src/poller.py`, `src/normalizer.py`, `src/mock_cloud_adapter.py` + tests | nobody — `block0_contract.md` is done |
| **Matthew** | MQTT (publisher, broker, originator, Pi bridge) | `src/mqtt_publisher.py`, `src/mqtt_to_influx.py`, `src/command_originator.py`, `src/bridge_adapter.py`, `pi/bridge.py`, `pi/mock_inverter.py` | `command_contract.md` (week 1), Ali's register map (week 7) |
| **Mahedi** | Database + dashboard | InfluxDB bucket, Grafana dashboard JSON, `web/command.html`, command history panel | Matthew's IoT Rule (week 3), originator (week 8) |
| **Ali** | Data files, verification, evidence, demo (**non-coding**) | `docs/setup.md`, `register_maps/solaredge.json`, SMA credential request, `docs/evidence/` (soak + swap logs), demo lead | nobody |

---

## 7. Smart Inverter — direction set by the professor, model still open

**Professor's answer (Prof. Mohamed Ali, 2026-09-22):** to the question "direct push + poll over
REST/MQTT with no local hardware, or fully satisfy the 8-item requirements list?" he replied
*"Ok; if you can get pull and push directly that is fine."* → **Direct cloud pull + push is
approved.** Candidates are the three direct-push vendors, none of which meets all 8 items:

| Vendor | Push path | Known gap |
|---|---|---|
| SMA | REST (GridControl API) | RS-485 needs an aftermarket card; Modbus TCP/UDP only, no native RTU |
| Victron | MQTT (VRM cloud broker) | battery/off-grid architecture, not grid-tie; no RS-485 on Cerbo GX (Modbus TCP yes) |
| GoodWe | REST (Open API) | closest to SolarEdge/Fronius, usually RS-485 + Modbus — requirements fit and API access NOT yet verified |

**Still open:** which of the three; one shared unit with Team 1 or two (the 09-04 "buy what Team 1
bought" decision predates this and may conflict — Team 1 reads RS-485/Modbus, which SMA and
Victron lack natively); vendor sandbox/API credentials. SolarEdge/Fronius remain the only clean
8/8 fits and the local-write (Pi + Modbus) path stays built as the second adapter shape.

**What stays true regardless:** the mock server and Block 3's field map model the **SolarEdge**
monitoring API. Only the adapter files change per vendor (`INVERTER_VENDOR`, see
`docs/command_contract.md`).

*The original 2026-07 selection notes below are HISTORICAL — kept for the rationale, not a decision.
The Fronius "over budget" rejection used a stale number; the real budget is $700–1300.*


**Why selected:** Only inverter that scored 7/7 on all 7 project requirements AND
is available under budget (~$686 on US Solar Supplier vs ~$2,590 typical retail).

**7 requirements it passes:**
- R1 API credentials — instant from monitoring portal
- R2 WiFi/Ethernet — built-in Ethernet + cellular modem included
- R3 Enable third party — SetApp enables Modbus TCP + RS-485
- R4 REST API — best-documented solar API publicly available
- R5 RS-485 — two built-in RS-485 ports (use port 2 for Team 1)
- R6 Modbus register map — official SunSpec map, also on GitHub
- R7 Modbus RTU/TCP — both supported simultaneously

**Key specs:**
- 5.7kW single-phase hybrid (solar + battery + backup + EV charging)
- Cellular modem with 5-year plan included — no WiFi router needed
- SetApp commissioning (phone app — no LCD panel)
- **Modbus TCP port: 1502** (NOT standard 502 — Team 1 must hardcode this)
- Data freshness: 15-minute cloud upload cycle
- Minimum: 8 solar panels + 8 SolarEdge power optimizers per string
- Requirements score: 7/7

**Other inverters evaluated (rejected):**
- Fronius Primo 3.0-1: 7/7 but ~$600–$900 (over budget)
- SolaX X1-Boost 3K G4: 7/7 at $280–$380 (strong alternative)
- Growatt MIC/MIN/SPH series: 5–5.5/7 (API weaknesses)
- Solis S6-GR1P3K: 5/7 (no official REST API)

**SolarEdge API — no sandbox confirmed:**
Community and official sources confirm: without a real commissioned Site ID,
the API key returns nothing. This is why the mock server was built.

---

## 8. SolarEdge API Field Mappings (Block 3 reference)

`currentPowerFlow` powers arrive in **kW** → ×1000 to **W**. `overview`/`energy` energies arrive in **Wh** → ÷1000 to **kWh**. `overview.currentPower.power` is already **W**. Grid/storage direction comes from `connections` (see §5 Block 3).

| SolarEdge API field | Our standard field | Unit | Notes |
|---|---|---|---|
| `PV.currentPower` | `solar_power_w` | W | AC output; kW in API → ×1000 |
| `STORAGE.chargeLevel` | `battery_soc_pct` | % | 0–100 |
| `STORAGE.currentPower` | `battery_power_w` | W | unsigned in API; sign from `connections`: +charge/−discharge |
| `GRID.currentPower` | `grid_power_w` | W | unsigned in API; sign from `connections`: +import/−export |
| `LOAD.currentPower` | `load_power_w` | W | Consumption |
| `overview.lastDayData.energy` | `energy_today_kwh` | kWh | Wh in API → ÷1000; resets midnight |
| `overview.lifeTimeData.energy` | `energy_lifetime_kwh` | kWh | Wh in API → ÷1000; cumulative |
| `overview.currentPower.power` | `solar_power_w` | W | Already W in API — no scaling |

---

## 9. Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.10+ | All Team 2 scripts |
| Mock server | Flask | `pip install flask` |
| API client | requests | `pip install requests` |
| Scheduler | APScheduler | `pip install apscheduler` |
| Config | python-dotenv | `.env` file; never commit real keys |
| MQTT client | paho-mqtt | `pip install paho-mqtt`; TLS port 8883 |
| Cloud broker | AWS IoT Core | Free tier: 250k msgs/month |
| Fallback broker | ThingSpeak | Free: 3M msgs/year; no certs needed |
| Database | InfluxDB (local) | 30-day retention; Grafana-native |
| Dashboard | Grafana | Preferred; connects to InfluxDB directly |
| Dashboard alt. | Vue.js + MQTT.js | Prior semester pattern available |
| Testing | pytest | All normalizer tests must pass before Block 4 |
| Version control | GitHub | Private repo; GitHub Education Pack (free) |
| Project mgmt | MS Project | Instructor requirement; Gantt + network diagram |

---

## 10. Files Already Built

| File | Status | Description |
|---|---|---|
| `mock_server.py` | ✅ DONE | Flask mock, 5 endpoints, solar curve, battery+grid logic |
| `test_mock_server.py` | ✅ DONE | 52 tests — all passing (rebuilt 2026-09-08; contract = `docs/block0_contract.md`) |
| `.env.example` | ✅ DONE | All ENV variables documented |
| `C2C_MS_Project.xlsx` | ✅ DONE | 74-task MS Project import file |
| `gantt_chart.html` | ✅ DONE | Interactive Gantt, collapsible groups, 2026 dates |
| `network_diagram.html` | ✅ DONE | Interactive CPM network, ES/EF/LS/LF, minimap |
| `Network_Diagram.pptx` | ✅ DONE | Native PPT network diagram, 9 swim lanes, vector |
| `C2C_Block_Diagram.pptx` | ✅ DONE | 6-slide PPT block diagram with sub-units |
| `CloudToCloud_TechSpec.docx` | ✅ DONE | Full tech spec, 10 sections, SI terminology updated |
| `SKILL.md` | ✅ DONE | This context file |
| `auth.py` | ⏳ NEXT | Gina's Block 1 — not yet built |
| `poller.py` | ⏳ PLANNED | Gina's Block 2 |
| `normalizer.py` | ⏳ PLANNED | Gina's Block 3 |
| `mqtt_publisher.py` | ⏳ PLANNED | Matthew's Block 4 |

---

## 11. Project Timeline (Spring 2026, 13 weeks)

| Weeks | Phase | Owner | Milestone |
|---|---|---|---|
| 1–2 | Project setup + mock server | PM + Ali | GitHub repo, AWS provisioned, full suite green |
| 3–4 | Auth module + polling engine | Gina | auth.py done, poller.py vs mock |
| 5–6 | Normalizer + MQTT publisher | Gina + Matthew | pytest pass, messages in AWS IoT |
| 7–9 | Dashboard + Team 1 integration | Mahedi + Matthew | Dashboard live, both teams on broker |
| 10–13 | Testing, failure scenarios, docs, demo | All | 60-min test pass, report submitted |

**Critical path (21 tasks):**
`#7→#9→#10→#14→#15→#16→#24→#25→#26→#27→#28→#40→#41→#42→#43→#44→#45→#46→#60→#74`
Plain English: kick-off → build mock → commit → polling engine → MQTT publisher → integration test → submit.

**Float exists on:** Auth module (~3d), Normalizer, Dashboard.
Any delay on the critical path directly delays the project end date.

---

## 12. Key Decisions & Rationale

| Decision | Choice | Rationale |
|---|---|---|
| SI vendor (PoC) | Modelled: SolarEdge. Purchase: same unit as Team 1, open (§7) | Best-documented API → mock built against it; hardware waits on the professor |
| API strategy | Mock server primary; real API optional | No SolarEdge sandbox; mock returns identical JSON |
| Architecture | Simulation-first | Team 2 has zero hardware dependency; unblocks team from Day 1 |
| MQTT protocol | paho-mqtt over TLS port 8883 | IoT standard; AWS IoT Core native; lightweight vs HTTP |
| Cloud broker | AWS IoT Core + ThingSpeak fallback | Free tier; TLS security; IoT Rule to DB |
| Database | InfluxDB | Time-series native; Grafana integration; free |
| Dashboard | Grafana (preferred) | Direct InfluxDB source; no custom JS |
| Project mgmt | MS Project | Instructor requirement; Gantt + network diagram produced |
| Terminology | Smart Inverters (SIs) not DERs | Professor's explicit instruction |
| Inverter minimum | 8 panels + 8 optimizers | SolarEdge hard electrical requirement per string |
| Modbus TCP port | 1502 not 502 | SolarEdge non-standard — must be hardcoded everywhere |

---

## 13. Scope Control Rules

| Scenario | Response |
|---|---|
| Real SI unavailable | Mock server IS the deliverable — pipeline is complete |
| AWS IoT Core down | Switch Block 4 to ThingSpeak (pre-configured Week 6) |
| API rate limit hit | Serve last cached value + `stale: true` — never crash |
| SolarEdge API changes | Mock server insulates pipeline — only Block 0 affected |
| Team 1 hardware delays | Team 2 continues independently on simulation |
| Real inverter arrives | Change 3 lines in `.env` — done in 60 seconds |

---

## 14. Success Criteria

**Primary (required for passing grade):**
> Full pipeline (Block 0 → Block 5) runs end-to-end on simulated data
> for a continuous **60-minute period without manual intervention**.

**Stretch goal (not required):**
Switch `.env` to real SolarEdge API → live inverter data flows through
the same pipeline. This is a 60-second config change.

---

## 15. Functional Specifications

| # | Specification | Metric |
|---|---|---|
| F1 | Data latency | Mock: <1s; Real API: 15-min resolution (SI vendor limit) |
| F2 | Polling frequency | Every 5 minutes during daylight (06:30–19:30) |
| F3 | API rate limit compliance | Never exceed 280 req/day (hard stop at 280, limit is 300) |
| F4 | Pipeline uptime | >99% during 60-min test; auto-recovers from network drop |
| F5 | Data fields | 7 fields normalized per poll cycle |
| F6 | MQTT delivery | QoS 1 — at-least-once, broker-acknowledged |
| F7 | Dashboard refresh | Every 5 minutes (matches poll cycle) |
| F8 | Test coverage | 52 mock server tests + full pytest suite for every module (whole suite green in CI) |

---

## 16. Resilience Patterns Built In

| Pattern | Where | What it does |
|---|---|---|
| Rate limit counter | Block 1 | Pauses polling at 280/300 req/day; resets UTC midnight |
| Exponential backoff | Block 1 | On 429: waits 1min→2min→4min before retry |
| Last-value cache | Block 2 | Returns stale data with `stale:true` flag instead of crashing |
| Stale flag | Block 3 | Propagates through to MQTT payload so dashboard can show warning |
| Auto-reconnect | Block 4 | Reconnects to MQTT broker after network dropout |
| Hot-standby broker | Block 4 | Switches to ThingSpeak if AWS IoT Core unavailable |

---

## 17. Presentation Context (Chapter 2: Planning)

The project has been presented in a Chapter 2 Planning presentation. Ratings:

| Slide | Score | Key feedback |
|---|---|---|
| Chapter title | 6/10 | Add subtitle showing what chapter covers |
| Project objective | 8/10 | Clear; replace "entity" with "organization" |
| Functional specs | 8.5/10 | Strongest slide; measurable targets (1–5s latency) |
| Deliverables table | 8/10 | Good; strengthen demo video row |
| One-page summary | 9/10 | Best slide; font slightly small for back of room |
| Block diagram | 7/10 | Too dense for presentation; simplify for slides |
| Network diagram | 6.5/10 | Text unreadable at slide scale; split into 2 slides |

**Fixes before next presentation:**
1. Block + network diagrams need larger text or split across slides
2. Add explicit team roles/responsibility slide
3. Chapter title slide needs visual treatment

**Network diagram walkthrough script** (for professor Q&A):
- Row 1 (dark blue): Project Setup — kick-off feeds two parallel tracks
- Row 2 (blue): Block 0 — critical path runs through #9→#10→#14→#15→#16
- Row 3 (purple): Block 1 Auth — has float (~3 days), not on critical path
- Row 4 (amber): Block 2 Polling — ALL tasks red; entire row on critical path
- Row 5 (green): Block 3 Normalizer — has float; must complete before integration
- Row 6 (blue): Block 4 MQTT — ALL tasks red; second concentration of critical path
- Row 7 (teal): Block 5 Cloud+Dashboard — Matthew (broker) + Mahedi (UI)
- Row 8 (purple): Integration — 60-min test (#60) is the success gate
- Row 9 (gray): Documentation — parallel writing, converges at #74 Submit

---

## 18. Interview Pitch (30-second version)

*"For my senior design at CCNY I'm PM of a 5-person team building cloud-to-cloud
middleware for solar energy. The problem: every Smart Inverter manufacturer locks
data in their own proprietary cloud. A VPP operator can't aggregate across vendors.
We built the translation layer — a Python pipeline that pulls from the vendor REST
API, normalizes it to a standard schema, and publishes to AWS IoT Core via MQTT.
The whole system runs in simulation mode — no hardware needed — and switches to a
real inverter with one config file change."*

**Strongest talking points:**
- "SolarEdge has no sandbox, so we built one" — shows initiative
- Simulation-first = architectural decision, not a limitation
- Vendor-agnostic by design — adding a new SI vendor = 2 file changes only
- 52 automated tests on the mock server before anyone wrote the poller

**Numbers to always have ready:**
5 people · 5 blocks · 74 tasks · 52 mock-server tests · 13 weeks · 300 req/day limit ·
TLS port 8883 · 5-min polling · 60-min success criterion

---

## 19. Quick Reference — What to Say in New Chats

| What you want | What to say |
|---|---|
| Build auth.py | "Build the auth module for Block 1 — Gina's work" |
| Build poller.py | "Build the polling engine for Block 2 — Gina's work" |
| Build normalizer.py | "Build the data normalizer for Block 3 — Gina's work" |
| Build mqtt_publisher.py | "Build the MQTT publisher for Block 4 — Matthew's work" |
| Set up AWS IoT Core | "Set up AWS IoT Core broker for Block 5 — Matthew's work" |
| Set up InfluxDB | "Set up the InfluxDB time-series database for Block 5 — Mahedi's work" |
| Build Grafana dashboard | "Build the Grafana dashboard for Block 5 — Mahedi's work" |
| Update project docs | "Update the gantt chart / network diagram / tech spec" |
| Continue from here | "Load the SKILL.md context and continue the project" |
| Explain any block | "Explain Block X in detail" → refer to Section 5 |
| Who owns what | Refer to Section 6 team table |
| Next thing to build | `auth.py` (Gina, Block 1) — first unbuilt file |



---

## 20. Binder Corrections (v2) — THE binder.pdf contains errors; THIS FILE WINS

The Chapter 1–3 binder was partly written by teammates without full project context.
When any document disagrees with this skill, **the skill is authoritative**. Known binder errors:

| # | Binder error | Correct (per this skill) |
|---|---|---|
| B1 | Uses "DERs" everywhere incl. title | **Smart Inverters (SIs)** — professor's explicit rule (§1) |
| B2 | Hardware = "GTB400 microinverter" | Purchase open — same SI as Team 1; modelled platform SolarEdge (§7) |
| B3 | Pipeline uses "Firebase storage" | InfluxDB primary, ThingSpeak standby (§5 Block 5) |
| B4 | Mahedi=Cloud/MQTT, Matthew=Dashboard | RE-RESOLVED (PM, 2026-07-10): **Gina = Blocks 1+2+3; Matthew = Block 4 + Block 5 broker; Mahedi = Block 5 DB + dashboard; Ali = Block 0 verify + docs/QA/demo (non-coding)**. Correct the binder team table to match §6. |
| B5 | SolarEdge vendor listed with SolaX contact info | Copy-paste error — use real SolarEdge contacts |
| B6 | Raspberry Pi 3 Model B+ | Pi 4B 4GB, and it is Team 1 scope (§4 Layer 1) |
| B7 | "1–5 s latency" unqualified | Pipeline latency <5 s (ours) vs data freshness 15 min (SolarEdge upload cycle — vendor limit) |
| B8 | "$851 total, no other choice" vs $250 budget | Mock-first = $0 hardware required for Team 2 deliverable; inverter is optional stretch |
| B9 | EE 59866 SD-I + Dec 22 2026 target | RESOLVED: two semesters — Spring 2026 (Jan 25–May 25) planning ✓, Fall 2026 (Aug 25–**Dec 20**) implementation (see v2 header note) |
| B10 | "translate into IEEE 2030.5/OpenADR" | Normalize to standard schema **aligned with** IEEE 2030.5/SunSpec (mapping doc: docs/standards_mapping.md) — never claim "implements" |

## 21. Build Manual (v2)

The full step-by-step execution plan lives in **VPP_C2C_BUILD_MANUAL.md** (same folder as this
skill in Downloads; also ~/vpp_c2c/). Structure: Part 0 goal · Part 1 ratings+corrections ·
Part 2 AI-agent session workflow + Definition of Done · Part 3 Phases 0–10 (each with owner,
steps, acceptance criteria, and a ready-to-paste agent prompt) · Part 4 risk register ·
Part 5 session bootstrap card.

**Session pattern:** load this skill + state "Phase N, Step N.M" from the manual + your role.
**Current next action:** Phase 0, Step 0.2 — bootstrap the GitHub repo (0.1's conflicts were resolved by the PM on 2026-07-06).
