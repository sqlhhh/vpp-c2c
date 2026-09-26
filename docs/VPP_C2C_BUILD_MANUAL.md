# VPP Cloud-to-Cloud Pipeline — Complete Build Manual
### From project setup to working demo · Step-by-step, AI-agent-ready
*Prepared 2026-07-06 for Shaoqin Li (PM). Source of truth: `vpp-c2c-context` SKILL.md. Binder used as reference only (contains errors — see Part 1).*

---

# PART 0 — Your Goal (figured out, stated plainly)

**The mission:** By the Senior Design final deadline (**Dec 20, 2026** — end of Fall semester), deliver a
**vendor-agnostic cloud-to-cloud middleware pipeline** that pulls Smart Inverter (SI) data from a
vendor cloud (mock SolarEdge first, real optional), normalizes it to a standard schema, publishes
it over MQTT/TLS to a neutral VPP DERMS cloud (AWS IoT Core → InfluxDB → Grafana), and
**survives a 60-minute unattended end-to-end run** — plus binder/presentation materials that
survive professor scrutiny, and an interview-grade story for your resume.

**The three simultaneous deliverables you are actually managing:**
1. **The working system** (code, cloud, dashboard) — graded on the 60-min test.
2. **The paper trail** (binder chapters, Gantt, network diagram, test evidence) — graded continuously.
3. **The team** (4 engineers with clear handoffs) — your PM execution is itself being graded.

**Non-goals (say these out loud whenever scope creeps):** no grid control commands, no
IEEE 2030.5 *server* implementation (mapping documentation only — see Phase 4), no dependency
on Team 1 hardware for anything Team 2 is graded on.

---

# PART 1 — Rating of the Current Setup & Required Corrections

## 1.1 Scores

| Asset | Score | Verdict |
|---|---|---|
| SKILL.md context file | **9/10** | Excellent: precise architecture, ownership, decisions, pitch. Missing: repo layout/URL, session workflow, semester dates conflict with binder. |
| Binder (THE binder.pdf) | **6/10** | Ch1 research is solid, but it contradicts the skill on hardware, storage, roles, terminology, and specs (below). Fix before any professor re-read. |
| Project design itself | **8.5/10** | Simulation-first + vendor-agnostic blocks is genuinely strong senior-design architecture. Gaps: standards claim vs implementation, no CI, no Team 1 interface contract, latency spec worded wrong. |

## 1.2 Binder errors to correct (against SKILL.md = source of truth)

| # | Binder says | Should say (per skill) | Where |
|---|---|---|---|
| B1 | "DERs / Distributed Energy Resources" throughout, incl. the TITLE | **Smart Inverters (SIs)** — professor's explicit instruction | Everywhere; retitle: "…Interoperability and Protocol Translation of **Smart Inverters**" |
| B2 | Hardware = "GTB400 microinverter" | **Purchase open** — professor approved direct cloud pull+push 2026-09-22 (SMA/Victron/GoodWe); modelled platform SolarEdge (SKILL.md §7) | Ch2 Project Scope (p.16) |
| B3 | Pipeline includes "Firebase storage" | **InfluxDB** (ThingSpeak standby) | Ch2 Project Scope (p.16) |
| B4 | Mahedi = Cloud & MQTT lead; Matthew = Dashboard | RE-RESOLVED (PM, 2026-07-10): **Gina = Blocks 1+2+3 (auth+poller+normalizer); Matthew = Block 4 + Block 5 broker (AWS IoT Core); Mahedi = Block 5 DB + dashboard (InfluxDB + Grafana); Ali = Block 0 verify + docs/QA/presentation (non-coding)**. Fix binder Ch3 team table. |
| B5 | SolarEdge vendor contact = SolaX email/phone/website | Real SolarEdge contact info (copy-paste error) | Ch3 vendors (p.28) |
| B6 | Raspberry Pi 3 Model B+ | Skill says **Pi 4B 4GB** (and it's Team 1's item anyway — mark as Team 1 scope) | Ch3 parts list |
| B7 | "target latency 1–5 seconds" unqualified | Split into: **pipeline latency** (poll→dashboard, <5 s achievable) vs **data freshness** (real SolarEdge uploads every 15 min — vendor limit, not ours) | Ch2 specs |
| B8 | Budget table: $250 budget, $851.35 total, "we have no other choice" | Reframe: **mock-first architecture means $0 hardware required for Team 2's deliverable**; inverter is optional stretch owned by Team 1 budget discussion | Ch3 budget |
| B9 | Course EE 59866 / completion Dec 22, 2026 vs skill "EE 59868 Spring 2026, 13 weeks" | RESOLVED: Spring 2026 (Jan 25–May 25) = planning ✓ · Fall 2026 (Aug 25–**Dec 20**) = implementation | Skill §1/§11 + binder |
| B10 | Goal says "translate into IEEE 2030.5 / OpenADR" | Implementation normalizes to a **custom JSON schema**. Fix the *claim*: "normalized schema **aligned with IEEE 2030.5 / SunSpec field definitions** (mapping table in appendix)" + do Phase 4b below | Ch1 goal + Ch2 scope |

