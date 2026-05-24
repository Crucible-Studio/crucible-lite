# Crucible Amendments

All amendments derive from Article I (Physics First) and/or Article II (Human in the Loop)
in CONSTITUTION.md. The governing Articles are unconditional and cannot be amended.

Amendment 1 is always the Domain Primitives amendment — written by `/spec collect` for
each specific project. Amendments 2–4 are mandatory framework amendments ratified here.
Amendments 5 onwards are domain-agnostic operational amendments included as defaults;
ratify them by removing the PROPOSED prefix. Project-specific amendments (signal plot
mandate, statistical derivation rules, etc.) are added after Amendment 1 is ratified.

---

## Mandatory Framework Amendments

These three must be ratified before /session 0 on any Crucible project.
They are pre-written here — read, confirm they are correct for your project,
then remove the PROPOSED prefix to ratify.

---

### Amendment 2 — Stage Gate Order
*Traces to: Article I + II*
*Status: PROPOSED — ratify by removing this line*

Development proceeds through exactly these stages in order, and no stage begins
until the previous stage's exit criteria are explicitly confirmed by the human:

  Spec Gate → Stage 0 (HIL Toolchain Lock) → Stage 1 (Simulation) →
  Stage 2 (Firmware Integration) → Stage 3 (Field Test) → Stage 4 (Host Integration)

An agent must not begin Stage N+1 work while Stage N has any open failure, even one
that appears unrelated to the next stage's work. Each stage's errors become
exponentially more expensive to fix in later stages. Hardware is a validation tool,
not a debugging tool.

**Exit criteria for each stage are defined in `/session`.**
**Stage closeout is executed by `stage-compactor`.**

---

### Amendment 3 — Toolchain Alignment
*Traces to: Article II*
*Status: PROPOSED — ratify by removing this line*

Every agent working on this project must operate within the toolchain that is currently
active and recorded in `docs/toolchain_config.md`. No agent may introduce a new
toolchain, framework, or build system without a Bill enacted through the Legislative
Process. Switching toolchains mid-stage is not permitted — it requires a new stage gate.

The active toolchain record in `docs/toolchain_config.md` is the single source of truth
for all build, flash, and test operations. An agent that silently switches from the active
toolchain to a different one violates Article II regardless of whether the output compiles.

A blocked toolchain may only be re-activated by explicit human decision at a stage gate,
recorded in toolchain_config.md with a date and reason.

---

### Amendment 4 — Three-Strike Escalation Rule
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

---

## Domain-Agnostic Operational Amendments

Ratify these as they become relevant to your project. Remove the PROPOSED prefix
after explicit human ratification.

---

### Amendment 5 — Simulation is the Hardware Proxy
*Traces to: Article I + II*
*Status: PROPOSED — ratify when Stage 1 begins*

If something cannot be tested in simulation, a simulation test must be written first.
Hardware results that deviate from simulation predictions are evidence of a hardware or
mounting problem — not a firmware problem — unless the corresponding simulation test
was never written.

The handoff document (`docs/governance/handoff.md`) is the binding prediction set
against which hardware results are compared at each stage gate.

---

### Amendment 6 — Signal Plot Mandate
*Traces to: Article I + II*
*Status: PROPOSED — ratify when Stage 1 begins*

After any change to the project's signal model or any filter coefficient in firmware
source, an agent must generate a signal plot, save it to `docs/plots/`, and wait for
human visual confirmation before proceeding.

Signal plots are the primary mechanism for catching silent model errors that pass
numerical tests. Human visual review of physical plausibility cannot be substituted
by a numerical test. A metric value that looks correct can be produced by a physically
implausible signal.

**Invoked by:** `/plot-profile` and `/plot-evidence signal`

---

### Amendment 7 — Calibration Discipline
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

---

### Amendment 8 — Algorithm Search Honesty
*Traces to: Article I + II*
*Status: PROPOSED — ratify when algorithm work begins*

When an algorithm fix domain has been exhausted without resolution, the agent must
explicitly state:
  - Which domain was searched
  - Why it yielded no result
  - No more than three alternative domains

The human selects exactly one alternative. The hardware iteration option (sensor
repositioning, BOM change, enclosure change) must always remain on the list —
it is never automatically eliminated.

