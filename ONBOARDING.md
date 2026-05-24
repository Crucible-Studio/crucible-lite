# Crucible — Onboarding Guide

> **If you are Claude Code:** read [`CLAUDE.md`](CLAUDE.md) first. It maps every file, command, agent, and enforcement hook. This guide is the workflow companion — read CLAUDE.md alongside it.

**Estimated time:** 30 minutes to first running session.

---

## Prerequisites — read before your first session

### 1. [CONSTITUTION.md](CONSTITUTION.md)
The two unconditional Articles and the four-branch governance system. Non-negotiable.

### 2. [CLAUDE.md](CLAUDE.md)
Repo map, command set, agent roster, enforcement stack, and corpus structure.
Read this before any coding session.

### 3. [docs/governance/amendments/MANIFEST.md](docs/governance/amendments/MANIFEST.md)
One-row-per-amendment status index. Always small, always current. Load this instead of
scanning the full `amendments.md` stub.

### 4. The Hearing procedure
Every Judicial Hearing must produce a structured file with all three required sections
(Attorney-A, Attorney-B, Justice ruling). A Hearing missing any section is an
**informal ruling** — it does not satisfy Amendment 12 and will be flagged.

### 5. [docs/governance/adoption_guide.md](docs/governance/adoption_guide.md)
How to fork and adapt this framework for your specific device. What is universal,
what is device-specific, and what you must write before your first session.

---

## Prerequisites — tooling

### A. Python environment
```bash
pip install numpy matplotlib bleak pytest chromadb sentence-transformers mem0ai
```
Check: `which renode` / `which pio` / `which ninja`

### B. Your firmware toolchain
Know the answers to:
- What board/MCU? (needed for FQBN in PlatformIO or Arduino CLI)
- How do you flash firmware? (UF2, J-Link, DFU, JTAG)
- How do you observe output? (USB serial, BLE, RTT, UART)

Run `/toolchain init` to record these formally.

### C. Install git hooks (one command per clone)

```bash
cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
cp scripts/pre-push   .git/hooks/pre-push   && chmod +x .git/hooks/pre-push
```

This installs two enforcement hooks:

- **`pre-commit`** — runs the constitutional check on every staged commit: Article I primitive
  citation check, Amendment 12 Corpus Supremacy check, and Stage Gate Order check. Any staged
  source file containing an empirical constant without a domain primitive citation blocks the commit.
- **`pre-push`** — re-runs the full constitutional check against the remote ref before any push.
  This catches `--no-verify` bypasses at commit time — the hook fires again at push and cannot
  be skipped silently.

Both hooks apply to you as much as to agents. The constitution does not distinguish.

The Claude Code agent-side enforcement runs in addition to the git hooks via `.claude/hooks/`:
- **`article1_check.py`** — fires on every `Edit` or `Write` tool call targeting source files
- **`bash_write_guard.py`** — fires on every `Bash` tool call; blocks shell-path writes to
  `src/signals.py` or `src/algorithm.py` without a Judicial Hearing on record

### D. A git repository

This framework uses git as the record of decisions. Every Bill enacted, every Amendment
ratified, and every Judicial Hearing is a commit. Without git, the governance record
cannot be reconstructed.

---

## Corpus structure — where governance records live

The governance corpus is split into two fragmented directories alongside the legacy monolithic files.
Use the fragmented structure for all new entries.

### Amendments

```
docs/governance/amendments/
  MANIFEST.md                              ← machine-readable index (always small)
  amendment_01_domain_primitives.md        ← written by /spec collect
  amendment_02_stage_gate_order.md
  ...
  amendment_13_time_domain_validation.md
```

Each amendment is a standalone file. To ratify: run `/governance ratify N` (interactive) or
manually change `Status: PROPOSED` to `Status: RATIFIED` in the file and in `MANIFEST.md`.
The enforcement checks read `MANIFEST.md` first (fast, always-small index) and load individual
files only when content is needed (e.g., primitive names from Amendment 1).

`docs/governance/amendments.md` is now a stub index that links to the individual files.
Do not add new amendment content there.

### Hearings

