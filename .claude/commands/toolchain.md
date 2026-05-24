Toolchain Janitor — gatekeeper and RAG setter for all hardware, pin, firmware library, and repository configuration.

This command is the single entry point for recording, updating, and validating what tools,
libraries, and boards are in use. Every other agent (/session, /hear, /plot-profile) reads
from docs/toolchain_config.md before acting. This command is the only thing that writes it.

Usage: /toolchain <subcommand> [args]

Subcommands:
  detect                  — probe USB/environment for connected boards before init
  status                  — print current toolchain config in full
  init                    — interactive setup from scratch (prompts for each section)
  add hw                  — add or update the hardware record (board, MCU, IMU)
  add pins                — add or update pin map entries
  add lib <name>          — add a firmware library (name, version, source, purpose)
  add repo <path_or_url>  — register a git repository (path/URL, branch, purpose)
  block <label>           — mark a toolchain layer as blocked (prompts for reason)
  unblock <label>         — propose lifting a block (requires /hear — cannot self-approve)
  lock                    — mark config as Stage 0 validated (requires Stage 0 pass evidence)
  validate                — run gatekeeper checks: conflicts, amendment violations, missing fields
  diff                    — show what has changed since last lock
  scaffold                — generate src/events.py, src/analysis.py, src/plot.py from device_context.md + toolchain_config.md

If no subcommand: print status and list available subcommands.

---

## The Config File

All state lives in `docs/toolchain_config.md`.
- Human-readable and human-editable at any time
- Structured with section headers so agents can grep for specific records
- Version-controlled — every janitor write is a git commit
- The janitor never overwrites human edits without showing a diff first

Agents that need toolchain context must read this file first. They must not assume a toolchain
from CONSTITUTION.md amendments alone — amendments say what is allowed, the config file says what
is currently wired up.

---

## Subcommand Procedures

### /toolchain status

Read `docs/toolchain_config.md` in full and print:
1. Lock status and date
2. Hardware summary (one line per device)
3. Active toolchain table
4. Blocked toolchain log
5. Library manifest (name + version)
6. Repo registry (name + purpose)
7. Any validation warnings (missing required fields, blocked toolchain in active slot)

---

### /toolchain detect

Probe the environment for connected boards before running init. Run this first on any
new project to eliminate the most common init errors (wrong FQBN, unknown variant).

**Step 1 — USB board detection**

Run the following in order, stopping when a match is found:
1. `arduino-cli board list` — lists connected boards with FQBN
2. `pio boards --installed` (fallback if arduino-cli not available)
3. `ls /dev/tty.usbmodem* /dev/tty.usbserial* /dev/ttyACM* /dev/ttyUSB*` (last resort — lists ports only)

If a board is detected:
  - Print: "Detected: [board name] on [port] — FQBN: [fqbn]"
  - Cross-reference against `.claude/toolchain/boards.json` board database
  - If the board is in the database: print pre-populated defaults and known issues:
    ```
    Board: [name]
    FQBN:  [fqbn]
    Flash: [default flash method]
    Known issues:
      [list from board database]
    ```
  - Ask: "Use these defaults for /toolchain init? (yes / customize)"

If no board is detected:
  - Print: "No board detected via USB. Connect your board and re-run /toolchain detect,
    or enter board details manually during /toolchain init."

**Step 2 — Library resolution**

If a sensor or library name is mentioned in the chat or in `docs/device_context.md`
Signal Inventory, run:
  `arduino-cli lib search "<library name>"` for each one
  Report the latest stable version found.
  Print: "Auto-pin suggestion: [LibraryName] v[version] (latest stable). Confirm?"

---

### /toolchain init

Interactive setup. Ask the human for each section in order. After each section,
print what you recorded and ask for confirmation before continuing to the next.

Suggestion: run `/toolchain detect` first — it pre-populates FQBN, flash method, and
known issues for recognized boards, reducing manual entry.

Do not guess values — every field must come from human input or be explicitly left blank.
Exception: if `/toolchain detect` produced auto-pin library versions, those are
pre-populated with `[AUTO-PINNED — confirm]` tags and the human confirms or overrides.

Sections in order:
1. Hardware record (board, MCU, IMU)
2. Pin map (run conflict check automatically after entry — see /toolchain validate)
3. Active firmware toolchain
4. Blocked toolchains
5. Firmware libraries (auto-pin via lib resolver if library name given without version)
6. Git repositories

