Run a full Crucible development session from HIL toolchain lock through host integration.

Usage: /session [stage]

Stages:
  status   — read constitutional record, print current stage and open gates
  spec     — Spec Gate: collect device purpose, signal inventory, and domain primitives  ← NEW PROJECT ALWAYS STARTS HERE
  0        — Stage 0: HIL Toolchain Lock  ← ALWAYS FIRST on any new session or new hardware
  1        — Stage 1: Simulation (physics model or field data replay)
  2        — Stage 2: Firmware Integration on Dev Kit
  3        — Stage 3: Field Test
  4        — Stage 4: Host Integration

Order for a new project: spec → 0 → 1 → 2 → 3 → 4
Order for a returning session: status → [resume open stage]

If no stage given, run status first, then ask Justice which stage to begin.

---

## Design Principle — HIL First

**Hardware-in-the-loop must be the first gate, not the last.**

Every session begins with Stage 0 before any simulation or algorithm work begins.
Toolchain failures (wrong board, cable, FQBN, BLE name truncation, flash offset) discovered
at Stage 0 take 20 minutes. Discovered at Stage 3, they take days.

Stage 0 is cheap. Stage 0 failure at Stage 3 is expensive.
Article II irreversibility does not apply to Stage 0 — counter flashing is trivially reversible.

---

## Session Initialisation (always runs first)

**Step 0 — Resume check (Error 23 — runs before Step 0a):**
Check for `docs/governance/session_checkpoint.md`.
If it exists and `status: IN_PROGRESS` or `status: PAUSED`:
```
  Session checkpoint found:
    Stage [N], Step [step-name] — IN PROGRESS
    Last action: [last_action]
    Next action: [next_action]
    Open threads: [open_threads list]
```
Ask: "Resume from checkpoint? [yes / no — start fresh]"
  If yes: skip Steps 0a–0e and jump directly to next_action.
  If no: proceed normally (checkpoint will be overwritten).
If not found or `status: COMPLETE`: proceed normally.

Write checkpoint to `docs/governance/session_checkpoint.md` after:
- Each smoke test gate (0.1, 0.2, 0.3, 0.4)
- Stage 1 pre-flight completion
- Each Stage 1/2/3/4 named step

**Re-anchor (runs at every named breakpoint — Error 25):**
```
Re-read: docs/governance/amendments/amendment_01_domain_primitives.md
         (or docs/governance/amendments.md if fragmented dir absent)
Re-read: docs/governance/session_checkpoint.md (if exists)
Write current state to: docs/governance/session_context.md
```

**Step 0a — Spec check:**
Read `docs/device_context.md`. Check Device Purpose and Signal Inventory sections.

Placeholder detection: a section is incomplete if it contains "> [", "TODO", "TBD",
"[describe", "[INFERRED — confirm]", or is missing entirely.

If Device Purpose or Signal Inventory is incomplete:
  - Identify which specific field is still a placeholder (Device Purpose, Project Target,
    Pass/Fail Threshold, Signal Inventory, Domain Primitives, Operating Envelope).
  - Stop and print:
    "Spec incomplete — [field name] still placeholder.
     Run /spec fast (quick) or /spec collect (guided) to fill it in."
  - If fields are marked `[INFERRED — confirm]`: do NOT stop. Instead print each flagged
    field and ask "Confirm: [field value]? [yes/correct it]" before proceeding.

If populated (including after INFERRED fields are confirmed), print one-line summary:
  "Project target: [project target line from device_context.md]"
  "Pass/fail threshold: [threshold line from device_context.md]"

**Step 0b — Toolchain config check:**
Read `docs/toolchain_config.md`. If missing: stop and print:
  "Toolchain config missing. Run /toolchain init before starting any stage."

Check lock status against stage status:
- Stage 0 NOT YET STARTED or OPEN: UNLOCKED is acceptable — Stage 0 will lock it.
  Print: "Toolchain status: UNLOCKED — Stage 0 will lock it."
- Stage 0 CLOSED but status is UNLOCKED: stop and print:
  "Stage 0 is closed but toolchain is not locked. Run /toolchain lock."
- Status LOCKED: proceed normally.

Print active toolchain summary: board, FQBN, flash method, wireless transport.
If any blocked toolchain appears in the active slot: stop and report the conflict.

