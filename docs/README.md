# docs/

What belongs here, and which phase produces it.

| File | Phase | Owner | Purpose |
|---|---|---|---|
| `block0_contract.md` | 1 | Ali | Frozen mock-server interface: 5 endpoints + `/health`, exact JSON per endpoint, auth behaviour. Gina codes Blocks 1–3 against this, so it must not change silently. |
| `standards_mapping.md` | 4b | Shaoqin + Gina | Our 7 schema fields ↔ IEEE 2030.5 resources ↔ SunSpec model 103 points, with section citations. This document is what backs the "aligned with" claim. |
| `team1_contract.md` | 6b | Shaoqin + Matthew | Team 1 publishes to the same broker under `gateway/site/...` with the same schema and `data_source: "modbus_gateway"`. Both leads sign by commit. |
| `soak_test_runbook.md` | 8 | Shaoqin | Start commands, the pass/fail checklist, and the four failure-drill scripts. |
| `demo_runbook.md` | 10 | Ali | Pre-flight, the 8-minute script, and the fallback if the live demo dies. |
| `grafana_dashboard.json` | 7 | Mahedi | Exported dashboard, so it survives any one laptop. |
| `evidence/` | all | everyone | Screenshots, logs and test output captured **as they happen**. The binder's results chapter is assembled from this, not written from memory. |
