"""
Crucible corpus knowledge graph.

Builds a structured graph from governance documents (amendments, hearings, primitives)
so enforcement checks can query relationships instead of doing fragile regex over
monolithic Markdown files.

Usage:
    from crucible.corpus.graph import CorpusGraph
    from crucible.corpus.query import has_valid_layer2_hearing, find_informal_rulings

The graph supports two corpus layouts:
  - Monolithic: docs/governance/case_law.md + docs/governance/amendments.md
  - Fragmented: docs/governance/hearings/MANIFEST.md + docs/governance/hearings/H-*.md
                + docs/governance/amendments/*.md (future)

Fragmented layout is preferred when the hearings/ directory exists. Both layouts
can coexist during migration — the graph reads whichever is present.
"""