**Step 0c — Domain primitives check:**
Read the project's Amendment 1 (Domain Primitives) from `docs/governance/amendments.md`.
Print them if present.

If Amendment 1 is absent entirely:
  "Amendment 1 absent — domain primitives have not been defined.
   Run /spec fast or /spec collect to generate and ratify them."

If Amendment 1 is present but still marked PROPOSED:
  "Amendment 1 present but not yet ratified.
   Read the primitives above and confirm they are correct, then run:
   /governance ratify 1
   (or manually remove the PROPOSED line from docs/governance/amendments.md)"

**Step 0d — Police check:**
Invoke `police` agent to audit the last 10 commits and the current session for
constitutional violations. Run this before printing the session header.

New project detection: if git log returns no commits, or case_law.md exists but
is empty (only placeholder text), skip the history audit and print:
  "Police check: new project — no history to audit."

If police reports any VIOLATION: print the violation report and stop.
Print: "Constitutional violation detected. Justice must rule before session continues.
See police report above."

If police reports only WARNINGs: print them inline in the session header under
a "⚠ Warnings" section. Session may proceed but warnings must be acknowledged.

If police reports CLEAN: note "Police check: clean" in the session header.

**Step 0e — Environment pre-check (Errors 6, 9, 10 — expanded from "Package check"):**

  **Part A — Board MCP activation:**
    Read docs/toolchain_config.md ## MCP Server.
    If board MCP URL present:
      Query MCP for: smoke test starter sketches + expected output values.
      Use MCP-provided sketches and expected values for Smoke Tests 1–4.
    If URL missing:
      Print: "Board MCP not configured — using generic smoke test templates."

  **Part B — Library / core compatibility:**
    For each library in docs/toolchain_config.md ## Library Manifest:
      Verify it is compatible with the FQBN core (not just installable).
      Known incompatibility: ArduinoBLE (NINA stack) is NOT compatible with
      nRF52 SoftDevice cores — use Bluefruit/Adafruit nRF52 SDK API instead.
      Flag any incompatibility before writing any sketch.

  **Part C — Local environment scan (Q12 from /spec):**
    Run: `arduino-cli core list` (or `pio platform list`) — is FQBN core installed?
    Run: `arduino-cli lib list` — which target libraries are already installed?
    Ask: "Does your team have a shared drive with pinned library versions?"
    If yes: use those; record in toolchain_config.md.

  **Part D — Python packages (existing behaviour — preserved):**
    Invoke `package-manager` to verify required Python packages.
    Do not proceed until package-manager reports clean.

Print session header:
```
══════════════════════════════════════════════════════════════════
  CRUCIBLE SESSION — $(date)
══════════════════════════════════════════════════════════════════
  Project target:    [project target line from docs/device_context.md]
  Pass/fail:         [threshold line from docs/device_context.md]
  Domain primitives: [from Amendment 1, or "NOT RATIFIED — run /spec"]

  Constitutional record:
    Amendments: [N] ratified  — most recent: [title]
    Case law:   [N] precedents recorded

  Stage status:
    Spec Gate  — Device Specification:    [COLLECTED / NOT STARTED]
    Stage 0    — HIL Toolchain Lock:      [CLOSED / OPEN / NOT STARTED]
    Stage 1    — Simulation:              [CLOSED / OPEN / NOT STARTED]
    Stage 2    — Firmware Integration:    [CLOSED / OPEN / NOT STARTED]
    Stage 3    — Field Test:              [CLOSED / OPEN / NOT STARTED]
    Stage 4    — Host Integration:        [CLOSED / OPEN / NOT STARTED]

  Active toolchain (from docs/toolchain_config.md):
    Board:    [hardware.board]
    Build:    [active_toolchain.build]
    Flash:    [active_toolchain.flash]
    Observe:  [active_toolchain.serial_monitor]
    Wireless: [active_toolchain.wireless_receiver]

  Commands:
    /spec [fast|collect|review|signals|target]  — device spec and domain primitives
    /session [stage]                            — this orchestrator
    /toolchain <subcommand>                     — toolchain janitor
    /judicial hear "<name>" A vs B             — judicial hearing
    /judicial bill <description>               — produce a Bill from evidence
    /governance ratify [1|2|3|4|all]           — ratify amendments interactively
    /advisor hw                                — hardware design suggestions from test results
    /advisor sw [focus]                        — algorithm design suggestions from signal profiles
    /plot evidence <type>                      — evidence collection
    /plot profile <name>                       — signal diagnostic plot
    /compact [target]                          — compact spiralling documentation

  Housekeeping (run any time, no stage gate required):
    code-reviewer agent                    — Article I compliance, FSM integrity, unit checks
    doc-reviewer agent                     — docs completeness and staleness gaps
    constitution-auditor agent             — governance consistency (amendments vs case law)
    bill-drafter agent                     — produce a debate-ready Bill from evidence
    regression-runner agent                — full profile matrix pass/fail against threshold
══════════════════════════════════════════════════════════════════
```