**Rationale:** An agent that continues searching within an exhausted domain without
disclosure violates Article II. Switching domains unilaterally violates the same
Article. The cost of an algorithm fix may exceed the cost of a hardware change —
the human must be in the decision.

---

### Amendment 9 — Hardware Optimization Transparency
*Traces to: Article II*
*Status: PROPOSED — ratify when algorithm work begins*

When an agent identifies that an algorithm change enables lower-cost hardware
(fewer sensors, lower-spec component, simpler enclosure), it must explicitly state
this and the physical reasoning before proceeding. The human decides whether to
optimize.

BOM changes have supply chain, procurement, and schedule consequences an agent
does not possess. All BOM or hardware specification changes require explicit human
authorization and must be recorded in `docs/device_context.md` BOM section.

---

### Amendment 10 — Interim Results and Decision Logging
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

---

### Amendment 11 — Scaffold Immutability
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

---

### Amendment 12 — Corpus Supremacy
*Traces to: Article I + Article II*

The corpus is the alignment target of the project. It is the authoritative record
of what the device must do, why, and against which physical reality it is measured.
All code is an approximation of the corpus. When code and corpus conflict, the
corpus is correct and the code is wrong.

**The corpus is not documentation. It is the product.** The physical device's
behaviour is defined by the corpus. Code is one instantiation of that behaviour,
generated from the corpus, and replaceable by regeneration.

#### The four corpus layers

| Layer | Contents | Change requirement |
|-------|----------|--------------------|
| **1 — Immutable corpus** | Signal inventory (`device_context.md`), domain primitives (Amendment 1), toolchain record (`toolchain_config.md`), `CONSTITUTION.md` | Amendment Ratification + Judicial Hearing |
| **2 — Interface implementations** | `src/signals.py`, `src/algorithm.py` | Judicial Hearing — `api-reviewer` must produce a derivation chain evidence report before the Hearing is declared |
| **3 — Generated artifacts** | Firmware source, Renode simulation config | Bill enacted through the Legislative Process |
| **4 — Ephemeral artifacts** | Test scripts, `src/analysis.py`, `src/plot.py`, `src/events.py` | None — delete and regenerate freely from the current corpus state |

#### Corpus Supremacy rule

No generated artifact (Layer 3 or 4) may be manually edited to produce a result
that the corpus does not authorize. If a generated artifact is wrong, the correct
path is:

  1. Identify which corpus layer contains the error
  2. Change the corpus through the required process for that layer
  3. Regenerate the artifact from the updated corpus

Editing a generated artifact directly to work around a corpus gap is an
**Article II violation** — it is a decision about physical or algorithmic direction
made without human approval of the underlying corpus change.

#### Regeneration is a Standing Order

Deleting and regenerating any Layer 3 or Layer 4 artifact from an **unchanged**
corpus requires no Bill, no Hearing, and no human approval. It is a pre-authorized
Bureaucracy operation. Regeneration that is triggered by a corpus change is covered
by whatever process authorized that corpus change.

#### Layer 2 swap requires a Hearing

`signals.py` and `algorithm.py` sit at the interface between the physical world
and the toolchain. A new implementation may nominally satisfy the Layer 1 interface
contract (correct units, correct output names) while introducing a derivation chain
that violates Article I — the physical link from domain primitive to output passes
through more than one intermediate physical quantity, making the primitive citation
unverifiable.

Before any Layer 2 Hearing is declared, `api-reviewer` must audit the proposed
implementation and produce a derivation chain evidence report. The attorneys argue
from that report. The Justice rules on Article I compliance before the swap is
authorized.

**Rationale:** The corpus is the mechanism by which the project remains aligned to
both physical reality (Article I) and human purpose (Article II). Code that drifts
from the corpus has drifted from both simultaneously. Regenerating from corpus is
not a build step — it is a realignment operation. The layer hierarchy makes the
alignment target explicit and the distance from ground truth measurable.

**What happens without it:** An agent hand-patches generated firmware to fix a
threshold that should have been changed in `algorithm.py`. The corpus and the code
diverge silently. The next regeneration overwrites the patch. No one knows why the
field behaviour changed. There is no corpus record to audit against.