**Priority: B1 (terminology) and B10 (standards claim) are professor-facing landmines. Fix first.**

## 1.3 Design gaps the plan below fixes

| Gap | Fix | Phase |
|---|---|---|
| No repo/branch/CI convention | GitHub repo layout + Actions CI running pytest on every push | 0 |
| No local broker for dev | Mosquitto local first, AWS IoT after — decouples Block 4 dev from cloud setup | 5 |
| IEEE 2030.5 claim unbacked | Standards mapping table (schema field ↔ 2030.5 resource ↔ SunSpec point) | 4b |
| No Team 1 interface contract | One-page shared MQTT topic + schema contract, signed by both teams | 6b |
| No failure-drill evidence | Scripted kill-tests with logged recovery (matches skill §16 patterns) | 8 |
| 60-min test undefined in detail | Soak-test script + pass/fail checklist + evidence capture | 8 |
| No demo-day script | Demo runbook with pre-flight checklist and fallback narrative | 9 |

---

# PART 2 — Operating System for the Project (how to use this manual)

## 2.1 The AI-agent workflow (how you'll actually execute)

Every work session, whoever is working (you or a teammate) does this:

1. **Bootstrap the session** — paste into the AI agent:
   > Load skill: vpp-c2c-context. We are on Phase N, Step N.M of the build manual.
   > My role is [PM/Ali/Gina/Matthew/Mahedi]. Repo state: [paste `git log --oneline -5`].
   > Today's goal: [step name]. Constraints: Python 3.10+, no new dependencies without PM approval,
   > all code must pass existing pytest suite.
2. **Work the step** using the step's "Agent prompt" below as the opening instruction.
3. **Gate before merge:** the step's Acceptance Criteria must ALL pass — paste the actual
   terminal output into the PR description as evidence.
4. **Close the loop:** update the skill's §10 file-status table and §19 "next thing to build"
   so the next session bootstraps correctly. Commit as `docs: skill status update`.

## 2.2 Cadence & PM rituals (you, weekly)

- **Mon:** 15-min standup — each member states: last week's acceptance criteria passed? this week's step? blockers?
- **Wed:** async check — post `git log` diff + CI status to the group chat.
- **Fri:** PM merges approved PRs, updates Gantt %-complete, logs risks.
- **Every meeting with professor:** bring (a) the block diagram, (b) live demo of the latest passing block, (c) one decision you want ratified — never arrive without an ask.

## 2.3 Definition of Done (applies to every code step)

- [ ] Code in repo on a feature branch → PR → reviewed by one other member → merged to `main`
- [ ] pytest suite green locally AND in CI
- [ ] `.env.example` updated if any new ENV var
- [ ] Runbook line added: how to start/stop/verify the component in 1 command
- [ ] Skill §10 table updated

---

# PART 3 — The Build Plan, Phase by Phase

> Timeline (confirmed): Fall implementation semester = **Aug 25 – Dec 20, 2026**. Summer (now)
> is a head-start window. Each phase lists: Owner · Effort · Steps · Acceptance Criteria · Agent
> prompt. Phases 0–8 are the graded pipeline. 9–10 are demo/docs. Stretch items marked ★.
>
> **Calendar mapping (fall-only pace · summer head start moves everything left):**
>
> | Fall weeks | Dates | Phases |
> |---|---|---|
> | Wk 1–2 | Aug 25 – Sep 7 | 0 repo/CI/corrections · 1 mock verify |
> | Wk 3–4 | Sep 8 – Sep 21 | 2 auth · 3 poller |
> | Wk 5–6 | Sep 22 – Oct 5 | 4 normalizer + standards mapping · 5 MQTT publisher (local) |
> | Wk 7–8 | Oct 6 – Oct 19 | 6 AWS IoT + InfluxDB + Team 1 contract |
> | Wk 9–10 | Oct 20 – Nov 2 | 7 Grafana dashboard |
> | Wk 11–12 | Nov 3 – Nov 16 | 8 integration + 60-min soak + failure drills |
> | Wk 13–14 | Nov 17 – Nov 30 | 9 ★ real-inverter stretch · buffer for slippage |
> | Wk 15–16 | Dec 1 – Dec 20 | 10 binder results chapters, slides, demo rehearsals, submit |
>
> **PM note:** anything you and the team knock out this summer (recommended: Phases 0–2, they
> need no cloud accounts and no team coordination) converts Fall buffer into safety margin.

