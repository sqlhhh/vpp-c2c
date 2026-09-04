# src/

One module per block. Nothing here yet — Block 0 is the gate.

Before writing any module, read its section in the build manual (Phase 2 for `auth.py`,
Phase 3 for `poller.py`, and so on). Each phase carries the design skeleton, the required
test cases, and the acceptance criteria you will be reviewed against.

Two rules that apply to every module in this directory:

- **Never raise to the caller.** Every failure path returns a value and logs. The 60-minute
  unattended run is the graded criterion, and one uncaught exception ends it.
- **Read configuration from `.env` only** — never a hardcoded key, host, or interval.