```
docs/governance/hearings/
  MANIFEST.md                              ← machine-readable index (always small)
  H-001_hearing-name.md                   ← one file per Judicial Hearing
  H-002_hearing-name.md
  ...
```

Each Judicial Hearing gets its own file. A complete hearing file **must** have all three sections:

```markdown
## Attorney-A argued:     ← non-empty
## Attorney-B argued:     ← non-empty
## Justice ruled:         ← non-empty
```

A hearing entry missing any section is an **informal ruling** — it does not satisfy Amendment 12
(Corpus Supremacy) and will be flagged by the police agent as `JUDICIAL-INDEPENDENCE-VIOLATION`.
The enforcement check queries structural completeness, not keyword presence.

`docs/governance/case_law.md` remains the record of non-hearing governance entries (Bills enacted,
stage gate records). New Judicial Hearing entries go in `hearings/`.

---

## New project setup

```
START NEW PROJECT
│
├─► Install git hooks ──────────────────────────────────────────────────────────────
│     cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
│     cp scripts/pre-push   .git/hooks/pre-push   && chmod +x .git/hooks/pre-push
│
├─► /spec collect ──────────────────────────────────────────────────────────────────┐
│     │  Interview: device purpose, project target, pass/fail threshold,            │
│     │  signal inventory, domain primitives, operating envelope                    │
│     │  (Use /spec fast for single-pass intake if you know all answers)            │
│     │                                                                             │
│     ▼                                                                             │
│   Human ratifies Amendment 1?                                                     │
│     No ──► revise and re-ask                                                      │
│     Yes──► Amendment 1 written to:                                                │
│              docs/governance/amendments/amendment_01_domain_primitives.md         │
│              docs/governance/amendments/MANIFEST.md row 1 updated to RATIFIED    │
│            agent-updater ──► propagates primitives to code-reviewer,             │
│                               sw-advisor, hw-advisor, bill-drafter               │
│                                                                                   │
├─► /toolchain init ────────────────────────────────────────────────────────────────┤
│     Fill in: ## Firmware UART Format (event markers, field names, session_end)    │
│     Writes: docs/toolchain_config.md (status: UNLOCKED)                          │
│                                                                                   │
├─► /governance ratify 2 3 4 12 ──────────────────────────────────────────────────  │
│     For each: updates amendment_NN_slug.md → Status: RATIFIED                    │
│               updates MANIFEST.md row → Status: RATIFIED                         │
│     Amendment 2:  Stage Gate Order                                                │
│     Amendment 3:  Toolchain Alignment                                             │
│     Amendment 4:  Three-Strike Rule                                               │
│     Amendment 11: Scaffold Immutability (recommended)                            │
│     Amendment 12: Corpus Supremacy (governs signals.py and algorithm.py)         │
│                                                                                   │
├─► agent-updater ──► propagate stage gate/toolchain/three-strike/corpus rules     │
│                                                                                   │
└─► Ready for /session 0 ──────────────────────────────────────────────────────────┘
```

---

## Stage 0 — HIL Toolchain Lock

**Purpose:** Prove the development loop works before any algorithm work begins.

**Why first:** HIL failures at Stage 0 cost 20 minutes. Discovered at Stage 3, they cost days.
Stage 0 proves exactly four things:
1. Build toolchain produces a flashable binary for this specific board
2. Flash mechanism works end-to-end
3. Observation path works (USB serial / BLE / UART / RTT)
4. Sensor hardware is alive over its interface

```
/session 0
│
Step 0a — CONSTITUTION.md loaded
│
Step 0b — Toolchain check
│  Read docs/toolchain_config.md
│  Blocked toolchain in active slot? ──► STOP: report conflict
│
Step 0c — Domain primitives check
│  Read docs/governance/amendments/amendment_01_domain_primitives.md
│  Amendment 1 ratified? ──► print primitives
│  Not ratified? ──► STOP: "Run /spec collect"
│
Step 0d — Police check
│  New project? ──► skip, note "new project"
│  Has history? ──► audit last 10 commits vs case_law.md + hearings/MANIFEST.md
│
Step 0e — Checkpoint resume check
│  session_checkpoint.md: IN_PROGRESS? ──► offer resume
│
[GATE 0.1] Build smoke test — firmware compiles for target board
[GATE 0.2] Flash smoke test — firmware runs on hardware
[GATE 0.3] Observation smoke test — UART / BLE output visible and parseable
[GATE 0.4] Sensor smoke test — sensor returns physically plausible values
│
All gates pass ──► Stage 0 CLOSED
  │  1. Record Stage 0: CLOSED in toolchain_config.md
  │  2. stage-compactor ──► case_law.md entry
  │  3. /toolchain lock ──► stamp toolchain as Stage 0 validated
  └─► Ready for /session 1
```

