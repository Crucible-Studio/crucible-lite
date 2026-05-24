# Amendment 4 — Three-Strike Escalation Rule
*Traces to: Article II*
*Status: PROPOSED — ratify by removing this line*

If a simulation, unit test, hardware smoke test, or iterative fix process fails to meet
exit criteria within three attempts, the agent must stop, report the full status to the
human, and wait for a human determination before any further action.

The three-strike report must include:
  1. What was attempted on each of the three tries
  2. What was observed on each attempt (exact output, not a summary)
  3. What the agent does not know — the open question that a human must answer

The agent must not propose a fourth approach without explicit human direction.

**Rationale:** Continuing past three failures compounds work debt and masks the root
cause. Three-strike reports also function as input to Judicial Hearings when the
failure pattern suggests a design conflict rather than a bug.
