# Example: FPGA Sensor Change Management — Avionics LRU Demo

**Hardware:** Intel MAX 10 Eval Kit (EK-10M08E144), algorithm runs on host PC  
**Domain:** Avionics inertial sensing — LSM6DS3 → LSM6DSO32 IMU substitution  
**Unit under change:** Attitude sensor front-end in a DAL C Data Concentrator Unit (DCU)  
**Applicable standards:** DO-254 (FPGA assurance), DO-160G (environmental qualification)  
**Demo duration:** ~3 minutes live, hardware in hand

---

## The problem this demo proves

In avionics programs, sensor EOL notices arrive mid-program. Swapping a "same-family"
sensor looks trivial — same vendor, same connector, same voltage — until it isn't.
The standard outcome without governed change management:

- Engineer swaps the sensor, gets silence (or wrong data)
- Spends hours with a logic analyzer finding the root cause
- Writes the change record manually after the fact
- Hopes nothing was missed before the next DO-254 audit

The governed outcome with Crucible:

- Engineer submits the swap as a bill — Crucible flags every register delta immediately,
  before hardware is touched, because it has already read both datasheets
- Engineer applies the flagged fixes, does the swap, it works first time
- Change record with primitive citations, approval conditions, and precedents is
  auto-generated at the moment of approval — not written by hand after the fact

The demo shows the governed path live, then shows the auto-generated artifact.
The "half a day with a logic analyzer" path is described but not acted out.

---

## Scenario

An avionics Data Concentrator Unit (DCU) uses an FPGA front-end to acquire 6-axis IMU
data from an LSM6DS3 (ST Microelectronics MEMS IMU) and stream it to a flight data bus.
The LSM6DS3 is approaching natural end-of-life as ST migrates to the DSO-series. The
proposed substitution is the LSM6DSO32 — same vendor, same SPI family, same connector,
but different WHO_AM_I value, different full-scale range encoding, and uncharacterized VRE
at temperature.

**DAL classification:** DAL C (flight data function, not primary flight control)  
**FPGA assurance target:** DO-254 Level C (three objectives: planning, design, verification)

---

## Demo flow (2 min 45 sec)

The demo runs the governed path — Crucible catches the issue before the swap happens.
The "no data" failure scenario is demonstrated via demo_run.py as a side callout,
not as something that occurs during the live demo.

