# Amendment 1 — Domain Primitives
*Traces to: Article I*
*Status: NOT YET RATIFIED — run /spec collect*

> This file is written by `/spec collect` after the human engineer reviews and ratifies
> the domain primitives for this specific project. Do not edit manually — run the command.

[Domain primitives will appear here after /spec collect is run and ratified.]

---

**What goes here after ratification:**

A numbered list of the first-order physically measurable quantities that govern every
threshold, parameter, and decision in this project's firmware and signal model.

Format:
```
1. Primitive Name (unit) — one-line physical definition.
2. Primitive Name (unit) — one-line physical definition.
...
```

Every constant in `src/signals.py`, `src/algorithm.py`, and firmware source must trace
to one of these primitives via an inline comment. A constant without a primitive citation
is an Article I violation — for agents AND for the human engineer.
