# Session Checkpoint

> Overwritten at each named breakpoint by the session orchestrator.
> Read at session start by /session (Step 0 — Resume check).
> Do not edit manually mid-session — let the orchestrator manage this file.

stage: 0
step: ""
status: NOT_STARTED
last_action: ""
next_action: ""
open_threads: []
session_date: ""
session_started: ""

---

## Status values

- `NOT_STARTED` — no session has run yet
- `IN_PROGRESS` — session is active; resume check will offer to restore
- `PAUSED` — human ran `/session pause`; next_action is the resume point
- `COMPLETE` — stage gate was closed cleanly; no resume needed