---

## PHASE 0 — Ground Truth & Repo Bootstrap (PM · 1–2 days)

**Goal:** one repo, one environment recipe, CI, corrected documents. Everything after this
builds on a clean foundation.

**Steps:**
0.1 **Open conflicts — RESOLVED (PM, 2026-07-06):**
   - B4: Gina = Blocks 1+2+3, Matthew = Block 4 + IoT Core, Mahedi = InfluxDB + dashboard, Ali = docs/QA (binder Ch3 table to be corrected in 0.5).
   - B9: Spring 2026 (Jan 25–May 25) = planning ✓ done · Fall 2026 (Aug 25–Dec 20) = implementation.
   Announce both to the team at the next standup so everyone works from the same map.
0.2 **Create the GitHub repo** (private, GitHub Education):
   ```
   vpp-c2c/
   ├── src/                    # all pipeline code
   │   ├── mock_server.py      # (move existing file here)
   │   ├── auth.py             # Phase 2
   │   ├── poller.py           # Phase 3
   │   ├── normalizer.py       # Phase 4
   │   ├── mqtt_publisher.py   # Phase 5
   │   └── pipeline.py         # Phase 8 (main entry point)
   ├── tests/                  # test_mock_server.py (move here) + one test file per block
   ├── certs/                  # .gitignored — AWS IoT certs live here locally
   ├── docs/                   # standards_mapping.md, team1_contract.md, runbook.md
   ├── .env.example            # every ENV var documented, no real values
   ├── .gitignore              # .env, certs/, __pycache__, *.log
   ├── requirements.txt        # flask, requests, apscheduler, python-dotenv, paho-mqtt, pytest
   └── .github/workflows/ci.yml
   ```
0.3 **CI in 20 minutes** — `.github/workflows/ci.yml`: on push/PR → set up Python 3.10 →
   `pip install -r requirements.txt` → `pytest tests/ -v`. Badge in README.
0.4 **Migrate existing assets** — `mock_server.py`, `test_mock_server.py`, `.env.example` into
   the layout above; run the full suite; first green CI run.
0.5 **Apply binder corrections B1–B10** (delegate the retyping; you review). Terminology pass:
   global replace of DER→SI language in every live document, INCLUDING the title.
0.6 **Branch protection:** `main` requires PR + 1 review + green CI.

**Acceptance criteria:**
- [ ] `git clone && pip install -r requirements.txt && pytest` → full suite green on a teammate's machine (69 as of 2026-09-26)
- [ ] CI badge green on README
- [ ] Corrected binder v2 saved; conflicts B4/B9 resolved and reflected in skill
- [ ] All 5 members have repo access and have cloned it

**Agent prompt:**
> Load skill vpp-c2c-context. Phase 0: create the repo skeleton exactly per the manual layout,
> write .github/workflows/ci.yml for pytest on Python 3.10, write .gitignore and requirements.txt,
> and migrate mock_server.py + tests. Do not modify mock server logic — the 52 mock-server tests must stay green.

---

## PHASE 1 — Block 0 Verification: Mock Server (Ali · 0.5 day — it exists, verify it)

**Goal:** re-validate the already-built mock server inside the new repo, and lock its contract.

**Steps:**
1.1 Run the suite: `pytest tests/test_mock_server.py -v` → 52/52.
1.2 Manual smoke: `python src/mock_server.py` then
   `curl "localhost:5000/site/demo_site_001/currentPowerFlow?api_key=x" | python -m json.tool`
   — verify solar bell curve value plausible for current time of day; verify 401 without key.