---

## Spec Gate — Device Specification

**Purpose:** Establish what the device does, the specific problem it solves, which signals
it produces, and the domain primitives all other agents reason against.
**Must complete before:** Stage 0, toolchain init, firmware writing, or any hearing.
**Command:** `/spec collect`

When `/session spec` is invoked, run `/spec collect` in full.
When `/session status` is invoked and the spec gate is NOT COLLECTED, print:

```
⚠  SPEC GATE OPEN — run /spec collect before proceeding
   Without a collected spec, domain primitives are undefined and Article I
   cannot be enforced. Attorneys have no evidence base. hw-advisor cannot advise.
```

### Spec Gate exit criteria
- [ ] `docs/device_context.md` Device Purpose section filled (no placeholder text)
- [ ] Project target stated in one sentence (the specific hard case)
- [ ] Pass/fail threshold stated as a measurable value
- [ ] Signal Inventory table populated (at least one signal per domain primitive)
- [ ] Domain primitives confirmed by human
- [ ] Amendment 1 ratified and written to `docs/governance/amendments.md`

**[JUSTICE GATE SPEC]** All criteria met → Spec Gate COLLECTED.
Before closing: invoke `police` to confirm no violations exist in the governance record.
Invoke `agent-updater` after Amendment 1 is ratified — domain primitives must propagate
to code-reviewer, sw-advisor, hw-advisor, and bill-drafter.
Run `/spec review` at any time to check for gaps.

---

## Stage 0 — HIL Toolchain Lock

**Purpose:** Prove the complete build → flash → run → observe loop works.
**Agents:** package-manager (already ran), uart-reader
**Reference:** docs/testing/hil_testing_guide.md

Implements your project's Smoke Test Order Amendment (see docs/governance/amendments.md).
All four tests must pass in sequence. A failure at any step blocks further stages.

### Smoke Test 1 — Counter

Flash a counter program (increments once per second, prints to USB serial).
Expected: `counter=1`, `counter=2`, `counter=3` — no resets.

Failure modes:
- Blank: charge-only USB cable or wrong board variant
- Garbage: baud rate mismatch
- Resets: watchdog or SoftDevice issue

[GATE 0.1] Pass → continue.

### Smoke Test 2 — Sensor Readout

Flash a sensor readout program (reads sensor, prints raw values to USB serial).
Expected: physically plausible values (gravity on Z for IMU; room temp for temperature sensor; etc.)

Failure modes:
- "Sensor init FAILED": I2C address wrong, power-enable pin not asserted
- All zeros: I2C not responding, check pin assignment
- Wrong units: sensor returns g, firmware multiplies by 9.81f (or vice versa)

[GATE 0.2] Pass → continue.

### Smoke Test 3 — Output Format Stub (Error 7)

Flash a stub firmware that emits **hardcoded** UART events in the format defined
in docs/toolchain_config.md ## Firmware UART Format.
Expected: all event fields appear in correct format, no garbled output, no reset.
Pass criterion: output parseable by the host tool / src/analysis.py.

**Note:** This test does NOT validate algorithm correctness — that is Stage 1.
It only confirms the output pipeline (UART → host parser) is functional.

Example hardcoded output (replace with your firmware UART format):
```
STEP,1000,1.02,45.3
STANCE,1100,520,0
SESSION_END
```

Failure modes:
- No output: UART not initialised or wrong baud rate
- Garbled output: format mismatch — check pattern in toolchain_config.md
- Parser rejects output: update src/analysis.py event regex

