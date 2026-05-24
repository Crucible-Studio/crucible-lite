# Crucible — Skill Contract Format Specification

**Amendment:** 13 (PROPOSED)  
**Purpose:** Define the `contract:` block embedded in every Crucible agent `.md` file. This block declares the agent's execution site, corpus access rights, and data forwarding rules. The RAG router reads it to enforce retrieval boundaries automatically.

---

## Why Skill Contracts Exist

RAG retrieval without access control is a privacy gap. Agent model assignment without data contracts is a capability gap. The skill contract closes both simultaneously, per agent:

- Which corpus tier it may retrieve from (`retrieves`)
- Where computation runs (`execution: local | cloud | split`)
- What it receives as input, and at which tier (`receives`)
- What it produces as output, and at which tier (`produces`)
- What it may forward upstream (`may_forward`)
- What it must never forward (`must_not_forward`)

Every agent `.md` file carries its contract in a `contract:` block in the YAML frontmatter. The RAG router (`crucible/hybrid/router.py`) reads the `retrieves:` field to filter corpus chunks before returning them.

---

## Contract Block Format

```yaml
---
name: <agent-name>
description: "..."
tools: ...
model: <model-id>

contract:
  execution: local | cloud | split
  retrieves:
    - tier: PUBLIC | DERIVED-OK | PRIVATE
      sources: [list of file patterns or labels, e.g. "amendments.md", "src/signals.py"]
  receives:
    - name: <input name>
      tier: PUBLIC | DERIVED-OK | PRIVATE
      format: <scalar | path | table | json-summary | free-text | raw-signal>
  produces:
    - name: <output name>
      tier: PUBLIC | DERIVED-OK | PRIVATE
      format: <scalar | path | table | json-summary | free-text | raw-signal>
      destination: <file path pattern | stdout | upstream-agent>
  may_forward:
    - tier: PUBLIC | DERIVED-OK
      to: <agent-name | cloud | any>
  must_not_forward:
    - tier: PRIVATE
      reason: <one-line reason>
  opaque_keys: true | false
---
```

### Field Definitions

| Field | Description |
|---|---|
| `execution` | `local` = runs on a local model (Ollama); `cloud` = runs on Claude API; `split` = step 1 local, step 2 cloud |
| `retrieves` | Corpus tiers this agent may access. Cloud agents (`execution: cloud`) must not list PRIVATE. |
| `receives` | Named inputs, their tier, and wire format. Cloud agents must not accept PRIVATE inputs. |
| `produces` | Named outputs, their tier, and destination. |
| `may_forward` | What the agent is permitted to pass upstream. PRIVATE is never in this list. |
| `must_not_forward` | Explicit prohibition — belt-and-suspenders with `may_forward` absence. Written for auditability. |
| `opaque_keys` | If `true`, this agent substitutes opaque key names before forwarding any DERIVED-OK scalar dict. |

### Format Types

| Format | Description |
|---|---|
| `scalar` | Single numeric value |
| `scalar-dict` | `{"w0": 1.34e-4, ...}` — use opaque keys if derived from PRIVATE |
| `path` | File path to a saved artifact (plot PNG, log file) |
| `table` | Formatted text table printed to stdout |
| `json-summary` | Flat JSON with scalars and status fields — no formula text |
| `free-text` | Human-readable prose — never forwarded upstream as structured data |
| `raw-signal` | NumPy array or binary blob — always PRIVATE |

---

## Execution Site Rules

| execution | Claude model | May retrieve PRIVATE? | May receive PRIVATE input? |
|---|---|---|---|
| `local` | Ollama (local) | Yes | Yes |
| `cloud` | Claude API | No | No |
| `split` | Step 1: Ollama; Step 2: Claude API | Step 1: Yes; Step 2: No | Step 1: Yes; Step 2: DERIVED-OK only |

---

## Example Contracts (Key Agents)

### police (local, constitutional auditor)

```yaml
contract:
  execution: local
  retrieves:
    - tier: PUBLIC
      sources: ["amendments.md", "case_law.md", "CONSTITUTION.md"]
    - tier: PRIVATE
      sources: ["src/signals.py", "src/algorithm.py", "firmware/**"]
  produces:
    - name: violation report
      tier: DERIVED-OK
      format: table
      destination: stdout
  may_forward:
    - tier: DERIVED-OK
      to: Justice
  must_not_forward:
    - tier: PRIVATE
      reason: violation reports contain findings, not source content
  opaque_keys: false
```

### attorney-A (cloud, argues assigned position)

```yaml
contract:
  execution: cloud
  retrieves:
    - tier: PUBLIC
      sources: ["amendments.md", "case_law.md", "CONSTITUTION.md", ".claude/agents/*.md"]
    - tier: DERIVED-OK
      sources: ["docs/simulation/*.png", "docs/hybrid/corpus_index.json"]
  produces:
    - name: argument
      tier: PUBLIC
      format: free-text
      destination: stdout
  may_forward:
    - tier: PUBLIC
      to: Justice
  must_not_forward:
    - tier: PRIVATE
      reason: cloud model — PRIVATE content must never leave local execution
  opaque_keys: false
```

---

## Enforcement

The `contract.retrieves` block is the machine-readable specification that `crucible/hybrid/router.py` reads. Calling `get_permitted_chunks(agent_name, query)` returns only entries the agent is contractually permitted to see.

Agents without a `contract:` block fail loudly (`ValueError`) rather than silently returning all chunks. This is intentional — an uncontracted agent is an unaudited agent.
