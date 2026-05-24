# Amendment 13 — Time-Domain Signal Validation Mandate
*Traces to: Article I*
*Status: PROPOSED — ratify before any signal model change*

A Bode plot or frequency-domain match does NOT validate a signal model.
After any change to `src/signals.py`, both of the following are required:
  1. A frequency-domain plot (Bode / transfer function — sensor model frequency response)
  2. A time-domain overlay: synthetic waveform vs real recorded waveform for at least
     one event type representative of the physical scenario being modeled

Human visual confirmation of the time-domain overlay is required before the change
may be committed. Frequency-domain validation alone does not justify a constant.

**Rationale:** Frequency-domain and time-domain models can diverge significantly for
non-linear transducers (PVDF, piezo cantilever, capacitive). A Bode match may hide
a time-domain amplitude or phase error. The specific failure pattern this closes:
a pilot-confirmed Bode match used to justify a linear scaling constant for a
non-linear PVDF transducer — the Bode match was real; the linear model was wrong;
the SVM classifier degraded silently because its input manifold shifted.

**What this means in practice:**
- `/plot profile` must generate both plot types before any `signals.py` commit
- Human review gate: "time-domain overlay confirmed" must appear in case_law.md
  (or hearing entry) before the commit is authorized
- Bode-only evidence in a Hearing brief is insufficient — attorney arguing for a
  `signals.py` change must present time-domain evidence as part of their case
