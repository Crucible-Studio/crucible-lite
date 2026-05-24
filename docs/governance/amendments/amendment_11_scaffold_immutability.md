# Amendment 11 — Scaffold Immutability
*Traces to: Article I + II*
*Status: PROPOSED — ratify before Stage 1 begins*

Project analysis modules (`src/events.py`, `src/analysis.py`, `src/plot.py`) are
generated exactly once — at the first execution of the stage that requires them
(Stage 1: Simulation) — by `/toolchain scaffold`.

After the human engineer and code-reviewer have confirmed the scaffolded modules
are correct (Article I compliant: all parsed fields trace to a domain primitive
declared in Amendment 1), those files are frozen. They must not be regenerated,
overwritten, or modified for the remainder of the project unless the human
explicitly authorizes a re-scaffold.

**What this means in practice:**

- `/toolchain scaffold` is blocked from running a second time without explicit human
  instruction. An agent must not invoke it silently during any session.
- Any change to `docs/device_context.md` Signal Inventory or
  `docs/toolchain_config.md` Firmware UART Format that would alter the scaffolded
  modules constitutes a change to the analysis pipeline and requires a **Bill**
  enacted through the Legislative Process before re-scaffolding is permitted.
- The code-reviewer must audit the scaffolded `src/` files at the Stage 1 Justice Gate
  as part of its Article I compliance check. Findings are resolved before the gate closes —
  not by silent re-generation.

**Rationale:** Regenerating scaffolded modules mid-project without governance is
identical in effect to changing firmware analysis logic without a Bill. It redefines
what the device measures, which violates Article I if the new definition has not been
traced to a domain primitive. It removes the human from a decision that changes
physical interpretation, which violates Article II.

**What happens without it:** An agent re-runs scaffold to "fix" a minor label,
silently changing a field name. The UART parser breaks on existing log files.
No one knows why Stage 3 field data no longer replays correctly.

**Amendment it complements:** Amendment 3 (Toolchain Alignment — the generated
modules are part of the analysis toolchain and are subject to the same alignment
discipline as firmware build tools).