**Amendment it complements:** Amendment 11 (Scaffold Immutability — Layer 4
ephemerality applies to scaffold outputs; Amendment 11 governs the specific
conditions under which they are regenerated).

---

### Amendment 13 — Hybrid Execution Tiers

**Status:** PROPOSED  
**Traces to:** Article I (data provenance), Article II (human controls where sensitive data flows)

**What it mandates:**

Every Crucible agent operates under a three-tier corpus sensitivity classification:

| Tier | Meaning | Permitted execution sites |
|---|---|---|
| PRIVATE | Project IP, raw sensor data, field recordings, algorithm source | Local only (Ollama or direct Python) |
| DERIVED-OK | Scalar summaries, plot files, metric tables derived from PRIVATE | Local or cloud |
| PUBLIC | Governance docs, agent definitions, constitutional records | Local or cloud, unrestricted |

**Rules:**

1. An agent whose `contract.execution` is `cloud` must not retrieve PRIVATE corpus entries and must not receive PRIVATE content in any prompt.
2. PRIVATE content may only flow to local execution contexts — it must not appear in any payload forwarded to a cloud API.
3. Every agent must carry a `contract:` block in its YAML frontmatter declaring its execution site, permitted retrieves, and forwarding rules. An agent without a `contract:` block may not call `query_tiered()`.
4. The RAG router (`crucible/hybrid/router.py`) enforces retrieval boundaries automatically by reading the `contract.retrieves` field — no agent may self-select access beyond its contract.
5. When field data is present (Stage 3+), all files under `docs/field-test/` are classified PRIVATE by default. Reclassifying any PRIVATE entry to a less-restrictive tier requires a Bill.
6. The corpus tier index lives at `docs/hybrid/corpus_index.json` and is updated as a Bureaucracy Standing Order — no Bill required to add PRIVATE entries, because restricting access is always safe.

**Relationship to Amendment 12 (Corpus Supremacy):**

The corpus layers (1–4) govern mutability and change gates. The hybrid tiers (PRIVATE / DERIVED-OK / PUBLIC) govern sensitivity and execution routing. The two systems are orthogonal — a Layer 1 file can be PUBLIC (CONSTITUTION.md) or PRIVATE (src/signals.py once a project spec is defined). Both classifications apply simultaneously.

**Enforcement mechanism:**

`crucible/hybrid/router.py` — reads `contract.retrieves` from agent frontmatter, filters `corpus_index.json` by permitted tiers, and returns only allowed chunks. `crucible/rag/query.py::query_tiered()` wraps the semantic search with router enforcement.

**Why this matters:**

As crucible-lite deploys on real devices with real field data, cloud agents (attorneys, sw-advisor) will receive session context. Without explicit tier boundaries, a cloud API call could receive raw sensor arrays or algorithm source. This amendment makes the boundary constitutionally explicit and mechanically enforced.

---

## Project-Specific Amendments

Amendment 1 (Domain Primitives) is written here by `/spec collect` after human
ratification. Subsequent project-specific amendments are added below Amendment 1
as the project evolves.

> [Amendment 1 will appear here after /spec collect is run and ratified.]

---

## Amendment Index

| # | Title | Status | Traces to |
|---|-------|--------|-----------|
| 1 | Domain Primitives | NOT YET RATIFIED — run /spec collect | Article I |
| 2 | Stage Gate Order | PROPOSED | Article I + II |
| 3 | Toolchain Alignment | PROPOSED | Article II |
| 4 | Three-Strike Escalation Rule | PROPOSED | Article II |
| 5 | Simulation is the Hardware Proxy | PROPOSED | Article I + II |
| 6 | Signal Plot Mandate | PROPOSED | Article I + II |
| 7 | Calibration Discipline | PROPOSED | Article I |
| 8 | Algorithm Search Honesty | PROPOSED | Article I + II |
| 9 | Hardware Optimization Transparency | PROPOSED | Article II |
| 10 | Interim Results and Decision Logging | PROPOSED | Article II |
| 11 | Scaffold Immutability | PROPOSED | Article I + II |
| 12 | Corpus Supremacy | RATIFIED | Article I + II |
| 13 | Hybrid Execution Tiers | PROPOSED | Article I + II |