After all sections: run validate, then ask Justice to confirm before writing the file.

---

### /toolchain add hw

Prompt for:
- Board model (e.g., "Seeed XIAO nRF52840 Sense 102010448")
- MCU (e.g., "nRF52840, ARM Cortex-M4F, 64 MHz")
- Sensors on board (e.g., "LSM6DS3TR-C IMU, I2C 0x6A, WHO_AM_I=0x6A")
- Any external hardware (PPK2, J-Link, oscilloscope, etc.)
- Notes (e.g., "Must be Sense variant — on-board IMU only on Sense, not standard")

Write to Hardware section of docs/toolchain_config.md.

---

### /toolchain add pins

Prompt for each pin entry:
- Signal name (e.g., "IMU_POWER", "IMU_SDA", "LED_RED")
- Arduino pin number (e.g., "15", "4", "—")
- nRF52840 port/pin (e.g., "P1.08", "P0.07")
- Function description
- Caution if any (e.g., "P0.27 = SCL — do not use as button")

Present current pin map before prompting, so human can see what already exists and choose
to add, update, or remove entries.

Write to Pin Map section of docs/toolchain_config.md.

---

### /toolchain add lib <name>

Prompt for:
- Library name
- Version (exact — not "latest")
- Source (Arduino library manager ID, GitHub URL, or local path)
- Purpose (one sentence: what it enables in this project)
- Known issues or patches (e.g., "setBitOrder() removed on ARDUINO_ARCH_MBED — patched in LSM6DS3.cpp")

Write to Library Manifest section. If library already exists, show diff before overwriting.

---

### /toolchain add repo <path_or_url>

Prompt for:
- Repo path (local) or URL (remote)
- Active branch
- Purpose (one sentence: what this repo contributes)
- Agent commands or scripts available in this repo that are usable cross-repo
- Access notes (e.g., "read-only reference — do not commit here from other project sessions")

Write to Repository Registry section.

---

### /toolchain block <label>

Prompt for:
- Which toolchain layer is being blocked (build, flash, serial monitor, simulation, etc.)
- The specific tool/framework being blocked
- Reason (must cite a failure mode — Amendment 4 three-strike rule evidence, or prior smoke test failure)
- Date
- What triggered the block (test result, error message, simulation failure)

Gatekeeper rule: a block recorded here is binding on all agents. An agent that attempts to
use a blocked toolchain must stop and report the block to the human rather than proceeding.

Write to Blocked Toolchains section.

---

### /toolchain unblock <label>

This subcommand cannot complete by itself. It must:
1. Show the current block record
2. Print: "Unblocking a toolchain requires a Judicial Hearing per Amendment 3 (Toolchain Alignment)."
3. Prompt: "Invoke /hear to open a hearing on this unblock? (yes/no)"
4. If yes: invoke /hear with a pre-filled declaration:
   Hearing: "Unblock [label] toolchain"
   Position A: "lift block — [human's reason]"
   Position B: "keep block — prior failure evidence stands"
5. Do not modify docs/toolchain_config.md until the Justice rules in favour of unblocking.

---

### /toolchain lock

Mark the config as Stage 0 validated. Requires the human to confirm:
- Stage 0 HIL smoke tests passed (counter ✓, IMU ✓, algo USB ✓, algo BLE ✓)
- All four test pass evidence logged (timestamps or session log path)

Print a lock summary:
```
══════════════════════════════════════════════════════════════
TOOLCHAIN CONFIG LOCKED
Date: [date]
Stage 0 evidence: [log path or "confirmed by human"]
Hardware: [board name]
Active firmware toolchain: [FQBN]
Libraries: [N] registered
Repos: [N] registered
Blocked: [N] toolchain layers
══════════════════════════════════════════════════════════════
```

Write lock record to docs/toolchain_config.md and commit.

---

### /toolchain validate

Run all gatekeeper checks. Print a report for each check.