[GATE 0.3] Pass → continue.

### Smoke Test 4 — Algorithm over Wireless

Flash wireless firmware, run host receiver script.
Expected: same algorithm output received on host.

Failure modes:
- Device not found: name truncation in advertising packet
- Connected but no data: write gated on `connected()` check; write unconditionally
- Truncated lines: MTU fragmentation; shorten format strings or add line-buffer in receiver

[GATE 0.4] **Stage 0 CLOSED.**

**[JUSTICE GATE S0]** All four tests pass → before closing:
1. Invoke `police` to confirm no violations in this stage's work.
2. Invoke `stage-compactor` to close Stage 0.
3. Run `/toolchain lock` to stamp toolchain config as Stage 0 validated.
4. If Amendment 3 (Toolchain Alignment) was ratified this stage, invoke `agent-updater`.

---

## Stage 1 — Simulation

**Purpose:** Validate algorithm on a physics model of your device domain.
Simulation can also accept field measurement data as input (field data replay).
**Entry condition:** Stage 0 closed.

### Stage 1 pre-entry — Python environment scan (Error 19)

Before the scaffold check, run:
```
pip list --format=json   (or pip freeze)
```
Store available package names in session context.
Before writing any `src/` file: check all imports against available packages.
Flag any import not in the list and ask the human before writing.

### Stage 1 pre-flight (Error 24 — runs before every full simulation)

Before running `/regression` or any full simulation profile:
```
1. python -m py_compile src/signals.py src/algorithm.py
   → non-zero exit: stop, show error, do not run simulation
2. python -c "from src.signals import generate; from src.algorithm import run; \
              r = run(generate('walk', n_steps=1)); print('pre-flight OK:', r)"
   → import error or runtime error: stop, show error
```
Only if both pass: proceed to full simulation profile.

### Plot stop rule (Error 20 — applies after any plot-generation step)

After generating any diagnostic plot or signal visualisation:
```
Print: plot path + one-line summary of what the plot should show.
STOP. Do not read, interpret, or draw conclusions from the plot.
Wait for human to confirm "plot looks correct" or "proceed" before continuing.
Ask explicitly if no confirmation received: "Does the plot look as expected?"
```

### Scaffold check (first run of Stage 1 only)

Before running any simulation, check whether `src/events.py` exists:
- **Exists:** print "Scaffold: src/ modules present — proceeding."
- **Missing:** print the following and stop:
  ```
  SCAFFOLD REQUIRED: Project Python modules not yet generated.
  Before running simulation:
    1. Fill in docs/toolchain_config.md ## Firmware UART Format section
       (session_end_marker + at least one [[event]] block)
    2. Run /toolchain scaffold
  This generates src/events.py, src/analysis.py, src/plot.py (infrastructure)
  and src/signals.py, src/algorithm.py (stubs to implement).
  Signal-only simulation requires src/signals.py and src/algorithm.py to be
  implemented. Renode simulation requires the firmware ELF.
  ```

### Simulation paths

Stage 1 supports two simulation paths. Both are valid. The stage gate requires
at least one run from each.

```
Path A — Signal-only (fast, no firmware):
    src/signals.py::generate(profile, n_steps)   → sensor samples
         │
         ▼
    src/algorithm.py::run(samples)               → metrics dict
         │
         ▼
    Validate metrics against pass/fail threshold
    → plotter (signal plot mandate)

    When to use: algorithm development, fast iteration, pre-firmware validation
    Prerequisite: src/signals.py and src/algorithm.py implemented (not stubs)

Path B — Renode (thorough, firmware in emulator):
    src/signals.py::generate(profile, n_steps)   → sensor samples
         │
         ▼
    RenoneBridge(elf_path).run(samples)          → UART text
         │
         ▼
    src/analysis.py::PARSER.parse_log(text)      → events
         │
         ▼
    Extract metrics → validate against threshold
    → uart-reader (print to terminal) + plotter

    When to use: firmware parity check, Stage 1 gate validation
    Prerequisite: firmware ELF + Renode installed

Path A+B — Both (parity check):
    Run A then B on same profile → compare_paths() → divergence report
    Any divergence = finding for Justice. Do not fix firmware until divergence
    is explained: the Python model may be wrong, OR the firmware may be wrong.

Field data replay (any stage):
    Replace Path A's signal generator with field UART log replay
    (src/analysis.py parses the field log the same way it parses Renode output)
    → If replay diverges from simulation: physics model is wrong — update model,
      re-run simulation, THEN look at firmware
```

