# Mahedi — Database and dashboard: InfluxDB, Grafana, command page

You own where the data lands and what the audience sees: the InfluxDB bucket, the six Grafana panels, and in week 8 the page that sends a command plus the table that shows its history. You need none of Gina's or Matthew's code to start — write fake rows yourself in week 1 and build every panel against them.

## Step 0 · today

Clone [github.com/sqlhhh/vpp-c2c](https://github.com/sqlhhh/vpp-c2c), venv, `pip install -r requirements.txt`, `cp .env.example .env`, `pytest tests/ -v` → `58 passed`. In week 2 you also test-drive Ali's `docs/setup.md`: follow it cold and tell him every place you had to guess.

## Task 1 — InfluxDB up, fake rows in · by 2026-09-27

1. Install [InfluxDB 2.x OSS](https://docs.influxdata.com/influxdb/v2/install/) locally, open [http://localhost:8086](http://localhost:8086), create org `vpp`, bucket `solar_data`, retention 30 days, and an all-access token. Put the token in your `.env` as `INFLUX_TOKEN` (never in git).
2. Write fake telemetry so panels have something to show. Measurement `telemetry`, tags `site_id`, `data_source`, `stale`, one field per number. Line protocol for the contract's example reading:

```
telemetry,site_id=demo_site_001,data_source=mock,stale=false solar_power_w=4191.0,battery_power_w=3698.0,battery_soc_pct=55.0,grid_power_w=0.0,load_power_w=493.0,energy_today_kwh=27.7,energy_lifetime_kwh=12477.7 1757357777000000000
```

3. Write a small `scripts/fake_day.py` that generates one such line every 5 minutes for a whole day with a bell-shaped `solar_power_w` (0 at night, about 5000 at 13:00) and `grid_power_w` going negative when solar exceeds load. This is your development data until week 3.

**Done when:** `influx query 'from(bucket:"solar_data") |> range(start:-24h) |> filter(fn:(r)=> r._measurement=="telemetry") |> count()'` returns about 288 rows per field.

## Task 2 — Grafana and the six panels · by 2026-10-18

Install [Grafana OSS](https://grafana.com/grafana/download), add the InfluxDB data source (Flux, org `vpp`, bucket `solar_data`, your token). Dashboard refresh 5 min, time range last 24 h.

| # | Panel | Type | Field / rule |
| --- | --- | --- | --- |
| 1 | Live solar power | time series, 0–6000 W | `solar_power_w` |
| 2 | Battery SOC | gauge 0–100 % | `battery_soc_pct`; green > 50, amber 20–50, red < 20 |
| 3 | Grid import / export | time series, bars about zero | `grid_power_w`; positive red (buying), negative green (selling) |
| 4 | Household load | time series | `load_power_w` |
| 5 | Energy today | stat, kWh | last `energy_today_kwh` |
| 6 | Inverter status | stat with value mapping | **Active** if `solar_power_w` > 0 in the last 15 min; **Idle** if 0 between 19:30 and 06:30; **Fault** if `stale` is `true` or no row for 15 min |

**Worked example — the Flux query for panel 1** (copy it, then change the field name for panels 2–5):

```
from(bucket: "solar_data")
  |> range(start: v.timeRangeStart, stop: v.timeRangeStop)
  |> filter(fn: (r) => r._measurement == "telemetry" and r._field == "solar_power_w")
  |> filter(fn: (r) => r.site_id == "demo_site_001")
```

For panel 6 add `|> last()` and a value mapping: `0 → Idle`, `>0 → Active`; the `stale` tag drives the Fault colour.

**Done when:** all six panels show your fake day; then in week 3 switch nothing and they show Matthew's real rows (the fake rows have `data_source=mock` too, so add a dashboard variable `data_source` to tell them apart). Export the dashboard as JSON to `grafana/dashboard.json` and PR it — the dashboard is code, not a screenshot.

## Task 3 — The command page · by 2026-11-15

Grafana cannot send a `POST` on its own, so the command control is a small page of your own, embedded in the dashboard. Matthew's originator (`localhost:5001`, week 7) is what it calls; read `docs/command_contract.md` for the shape.

| Part | Detail |
| --- | --- |
| File | `web/command.html` — one page, no framework: a slider 0–100, the current value, a **Send** button, a result line |
| Send | `fetch("http://localhost:5001/command", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({command: "set_power_limit_pct", value: Number(slider.value)})})` |
| Result line | show `success`, `adapter` and `detail` from the response; red if `success` is false; show "DRY RUN" when `detail` is `dry_run` |
| Embed | Grafana **Text** panel in HTML mode with an `<iframe>` to the page, served by the originator at `GET /` (agree with Matthew), or opened in its own browser tab for the demo |

**Done when:** moving the slider to 60 and pressing Send shows `success: true · adapter: mock_cloud · detail: dry_run` with `DRY_RUN=1`, and the request appears in Matthew's log. Nothing else needs to be running for that test.

## Task 4 — Command history panel · by 2026-11-22

A Grafana **Table** panel on measurement `commands`, newest first, columns: time, `command`, `value`, `adapter`, `success`, `detail`. Colour the `success` cell green/red. This is the panel the audience watches during the swap demo: the same command with `adapter: mock_cloud` then `adapter: bridge`.

```
from(bucket: "solar_data")
  |> range(start: -7d)
  |> filter(fn: (r) => r._measurement == "commands")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 20)
```

**Done when:** Matthew's `curl` from his Task 3 adds a row to your table within one refresh.

## Task 5 — Sign-off

Show Shaoqin the dashboard twice: after Task 2 on real pipeline data (week 4), and after Task 4 with the command page (week 9). Ali's demo runbook uses your dashboard, so give him the exact URL and the panel order.

## Who is waiting on you

| Who | For | When |
| --- | --- | --- |
| Matthew | bucket, org, token (Task 1) so `mqtt_to_influx.py` has somewhere to write | week 2 |
| Ali | a cold run of `docs/setup.md` | week 2 |
| Shaoqin | six panels for the soak (week 5–6); history table for the swap demo (week 10) | |

You wait on Matthew for real rows (week 3) and for `POST /command` (week 8). Neither blocks Tasks 1–2.