---

## Stage 1 — Simulation

**Purpose:** Validate algorithm logic and signal model consistency using the two simulation paths.

**Entry condition:** Stage 0 CLOSED.

### Two simulation paths

```
Signal-only path (crucible/sim/signal_sim.py)
  │  Pure Python, no firmware, runs in seconds
  │  Input: src/signals.py generate(profile, condition) → sample array
  │  Output: src/algorithm.py run(samples) → result
  │
Renode path (crucible/sim/renode.py)
  │  Firmware in emulated hardware — validates firmware parity
  │  Stage 1 gate REQUIRES at least one Renode run confirming parity
  │
Both paths must agree ──► parity confirmed ──► Stage 1 gate PASSES
Both paths disagree   ──► STOP: escalate to Judicial Hearing
```

### Scaffold check (first run of Stage 1 only)
`/toolchain scaffold` must have generated `src/` before the first simulation run:
- `src/events.py`, `src/analysis.py`, `src/plot.py` — Layer 4 ephemeral files
- These are **frozen at Stage 1 gate** (Amendment 11) — never edit directly

### Amendment 12 — Layer 2 Corpus Supremacy
Before any work on `src/signals.py` or `src/algorithm.py`, a Judicial Hearing is required.
The `bash_write_guard.py` hook blocks Bash-path writes. The pre-commit hook blocks commits.

```
/session 1
│
Stage 1 pre-flight:
│  Check for src/ ──► prompt scaffold if missing
│  Read Amendment 1 primitives
│  Run police check
│  Check session_checkpoint.md
│
WORK LOOP ──────────────────────────────────────────────────────────────────────────┐
│                                                                                   │
│  /judicial hear before first signals.py or algorithm.py write (Amendment 12)    │
│  Develop signals.py + algorithm.py with Amendment 1 primitive citations          │
│                                                                                   │
│   /regression [profile]                                                           │
│   │  signal-only across all profiles                                              │
│   │  Fail 3x? ──► AMENDMENT-4-VIOLATION ──► /judicial hear                     │
│   │                                                                               │
│   /plot profile <name> ──► plotter generates signal diagnostic plot              │
│   [Plot evidence required before any algorithm change Bill]                       │
│                                                                                   │
│   Conflicting agent findings?                                                    │
│   ──► /judicial hear ──► hearings/H-NNN.md + MANIFEST.md updated                │
│                                                                                   │
└─────────────────────────────────────────────────────────────────── back ─────────┘
│
Stage 1 gate check:
│  /review code ──► ARTICLE-I-VIOLATION? ──► Bill required
│  /review doc  ──► BLOCKER? ──► fix before gate
│  police ──► VIOLATION? ──► STOP (checks hearings/MANIFEST for incomplete entries)
│  All clean? ──► human confirms ──► stage-compactor ──► Stage 1 CLOSED
│  /session clean ──► Mem0 selective forgetting of resolved threads
└─► Ready for /session 2
```

---

## Stage 2 — Firmware Integration

**Purpose:** Validate that C firmware matches the Python algorithm model on real hardware.

**Entry condition:** Stage 1 CLOSED.

```
/session 2
│
Stage 2 pre-flight:
│  Check toolchain locked + Stage 1 CLOSED + police check
│
Firmware iteration loop:
│  [Article I applies — every constant must cite Amendment 1 primitive]
│  [Bills required for all firmware source changes]
│
  Build ──► flash ──► uart-reader captures ──► analysis.parse()
  Signal-only vs firmware output:
    Agree? ──► parity confirmed ──► continue
    Disagree? ──► Judicial Hearing on parity failure
│
Stage 2 gate check:
│  All profiles pass in both paths?
│  police clean? ──► human confirms ──► stage-compactor ──► Stage 2 CLOSED
└─► Ready for /session 3
```

