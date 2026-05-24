# Session Working Memory

> Overwritten at every named breakpoint (re-anchor rule — Error 25).
> Cleaned by `/session clean` at every stage gate close.
> Cannot be erased by context compression — always re-read at breakpoints.
> Backed by Mem0 (`pip install mem0ai`) for selective thread forgetting.

---

## Active primitives (Amendment 01)

<!-- Filled at session start from amendment_01_domain_primitives.md.
     Re-read at every named breakpoint. -->

(not yet loaded — run /session to populate)

---

## Locked constants this session

<!-- Updated as constants are established via Hearings or Stage gates.
     Format: `CONSTANT_NAME = value  # Traces to: [primitive] (Hearing H-NNN)` -->

(none yet)

---

## Current position

Stage: — | Step: — | Status: NOT_STARTED

---

## Open threads

<!-- Append-only within session. Mark resolved entries [RESOLVED] or [CLOSED].
     /session clean removes [RESOLVED]/[CLOSED] entries via Mem0 delete API:
       client.delete(filter={"status": "RESOLVED", "session": "<session_date>"})
     /session clean also prints: "Working memory cleaned — [N] threads removed." -->

(none)
