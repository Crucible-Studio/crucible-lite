# Amendment 7 — Calibration Discipline
*Traces to: Article I*
*Status: PROPOSED — ratify before any threshold is introduced in firmware*

One new calibration constant may be introduced per algorithmic iteration. Every
calibration constant must be documented with its physical derivation before the
session ends.

A constant derived from a physical measurement predicts its own correct value when
the operating conditions change. A tuned constant (fitted to observed data without
physical derivation) requires re-tuning at every hardware or population change.

Documentation format (inline in firmware source):
```
/* CONSTANT_NAME — derived from [domain primitive].
 * Physical derivation: [formula or measurement].
 * Value: [N] [unit].
 * Traces to: Amendment 1 primitive [N]. */
```