```
0:00 – 0:15   WORKING BASELINE
      MAX 10 board on the table. LSM6DS3 wired up. Run demo_run.py — BEFORE SWAP row:
        BEFORE SWAP — LSM6DS3, WHO_AM_I = 0x69 (FPGA expects 0x69 — PASS)  ✓
      "This is our current sensor. Attitude data is clean."

0:15 – 0:30   SUBMIT THE CHANGE
      Open Crucible. File the sensor swap bill: LSM6DS3 → LSM6DSO32.
      "Same vendor, same SPI family, same connector. Looks like a drop-in.
       Let's see what Crucible says before we touch anything."

0:30 – 0:55   CRUCIBLE FLAGS THE DELTA  (both datasheets pre-loaded — response is instant)
      Crucible responds immediately with the register diff:

        ✗ Primitive 3 — WHO_AM_I: 0x69 → 0x6C
          config_rom.v must update WHO_AM_I_EXPECTED before any streaming test.
          Without this: FPGA init halts, data path never armed, zero output.

        ⚠ Primitive 4 — FS range minimum: ±2g → ±4g (CTRL1_XL[3:2] encoding changed)
          config_rom.v and data_formatter.v sensitivity constant must be updated.
          Without this: 2× sensitivity error, silent, passes all bench tests.

        ✓ Primitive 1 — SPI clock: 10 MHz max on both. Operating point 2 MHz unchanged.
        ✓ Primitive 2 — VDDIO: 3.3V on both. I/O constraints unchanged.

      "It read both datasheets and found two register differences. Before we plugged
       in the new sensor. The first one would have given us silence. The second one
       would have given us plausible-looking wrong data."

0:55 – 1:10   APPLY THE FIXES
      Two constants changed in config_rom.v:
        WHO_AM_I_EXPECTED = 8'h6C   // Traces to: Init Handshake (primitive 3)
        CTRL1_XL_FS       = 2'b10   // Traces to: ODR / FS Range (primitive 4)
      "Two lines. Both cited to domain primitives. Done."

1:10 – 1:35   DO THE SWAP + REFLASH
      Unplug 6 wires from LSM6DS3. Plug 6 wires into LSM6DSO32. 20 seconds.
      Flash updated firmware. 20 seconds.

1:35 – 1:45   WORKS FIRST TIME
      Run demo_run.py — AFTER FIX row:
        AFTER FIX — LSM6DSO32, WHO_AM_I check updated to 0x6C  ✓
      "First time. No logic analyzer. No debug session."

      [Optional side callout — show the AFTER SWAP row:]
        AFTER SWAP — WHO_AM_I = 0x6C, FPGA expects 0x69 — init halts  NO OUTPUT
      "This is what the ungoverned path looks like. That's half a day of debugging."

1:45 – 2:15   THE POINT
      "Same vendor. Same family. Same register address — different value.
       WHO_AM_I is a fixed identifier baked into the silicon. It changes between
       generations. If you don't have a system that reads both datasheets and diffs
       the initialization parameters, you find this with a logic analyzer at 2 AM.
       We found it in 30 seconds, before the hardware was touched."

2:15 – 2:45   THE RECORD  (auto-generated — runs at end of demo_run.py)
      Terminal prints the Crucible change record:

        CRUCIBLE CHANGE RECORD — auto-generated
        Bill: B-001  │  Hearing: H-001  │  Status: APPROVED
        Delta:      WHO_AM_I 8'h69→8'h6C  [Primitive 3]
                    FS range  2'b00→2'b10  [Primitive 4]
        Conditions: C-1 ✓  C-2 ✓  C-3 ✓  C-4 ⏳ (DO-160G VRE test pending)  C-5 ✓
        Precedent:  P-001 — future WHO_AM_I swaps auto-flagged, no Hearing required
        Artifacts:  H-001_sensor_swap.md / case_law.md / domain_primitives.md

      "This is your certification data package entry. Every constant traced to a
       primitive. Datasheet citations on record. Conditions enumerated — including
       C-4 which is still open, because the DO-160G VRE test hasn't been run yet.
       The system doesn't pretend the test happened. And P-001 means the next
       engineer who swaps any sensor in this class gets flagged automatically —
       no Hearing required."

2:45  THE CLOSE
      "This is hardware CI/CD. Not a checklist someone fills out after the fact.
       Not a bug found at hardware test. A governed workflow that catches register
       deltas at change time, produces traceable artifacts automatically, and builds
       institutional memory that compounds across every future substitution."
```

---

## What the demo actually outputs

```
========================================================================
  FPGA Sensor Swap Demo — LSM6DS3 → LSM6DSO32
  Attitude budget: ±0.5°
========================================================================

  BEFORE SWAP — LSM6DS3, WHO_AM_I = 0x69 (FPGA expects 0x69 — PASS)
  Roll:  -0.00°  |+                                        |
  Pitch: +0.00°  |+                                        |
  Status: PASS ✓

  AFTER SWAP — LSM6DSO32, WHO_AM_I = 0x6C (FPGA expects 0x69 — init halts)
  Roll:  ---- (no data)
  Pitch: ---- (no data)
  Status: NO OUTPUT  ← WHO_AM_I = 0x6C, FPGA expects 0x69 — init halts

  AFTER FIX  — LSM6DSO32, WHO_AM_I check updated to 0x6C in config_rom.v
  Roll:  -0.00°  |+                                        |
  Pitch: +0.00°  |+                                        |
  Status: PASS ✓

========================================================================
  Root cause: WHO_AM_I changed — LSM6DS3 = 0x69, LSM6DSO32 = 0x6C (FPGA expected 0x69).
  Fix: Update WHO_AM_I check in config_rom.v  (8'h69 → 8'h6C).
========================================================================
```

The WHO_AM_I register (0x0F) is a read-only device identifier, fixed at the factory.
Both sensors use the same register address. The FPGA reads it once at startup to confirm
it is talking to the expected sensor before enabling the data path. With the new sensor,
the FPGA gets 0x6C where it expects 0x69 — one byte, no match, data path stays gated.
This is verifiable from both ST datasheets in under a minute.

---

