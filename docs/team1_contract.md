# Team 1 ↔ Team 2 interface contract

**Status: DRAFT — UNSIGNED.** Drafted 2026-09-08 by Team 2 (PM). Not in force until both leads
sign per §9.

| | Team 1 | Team 2 |
|---|---|---|
| Deliverable | Local gateway — reads the inverter over the wire | Cloud-to-cloud — reads the vendor's cloud |
| Transport in | RS-485 / Modbus RTU + Modbus TCP | HTTPS REST to the vendor monitoring API |
| Freshness | sub-second | **15 min, set by the vendor — not improvable by us** |
| Scale | one Pi per site, needs physical possession | one integration reaches every commissioned site |
| Lead | *TBD* | Shaoqin Li (`sqlhhh`) |

*Team 1 proves you can read a smart inverter. Team 2 proves you can read anybody's without
touching it.* Both publish to **one broker, one schema**, so the two readings of the same
hardware can be laid on one chart.

---

## 1. Why this document exists now and not in Week 7

The build manual slots this at Weeks 7–8. That is too late: Team 2's broker work (Matthew) is
already scheduled to start, and the moment either side hardcodes a topic name or a field name
the other side is retrofitting. **Nothing below is expensive to agree now and all of it is
expensive to change later.**

## 2. The broker

| | Value |
|---|---|
| Broker | AWS IoT Core, Team 2's account, ATS endpoint | 
| Endpoint | *TBD — Team 2 supplies after Phase 6.1* |
| Port / transport | 8883, MQTT over TLS 1.2, mutual auth (X.509) |
| Local fallback | Mosquitto on Team 2's laptop, port 1883, no TLS — **development only, never the demo** |

**Certificates: each team provisions its own.** Team 2 creates the AWS IoT Thing, certificate and
policy for Team 1 and hands over the cert, private key and root CA once. Neither team ever shares
a private key in the repo, in Slack, or in email — transfer in person or via the repo's
`certs/` directory, which is git-ignored. Team 1's policy is scoped to `gateway/*` only; Team 2's
to `solar/*` only. Neither can publish under the other's prefix, so a misconfigured client cannot
silently corrupt the other team's data.

## 3. Topics

```
solar/site/{site_id}/telemetry      Team 2  — vendor cloud reading
gateway/site/{site_id}/telemetry    Team 1  — Modbus reading
```

* `{site_id}` is the **same string for both teams** when both read the same physical inverter.
  This is the join key for the Phase 8.6 chart. Agreeing it is item 1 of §8.
* Dashboards subscribe `solar/#` and `gateway/#`.
* Prefixes are fixed. Anything after `.../telemetry` is that team's business.

## 4. Message format

UTF-8 JSON, one object per reading. **Identical schema both sides** — only `data_source` differs.

```json
{
  "site_id": "demo_site_001",
  "data_source": "live",
  "utc_timestamp": "2026-09-08T18:56:17Z",
  "stale": false,
  "solar_power_w": 4191.0,
  "battery_power_w": 3698.0,
  "battery_soc_pct": 55.0,
  "grid_power_w": -302.0,
  "load_power_w": 493.0,
  "energy_today_kwh": 27.7,
  "energy_lifetime_kwh": 12477.7
}
```

| Field | Type | Unit | Required | Notes |
|---|---|---|---|---|
| `site_id` | string | — | yes | same value both teams for the same inverter |
| `data_source` | string | — | yes | Team 2: `mock` or `live` (per `SKILL.md` §5). Team 1: `modbus_gateway` |
| `utc_timestamp` | string | ISO-8601 `Z` | yes | **UTC always.** Time of the *reading*, not of publishing |
| `stale` | bool | — | yes | true = cached value re-served after a fetch failure |
| `solar_power_w` | number | W | yes | AC output |
| `battery_power_w` | number | W | no | **+ charging, − discharging**; omit if no battery |
| `battery_soc_pct` | number | % 0–100 | no | omit if no battery |
| `grid_power_w` | number | W | yes | **+ importing, − exporting** |
| `load_power_w` | number | W | yes | household consumption |
| `energy_today_kwh` | number | kWh | yes | resets at local midnight |
| `energy_lifetime_kwh` | number | kWh | yes | cumulative |