1.3 **Write the contract doc** `docs/block0_contract.md`: the 5 endpoints + `/health`, exact JSON
   shape per endpoint, the `_mock` tag, auth behavior. This is what Gina codes the poller against
   — it freezes the interface so Blocks 1–3 never break if mock internals change.
1.4 ★ Add `/health` endpoint if missing (uptime, request count) — trivially useful in Phase 8.

**Acceptance criteria:**
- [ ] 52/52 mock-server tests green in CI
- [ ] `block0_contract.md` merged — Gina has read and acknowledged it
- [ ] Bell-curve sanity: 0 W at 22:00, >3000 W at 13:00 (screenshot into docs/evidence/)

**Agent prompt:**
> Load skill vpp-c2c-context §5 Block 0. Verify mock_server.py against the 52 tests, then write
> docs/block0_contract.md documenting every endpoint's exact JSON schema with one real response
> example each. Flag any mismatch between code behavior and skill §5 description.

---

## PHASE 2 — Block 1: Authentication Module `auth.py` (Gina · 2–3 days)

**Goal:** every outbound request passes through one module that injects the key, counts requests,
and never lets a failure crash the pipeline. (Skill §5 Block 1 is the spec — follow it exactly.)

**Design (single class, ~150 lines):**
```python
class AuthSession:
    def __init__(self):        # reads API_KEY, API_BASE_URL, SITE_ID from .env
    def get(self, path, params=None) -> AuthResult:
        # 1. rate check: if self.count >= 280 → return cached/refusal, log warning
        # 2. inject api_key param; requests.get(timeout=10)
        # 3. 200 → count += 1, return (json, stale=False)
        # 4. 401 → log CRITICAL (bad key), return (last_cached, stale=True)
        # 5. 429 → exponential backoff 60s/120s/240s (max 3), then cached+stale
        # 6. Timeout/ConnectionError → cached + stale=True
    def _reset_if_new_utc_day(self):   # counter reset at UTC midnight
```
**Steps:**
2.1 Write `src/auth.py` per the skeleton + skill §5 Block 1 sub-units A/B/C.
2.2 Write `tests/test_auth.py` (mock `requests` with `responses` lib or monkeypatch):
   - key injected on every call · 401 path → stale cache · 429 path → backoff sequence called
   - counter stops at 280 · counter resets on UTC day change · timeout → stale, no exception
2.3 Integration check against the live mock server: 5 real GETs, count == 5.
2.4 Wire a `RATE_LIMIT_MAX` ENV (default 280) — testability + real-mode flexibility.

**Acceptance criteria:**
- [ ] ≥8 pytest cases green (the 6 above minimum)
- [ ] Demo: kill mock server mid-run → auth returns stale cache, logs warning, **process does not exit**
- [ ] No API key string appears anywhere in repo (`git grep -i api_key` shows only ENV reads)

**Agent prompt:**
> Load skill vpp-c2c-context §5 Block 1. Build src/auth.py per the AuthSession skeleton in the
> manual Phase 2: dotenv key injection, 280/300 rate counter with UTC-midnight reset, exponential
> backoff on 429 (60/120/240s), last-value cache with stale flag on all failure paths. Then write
> tests/test_auth.py covering the 6 listed cases with mocked HTTP. Never raise to caller.

---

## PHASE 3 — Block 2: Polling Engine `poller.py` (Gina · 2–3 days)

**Goal:** scheduled data collection through `AuthSession`, with the in-memory cache that
guarantees downstream blocks always receive data.

**Design:**
```python
class Poller:
    ENDPOINTS = {          # per skill §5 Block 2 sub-unit B
      "power_flow": "/site/{site_id}/currentPowerFlow",
      "overview":   "/site/{site_id}/overview",
      "energy":     "/site/{site_id}/energy?timeUnit=DAY",
    }
    def poll_once(self) -> dict:   # {"power_flow": {...}, "overview": {...}, "energy": {...}}
        # calls AuthSession.get per endpoint; on failure per-endpoint cached value w/ stale
    def start(self, callback):     # APScheduler: every POLL_INTERVAL_MIN (default 5)
        # only within DAYLIGHT_START..DAYLIGHT_END (default 06:30-19:30, ENV-configurable)
```
**Steps:**
3.1 Write `src/poller.py` — scheduler + endpoint caller + cache manager (skill §5 Block 2 A/B/C).
3.2 `tests/test_poller.py`: poll_once returns all 3 keys · endpoint failure → cached+stale for
   that endpoint only · outside daylight window → scheduler idle · callback fired with dict.
