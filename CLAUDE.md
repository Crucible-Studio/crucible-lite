# Crucible — Claude Code Entry Point

You are operating inside a Crucible project. Crucible is a constitutional governance
framework for hardware development. Before doing anything, read this file in full.
It tells you what governs your behaviour, where to find everything, and what you
must never do without human approval.

---

## The two unconditional rules

Read `CONSTITUTION.md` for the full text. The two Articles are non-negotiable:

**Article I — Physics First**
Every threshold, parameter, filter cutoff, FSM transition, and algorithm decision
must trace to a named domain primitive — a first-order physically measurable quantity.
A constant without a primitive citation is a guess. Guesses are not permitted.

**Article II — Human in the Loop**
You execute. The human decides. Any action whose consequence cannot be fully
reversed by a single `git revert` requires explicit human approval before execution.
Flashing firmware to hardware is the hard case. Algorithm changes, BOM changes,
and toolchain switches are also covered.

If you are about to do something and you are unsure whether it requires a Bill
or a Hearing: stop and ask. The cost of pausing is zero. The cost of an
unauthorized change is a /hear and a retroactive audit.

---

## Where everything lives

```
CONSTITUTION.md                              ← start here — Articles, Branches, Standing Orders
docs/governance/amendments/                  ← individual amendment files (canonical)
  MANIFEST.md                                  machine-readable index (always small, always load)
  amendment_01_domain_primitives.md            LOAD THIS for primitives — written by /spec collect
  amendment_NN_slug.md                         one file per amendment; load only what you need
docs/governance/amendments.md               ← stub index only — links to amendments/; do not read for content
docs/governance/hearings/                   ← individual Judicial Hearing files (canonical)
  MANIFEST.md                                  machine-readable index; checked by corpus enforcement
  H-NNN_hearing-name.md                        one file per Judicial Hearing
docs/governance/case_law.md                 ← Bills enacted, stage gate records, non-hearing entries
docs/device_context.md                      ← device purpose, BOM, signal inventory, test results
docs/toolchain_config.md                    ← active board, FQBN, pins, libs, blocked toolchains,
                                               firmware UART format (event definitions for scaffold)
docs/notebook.md                            ← informal session log; append freely, no police check
docs/knowledge_map.json                     ← project knowledge graph (nodes + edges)
docs/hybrid/corpus_classification.md        ← three-tier sensitivity guide (PRIVATE/DERIVED-OK/PUBLIC)
docs/hybrid/corpus_index.json               ← RAG tier index for hybrid routing
docs/hybrid/skill_contract_spec.md          ← contract.retrieves format specification
docs/testing/hil_testing_guide.md           ← HIL testing protocol and Stage 0 smoke test sequence

crucible/                                   ← infrastructure Python (no domain knowledge)
  checks/                                      pre-commit enforcement
    article_i.py                               Article I: uncited constants in firmware/Layer 2
    corpus.py                                  Amendment 12: Layer 2 hearing gate, Layer 4 regen check
    runner.py                                  entry point; _resolve_repo_root() + _check_hooks_path()
    stage_gate.py                              Stage Gate Order (Amendment 2)
  corpus/                                      governance knowledge graph
    graph.py                                   CorpusGraph — parses amendments/ + hearings/ into typed nodes
    query.py                                   stable query API: has_valid_layer2_hearing(), find_informal_rulings()
  db/                                          SQLite corpus database
    conn.py                                    connection helper; creates corpus.db on first call
    migrate.py                                 schema migration runner
  export/
    redact.py                                  [REDACT]/<!-- redact --> pass before external output
  hybrid/                                      hybrid execution tier system
    router.py                                  tier filter; reads contract.retrieves from agent frontmatter
    ollama_client.py                           local LLM wrapper (Ollama, default qwen2.5:0.5b)
  rag/                                         RAG stack
    indexer.py                                 chunk Layer 1 corpus files → Chroma vector store (.chroma/)
    query.py                                   semantic search with keyword fallback; tier-enforced variant
  signal/                                      infrastructure signal layer
    analysis.py                                configurable UartParser + EventDefinition (project-neutral)
    events.py                                  UartEvent container types
    plot.py                                    base plotting utilities
  sim/                                         simulation
    renode.py                                  Renode integration path (firmware parity validation)
    signal_sim.py                              signal-only path (pure Python, no firmware, seconds not minutes)
    stubs/                                     sim_imu_stub.py, sim_uart_stub.py
  toolchain/
    conflict_checker.py                        detects blocked toolchain conflicts
    lib_resolver.py                            library resolution for PlatformIO
  transport/
    ble.py                                     Nordic UART Service (NUS) BLE console receiver
  wiki/
    renderer.py                                docs/wiki/ generator from knowledge_map + corpus.db

src/                                        ← generated project Python (events, analysis, plot)
  events.py, analysis.py, plot.py             frozen at Stage 1 gate (Amendment 11)
  signals.py                                  physics model / signal generator — you implement generate(profile, condition)
  algorithm.py                                Python algorithm model — you implement run(samples); mirrors firmware

.claude/agents/                             ← 18 agent definitions
.claude/commands/                           ← 12 slash command definitions
.claude/hooks/article1_check.py            ← PreToolUse hook — Edit/Write to source files
.claude/hooks/bash_write_guard.py          ← PreToolUse hook — Bash writes to Layer 2 files
.claude/toolchain/boards.json              ← known board FQBN catalogue
scripts/pre-commit                          ← installable pre-commit hook template
scripts/pre-push                            ← installable pre-push hook template
```