**The simulator-operator agent handles path selection automatically.**
Run `/plot-profile` for signal diagnostic plots after any algorithm parameter change.

### Exit criteria
- [ ] Path A (signal-only): algorithm produces correct output on physics model for all profiles
- [ ] Path B (Renode): firmware produces correct output for at least one profile
- [ ] Path A+B parity: Python model and firmware agree within project tolerance (no unexplained divergence)
- [ ] Algorithm tested under conditions where the correct answer is non-zero (mandatory — zero-output trap)
- [ ] Signal plots reviewed by Justice
- [ ] No unexplained deviation between simulation and any available field data

**[JUSTICE GATE S1]** → before closing:
1. Run `/code-review` — include `src/` scaffolded modules in the audit.
   Any ARTICLE-I-VIOLATION blocks gate. This is the confirmation step
   required by Amendment 11 (Scaffold Immutability) — once the gate closes,
   src/ modules are frozen. Print: "Amendment 11: src/ modules confirmed at
   Stage 1 gate — re-scaffold now requires explicit human authorization + Bill."
2. Run `/regression` — all profiles must pass threshold before gate. Run with both
   paths if Path B (Renode) is available: signal-only matrix first, then Renode matrix.
3. Invoke `police` to confirm no unauthorized changes this stage.
4. Invoke `stage-compactor` to close Stage 1.

---

## Stage 2 — Firmware Integration

**Purpose:** Run the validated algorithm on real hardware via USB serial.
Cross-validate that the dev kit port matches simulation predictions.
**Entry condition:** Stage 1 closed.

### Stage 2 pre-flight (Error 24 — runs before every flash)

Before flashing firmware:
```
arduino-cli compile --fqbn [FQBN] firmware/
(or: pio run --target compiledb)
→ compile error: stop, show error, do not flash
```
Only if compile succeeds: proceed to flash.

### Pipeline

```
1. Build and flash production firmware (algorithm + wireless output)
2. USB serial monitoring path:
   Stimulate sensor / apply test input
   → capture event/reading lines
   → compare against Stage 1 simulation prediction
3. Sensitivity test:
   Apply known perturbation (asymmetry, offset, anomaly — per your domain primitive)
   → output must change measurably
```

