"""
Semantic query interface for agents.

Usage (from agent code or commands):
  from crucible.rag.query import query, query_tiered

  results = query("what primitive governs cadence thresholds", n=3)
  for r in results:
      print(r['section'], r['score'])
      print(r['text'][:200])

  # Tier-enforced query — filters by agent contract (Amendment 13)
  results = query_tiered("attorney-A", "signals algorithm", n=3)
  # → no PRIVATE chunks returned for cloud agents

Returns a list of {id, section, file, layer, hybrid_tier, text, score} dicts,
sorted by relevance (highest score first).

Falls back to grep-style keyword search if Chroma is not installed or
the index does not exist — so agents always get something back.
"""

import re
from pathlib import Path
from typing import Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _chroma_path() -> Path:
    return _repo_root() / '.chroma'


def query(question: str, n: int = 5,
          layer: Optional[int] = None,
          file_filter: Optional[str] = None) -> list[dict]:
    """
    Semantic search over the indexed corpus.

    Args:
        question:    Natural language query
        n:           Number of results to return
        layer:       Filter to a specific corpus layer (1-4)
        file_filter: Filter to a specific file label (e.g. 'amendments')

    Returns list of dicts: {id, section, file, layer, text, score}
    """
    try:
        return _chroma_query(question, n, layer, file_filter)
    except Exception:
        return _fallback_grep(question, n)


def _chroma_query(question: str, n: int, layer: Optional[int],
                  file_filter: Optional[str]) -> list[dict]:
    import chromadb
    import chromadb.utils.embedding_functions as ef
    import os

    if not _chroma_path().exists():
        raise FileNotFoundError('Chroma index not found. Run: python -m crucible.rag.indexer')

    model = os.environ.get('CRUCIBLE_EMBEDDING_MODEL', 'local')
    if model == 'openai':
        embed_fn = ef.OpenAIEmbeddingFunction(
            api_key=os.environ.get('OPENAI_API_KEY', ''),
            model_name='text-embedding-3-small',
        )
    else:
        embed_fn = ef.SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')

    client = chromadb.PersistentClient(path=str(_chroma_path()))
    collection = client.get_collection(name='crucible_corpus', embedding_function=embed_fn)

    where: dict = {}
    if layer is not None:
        where['layer'] = {'$eq': layer}
    if file_filter is not None:
        where['file'] = {'$eq': file_filter}

    results = collection.query(
        query_texts=[question],
        n_results=min(n, collection.count()),
        where=where if where else None,
        include=['documents', 'metadatas', 'distances'],
    )

    out = []
    for i, doc_id in enumerate(results['ids'][0]):
        meta = results['metadatas'][0][i]
        dist = results['distances'][0][i]
        out.append({
            'id':         doc_id,
            'section':    meta.get('section', ''),
            'file':       meta.get('file', ''),
            'layer':      meta.get('layer', 1),
            'hybrid_tier': meta.get('hybrid_tier', 'PUBLIC'),
            'text':       results['documents'][0][i],
            'score':      round(1.0 - dist, 4),   # cosine similarity
        })

    return sorted(out, key=lambda x: x['score'], reverse=True)


def query_tiered(agent_name: str, question: str, n: int = 5,
                 file_filter: Optional[str] = None) -> list[dict]:
    """
    Tier-enforced semantic search (Amendment 13).

    Wraps query() and post-filters results to corpus chunks the named agent
    is contractually permitted to retrieve. Falls back to unfiltered query()
    if the router or corpus_index is unavailable.

    Args:
        agent_name:  Name of the agent (must match .claude/agents/<name>.md)
        question:    Natural language query
        n:           Number of results to return
        file_filter: Restrict to a specific file label (e.g. 'amendments')

    Returns list of dicts: {id, section, file, layer, hybrid_tier, text, score}
    All returned chunks are within the agent's permitted tier set.
    """
    try:
        from crucible.hybrid.router import load_contract_tiers
        permitted_tiers = set(load_contract_tiers(agent_name))
    except Exception:
        # Router unavailable (no corpus_index.json, no contract block) — degrade gracefully
        return query(question, n=n, file_filter=file_filter)

    # Fetch more than n to have enough after tier filtering
    raw = query(question, n=n * 4, file_filter=file_filter)

    filtered = [
        r for r in raw
        if r.get('hybrid_tier', 'PUBLIC') in permitted_tiers
    ]
    return filtered[:n]


def _fallback_grep(question: str, n: int) -> list[dict]:
    """
    Keyword fallback when Chroma is unavailable.
    Searches Layer 1 files for lines matching any word in the question.
    """
    root = _repo_root()
    corpus_files = [
        ('docs/governance/amendments.md', 'amendments'),
        ('docs/governance/case_law.md',   'case_law'),
        ('docs/device_context.md',        'device_context'),
        ('CONSTITUTION.md',               'constitution'),
    ]

    words = [w.lower() for w in re.findall(r'\w{4,}', question)]
    if not words:
        return []

    hits: list[dict] = []
    for rel, label in corpus_files:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text()
        sections = re.split(r'^#{2,3} .+$', text, flags=re.MULTILINE)
        headers  = re.findall(r'^(#{2,3} .+)$', text, re.MULTILINE)
        for j, section in enumerate(sections[1:], 0):
            score = sum(1 for w in words if w in section.lower())
            if score > 0:
                hits.append({
                    'id':      f'{label}/{j}',
                    'section': headers[j] if j < len(headers) else '',
                    'file':    label,
                    'layer':   1,
                    'text':    section.strip()[:800],
                    'score':   score / len(words),
                })

    hits.sort(key=lambda x: x['score'], reverse=True)
    return hits[:n]