---

## Domain primitives — read first, every session

**Read `docs/governance/amendments/amendment_01_domain_primitives.md` first in every session.**
This is the only file you need for domain primitives — it is small and self-contained.
Do not load the full monolithic `amendments.md` stub.

Read `docs/governance/amendments/MANIFEST.md` to check amendment statuses without loading
every amendment file. One row per amendment, always current.

Read `docs/toolchain_config.md` before any toolchain-dependent action — it records
the active board, flash method, and any blocked tools. A blocked toolchain is a hard stop.

---

## The two simulation paths

`src/signals.py` + `src/algorithm.py` enable the **signal-only path** — pure Python,
no firmware required, runs in seconds. Fast iteration on the physics model and algorithm.

`crucible/sim/renode.py` drives the **Renode path** — validates that the C firmware
implementation matches the Python model. Stage 1 gate requires at least one successful
Renode run confirming parity between the two paths.

Both paths must agree at Stage 1 gate. Disagreement is escalated by simulator-operator
to a Judicial Hearing.

---

## The agent roster (18 agents)

### Judicial Branch
| Agent | Role |
|---|---|
| `attorney-A` | Argues assigned position in a /judicial hear |
| `attorney-B` | Argues opposing position in a /judicial hear |
| `judicial-clerk` | Warms up the courtroom, confirms agent roster |
| `police` | Audits commits and session for constitutional violations |

### Bureaucracy — Simulation pipeline
| Agent | Role |
|---|---|
| `simulator-operator` | Orchestrates simulation runs per profile; escalates parity failures to Hearing |
| `uart-reader` | Captures and prints UART output from Renode or hardware |
| `plotter` | Generates signal diagnostic plots |
| `regression-runner` | Runs full profile matrix, reports pass/fail |

### Bureaucracy — Advisory
| Agent | Role |
|---|---|
| `sw-advisor` | Algorithm suggestions grounded in simulation profile evidence |
| `hw-advisor` | Hardware suggestions grounded in test results and BOM |
| `bill-drafter` | Produces complete, debate-ready Bills from evidence |

### Bureaucracy — Housekeeping
| Agent | Role |
|---|---|
| `api-reviewer` | Pre-Hearing evidence: derivation chain depth and interface contract alignment for signals.py and algorithm.py |
| `code-reviewer` | Article I traceability, FSM integrity, filter chain, unit checks in src/ during development |
| `doc-reviewer` | Documentation completeness, staleness, cross-doc consistency |
| `constitution-auditor` | Governance record consistency (amendments vs case law vs hearings) |
| `package-manager` | Python/brew/pio dependency management |
| `stage-compactor` | Freezes and compacts case law at each stage gate |
| `agent-updater` | Propagates Amendment/Bill changes to affected agent files |

---

## The command set (12 commands)

### Orchestration
| Command | What it does |
|---|---|
| `/session [stage]` | Run or check a full development stage; includes checkpoint resume |
| `/spec [fast\|collect\|review\|signals\|target]` | Device spec, domain primitives, and signal inventory |
| `/toolchain <subcommand>` | Register hardware, lock toolchain, block tools, scaffold project modules |
| `/compact [target]` | Compact spiralling documentation |
| `/governance ratify [N\|all]` | Interactive amendment ratification (updates fragment files + MANIFEST) |

### Judicial
| Command | What it does |
|---|---|
| `/judicial hear "<name>" A vs B` | Declare a Judicial Hearing; outputs structured H-NNN file + MANIFEST row |
| `/judicial bill <description>` | Produce a debate-ready Bill from evidence |

### Advisory
| Command | What it does |
|---|---|
| `/advisor hw [focus]` | Hardware design suggestions |
| `/advisor sw [focus]` | Algorithm design suggestions |

### Evidence and validation
| Command | What it does |
|---|---|
| `/regression [profile]` | Full simulation profile matrix |
| `/plot profile <name>` | Single signal diagnostic plot |
| `/plot evidence <type> [args]` | Evidence for a hearing or validation |

