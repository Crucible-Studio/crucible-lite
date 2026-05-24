# Amendment 12 — Corpus Supremacy
*Traces to: Article I + II*
*Status: PROPOSED — ratify before Stage 1 begins*

The Layer 2 corpus files (`src/signals.py`, `src/algorithm.py`) encode the project's
physical model. They are governed by the corpus record, not by agent judgment alone.

No change to Layer 2 may be committed without a Judicial Hearing entry in
`docs/governance/case_law.md` (or `docs/governance/hearings/`) that:
  1. Was adjudicated by Attorney-A and Attorney-B (both sections present)
  2. Records a Justice ruling (ruling section present)
  3. Explicitly names the file(s) being changed

A Hearing entry that is missing any of these three sections is an informal ruling
and does not satisfy this amendment. The `corpus.py` pre-commit check enforces this.

Layer 4 ephemeral files (`src/events.py`, `src/analysis.py`, `src/plot.py`) must not
be edited directly — they must be regenerated from a corpus change.