3.3 **Dev-mode interval**: `POLL_INTERVAL_SEC` override (e.g. 10 s) so demos/tests don't wait 5 min.
3.4 Run 15 minutes against the mock at 10 s interval → log shows ~90 successful cycles.

**Acceptance criteria:**
- [ ] pytest green (≥6 cases) in CI
- [ ] 15-min live run log committed to docs/evidence/ (cycles, zero exceptions)
- [ ] Kill mock mid-run → poller continues with stale cache, resumes on mock restart **without operator action**

**Agent prompt:**
> Load skill vpp-c2c-context §5 Block 2. Build src/poller.py per the manual Phase 3 skeleton,
> using auth.AuthSession for all HTTP. APScheduler, daylight window from ENV, POLL_INTERVAL_SEC
> dev override, per-endpoint last-value cache. Then tests/test_poller.py per the listed cases.
> The callback receives the combined dict — that is Block 3's input contract.

---

## PHASE 4 — Block 3: Data Normalizer `normalizer.py` (Gina · 2–3 days)

**Goal:** the interoperability engine — vendor JSON in, standard schema out. This block IS the
thesis of the project; its tests are your strongest grading evidence.

**Steps:**
4.1 Write `src/normalizer.py` implementing skill §8 field map exactly:
   - kW→W ×1000 · grid sign convention (+import/−export) · add `utc_timestamp`, `site_id`,
     `data_source` (mock/live from the `_mock` tag), propagate `stale`
   - Validator: null → drop record + `pipeline.log` warning; range checks per skill §5 Block 3 C
     (solar 0–5700 W, SOC 0–100, grid ±10 000 W, load 0–20 000 W)
4.2 `tests/test_normalizer.py` — the skill demands these explicitly: null fields, out-of-range,
   wrong sign; plus: kW→W math exact, all 7 fields present, stale propagation, timestamp is UTC ISO-8601.
4.3 **Golden-file test:** capture one real mock response → commit as fixture → assert normalizer
   output byte-stable. Catches accidental schema drift forever after.

**4b — Standards Alignment (PM + Gina · 1 day · fixes binder gap B10):**
4.4 Write `docs/standards_mapping.md`: a table mapping each of the 7 schema fields ↔ IEEE 2030.5
   resource (e.g. `solar_power_w` ↔ 2030.5 `MirrorMeterReading` active power) ↔ SunSpec point
   (e.g. model 103 `W`). Cite the standard section numbers. ~1 page.
4.5 Update binder/slides language: "normalized schema **aligned with** IEEE 2030.5 and SunSpec
   field definitions (see mapping table)" — never claim "implements IEEE 2030.5".
   ★ Optional stretch: `to_ieee2030_5()` emitter producing 2030.5-shaped XML/JSON for one reading —
   only if Fall schedule has slack; the mapping doc alone closes the claim gap.

**Acceptance criteria:**
- [ ] pytest green (≥10 cases incl. the 3 skill-mandated ones + golden file)
- [ ] Chained demo: mock → poller → normalizer prints valid schema dicts each cycle for 10 min
- [ ] `standards_mapping.md` merged; binder claim language updated (B10 closed)

**Agent prompt:**
> Load skill vpp-c2c-context §5 Block 3 + §8. Build src/normalizer.py: exact field map from §8,
> kW→W, grid sign convention, validator with the §5 range checks, stale/data_source propagation.
> tests/test_normalizer.py must cover null/out-of-range/wrong-sign plus a golden-file fixture.
> Separately draft docs/standards_mapping.md mapping our 7 fields to IEEE 2030.5 resources and
> SunSpec model 103 points with section citations.

---

## PHASE 5 — Block 4: MQTT Publisher `mqtt_publisher.py` (Matthew · 3–4 days)

**Goal:** normalized JSON → MQTT topics with QoS 1, TLS, auto-reconnect. Local broker first so
this phase never waits on AWS.

**Steps:**
5.1 **Local Mosquitto first** (Docker: `docker run -p 1883:1883 eclipse-mosquitto` or WSL install).
   `MQTT_MODE=local` (localhost:1883, no TLS) vs `MQTT_MODE=aws` (endpoint + certs, port 8883).