### Housekeeping
| Command | What it does |
|---|---|
| `/review code [focus]` | Article I compliance audit |
| `/review doc [focus]` | Documentation gap audit |
| `/review gov [focus]` | Governance record consistency audit |
| `/wiki generate [--page <name>] [--no-redact]` | Generate docs/wiki/ from corpus state |
| `/gen-new-agent <name>` | Human-executed protocol to add an agent |

---

## What you may do without a Bill or Hearing

These are Bureaucracy Standing Orders — pre-approved, no human decision required:

- Build firmware from existing source using the active toolchain
- Install, update, or pin Python/brew/pio dependencies
- Run simulation profiles against existing firmware and signal models
- Generate signal diagnostic plots and wiki pages
- Capture and print UART output
- Export session data to established formats (with redaction pass if external)
- Read any file in this repository
- Write to `docs/device_context.md` Test Results and Signal Measurements sections
  (recording data, not changing thresholds)
- Append to `docs/notebook.md` (informal log, no constitutional check)
- Commit and push validated, already-approved work
- Run `crucible.rag.indexer` to rebuild the Chroma vector index

## What requires a Bill (Legislative Process)

Any proposed change to:
- Firmware source (algorithm logic, thresholds, FSM conditions)
- Simulation (new profile, signal model parameter)
- Software pipeline (new stage, new metric)
- Hardware (BOM change, sensor repositioning, enclosure)

Use `/judicial bill <description>` to produce the Bill. Then `/judicial hear` to debate it.

## What requires a Hearing (Judicial Process)

- **Any change to `src/signals.py` or `src/algorithm.py`** (Amendment 12 — Corpus Supremacy)
- Two amendments mandate incompatible actions
- An agent is uncertain which amendment governs
- A Bill is disputed
- A blocked toolchain is proposed for unblocking
- Three-strike escalation: a fix fails three times (Amendment 4)
- Simulation path and Renode path disagree at Stage 1 gate

Use `/judicial hear "<hearing name>" <position A> vs <position B>`.

**Every Hearing must produce a structured file** in `docs/governance/hearings/H-NNN_name.md`
with all three sections present before the hearing is considered complete:
```
## Attorney-A argued:    ← non-empty
## Attorney-B argued:    ← non-empty
## Justice ruled:        ← non-empty
```
Then add a row to `docs/governance/hearings/MANIFEST.md` with Has-A/Has-B/Has-J = TRUE.
A Hearing entry missing any section is an informal ruling — it does not satisfy Amendment 12.
The pre-commit Corpus check and the police agent enforce this.

## What requires human approval before execution (Article II)

- Flashing firmware to physical hardware
- Running a field test (Stage 3 pre-flight gate)
- Deploying to a host system (Stage 4)
- Any action outside a defined Standing Order
- Closing a stage gate

---

## How to orient yourself in a returning session

Run `/session status`. It reads the constitutional record and prints:
- Current stage status (which stages are CLOSED / OPEN / NOT STARTED)
- Active toolchain
- Amendment count and most recent (read from `amendments/MANIFEST.md`)
- Hearing count (read from `hearings/MANIFEST.md`)
- Any open violations from police

If you are resuming mid-stage, check `docs/governance/session_checkpoint.md` first —
`/session` will detect an IN_PROGRESS checkpoint automatically and offer to resume.

Read `docs/governance/hearings/MANIFEST.md` — what Hearings are on record and whether they are complete.
Read `docs/governance/case_law.md` — Bills enacted and stage records.
Do not re-debate closed cases. Do not treat incomplete Hearing entries as authoritative rulings.

Run `/session refresh` if quality degrades mid-session — re-reads Amendment 01, checkpoint,
and `docs/governance/session_context.md` (short working-memory file updated at every named breakpoint).

`/session clean` removes resolved threads from `session_context.md` using Mem0
(`pip install mem0ai`) for selective forgetting. Runs automatically at every stage gate close.

---

## The enforcement stack

Four overlapping layers. Understanding how they interact prevents confusion when a commit is blocked:

```
Layer 1 — Agent-side hooks (Claude Code, real-time)
  Fires before every Edit/Write/Bash tool call.
  • article1_check.py  → blocks write to source file with uncited constant
  • bash_write_guard.py→ blocks shell write to src/signals.py or src/algorithm.py
                         without a Judicial Hearing on record

Layer 2 — Pre-commit hook (git, per commit)
  Install: cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
  • Article I    → no uncited constant in staged firmware or Python Layer 2
  • Amendment 12 → no Layer 2 commit without complete Hearing
  • Amendment 2  → stage gate order not violated

Layer 3 — Pre-push hook (git, catches --no-verify bypasses)
  Install: cp scripts/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push
  • Same checks as Layer 2, runs against remote ref — cannot be silently skipped

Layer 4 — Police agent (audit on demand / at stage gate)
  Invoked at every stage gate exit attempt.
  • Full audit of commits, session, governance records
  • Detects INFORMAL-RULING-VIOLATION, JUDICIAL-INDEPENDENCE-VIOLATION, Amendment 13
```

