# Amendment 10 — Interim Results and Decision Logging
*Traces to: Article II*
*Status: PROPOSED — ratify before any multi-step iterative session*

During any iterative build-debug process, intermediate results must be printed to
the terminal for human review. The agent waits for a human determination before
proposing the next action.

The specific human decision must be recorded in `docs/governance/case_law.md` or
the relevant stage record before the session ends.

**Rationale:** Prevents the most common failure mode in agentic development — an
agent runs five sub-steps autonomously, encounters an anomaly in step 2, compensates
in step 3, and delivers a result in step 5 that looks correct but carries a hidden
assumption no human ever approved.
