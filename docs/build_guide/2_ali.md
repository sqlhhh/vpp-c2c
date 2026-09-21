# Ali — Setup, data files, evidence, demo

You own the things that prove the pipeline works: the setup page everyone follows, the register table the Pi bridge writes to, the SMA request, the evidence logs, and the final demo. No adapter or pipeline code is on your list. Six tasks, **one at a time, in this order**. Each ends the same way: send Shaoqin the file, he ticks it at your weekly 15-minute checkpoint, then you start the next one.

**If anything on this page does not work:** stop, copy the whole error message (not a screenshot of part of it), paste it to Shaoqin, and wait. Do not try random fixes. Being stuck for 30 minutes is the limit.

## Task 1 — Be the first teammate to run the repo · by 2026-09-27

Nobody except Shaoqin has cloned the repo. The project's Phase 0 closes when *someone else's* machine shows all tests passing. That someone is you.

**Before you start:** install [Git](https://git-scm.com/downloads) and [Python 3.10 or newer](https://www.python.org/downloads/). On Windows, tick "Add python.exe to PATH" in the installer. Send Shaoqin your GitHub username so he can add you to the private repo.

**Steps (type each line, press Enter, read the output before the next):**

```bash
git clone https://github.com/sqlhhh/vpp-c2c.git
cd vpp-c2c
python -m venv .venv
```

Then activate the virtual environment — this line differs by system:

```bash
.venv\Scripts\activate          # Windows (PowerShell or cmd)
source .venv/bin/activate       # Mac or Linux
```

Your prompt now starts with `(.venv)`. If it does not, stop and send Shaoqin the screen. Then:

```bash
pip install -r requirements.txt
copy .env.example .env          # Windows;  Mac/Linux: cp .env.example .env
pytest tests/ -v
```

**What the screen must show at the end:**

```
======================== 58 passed in 0.71s ========================
```

The time will differ. The number must be **58** and the word must be **passed**. Any `failed` or `error` → copy the whole output to Shaoqin.

**Deliverable:** a screenshot of that last line saved as `docs/evidence/phase0_ali_2026-09-XX.png` (put the real date in the name). Send it to Shaoqin. Do not push to GitHub yet; he will show you that at the checkpoint.

**Done when:** Shaoqin ticks it. This single screenshot closes Phase 0 for the whole team.

## Task 2 — Request SMA sandbox credentials · by 2026-09-27

SMA runs a free developer sandbox (a fake solar plant on their servers). We want to know two things: can we get credentials, and does their **GridControl** API (the part that *sends commands*) work in the sandbox, or only the monitoring part. You send the request; you do not write any code with the answer.

1. Go to the [SMA Developer Portal](https://developer.sma.de/) and find the sandbox / "API access" request page or the developer support email.
2. Send this, filling in your name:

```
Subject: Sandbox API access request - CCNY student project

Hello SMA Developer Support,

I am a student on a senior design team at The City College of New York.
We are building a vendor-neutral integration layer that reads Smart Inverter
data over REST and sends control commands back. We would like sandbox
access to evaluate SMA's API.

Two questions:
1. Can we obtain sandbox client credentials (client id / secret) for
   the Monitoring API?
2. Is the GridControl API (setting a feed-in / active power limit)
   available in the sandbox, or only against a real plant?

Thank you,
<your name>, CCNY Senior Design Team 2
```

3. Create `docs/evidence/sma_request.md` with three lines: date sent, address sent to, and "reply: none yet". Update the third line when a reply arrives, and forward the reply to Shaoqin the same day.

**Done when:** the email is sent and `sma_request.md` exists. Ticked at the checkpoint.

## Task 3 — Write `docs/setup.md` · by 2026-10-04

You just did Task 1 with no help page. Write that page so the next person needs no help either.

**Contents, in this order:** what to install (with the two links above); the clone / venv / activate / pip / `.env` / pytest steps exactly as you typed them, both Windows and Mac lines; what the screen shows when it works; the three mistakes you made or nearly made and how you fixed them; and how to run the mock server on its own (`python src/mock_server.py`, then open [http://localhost:5000/health](http://localhost:5000/health) in a browser and paste the JSON you see).

**Done when:** Mahedi follows the page on his machine without asking you or Shaoqin a single question, and gets `58 passed`. If he had to ask, add the answer to the page and try again.

## Task 4 — `register_maps/solaredge.json` · by 2026-11-01

When the professor picks a SolarEdge or Fronius inverter, our Raspberry Pi will send commands by writing numbers into the inverter's **Modbus registers** — numbered mailboxes inside the inverter. Matthew's bridge code needs to know which mailbox does what. That table is your file. It is a data file, not code, and Matthew's mock inverter loads it in week 7.

**Source:** Shaoqin will hand you the SolarEdge PDF *"Power Control Open Protocol for SolarEdge Inverters"*. Every number in your file comes from that PDF, page number noted.

**Shape of the file** (three registers are enough for v1; the addresses below are what we *expect* from the PDF — confirm each one and put the page number in `source_page`):

```json
{
  "vendor": "solaredge",
  "modbus_tcp_port": 1502,
  "unit_id": 1,
  "registers": {
    "advanced_power_control_enable": {
      "address": 61762, "hex": "0xF142", "type": "int32", "writable": true,
      "default": 0, "note": "must be 1 before any limit is accepted", "source_page": 0
    },
    "active_power_limit_pct": {
      "address": 61441, "hex": "0xF001", "type": "uint16", "writable": true,
      "min": 0, "max": 100, "default": 100, "unit": "%", "source_page": 0
    },
    "commit_power_control_settings": {
      "address": 61696, "hex": "0xF100", "type": "int16", "writable": true,
      "note": "write 1 to save settings to inverter memory", "source_page": 0
    }
  }
}
```

Replace every `"source_page": 0` with the real page. If the PDF disagrees with an address above, **the PDF wins** — change the number and tell Shaoqin which one differed.

**Done when:** Shaoqin checks all three addresses against the PDF at the checkpoint and the file opens without error at [jsonlint.com](https://jsonlint.com/).

## Task 5 — Evidence logs for the two gates · soak by 2026-11-01, swap demo by 2026-12-04

The grade rests on a 60-minute unattended run. Your log is the proof it happened. Create `docs/evidence/soak_2026-XX-XX.md` from this template and fill it in **during** the run, not after:

```markdown
# Pull soak - <date>
Operator: Ali        Start (local): HH:MM       End: HH:MM
/health request_count at start: ___    at end: ___   (expect +12, one poll per 5 min)

| Time | Grafana screenshot file | stale:true seen? | Notes |
| --- | --- | --- | --- |
| +0 min  | soak_00.png | no | |
| +15 min | soak_15.png | no | |
| +30 min | soak_30.png | no | |
| +45 min | soak_45.png | no | |
| +60 min | soak_60.png | no | |

Manual interventions during the run: none / <describe>
Result: PASS / FAIL
```

For the swap demo in week 10, the same idea: one file, two rows (`INVERTER_VENDOR=mock_cloud`, `INVERTER_VENDOR=bridge`), each with the `curl` command Matthew gives you, the response it printed, and a screenshot of the command-history panel.

**Done when:** both files are in `docs/evidence/` with every cell filled and every screenshot present.

## Task 6 — Demo lead · by 2026-12-04

You run the live demo at the defense. Write `docs/runbook.md`: the exact list of clicks and commands, in order, with what the audience should see after each. Rehearse it twice with Shaoqin in week 11. If any step needs a teammate, name them in the runbook.

## Your calendar

| Week | Dates | You |
| --- | --- | --- |
| 1 | Sep 21–27 | Task 1 (repo runs), Task 2 (SMA email) |
| 2 | Sep 28–Oct 4 | Task 3 (setup.md), Mahedi tests it |
| 3–6 | Oct 5–Nov 1 | Task 4 (register map); soak log in week 5–6 |
| 7–10 | Nov 2–29 | on call for Matthew's questions about the register map; swap-demo log week 10 |
| 11–13 | Nov 30–Dec 20 | Task 6 (runbook), two rehearsals, the demo |