**Rules that are not negotiable once signed:**

1. **Power in watts, energy in kilowatt-hours.** No kW power fields, no Wh energy fields. Both
   vendors' raw APIs mix these; converting is each team's own job before publishing.
2. **The sign conventions above.** Getting `grid_power_w` backwards makes the joint chart show
   the two teams disagreeing about which way the power is flowing — which looks like a data bug
   in the defense and is really just a convention mismatch.
3. **`utc_timestamp` is UTC.** New York is UTC−4 in September and UTC−5 after 1 November. A local
   timestamp puts the two curves 4 hours apart on the Phase 8.6 chart, and the DST change would
   move them mid-semester.
4. **Absent ≠ zero.** Omit a field you cannot measure. Publishing `0` for an unmeasured battery
   makes the dashboard draw a flat line that looks like real data.
5. Unknown extra fields must be **ignored, not rejected**, by any subscriber.

## 5. QoS and delivery

| | Value |
|---|---|
| QoS | **1** (at least once) both directions |
| Retain | **false** — a retained stale reading would repopulate the dashboard after a restart and look live |
| Publish interval | Team 2: 5 min (vendor refreshes every 15, so 3 of 4 are unchanged). Team 1: *TBD, propose 5 min for the joint run* |
| Last Will | Each team sets an LWT on `{prefix}/site/{site_id}/status` with `{"online": false}`; publish `{"online": true}` on connect |
| Duplicates | QoS 1 permits redelivery. Subscribers must tolerate a repeated `utc_timestamp` |

## 6. What Team 2 owes Team 1

* AWS IoT endpoint, Thing, certificate, private key, root CA, and the `gateway/*` policy.
* This document, and any change to it, before it takes effect.
* Notice that **Team 2 runs its own Raspberry Pi** for the push path (`pi/bridge.py`, writes one
  Modbus register on command). It is a separate unit from Team 1's Pi: ours only *writes*, theirs
  only *reads*. Neither Pi is wired to the inverter without the lab-tech sign-off in
  `command_contract.md` §4.
* Two facts from our vendor research, useful regardless of what we sign:
  * **RS-485 is on port 2**, not port 1.
  * **Modbus TCP is on port 1502**, not the standard 502.

## 7. What Team 1 owes Team 2

* The answers in §8.
* Confirmation of their publish interval and their `site_id` string.
* Notice before changing their field names — the Phase 8.6 dashboard queries them by name.

## 8. Open questions — the agenda for the first joint meeting

These are Team 2's blockers, in priority order. Item 3 is the one that can quietly sink us.

1. **Which inverter model was bought?** Decides whether our path ever sees non-zero watts, and
   which vendor cloud API Block 0 is swapped to in Phase 9. → `SKILL.md` §7 still says
   "SolarEdge Home Hub USE5700H" and must be rewritten to match reality.
2. **One physical unit shared, or two units of the same model?** One shared unit is what makes
   Phase 8.6 meaningful — two acquisition paths, one device, and the gap between the curves
   *measures* vendor cloud latency. Two units means two devices in different light and
   temperature, the curves never match, and the joint demo degrades to two graphs sharing a
   screen.
3. **Is the unit commissioned and registered in the vendor's cloud portal?** ⚠ **Chase this
   hardest.** Team 1 needs only the wire and is unblocked the moment the inverter is powered.
   **Team 2 needs a commissioned Site ID or the vendor API returns nothing at all** — not an
   error, just an empty site. If Team 1 racks it, wires it and never commissions it, they are
   done and we are blocked by a step no one currently owns.
4. Who is Team 1's lead, and who signs this? *(Team 2: Shaoqin Li.)*
5. Do they agree to publish to our broker, or do they want their own with a bridge?
6. Target date for the first joint run on the shared broker.

## 9. Signing

Both leads sign by committing an edit to this file that adds their name, GitHub handle and date
to the table below. **The commit is the signature** — no separate document.

| Team | Lead | GitHub | Date signed |
|---|---|---|---|
| Team 2 (Cloud-to-Cloud) | *unsigned* | | |
| Team 1 (Gateway) | *unsigned* | | |

Amendments follow the same route: a PR editing this file, approved by both leads. Neither team
changes a topic, a field name, a unit or a sign convention without one.
