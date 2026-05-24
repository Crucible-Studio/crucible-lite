# /wiki — Project Wiki Generator

Generates human-readable documentation from the live corpus state.

Output: `docs/wiki/` directory (gitignored — generated on demand, not checked in).

---

## Subcommands

### `/wiki generate [--page <name>] [--no-redact]`

Generate all wiki pages (or a single page) from the current corpus state.

**What it does:**

1. Read `docs/knowledge_map.json` for the knowledge graph
2. Read `docs/governance/amendments.md` (or query corpus.db if available)
3. Read `docs/device_context.md` for device overview
4. Render all pages to `docs/wiki/`:
   - `index.md` — project overview, stage summary, constitutional record
   - `primitives.md` — domain primitives and their signal linkages
   - `amendments.md` — full amendment log with status
   - `stage_history.md` — stage closeout summaries with links to full records
   - `known_issues.md` — failure modes from the knowledge map
   - `knowledge_graph.md` — Mermaid diagram of the knowledge map
5. Apply redaction pass — any `[REDACT]` or `<!-- redact -->` tagged values in
   the corpus are replaced with `[REDACTED]` before writing to `docs/wiki/`
   (the original corpus files are never modified)

**Run:**
```
python -m crucible.wiki.renderer
```

Or for a single page:
```
python -m crucible.wiki.renderer --page primitives
```

To generate unredacted output (internal use only):
```
python -m crucible.wiki.renderer --no-redact
```

**Options:**
- `--page`: one of `index`, `primitives`, `amendments`, `stage_history`, `known_issues`, `knowledge_graph`
- `--no-redact`: bypass redaction (for internal review, never for external sharing)

---

### `/wiki index-corpus`

Index the Layer 1 corpus into the Chroma vector store.
Required before agents can use semantic retrieval via `crucible.rag.query`.

**Run:**
```
python -m crucible.rag.indexer
```

Files indexed:
- `docs/governance/amendments.md`
- `docs/governance/case_law.md`
- `docs/device_context.md`
- `docs/toolchain_config.md`
- `CONSTITUTION.md`
- Any `docs/governance/stage_*_closeout.md` files

Index is stored at `.chroma/` (gitignored). Rebuild after any Layer 1 corpus change.

---

### `/wiki seed-db`

Seed the SQLite corpus DB with the current amendments.md state.
Required before agents can use structured queries against amendments table.

**Run:**
```
python -m crucible.db.migrate --seed
```

---

### `/wiki build` (alias for `/wiki generate`)

Alias: `build` → runs `python -m crucible.wiki.renderer` with default flags.
Produces `docs/wiki/` with `index.md`, per-primitive pages, per-hearing pages, and `constants.md`.

---

### `/wiki primitive <name>`

Print all corpus references to a domain primitive inline — no build required.

```
python -m crucible.corpus.graph --wiki-primitive "<name>"
```

Output: amendment citation, all hearing references, all `Traces to:` annotations in src/.

---

### `/wiki hearing <H-NNN>`

Print hearing summary + linked primitives + case law entry.

```
python -m crucible.corpus.graph --wiki-hearing H-NNN
```

Output: hearing completion status, positions A and B, ruling summary, linked primitives.

---

### `/wiki status`

Print amendment + hearing index as ASCII table. Token-efficient alternative to running
the full police agent for session orientation (~200 tokens vs 2000–5000).

```
python -m crucible.corpus.graph --summary
```

Use `/wiki status` in place of `/session status` police check when you only need
corpus orientation, not a full constitutional audit.

---

## Redaction tags

Tag sensitive values in corpus source files for automatic stripping from wiki output:

```markdown
Threshold: `42.5 dps`  <!-- redact -->
Patient cohort: [REDACT]
```

Both forms produce `[REDACTED]` in wiki output. Original corpus files are unchanged.

Use for:
- Calibration constants that are trade secrets
- Patient identifiers in test result tables
- Hardware revision codes not yet public

---

## Lifecycle

| Event | Action |
|---|---|
| Any Layer 1 corpus change | Re-run `/wiki index-corpus` to keep Chroma in sync |
| Stage gate closed | Re-run `/wiki generate` — `stage_history.md` will update |
| New primitive added | Re-run `/wiki generate` — `primitives.md` and `knowledge_graph.md` update |
| Sharing externally | Always use `/wiki generate` (redaction on by default) — never share raw corpus |