---

## The hybrid execution tier system

Three sensitivity tiers govern which agents may retrieve which corpus content
and whether computation may run locally or be forwarded to cloud models:

| Tier | Content | Routing |
|---|---|---|
| PRIVATE | signals.py, algorithm.py, firmware source, raw field data | Local only; never forwarded to cloud |
| DERIVED-OK | Scalar outputs, plot files, summary JSON, sim pass/fail | Safe to forward to cloud agents |
| PUBLIC | Governance docs, agent definitions, CONSTITUTION.md | Unrestricted |

`crucible/hybrid/router.py` enforces tier boundaries: reads each agent's `contract.retrieves`
block from its YAML frontmatter and filters corpus chunks accordingly.
`crucible/hybrid/ollama_client.py` provides local LLM inference (Ollama, default qwen2.5:0.5b)
for tasks that must not send PRIVATE content to a cloud API.

The RAG stack (`crucible/rag/`) provides semantic search over Layer 1 corpus files via
Chroma (`.chroma/`). Rebuild the index: `python -m crucible.rag.indexer`.
Use `query_tiered("agent-name", "query")` to enforce tier boundaries in agent queries.

The corpus knowledge graph (`crucible/corpus/graph.py`) builds typed nodes from amendments/
and hearings/ for structural validation by enforcement checks.

---

## The corpus structure — fragmented layout

The governance corpus is split into fragmented directories. Use fragmented for all new entries.

```
docs/governance/amendments/
  MANIFEST.md                              ← machine-readable index (always small — always load)
  amendment_01_domain_primitives.md        ← written by /spec collect; load for primitives
  amendment_NN_slug.md                     ← one file per amendment

docs/governance/hearings/
  MANIFEST.md                              ← machine-readable index; checked by corpus enforcement
  H-NNN_hearing-name.md                   ← one file per Judicial Hearing; must have all 3 sections

docs/governance/case_law.md               ← Bills enacted, stage gate records (not hearings)
docs/governance/amendments.md             ← stub index only; kept for backward compat
```

---

## How to start a new project (forking this repo)

1. `/spec collect` — interview about device purpose, signal inventory, domain primitives
2. Run `agent-updater` — propagate Amendment 1 primitives to all agents
3. `/toolchain init` — register your board, pins, libraries
4. Install git hooks:
   ```
   cp scripts/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
   cp scripts/pre-push   .git/hooks/pre-push   && chmod +x .git/hooks/pre-push
   ```
5. `/governance ratify 2 3 4 12` — ratify Stage Gate, Toolchain Alignment, Three-Strike, Corpus Supremacy
   (updates individual amendment files + `amendments/MANIFEST.md`)
6. Run `agent-updater` again — propagate stage gate/toolchain/three-strike/corpus rules
7. `/session 0` — HIL toolchain lock
8. Fill in `docs/toolchain_config.md` `## Firmware UART Format` (event markers, field names)
9. `/toolchain scaffold` — generate `src/events.py`, `src/analysis.py`, `src/plot.py`
10. `/session 1` — simulation (scaffold check runs automatically)

Do not skip `/spec collect`. Domain primitives are the foundation Article I enforces
against. Without them, code-reviewer, sw-advisor, hw-advisor, and bill-drafter
have no basis for their findings.

---

## The one thing you must not do

Do not set a threshold, cutoff, or parameter in firmware source or in
`src/signals.py` / `src/algorithm.py` without citing a domain primitive in an
inline comment. Not as a style rule — as a constitutional requirement.

**The citation must name an actual Amendment 1 primitive.** A comment like
`# Traces to: sensor mismatch (empirical)` passes the keyword check but fails
the primitive-name check in `article1_check.py` and `article_i.py`. The only
comment that passes is one that names a primitive from Amendment 1, e.g.:
`# Traces to: Floor Acceleration (Amendment 1 primitive 1)`.

**Also: do not write to `src/signals.py` or `src/algorithm.py` without a
Judicial Hearing on record** (Amendment 12 — Corpus Supremacy). The
`bash_write_guard.py` hook will block Bash-path writes. The pre-commit hook will
block git commits. The only way through is a completed Hearing — which is the
correct path. This applies even during initial Stage 1 development.

For toolchain constants (USB CDC, BLE GAP, etc.), use an inline comment:
```
Bluefruit.Advertising.setInterval(32, 244); // Traces to: BLE GAP — toolchain constant
```

If you do not know which primitive a constant traces to, that is the signal to
stop and ask the human — not to guess and proceed.