## Domain primitives (avionics inertial sensor interface)

See `domain_primitives.md` for derivation and DO-160G mapping.

1. **SPI Clock Frequency** (Hz) — governs RTL clock divider; both sensors 10 MHz max
2. **VDDIO Voltage** (V) — governs FPGA I/O standard; both sensors 3.3V (unchanged)
3. **Initialization Handshake** (WHO_AM_I hex) — governs `config_rom.v` identity check; changes on swap
4. **Output Data Rate / FS Range** (Hz / g) — governs UART throughput and sensitivity scaling; FS minimum changes
5. **Vibration Rectification Error** (µg/g²) — DO-160G Cat B sensitivity; governs VRE compensation table

Primitive 3 is the demo failure mode (WHO_AM_I). Primitive 5 is the avionics-specific addition
that makes the Hearing necessary — invisible on bench, critical in flight.

---

## Other demo candidates (same Crucible framework, different failure class)

Three alternative hardware failure stories for the same demo slot. Each is a different
class of failure — different detectability, different consequence, different time-to-diagnose.

---

### Candidate A — Full-Scale Range Encoding (silent data corruption)

**Sensor pair:** LSM6DS3 → LSM6DSO32 (same pair as primary demo)  
**Failure class:** Data flows, output looks plausible, wrong scale factor applied  
**Detectability:** Near-zero at bench; fails only at non-zero attitude angles  

**What happens:** Both sensors use `CTRL1_XL[3:2]` for full-scale range selection.
On LSM6DS3, `0b00` = ±2g (sensitivity 0.061 mg/LSB). On LSM6DSO32, `0b00` = ±4g
(sensitivity 0.122 mg/LSB) — the minimum range doubled. `config_rom.v` writes the
same FS byte. At bench (level flight, near-zero pitch), the filter normalizes gravity
and the output looks correct. At 10° pitch, the accelerometer reads half the expected
projection — the filter reports 5° instead of 10°. Crew sees wrong attitude.

**Why it's harder to demo than WHO_AM_I:** The failure is magnitude-dependent.
The setup needs a known pitch angle to demonstrate the error. Feasible with a phone
inclinometer as the reference.

**AI story:** Reads both CTRL1_XL register tables side by side, flags FS encoding
change: "LSM6DS3 minimum FS = ±2g; LSM6DSO32 minimum FS = ±4g. If `config_rom.v`
is not updated, all accelerometer readings will be half of true value."

**Fix:** `config_rom.v` → `CTRL1_XL_FS = 2'b10` (±8g on DSO32 = ±4g effective at 2× sensitivity)
or recalibrate the sensor conversion factor in `data_formatter.v`.

---

### Candidate B — VRE Coefficient Mismatch (bench-invisible flight hazard)

**Sensor pair:** LSM6DS3 → LSM6DSO32 (same pair)  
**Failure class:** Data flows, attitude is correct at bench, wrong in flight vibration  
**Detectability:** Zero at bench; requires DO-160G vibration table to surface  

**What happens:** `data_formatter.v` carries the VRE compensation coefficient for
LSM6DS3 (70 µg/g²). After swap to LSM6DSO32 (55 µg/g²), the coefficient overcorrects —
LSM6DS3's larger coefficient applied to LSM6DSO32's smaller VRE produces a −37.5 mg
residual bias on accel_x. At 50 g_rms structural resonance, this is a −2.2° systematic
pitch error on every flight. Attitude display is wrong by a fixed amount in one direction.
Not noise — a constant offset indistinguishable from real pitch.

**Already implemented:** `signals.py` condition `vre_wrong_sensor` models this exactly.
Scenario can be added to `demo_run.py` as a fourth case.

**AI story:** Reads both sensor VRE characterization reports, computes residual:
"LSM6DS3 coefficient applied to LSM6DSO32 output → −37.5 mg residual at 50 g_rms.
DAL C budget is ±0.5°. This residual produces −2.2° pitch error. DO-160G test required
before deploying updated coefficient."

**Fix:** Requires DO-160G characterization of LSM6DSO32 VRE before updating `data_formatter.v`.
The Hearing is required because the coefficient does not exist yet.

---

### Candidate C — Power-On Reset Timing (cold-soak intermittent failure)