Checks:
1. **Blocked toolchain in active slot** — if any layer's active tool appears in the Blocked list, flag as ERROR
2. **Missing required fields** — Hardware: board, MCU, IMU. Toolchain: build FQBN, flash method, serial monitor. Flag blank required fields as WARNING
3. **Library version pinned** — any library with version = "latest" or blank → WARNING
4. **Toolchain Amendment alignment** — active toolchain table in config must match the table in docs/governance/amendments.md. Mismatch → ERROR
5. **Repo paths exist** — for local repo paths: check the path exists on disk. Missing → WARNING
6. **Pin conflicts (declared)** — if two signals share the same nRF52840 port/pin → ERROR (e.g., P0.27 as both SCL and button)
7. **Blocked toolchain without reason** — a block entry with no failure mode cited → WARNING (Amendment 7 requires evidence)
8. **Board database conflict check** — if the declared board matches a known board in
   `.claude/toolchain/boards.json`, cross-reference the pin map against the board's
   known shared-function pins. For each conflict found: → WARNING with the specific
   pin, its shared functions on this board, and which of the two functions the user
   has declared.
   Example: "WARNING: P0.27 declared as I2C SCL — on Seeed XIAO nRF52840 Sense,
   P0.27 is also used by the SBD/I2C pin shared with the on-board button pull-up.
   Confirm this does not conflict with your button wiring."

Print each check as:
  [PASS]    <check name>
  [WARNING] <check name> — <detail>
  [ERROR]   <check name> — <detail> — must resolve before Stage 0

Overall result:
  CLEAN — all checks pass
  WARNINGS ONLY — can proceed; review warnings
  ERRORS PRESENT — do not proceed with Stage 0 until errors resolved

---

### /toolchain diff

Compare the current docs/toolchain_config.md against the last locked version (git):
```bash
git diff HEAD~1 docs/toolchain_config.md
```

Print a human-readable summary of what changed since the last lock:
- New hardware added
- Pin map changes
- Libraries added/updated
- Repos added
- Blocks added or lifted
- Lock status changed

---

### Smoke Test Diagnosis Mode

When a Stage 0 smoke test fails, classify the failure before counting it as a strike.

**Failure classification:**

| Failure type | Classification | Counts toward Amendment 4 three-strike? |
|---|---|---|
| Wrong FQBN / board not found | Operational (config) | NO |
| Wrong pin number or assignment | Operational (config) | NO |
| Library missing or wrong version | Operational (config) | NO |
| Flash failed (port not found, permission denied) | Operational (environment) | NO |
| UF2 `fcopyfile` error on macOS | Operational (known macOS quirk — flash succeeded) | NO |
| Firmware flashed, device silent (no UART output) | Constitutional (algorithm/firmware) | YES |
| Firmware flashed, wrong output (bad values) | Constitutional (algorithm) | YES |
| Sensor returns unexpected value (WHO_AM_I wrong) | Operational unless firmware confirmed correct | Diagnose first |
| BLE device not found in scan | Operational (config — name truncation likely) | NO |

**Diagnosis trees for each Stage 0 smoke test:**

**Smoke Test 1 — Counter (USB):**
- No serial output → check port and baud rate first (operational); if port correct, firmware likely not running (constitutional)
- Counts increment wrong → constitutional (algorithm)
- `fcopyfile` error during UF2 → known macOS quirk; flash likely succeeded — re-check port

**Smoke Test 2 — Sensor/IMU (WHO_AM_I):**
- Returns 0x00 → likely wrong I2C address in firmware — check sensor datasheet for correct address (operational)
- Returns 0xFF → I2C bus floated — check SDA/SCL wiring and pull-up resistors (operational)
- Returns EIO / errno -5 → pin conflict — check if SCL pin is shared with another function (operational; see board database)
- Returns correct ID → sensor wired correctly; proceed

**Smoke Test 3 — Algorithm output (USB):**
- Output present but value always 0 or constant → constitutional (algorithm — check FPU, signed/unsigned, integer truncation)
- Output absent → operational (serial port issue) or constitutional (firmware crash)
- Output present, value changes with motion → PASS

**Smoke Test 4 — Wireless (BLE/WiFi):**
- Device not found in scan → check advertised name first: run `hcitool lescan` (Linux) or `nRF Connect` app and look for any device, including truncated names. BLE advertising names are often truncated to ≤8 chars by the stack. (operational)
- Device found but cannot connect → operational (pairing, MTU, service UUID)
- Device connects but produces no output → constitutional (firmware not writing to characteristic)
- UART lines fragment across packets → operational; increase BLE MTU or shorten format strings

**Three-strike fast-path rule:**

Operational failures (config, wiring, environment) do NOT count toward the Amendment 4
three-strike count. Only constitutional failures (algorithm produces wrong output, firmware
crashes) count.