Tolerance: hardware vs simulation per your domain-specific Amendment
(set in your project's domain-primitive Amendment)

### Exit criteria
- [ ] Output within tolerance of Stage 1 simulation on standard stimulus
- [ ] Output changes measurably under known perturbation (sensitivity confirmed)
- [ ] No firmware resets in ≥ 10 min continuous session

**[JUSTICE GATE S2]** → before closing:
1. Run `/code-review` — any ARTICLE-I-VIOLATION or FSM-DEAD-STATE blocks gate.
2. Run `/doc-review` — any BLOCKER in Test Results (no data for this stage) blocks gate.
3. Invoke `police` to confirm no unauthorized firmware changes since Stage 1 gate.
4. Invoke `stage-compactor` to close Stage 2.

---

## Stage 3 — Field Test

**Purpose:** Real device, real conditions. Data captured and fed back to Stage 1.
**Entry condition:** Stage 2 closed.

### Pre-flight (Article II)

Before any field test data collection:
- Justice reviews Stage 2 evidence
- Justice confirms hardware is ready for field deployment
- **JUSTICE APPROVES FIELD TEST** — hard gate, no agent self-selects

### Protocol

Define your field test protocol per your device domain.
At minimum:
1. Baseline run — nominal conditions, measure primary output
2. Perturbation run — known deviation from nominal, measure output change
3. Edge case run — extreme but realistic conditions
4. Data capture — capture raw sensor output via `uart-reader` during each run.
   Save logs to `docs/field_data/<session_date>_<profile>.log`.
   Record in Test Results section of `docs/device_context.md`.

### Feedback loop to simulation

After field test, replay field data through Stage 1 simulation:

```
uart-reader captures field session UART log
         │
         ▼
docs/field_data/<date>_<profile>.log
         │
         ▼
/regression --profile <field_profile>    ← add field log as a replay profile
         │
         ├─ Simulation matches field: physics model is valid ✓
         └─ Simulation does not match:
                Update physics model (Bill required)
                Re-run /regression
                Do NOT fix firmware until simulation matches field data
```

The field replay profile name is added to the Signal Inventory in `docs/device_context.md`
so `/regression` and `regression-runner` can discover and run it.

### Exit criteria
- [ ] Baseline run: output within target range
- [ ] Perturbation run: output changes measurably in expected direction
- [ ] Field data replayed in simulation: model validated or updated
- [ ] All deviations explained and recorded in case law

**[JUSTICE GATE S3]** → before closing:
1. Invoke `police` to confirm field test protocol was Justice-approved (Article II).
2. Invoke `stage-compactor` to close Stage 3.

---

## Stage 4 — Host Integration

**Purpose:** Connect device to smart home hub, gateway, cloud, or other consumer system.
**Entry condition:** Stages 0–3 all closed.

### Pipeline

```
1. Host system connection (MQTT, Matter, BLE GATT, REST API)
2. Data ingestion verification:
   → Host receives correct values
   → Host handles device disconnect/reconnect gracefully
3. Automation trigger test:
   → Define one automation (light on = occupancy detected, alert = threshold exceeded)
   → Verify trigger fires correctly and within latency budget
4. Long-run stability (≥ 30 min session)
   → No dropped connections, no corrupt data, no false triggers
```

### Exit criteria
- [ ] Host receives correct values matching Stage 3 field test output
- [ ] Automation trigger fires correctly with latency < [your target]
- [ ] 30-min stability: no resets, no dropped data, no false triggers

**[JUSTICE GATE S4 — FINAL]** → before closing:
1. Invoke `police` for a full audit — this is the final constitutional record review.
2. Invoke `stage-compactor` to close Stage 4.

---

## Session Subcommands (Errors 23, 25)

### /session pause
Writes checkpoint with `status: PAUSED` to `docs/governance/session_checkpoint.md`.
Prints `next_action` so the session can be resumed cleanly.

### /session refresh (Error 25)
Re-reads:
- `docs/governance/amendments/amendment_01_domain_primitives.md` (Amendment 01)
- `docs/governance/session_checkpoint.md` (if exists)
- `docs/governance/session_context.md`

Prints: corpus graph summary (`python -m crucible.corpus.graph --summary`)
Use this when session quality degrades or after long pauses.

### /session clean (Error 25 — memory cleaning)
Reads `docs/governance/session_context.md`.
Removes any "Open threads" entries marked `[RESOLVED]` or `[CLOSED]`.
Updates "Current position" to reflect present step.
Re-writes the file cleanly (no stale entries, no duplicate primitives).
Prints: "Working memory cleaned — [N] resolved threads removed."

**Automatic trigger:** At every stage gate close (Justice Gate), before stage-compactor
runs, `/session clean` executes automatically. The cleaned `session_context.md` is
copied into `docs/governance/stage_[N]_closeout.md` as the structured handoff record,
then reset to a fresh template for the next stage.

---

## Constitutional References

- Article I: all thresholds trace to domain primitives — not to data fitting
- Article II: no field test or host deployment without Justice approval
- Amendment 1: domain primitives (set by /spec collect — your device-specific version)
- Amendment 2: stage gate order
- Amendment 3: toolchain alignment
- Amendment 4: three-strike escalation — three failures → /hear before new approach

## New project checklist

```
[ ] /spec collect          — device purpose, project target, signal inventory, Amendment 1
[ ] agent-updater          — run after Amendment 1 ratified (propagate primitives)
[ ] /toolchain init        — register board, pins, libraries, repos
[ ] Ratify Amendments 2–4  — remove PROPOSED prefix in amendments.md for each
[ ] agent-updater          — run after Amendments 2–4 ratified (propagate stage gate/toolchain/three-strike)
[ ] /session 0             — HIL toolchain lock (four smoke tests) → /toolchain lock
[ ] /session 1             — simulation validation
[ ] /session 2             — firmware integration
[ ] /session 3             — field test
[ ] /session 4             — host integration
```