**Sensor pair:** LSM6DS3 → cross-vendor replacement (e.g., TDK ICM-42688-P)  
**Failure class:** Intermittent — reproducible only at cold soak or power-cycle  
**Detectability:** Lab test (warm) passes; DO-160G cold soak (-40°C) fails intermittently  

**What happens:** LSM6DS3 requires 35 ms from VDD power-on to first SPI access
(datasheet t_BOOT). `config_rom.v` waits 40 ms before reading WHO_AM_I — safe margin.
ICM-42688-P (TDK) requires 100 ms to complete internal self-calibration before SPI
is stable. `config_rom.v` accesses the sensor at 40 ms — sensor is mid-boot. At room
temperature, the sensor usually finishes early and the access succeeds. At −40°C,
the oscillator is slower, boot takes the full 100 ms, the FPGA reads floating bus
lines, WHO_AM_I returns 0xFF, initialization fails. Intermittent — unrepeatable
in the lab without temperature chamber.

**Why it's the hardest class:** The failure disappears when you warm up the board.
Engineers spend days ruling out connectors, FPGAs, and code before checking boot timing.

**AI story:** Compares t_BOOT from both datasheets: "LSM6DS3 t_BOOT = 35 ms;
ICM-42688-P t_BOOT = 100 ms at −40°C. `config_rom.v` startup delay = 40 ms.
At worst-case temperature, FPGA accesses sensor 60 ms before it is ready."

**Fix:** `config_rom.v` → startup delay from 40 ms to 110 ms. One constant change.

---

### Comparison matrix

| Demo | Symptom | Visible at bench? | Time to diagnose (no AI) | Fix complexity |
|------|---------|:-----------------:|:------------------------:|:--------------:|
| **Primary (WHO_AM_I)** | No data | Yes (immediate) | 4–12 h (logic analyzer) | 1 constant |
| **A (FS encoding)** | Wrong output at angle | No (needs tilt) | 8–24 h (calibration test) | 1 constant |
| **B (VRE coefficient)** | Wrong output in vibration | No (needs vibe table) | Weeks (DO-160G test) | DO-160G test + 1 coefficient |
| **C (boot timing)** | Intermittent at cold | No (needs temp chamber) | Days (env test) | 1 constant |

Primary demo is the right opening: hardest symptom, fastest AI win, most hardware-visible.
Candidates A–C are escalating follow-ons for a longer audience engagement or a multi-demo sequence.

---

## ROI framework — the knowledge gap problem

### The demographic context

The avionics hardware engineering workforce is aging. The engineers who know
why WHO_AM_I matters, why VRE is invisible on the bench, and why FS encoding
changes are silent — are retiring. Their replacements come from software backgrounds
and reach hardware-competent faster on logic than on failure modes.

The bottleneck is not raw intelligence. It is **first-draft hardware design judgment**:
the pattern recognition that tells a senior engineer which register differences matter
and which are safe, before touching the hardware. That judgment takes 5–10 years to
develop organically. It cannot be taught from datasheets. It is accumulated through
having debugged failures.

When a senior engineer retires, that pattern recognition walks out with them.
There is no structured way to transfer it under current practice.

### What Crucible actually does to that gap

Crucible converts tacit senior knowledge into explicit case law during normal work —
not as a separate knowledge-transfer project. Every Bill, Hearing, and settled
precedent is a piece of a junior engineer's accelerated curriculum:

- **P-001** (from this demo): "WHO_AM_I must be verified on any sensor substitution —
  auto-flagged, no Hearing required." A junior running their first sensor swap gets
  this check automatically. They don't need to have debugged a silent init failure
  at 2 AM to know it matters.
- **P-002**: "FS range encoding must be verified with a reference angle — bench-level
  test is not sufficient." A junior learns the failure mode before encountering it.
- **P-003**: "VRE coefficients cannot transfer between sensors — DO-160G test required
  before deploying." A junior knows to ask for the test without having seen a
  systematic pitch error in flight data first.

Each precedent is a senior engineer's hard-won pattern, captured at approval time,
reused automatically by every future engineer on every future substitution.

### ROI quantification — starting framework

**Cost of an undetected sensor change failure, by detection point:**