When a smoke test fails:
1. Classify the failure using the diagnosis tree above
2. If operational: fix the config/wiring issue and retry — do NOT increment the strike count
3. If constitutional: increment the strike count and document the attempt
4. If ambiguous: ask the human to classify before retrying

Print the classification explicitly:
  "[OPERATIONAL] Smoke Test 2 failed — I2C address mismatch. Fix pin assignment and retry.
   Strike count unchanged."
or:
  "[CONSTITUTIONAL] Smoke Test 3 failed — algorithm output constant 0. Strike 1 of 3.
   If this happens twice more, Amendment 4 escalation is required."

---

### /toolchain scaffold

Generate project-specific Python modules from the device spec and toolchain config.
Run this before Stage 1 (simulation). Re-run whenever you add signals to the Signal Inventory
or change the firmware UART format.

**Reads:**
- `docs/device_context.md` — Signal Inventory (event names, field names, units), Amendment 1 domain primitives
- `docs/toolchain_config.md` — `## Firmware UART Format` section (event definitions, session_end_marker)

**Generates:**
- `src/events.py` — dataclass per UART event type, derived from Signal Inventory
- `src/analysis.py` — project UartParser instance wired to the firmware's UART patterns
- `src/plot.py` — plot functions named after the domain primitives (wraps crucible.signal.plot generics)

**Amendment 11 guard (re-run check):**

Before generating any files, check whether `src/events.py` already exists:
- **Does not exist:** first scaffold — proceed.
- **Exists:** print the following and stop:
  ```
  SCAFFOLD BLOCKED (Amendment 11 — Scaffold Immutability):
  src/ modules were already generated and confirmed.
  Regenerating them without authorization is a Bill-level change.

  To re-scaffold, the human must explicitly state: "re-scaffold approved."
  This statement must be followed by a Bill recording what changed in
  the Signal Inventory or Firmware UART Format and why.
  ```
  If the human's current message contains "re-scaffold approved": proceed, then
  print a reminder that the enacted Bill must be recorded before the session ends.

**Procedure:**

1. Read `docs/device_context.md`. Extract:
   - Domain primitives from Amendment 1 (name, unit for each)
   - Signal Inventory table (event name, field names, units for each row)

2. Read `docs/toolchain_config.md` `## Firmware UART Format`. Extract:
   - `session_end_marker` (default: `SESSION_END` if not set)
   - Each `[[event]]` block: name, pattern, fields, types
   - Binary export block if present

3. **Guard:** if `## Firmware UART Format` is empty or contains only `> [` placeholder text:
   ```
   SCAFFOLD BLOCKED: Firmware UART format not defined.
   Fill in docs/toolchain_config.md ## Firmware UART Format before scaffolding.
   Minimum required: session_end_marker and at least one [[event]] block.
   ```

4. Generate `src/events.py`:
   - One `@dataclass` per event type from the Signal Inventory
   - Field names and types from toolchain_config event definitions
   - Imports: `from __future__ import annotations`, `from dataclasses import dataclass`
   - Comment header: "Generated by /toolchain scaffold — re-run to update"
   - Include `SessionEndEvent` as a pass-through import from `crucible.signal.events`

5. Generate `src/analysis.py`:
   - Imports: `from crucible.signal.analysis import UartParser, EventDefinition`
   - One `EventDefinition(...)` per event block from toolchain_config
   - Single `PARSER = UartParser([...], session_end_marker="...")` instance
   - `parse_log(text)` and `parse_line(line)` top-level functions delegating to PARSER

6. Generate `src/plot.py`:
   - Imports: `from crucible.signal.plot import plot_sensor_trace, plot_metric_bar, plot_metric_timeline`
   - One wrapper function per domain primitive, named e.g. `plot_<primitive_name>_comparison(...)`
   - Wrapper fills in `metric_label`, `metric_unit`, `threshold` from Amendment 1 pass/fail threshold
   - Comment header: "Generated by /toolchain scaffold — re-run to update"

7. Generate `src/signals.py` **stub** (if it does not already exist):
   - Comment header: "Signal generator stub — implement generate() for each profile"
   - One `generate(profile, n_steps)` function with `raise NotImplementedError` per profile
     listed in the Signal Inventory / Operating Envelope of docs/device_context.md
   - Profile names extracted from the Signal Inventory table
   - Include a docstring explaining the expected return type: `np.ndarray (n_steps, C)`
     where C = number of sensor channels from the UART format
   - Do NOT overwrite if the file already exists and contains non-stub code
     (detected by absence of `raise NotImplementedError`)