---

## Stage 3 — Field Test

**Entry condition:** Stage 2 CLOSED. Human approval required (Article II).

```
/session 3
│
Stage 3 pre-flight [HUMAN APPROVAL REQUIRED]:
│  "Ready to run field test?" ──► No? STOP
│
Field run ──► uart-reader / BLE transport ──► live data to docs/device_context.md
│
Post-field analysis:
│  /regression with field replay data
│  Anomaly requiring algorithm change? ──► Bill ──► Hearing ──► Stage 1 re-entry
│
Stage 3 gate check:
│  police clean? ──► human confirms field performance meets project target (Amendment 1)
│  stage-compactor ──► Stage 3 CLOSED
└─► Ready for /session 4
```

---

## Stage 4 — Host Integration

**Entry condition:** Stage 3 CLOSED. Human approval required (Article II).

```
/session 4
│
Deploy to host [HUMAN APPROVAL REQUIRED] ──► integration testing
│
Stage 4 gate:
│  police clean? ──► human confirms ──► stage-compactor ──► Stage 4 CLOSED
│  /wiki generate ──► produce final docs/wiki/ output
└─► Project complete
```

---

## The judicial process — Bills and Hearings

```
Change needed (algorithm, firmware, hardware, simulation)
│
├─► /judicial bill "problem description"
│     bill-drafter reads: amendments/MANIFEST.md, case_law.md,
│                          hearings/MANIFEST.md, device_context.md,
│                          source files
│     Evidence gate + Amendment gate + Outcome gate + Scope gate
│        Gates pass ──► complete Bill output
│        Gates fail ──► INCOMPLETE: "run /regression or /plot evidence first"
│
├─► Human reviews Bill
│
├─► /judicial hear "<name>" A vs B
│     judicial-clerk ──► COURTROOM READY
│     attorney-A + attorney-B argue in parallel
│     (optional) /plot evidence ──► generate requested evidence
│     Justice rules ──► prevailing position + physical basis
│     Prevailing attorney writes to:
│       docs/governance/hearings/H-NNN_name.md     ← structured file
│       docs/governance/hearings/MANIFEST.md       ← index row added
│     agent-updater ──► if ruling changes agent scope: propose edits
│     Amendment 12 ──► Corpus check now satisfied for covered files
│
└─► Implement on branch named in Bill ──► validate ──► merge
```

**Hearing files must contain all three sections before commit:**

```markdown
## Attorney-A argued:
[non-empty — position assigned at hearing declaration]

## Attorney-B argued:
[non-empty — opposing position]

## Justice ruled:
[non-empty — ruling with physical basis]
```

---

## The enforcement stack

```
Layer 1 — Agent-side hooks (Claude Code, real-time)
  • article1_check.py  → blocks Edit/Write to source file with uncited constant
  • bash_write_guard.py→ blocks Bash write to src/signals.py or src/algorithm.py
                         without a Judicial Hearing on record

Layer 2 — Pre-commit hook
  Install: cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
  • Article I    → uncited constant blocks commit
  • Amendment 12 → no Layer 2 commit without complete Hearing
  • Amendment 2  → stage gate order enforced

Layer 3 — Pre-push hook (catches --no-verify bypasses)
  Install: cp scripts/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push
  • Same checks as Layer 2, against remote ref; cannot be silently skipped

Layer 4 — Police agent (at stage gate / on demand)
  • INFORMAL-RULING-VIOLATION        — Hearing suggestion bypassed
  • JUDICIAL-INDEPENDENCE-VIOLATION  — Hearing missing a required section
  • AMENDMENT-13-VIOLATION           — signals.py committed with Bode-only validation
  • AMENDMENT-11-VIOLATION           — scaffold re-run without authorization
  • ARTICLE-I/II-VIOLATION           — uncited constant or unauthorized change
```

---

## The hybrid execution tier system

Three sensitivity tiers control agent access and cloud forwarding:

| Tier | Content | Routing |
|---|---|---|
| PRIVATE | signals.py, algorithm.py, firmware source, raw field data | Local only |
| DERIVED-OK | Scalars, plot files, summary JSON, pass/fail tables | Safe for cloud |
| PUBLIC | Governance docs, agent definitions, CONSTITUTION.md | Unrestricted |

`crucible/hybrid/router.py` enforces tier boundaries via each agent's `contract.retrieves` block.
`crucible/hybrid/ollama_client.py` provides local LLM inference (Ollama, default `qwen2.5:0.5b`).
RAG stack: Chroma at `.chroma/`. Rebuild: `python -m crucible.rag.indexer`. Use `query_tiered()`.

---

## The src/ module roles

`src/` is generated by `/toolchain scaffold`. Never edit directly — regenerate from corpus change.

| File | Role | Amendment constraint |
|---|---|---|
| `src/events.py` | UART event dataclasses | Layer 4 — regen only (Am. 11/12) |
| `src/analysis.py` | Project UartParser | Layer 4 — regen only (Am. 11/12) |
| `src/plot.py` | Project plotting | Layer 4 — regen only (Am. 11/12) |
| `src/signals.py` | Physics model / signal generator | Layer 2 — Judicial Hearing required (Am. 12) |
| `src/algorithm.py` | Python algorithm model | Layer 2 — Judicial Hearing required (Am. 12) |

Article I applies to `signals.py` and `algorithm.py` exactly as it does to firmware.
Amendment 13 (PROPOSED) requires a time-domain overlay plot as evidence before `signals.py` changes.

---

## Housekeeping (on demand, no stage gate required)

| Command | When to use |
|---|---|
| `/review code [focus]` | Article I audit of current `src/` |
| `/review doc [focus]` | Documentation gaps, staleness, cross-doc consistency |
| `/review gov [focus]` | Governance record health (amendments, case law, hearings) |
| `/wiki generate` | Regenerate `docs/wiki/` from current corpus state |
| `/compact [target]` | Compact spiralling docs (session_context.md, case_law.md) |
| `/session refresh` | Re-read Amendment 1 + checkpoint mid-session if quality drops |
| `/session clean` | Mem0 selective forgetting of resolved threads |
| `/spec review` | Flag gaps in docs/device_context.md |
| `/spec signals` | Add/update signal inventory only |
| `/governance ratify N` | Interactively ratify amendment N |

---

## Quick reference — what blocks what

| Action | Prerequisite |
|---|---|
| Write to `src/signals.py` or `src/algorithm.py` | Completed Judicial Hearing in `hearings/` |
| Commit firmware source change | Enacted Bill in case_law.md |
| Close a stage gate | All police violations resolved + human confirmation |
| Flash firmware to hardware | Human approval (Article II) |
| Run field test | Human approval (Article II) |
| Ratify an amendment | Human confirmation via `/governance ratify N` |
| Add a new agent | Human-executed protocol via `/gen-new-agent` |

---

## Amendment quick reference

| # | Title | Key constraint |
|---|---|---|
| 1 | Domain Primitives | Every constant must trace to one of these — enforced by Article I |
| 2 | Stage Gate Order | Stages must close in order; gate without compactor = VIOLATION |
| 3 | Toolchain Alignment | Toolchain switch requires a Bill |
| 4 | Three-Strike Rule | 3 consecutive failures → Judicial Hearing required |
| 5 | Simulation Hardware Proxy | Simulation must run before hardware validation |
| 6 | Signal Plot Mandate | Algorithm change requires a signal diagnostic plot |
| 7 | Calibration Discipline | Calibration constants require derivation record |
| 8 | Algorithm Search Honesty | Domain switch requires human selection |
| 9 | Hardware Optimization Transparency | BOM change requires human authorization |
| 10 | Interim Results Logging | Human decisions must be recorded |
| 11 | Scaffold Immutability | Scaffold re-run after Stage 1 gate requires authorization |
| 12 | Corpus Supremacy | Layer 2 write requires complete Hearing; Layer 4 is regen-only |
| 13 | Time-Domain Validation (PROPOSED) | signals.py change requires time-domain overlay plot |