| Detection point | Typical cost | Time lost |
|---|---|---|
| Logic analyzer debug (bench) | $5K–15K engineer time | 1–3 days |
| DO-160G test abort (wrong sensor in chamber) | $50K–150K (chamber + engineer + reschedule) | 4–12 weeks |
| Flight test anomaly (silent data corruption) | $200K–500K+ (root cause + re-qualification) | 3–9 months |
| Field incident (in service) | Program-level consequence | — |

**Cost of Crucible per program:**

| Item | Cost |
|---|---|
| Initial setup + domain primitive ratification | $5K–10K (one-time) |
| Model fine-tuning for local deployment | ~$150–300 (one-time) |
| Per-change governance overhead | ~30 min per sensor swap bill + hearing |
| Annual maintenance | Minimal — case law accumulates passively |

**Break-even:** One prevented DO-160G test abort per year covers 2–5 years
of Crucible program costs. A single prevented flight test anomaly covers the
tool cost for the entire program life.

**Junior-to-senior acceleration:**

Current path to first-draft hardware design competence: 5–10 years.
Crucible path: junior engineer works against accumulated case law from day one.
First drafts are governed by the institution's pattern recognition, not the individual's.
Estimated ramp reduction: 2–4 years to reach acceptable first-draft quality.

At $120K CAD average junior salary, a 2-year acceleration to productive first-draft
contribution is worth ~$240K per hire in recovered productivity — before accounting
for reduced rework costs on their early designs.

**Knowledge retention on retirement:**

Current practice: when a senior retires, knowledge transfer is a 6–12 month
informal project if planned, zero if unexpected. Success rate is low — tacit
knowledge does not transfer well through documentation written after the fact.

Crucible practice: case law is written at the moment decisions are made, in a
format that is immediately actionable by any engineer. A senior's retirement removes
a person, not the institution's accumulated judgment.

**Senior engineer hiring gap:**

The avionics hardware talent pool is thin. When a senior FPGA engineer retires or
departs, the realistic time-to-replace is 6–18 months — if a replacement exists at all.
During that gap, programs cannot pause. Junior engineers are asked to make first-draft
decisions they are not yet equipped to make independently.

Crucible bridges that waiting period. A junior working against an established case law
record operates with the institution's accumulated senior judgment, not their own.
The program continues producing governed first drafts during the hiring gap, rather than
accumulating technical debt that the eventual senior hire must audit and remediate.

At $180K CAD total compensation for a senior hire, a 12-month search with 3 months of
ungoverned junior work in the interim carries a remediation tail that often exceeds
$200K. Crucible eliminates most of that tail — the junior's work is governed throughout.

### The compounding dynamic

Crucible's value increases with use. The tenth sensor swap in a program is governed
by nine precedents. A new engineer joining an established Crucible program inherits
years of institutional pattern recognition on day one.

This is the inverse of current practice, where each new engineer re-learns the same
failure modes independently, and the institution's knowledge resets on every departure
or extended hiring gap.

---

## Local deployment and model training path (avionics production)

### Why local is non-negotiable

Three distinct blockers for any cloud API in an avionics program:

| Blocker | Mechanism |
|---|---|
| **ITAR/EAR** | Sensor characterization data (VRE coefficients, DO-160G test results, FPGA source) is likely ITAR-controlled. Sending it to a cloud API is a potential export violation. |
| **DO-330 tool qualification** | Every tool in the certification toolchain must be qualified or its output independently verified. A cloud model with undisclosed update cadence cannot be qualified. |
| **Air-gap** | Avionics dev environments are routinely air-gapped. No internet access in the lab. |

The human Justice role (engineer rules, model advises) is the correct architecture
for qualification: the model is an advisor, not a decision-maker. The change record —
which the engineer approves — is the auditable artifact, not the model's intermediate
reasoning. This satisfies DO-330 output verification without requiring the model itself
to be a qualified tool.

### What the agents need to learn

Domain knowledge lives in the files, not the weights. The model only needs to learn:

- The Crucible bill / hearing / case-law format (structured templates)
- How to marshal evidence from a bounded set of governance documents
- How to follow the 4-element argument structure
- How to flag when evidence is missing rather than hallucinate

It does **not** need to know avionics, sensor physics, or DO-254 in its weights —
those live in `domain_primitives.md`, `device_context.md`, `amendments.md`. The agent
reads those at runtime. This dramatically reduces training data requirements.