8. Generate `src/algorithm.py` **stub** (if it does not already exist):
   - Comment header: "Python algorithm stub — implement run() to mirror firmware logic"
   - One `run(samples)` function with `raise NotImplementedError`
   - Return type documented as `dict[str, Any]` keyed by domain primitive names from Amendment 1
   - Include a docstring listing each domain primitive name, unit, and expected value range
   - Do NOT overwrite if the file already exists and contains non-stub code

9. Create `src/__init__.py` if it does not exist (empty file).

10. Print scaffold summary:
    ```
    SCAFFOLD COMPLETE
      src/events.py    — [N] event types: [names]            [GENERATED]
      src/analysis.py  — parser, [N] event defs              [GENERATED]
      src/plot.py      — [N] plot wrappers                    [GENERATED]
      src/signals.py   — generate() stub, [N] profiles        [STUB — implement]
      src/algorithm.py — run() stub                           [STUB — implement]
    
    Next steps:
      1. Implement src/signals.py::generate() — one branch per profile
         Returns np.ndarray (n_steps, [N channels]) physical-unit sensor data
      2. Implement src/algorithm.py::run() — Python model of the firmware algorithm
         Returns dict keyed by Amendment 1 domain primitive names
      3. Run /session 1 to start simulation stage (signal-only path active immediately)
    ```

**Re-run behaviour (Amendment 11):**
- Always overwrites `src/events.py`, `src/analysis.py`, `src/plot.py` (requires re-scaffold authorization after Stage 1 gate — see Amendment 11 guard above)
- Never overwrites `src/signals.py` or `src/algorithm.py` if they contain non-stub code
  (these are engineer-authored and change via Bills, not via scaffold re-run)

---

## Gatekeeper Rules (for all other agents)

When any agent (/session, /hear, /plot-profile, simulator-operator, etc.) is about to
take a toolchain-dependent action, it must:

1. Read docs/toolchain_config.md
2. Check that the tool it is about to use is in the Active Toolchain section
3. Check that the tool is NOT in the Blocked Toolchains section
4. If blocked: stop and print:
   "TOOLCHAIN BLOCKED: [tool] is recorded as blocked in docs/toolchain_config.md.
    Reason: [reason]. Use /toolchain unblock to propose lifting this block."
5. If not found in either list: stop and print:
   "TOOLCHAIN NOT REGISTERED: [tool] is not in docs/toolchain_config.md.
    Use /toolchain add to register it before use."

This rule applies to: build tools, flash methods, serial monitor tools, Python packages,
simulation frameworks, and external hardware interfaces.

---

## RAG Usage by Other Agents

Every agent that needs toolchain context should read these specific sections from
docs/toolchain_config.md (grep targets):

| Agent need | Section to read |
|-----------|----------------|
| What FQBN to build for | `## Active Firmware Toolchain` |
| What pin is the IMU on | `## Pin Map` |
| What library version to use | `## Library Manifest` |
| Is this toolchain blocked? | `## Blocked Toolchains` |
| What repos can I reference? | `## Repository Registry` |
| What board is connected? | `## Hardware` |
| What does firmware emit over UART? | `## Firmware UART Format` |
| What sentinel marks session end? | `## Firmware UART Format` → `session_end_marker` |
| What modules to import for parsing? | `src/analysis.py` (generated by `/toolchain scaffold`) |

Agents must not ask the human for toolchain details that are already in this file.
If the file is missing or incomplete for the required section, run /toolchain validate
and report the gaps to the human before proceeding.

---

## Constitutional References

- Article II: no toolchain switch without human decision (the block/unblock gate enforces this)
- Amendment 4: three-strike rule — block entries in this file are the formal record of strikes
- Amendment 2: stage gate order — Stage 0 lock (HIL confirmation) is a hard gate in the stage sequence
- Amendment 3: toolchain alignment — this file is the live implementation of Amendment 3's active toolchain record

Now parse "$ARGUMENTS":
  First word is the subcommand (status, init, add, block, unblock, lock, validate, diff).
  For "add": second word is the type (hw, pins, lib, repo).
  For "block" / "unblock": remaining words are the label.
  If no subcommand: print status then list subcommands.
