# Crucible — Hybrid Corpus Classification

**Amendment:** 13 (PROPOSED)  
**Purpose:** Define the three-tier sensitivity classification that governs which agents may retrieve which corpus content, and whether computation may run locally or be forwarded to cloud models.

This classification is orthogonal to Amendment 12's four-layer corpus (immutability/change gates). A file may be Layer 1 (immutable) and PUBLIC simultaneously, or Layer 2 (hearing-gated) and PRIVATE simultaneously.

---

## Three Tiers

### PRIVATE — Local execution only

Content that must never be forwarded to cloud models. Includes project-specific signal models, algorithm source, raw field data, and any content from which sensitive IP or personal data could be reconstructed.

**Rules:**
- May only be retrieved by agents with `execution: local` in their contract
- Must not appear in any prompt sent to a cloud API
- Must not appear in forwarded summaries, even in paraphrased form

**Examples:**
- `src/signals.py` — physics model / signal generator (Layer 2, project IP)
- `src/algorithm.py` — Python algorithm mirror of firmware (Layer 2, project IP)
- Firmware source (`firmware/*.ino`, `firmware/*.cpp`) — Layer 3, implementation IP
- Field data exports (`docs/field-test/*.csv`, `*.bin`) — raw sensor recordings
- Device-specific calibration constants once measured

### DERIVED-OK — Safe for cloud forwarding

Outputs derived from PRIVATE content but stripped of enough detail that the PRIVATE source cannot be reconstructed. Safe to forward to cloud models for reasoning.

**Rules:**
- Scalar values (step count, cadence Hz, filter cutoff) are DERIVED-OK when not accompanied by the formula that produced them
- Plot image files (PNG/SVG) are DERIVED-OK — shapes and trends, not raw arrays
- Summary JSON with opaque keys is DERIVED-OK
- Simulation pass/fail tables are DERIVED-OK

**Examples:**
- Simulation plot files (`docs/simulation/*.png`)
- Session summary JSON (step count, detection rate)
- Regression pass/fail tables
- `docs/hybrid/corpus_index.json` (the index itself is not sensitive)

### PUBLIC — Unrestricted

Governance records, constitutional documents, agent definitions, and any content that describes how the system works rather than what it measures.

**Rules:**
- Any agent may retrieve PUBLIC content regardless of execution site
- PUBLIC content may be forwarded to cloud models without restriction

**Examples:**
- `CONSTITUTION.md`
- `docs/governance/amendments.md`
- `docs/governance/case_law.md`
- `docs/device_context.md` (device purpose, BOM, signal inventory — not raw data)
- `docs/toolchain_config.md`
- `.claude/agents/*.md` (agent definitions)
- `.claude/commands/*.md` (command definitions)
- `CLAUDE.md`, `ONBOARDING.md`, `README.md`
- `docs/hybrid/*.md` (this document and siblings)

---

## Tier Assignment Table

| Path pattern | Tier | Rationale |
|---|---|---|
| `CONSTITUTION.md` | PUBLIC | Governance |
| `CLAUDE.md` | PUBLIC | Entry point, no IP |
| `ONBOARDING.md` | PUBLIC | Workflow docs |
| `README.md` | PUBLIC | Public-facing |
| `docs/governance/*.md` | PUBLIC | Constitutional record |
| `docs/device_context.md` | PUBLIC | Device spec, not data |
| `docs/toolchain_config.md` | PUBLIC | Toolchain record |
| `docs/hybrid/*.md` | PUBLIC | Governance |
| `docs/hybrid/corpus_index.json` | DERIVED-OK | Index metadata |
| `.claude/agents/*.md` | PUBLIC | Agent definitions |
| `.claude/commands/*.md` | PUBLIC | Command definitions |
| `crucible/**/*.py` | PUBLIC | Infrastructure, no domain IP |
| `src/signals.py` | PRIVATE | Project physics model |
| `src/algorithm.py` | PRIVATE | Project algorithm IP |
| `src/events.py` | PUBLIC | Scaffold, no IP |
| `src/analysis.py` | PUBLIC | Scaffold, no IP |
| `src/plot.py` | PUBLIC | Scaffold, no IP |
| `firmware/**` | PRIVATE | Implementation IP |
| `docs/field-test/**` | PRIVATE | Raw sensor recordings |
| `docs/simulation/*.png` | DERIVED-OK | Visual summaries |
| `docs/simulation/*.csv` | PRIVATE | Raw simulation arrays |
| `examples/**` | PUBLIC | Reference implementations |

---

## Stage-Based Escalation

Before Stage 3 (field test), no real field data exists, so no PRIVATE field data is present. After Stage 3 begins, any file under `docs/field-test/` is automatically PRIVATE regardless of format, unless the project engineer explicitly reclassifies it with a case law entry.

---

## Updating This Classification

Adding a new PRIVATE entry: update `docs/hybrid/corpus_index.json`. No Bill or Hearing required — classification is a Bureaucracy Standing Order.

Reclassifying a PRIVATE file as DERIVED-OK or PUBLIC: requires a Bill, because it changes what cloud agents may receive.