### Distillation path

**Phase 1 — Synthetic data generation (teacher model)**

Use Claude Opus or GPT-4o as teacher. Generate structured training pairs across
5 primitive violation classes × 20 sensor pairs, with cross-domain variants
(pressure sensors, GPS receivers, display drivers — same governance structure):

| Task | Examples | Tokens each | Total |
|---|---|---|---|
| Bill drafting | 500 | ~800 | ~400K |
| Attorney-A arguments | 300 | ~1200 | ~360K |
| Attorney-B counter-arguments | 300 (paired to A) | ~1200 | ~360K |
| Stage-compactor cards | 200 | ~600 | ~120K |
| Negative examples (malformed, rejected) | 200 | ~500 | ~100K |
| **Total** | | | **~1.3M tokens** |

Cost at Opus batch pricing: ~$10–15 total for the full dataset.

**Phase 2 — Fine-tune a single student model**

One model plays all four roles via system prompt switching:

```
Base:     Qwen 2.5 32B (instruction-tuned)
Method:   LoRA fine-tuning (r=64, α=128)
Hardware: 2× A100 80GB, ~4–8 hours
Output:   Qwen 2.5 32B + Crucible LoRA adapter merged
Deploy:   RTX 4090 (24GB) at Q4_K_M — workstation-class hardware
```

A fine-tuned 32B on Crucible templates outperforms a raw 72B on this specific
task because the task is format-constrained. The 32B merged model fits on a
**single RTX 4090 (24GB)** — hardware every avionics lab already has.

**Phase 3 — Data flywheel from production use**

Every real sensor swap generates human-validated training data automatically:

- 1 completed hearing ≈ 3,000 tokens of validated signal
- 10 real swaps → enough to re-fine-tune and correct format drift
- 100 real swaps across programs → a domain-specific dataset no competitor has

The auto-generated change record is already structured enough to use as a training
label directly. Crucible's output IS its own training corpus.

### Production deployment stack

```
Avionics lab workstation (air-gapped)
├── GPU:  RTX 4090 24GB  (or A5000 24GB for ECC)
├── RAM:  64GB
├── OS:   Ubuntu 22.04 LTS
│
├── Ollama (local inference server, OpenAI-compatible API)
│   └── crucible-qwen32b-q4:latest   ← fine-tuned adapter merged
│
├── Python SDK agent wrappers
│   ├── Replaces .claude/agents/*.md interface
│   ├── System prompts preserved verbatim from agent definitions
│   ├── temperature=0, seed=42  → deterministic, reproducible output
│   └── Full I/O logging        → enters certification data package
│
└── Crucible governance docs (local files — customer's own)
    ├── domain_primitives.md   ← customer's primitives for their sensors
    ├── amendments.md          ← customer's amendments for their program
    └── case_law.md            ← accumulates one entry per approved change
```

Determinism is the answer to the DO-330 question. temperature=0 + fixed seed +
logged I/O means every model invocation is reproducible and auditable. The output
log enters the certification data package alongside the change record.

### Timeline to first air-gapped deployment

| Phase | Duration | Cost |
|---|---|---|
| Synthetic dataset generation | 1 day | ~$15 API |
| LoRA fine-tuning (cloud GPU rental) | 4–8 hours | ~$50–100 |
| Evaluation + format validation | 1 day | — |
| Python SDK packaging + Ollama model | 2–3 days | — |
| Customer onboarding + first real hearing | 1 day on-site | — |
| **Total to first air-gapped deployment** | **~1–2 weeks** | **~$150** |

Marginal cost per additional customer is near zero once the base model exists —
each customer adds their own governance documents and first few hearings to adapt
to their program.

---

## Files in this example

```
device_context.md           MAX 10 BOM, LSM6DS3 interface, DO-160G test plan
domain_primitives.md        Five primitives with avionics derivations and DO-160G mapping
bill_B001_sensor_swap.md    Bill — LSM6DS3→LSM6DSO32 substitution, DAL C change impact
hearing_H001_sensor_swap.md Hearing — WHO_AM_I, FS range, and VRE risks raised and resolved
case_law_entry.md           Case law entry + three precedents for sensor substitution class
```