5.2 Write `src/mqtt_publisher.py` per skill §5 Block 4:
   - Connection manager: paho-mqtt, keepalive 60, auto-reconnect 5 s + exponential backoff,
     `on_connect`/`on_publish` logging
   - Topic router: the 5 topics from skill §5 (root from `MQTT_TOPIC_ROOT`, default `solar/`)
   - Publish loop: `json.dumps` → publish QoS 1 → log mid; failures logged, never raised
5.3 `tests/test_mqtt_publisher.py`: topic routing correct per field · payload is valid JSON with
   all keys · publish failure → logged not raised (mock the client).
5.4 Verify with **MQTT Explorer** (binder's own tool): subscribe `solar/#` on local broker, run
   mock→poller→normalizer→publisher for 10 min, watch 5 topics update per cycle. Screenshot → evidence.

**Acceptance criteria:**
- [ ] pytest green in CI
- [ ] MQTT Explorer screenshot: all 5 topics with live values, timestamps advancing
- [ ] Broker kill-test: stop Mosquitto 60 s mid-run → publisher reconnects and resumes **unattended**

**Agent prompt:**
> Load skill vpp-c2c-context §5 Block 4. Build src/mqtt_publisher.py with paho-mqtt: MQTT_MODE
> local (1883 plain) / aws (8883 TLS with 3 cert paths from ENV), the 5-topic router from the
> skill, QoS 1, auto-reconnect with backoff, on_connect/on_publish logging. Failures log-only.
> tests/test_mqtt_publisher.py with a mocked client. Target local Mosquitto first.

---

## PHASE 6 — Block 5a: Cloud Broker + Database (Matthew: AWS IoT Core · Mahedi: InfluxDB · 3–4 days)

**Goal:** AWS IoT Core live, IoT Rule → InfluxDB, ThingSpeak standby. The pipeline's landing zone.

**Steps:**
6.1 **AWS IoT Core setup** (console, ~1 hr): create Thing `vpp-c2c-pipeline` → generate certs
   (download all 3: root CA, device cert, private key → `certs/`, verify .gitignored) → attach
   policy allowing `iot:Connect/Publish` on `solar/*` → note the ATS endpoint.
   Free-tier sanity: 5-min polling × 5 topics ≈ 43 k msgs/month « 250 k limit. ✓
6.2 Switch publisher to `MQTT_MODE=aws` → verify messages in **AWS IoT console MQTT test client**
   subscribed to `solar/#`. Screenshot → evidence.
6.3 **InfluxDB local install** (v2.x, free): org `vpp`, bucket `solar_data`, 30-day retention.
6.4 **Bridge AWS → InfluxDB.** Simplest robust route for the demo: a small `src/mqtt_to_influx.py`
   subscriber (paho) that subscribes `solar/#` on AWS IoT and writes points to InfluxDB
   (tags: `site_id`, `data_source`, `stale`; field per topic). ~60 lines, testable, no AWS Rules
   engine complexity. ★ Stretch: replace with IoT Rule + Lambda/Timestream if time allows —
   document the trade-off either way (good report material).
6.5 **ThingSpeak standby** (skill §13): create channel, map the 5 fields, `MQTT_MODE=thingspeak`
   path in publisher. 30-min setup, do it now not Week 12.

**6b — Team 1 interface contract (PM + Matthew · half a day):**
6.6 Write `docs/team1_contract.md`: Team 1 publishes to the SAME broker under `gateway/site/...`
   topics with the SAME normalized schema + `data_source: "modbus_gateway"`. One page: topics,
   schema, QoS, who provisions their cert. Both team leads sign (commit message = signature).
   This is what makes the joint demo work in Fall — agree on it before either side hardcodes.

**Acceptance criteria:**
- [ ] AWS IoT test client shows live `solar/#` traffic (screenshot)
- [ ] `influx query` returns rows with correct tags for a 10-min run
- [ ] ThingSpeak channel receives data when `MQTT_MODE=thingspeak` (screenshot)
- [ ] `team1_contract.md` merged, acknowledged by Team 1 lead

**Agent prompt:**
> Load skill vpp-c2c-context §5 Block 5 sub-units A+B. Walk me through AWS IoT Core Thing+cert+
> policy setup for topics solar/*, then build src/mqtt_to_influx.py: paho subscriber on solar/#
> writing to local InfluxDB v2 bucket solar_data with tags site_id/data_source/stale. Include a
> --dry-run flag printing points instead of writing. Then the ThingSpeak fallback mapping.

---

## PHASE 7 — Block 5b: Grafana Dashboard (Mahedi · 3–4 days)

**Goal:** the 6 professor-facing panels, live against InfluxDB.

**Steps:**
7.1 Grafana local install → add InfluxDB data source (Flux, org `vpp`, bucket `solar_data`).
7.2 Build the 6 panels per skill §5 Block 5 C — exact spec:
   1. Solar power time-series (0–6000 W, 5-min refresh) · 2. Battery SOC gauge
   (green >50 / amber 20–50 / red <20) · 3. Grid ± bar (red import / green export) ·
   4. Load W · 5. Daily kWh counter · 6. Inverter status badge (map: recent data = Active,
   stale flag = Fault, night = Idle)
7.3 **Stale-data visibility:** panel or annotation driven by the `stale` tag — this showcases the
   resilience story in the demo ("watch the dashboard flag stale data when we kill the mock").
7.4 Export dashboard JSON → commit to `docs/grafana_dashboard.json` (reproducible on any machine).
7.5 Sign-off demo to PM (skill's stated gate: Mahedi shows, PM approves).

**Acceptance criteria:**
- [ ] All 6 panels live-updating through a full mock day-cycle (time-lapse or 3 screenshots: morning/noon/night)
- [ ] Stale indicator visibly fires during a mock-kill test
- [ ] Dashboard JSON in repo; fresh Grafana import reproduces it
- [ ] PM sign-off recorded (commit or chat log)

**Agent prompt:**
> Load skill vpp-c2c-context §5 Block 5 sub-unit C. Help me build the 6 Grafana panels against
> InfluxDB bucket solar_data (Flux queries): exact thresholds/colors per the skill. Then a stale-
> data annotation from the stale tag. Output each panel's Flux query so I can paste them, and
> finally export instructions for grafana_dashboard.json.

---

## PHASE 8 — Integration & the 60-Minute Soak Test (ALL · 1 week)

**Goal:** the graded success criterion — Block 0→5 for 60 continuous unattended minutes — plus
scripted failure drills proving skill §16's resilience patterns actually work.

**Steps:**
8.1 Write `src/pipeline.py` — the single entry point: starts poller with the
   normalize→publish callback chain; `--interval-sec` override; structured logging to `pipeline.log`.
8.2 **Dress rehearsal at 10 s interval for 30 min** (fast-forward soak, catches leaks/drift early).
8.3 Fix whatever broke. Repeat until clean.
8.4 **THE 60-MIN TEST** (5-min real interval): checklist —
   - [ ] Start: mock, pipeline, mqtt_to_influx, Grafana open, `pipeline.log` tailing
   - [ ] Hands off keyboard for 60 min (record screen — this video IS deliverable evidence)
   - [ ] Pass = 12/12 poll cycles published & visible in Grafana, zero unhandled exceptions,
         zero manual interventions
   - [ ] Archive: log file + Influx row-count query + video → `docs/evidence/soak_YYYY-MM-DD/`
8.5 **Failure drills** (each scripted, logged, screenshotted — 1 hr total):
   | Drill | Expect (skill §16) |
   |---|---|
   | Kill mock 2 min mid-run | stale cache serves, stale flag on dashboard, auto-recovery |
   | Kill Mosquitto/AWS connectivity 1 min | publisher backoff → reconnect, no loss after resume (QoS 1) |
   | Set RATE_LIMIT_MAX=3 artificially | polling pauses at cap, warning logged, resumes at UTC reset (simulate) |
   | Feed malformed JSON via mock hack | normalizer drops + logs, pipeline continues |
8.6 ★ Joint run with Team 1 on the shared broker per `team1_contract.md` (both `solar/#` and
   `gateway/#` visible in one Grafana view) — the money shot for the final presentation.

**Acceptance criteria:**
- [ ] 60-min soak PASSED with archived evidence (log + video + DB counts)
- [ ] 4/4 failure drills documented with logs/screenshots
- [ ] ★ Joint-broker screenshot if Team 1 ready

**Agent prompt:**
> Load skill vpp-c2c-context §14+§16. Build src/pipeline.py chaining poller→normalizer→publisher
> with structured logging, then write docs/soak_test_runbook.md: exact start commands, the pass/
> fail checklist from manual Phase 8.4, and the 4 failure-drill scripts with expected log lines.

---

## PHASE 9 — ★ Stretch: Real Inverter Mode (Matthew + PM · only if Team 1 hardware lands)

Per skill §3 Possibility B — pipeline is complete without this. If the SolarEdge site materializes:
9.1 Generate API key (portal: Admin → Site Access → API Access), fill real `.env` (never commit).
9.2 The 3-line `.env` switch → run Phase 8's soak at 15-min effective freshness.
9.3 Language for report: "identical pipeline, zero code changes, config-only cutover" — measure and
   report the actual end-to-end latency (poll→dashboard) to back the corrected B7 spec claim.

---

## PHASE 10 — Documentation, Presentation & Demo Day (ALL · final 2–3 weeks)

**Steps:**
10.1 **Binder final chapters:** testing methodology (Phase 8 evidence), results (soak + drills),
   updated diagrams. Reuse `docs/evidence/` verbatim — you generated the proof as you built.
10.2 **Presentation fixes from skill §17:** split block+network diagrams across slides (they scored
   6–7/10 for density), add team-roles slide, retitle per B1. Target: every slide readable from
   the back of the room (skill's own feedback).
10.3 **Demo runbook** `docs/demo_runbook.md`:
   - Pre-flight (T-30 min): mock up, pipeline up, Grafana on projector, MQTT Explorer on second
     screen, phone hotspot as network backup
   - Script (8 min): problem (30 s) → architecture on block diagram (90 s) → LIVE: watch a poll
     cycle land in Grafana (2 min) → kill the mock live, show stale flag + recovery (2 min — the
     applause moment) → numbers slide (52 mock-server tests, 60-min soak, QoS 1, 74 tasks) (60 s) → Q&A
   - Fallback: if live demo dies, play the 60-min soak video — rehearse the pivot sentence.
10.4 **Interview asset for each member:** one paragraph each "what I built, what broke, what I'd
   do differently" — feeds resumes (yours routes to the resume automation).

**Acceptance criteria:**
- [ ] Binder v2 submitted (all B1–B10 corrections + results chapters)
- [ ] Slide deck revised per §17 feedback; dry-run presented to the team once
- [ ] Demo runbook rehearsed end-to-end twice, including the fallback path

---

# PART 4 — Risk Register (PM reviews every Friday)

| # | Risk | L×I | Mitigation | Trigger → Response |
|---|---|---|---|---|
| 1 | AWS account/billing snag | M×M | Free-tier audit in Phase 6.1; ThingSpeak standby ready | Broker unreachable 1 day → flip MQTT_MODE=thingspeak |
| 2 | Teammate stalls on a block | M×H | Each block has tests + contract doc → anyone can take over; PM tracks weekly | 2 missed standups → PM pairs or reassigns |
| 3 | Team 1 hardware never arrives | H×L | Possibility A is the deliverable by design | Ignore — never blocked |
| 4 | Scope creep (control commands, more vendors) | M×M | Part 0 non-goals; PM says "post-demo backlog" | Any new-feature ask → backlog, not sprint |
| 5 | Windows/WSL dev-env divergence | M×M | requirements.txt + CI is the arbiter; Docker for Mosquitto/Influx if needed | "works on my machine" → reproduce in CI |
| 6 | Professor challenges standards claim | M×H | Phase 4b mapping doc + corrected language | Question in review → open standards_mapping.md |
| 7 | Demo-day network failure | L×H | Local-mode fallback (Mosquitto+Influx+Grafana all local); soak video | Live demo fails → video + pivot sentence |

---

# PART 5 — Session Bootstrap Card (print this / pin in group chat)

```
── EVERY AI SESSION STARTS WITH ──────────────────────────────
Load skill: vpp-c2c-context (v2).
Manual: VPP_C2C_BUILD_MANUAL.md, Phase <N>, Step <N.M>.
Role: <name/block>.  Repo: <git log --oneline -3>.
Goal today: <step title>.
Rules: Python 3.10+, pytest must stay green, no new deps
without PM, secrets only in .env (never committed).
──────────────────────────────────────────────────────────────
Definition of Done: code on branch → PR + review + green CI →
evidence pasted in PR → skill §10 status table updated.
```

**Current next action (as of 2026-07-06):** Phase 0, Step 0.2 — bootstrap the GitHub repo.
(0.1 resolved 2026-07-10: Gina=auth+poller+normalizer, Matthew=MQTT+IoT Core, Mahedi=InfluxDB+Grafana, Ali=docs/QA/presentation; Fall build semester Aug 25 – Dec 20.)
