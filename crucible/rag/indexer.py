"""
Corpus indexer — chunks Layer 1 corpus files by section and writes to Chroma.

Usage:
  python -m crucible.rag.indexer           — index all Layer 1 corpus files
  python -m crucible.rag.indexer --file F  — index a single file

Corpus files indexed:
  docs/governance/amendments.md   — by H3 amendment block
  docs/governance/case_law.md     — by H2/H3 case entry
  docs/device_context.md          — by H2 section
  docs/toolchain_config.md        — by H2 section
  CONSTITUTION.md                 — by H2 section

Vector store: Chroma (local), persisted at .chroma/ in repo root.
Embedding model: sentence-transformers/all-MiniLM-L6-v2 (local, no API key).
Swappable via CRUCIBLE_EMBEDDING_MODEL env var (set to 'openai' for text-embedding-3-small).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _chroma_path() -> Path:
    return _repo_root() / '.chroma'


def _load_hybrid_tier_map() -> dict:
    """Return {path_fragment: tier} from docs/hybrid/corpus_index.json.

    Falls back to empty dict if the index does not exist yet (bootstrapping).
    Path matching is a simple substring check — first match wins.
    """
    index_path = _repo_root() / 'docs' / 'hybrid' / 'corpus_index.json'
    if not index_path.exists():
        return {}
    with open(index_path) as f:
        entries = json.load(f)
    return {e['path']: e['tier'] for e in entries}


def _hybrid_tier(file_rel_path: str, tier_map: dict) -> str:
    """Resolve the hybrid tier for a corpus file path.

    Checks exact match first, then substring containment.
    Returns 'PUBLIC' as default when not found.
    """
    if file_rel_path in tier_map:
        return tier_map[file_rel_path]
    for pattern, tier in tier_map.items():
        if pattern in file_rel_path or file_rel_path in pattern:
            return tier
    return 'PUBLIC'


CORPUS_FILES = [
    ('docs/governance/amendments.md',  'amendments',    1),
    ('docs/governance/case_law.md',    'case_law',      1),
    ('docs/device_context.md',         'device_context', 1),
    ('docs/toolchain_config.md',       'toolchain',     1),
    ('CONSTITUTION.md',                'constitution',   1),
]


def _chunk_by_headers(text: str, file_label: str, corpus_layer: int) -> list[dict]:
    """
    Split markdown by H2 or H3 headers. Each chunk:
      {id, text, metadata: {file, section, layer, header_level}}
    """
    chunks = []
    pattern = re.compile(r'^(#{2,3})\s+(.+)$', re.MULTILINE)
    matches = list(pattern.finditer(text))

    for i, match in enumerate(matches):
        start = match.start()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section_text = text[start:end].strip()
        if len(section_text) < 30:
            continue

        header_level = len(match.group(1))
        title = match.group(2).strip()
        slug  = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        chunk_id = f'{file_label}/{slug}'

        chunks.append({
            'id':   chunk_id,
            'text': section_text,
            'metadata': {
                'file':         file_label,
                'section':      title,
                'layer':        corpus_layer,
                'header_level': header_level,
            },
        })

    return chunks


def _get_collection(client):
    return client.get_or_create_collection(
        name='crucible_corpus',
        metadata={'hnsw:space': 'cosine'},
    )


def _get_client():
    try:
        import chromadb
    except ImportError:
        raise ImportError(
            'chromadb is required for RAG indexing. '
            'Install with: pip install chromadb sentence-transformers'
        )
    return chromadb.PersistentClient(path=str(_chroma_path()))


def _get_embedding_fn():
    model = os.environ.get('CRUCIBLE_EMBEDDING_MODEL', 'local')

    if model == 'openai':
        try:
            import chromadb.utils.embedding_functions as ef
            api_key = os.environ.get('OPENAI_API_KEY', '')
            return ef.OpenAIEmbeddingFunction(
                api_key=api_key,
                model_name='text-embedding-3-small',
            )
        except ImportError:
            pass

    # Default: local sentence-transformers
    try:
        import chromadb.utils.embedding_functions as ef
        return ef.SentenceTransformerEmbeddingFunction(
            model_name='all-MiniLM-L6-v2'
        )
    except ImportError:
        raise ImportError(
            'sentence-transformers is required for local embedding. '
            'Install with: pip install sentence-transformers'
        )


def index_file(file_path: Path, file_label: str, corpus_layer: int,
               collection, tier_map: Optional[dict] = None) -> int:
    if not file_path.exists():
        print(f'  [SKIP] {file_path} not found')
        return 0

    text   = file_path.read_text()
    chunks = _chunk_by_headers(text, file_label, corpus_layer)
    if not chunks:
        print(f'  [SKIP] {file_label} — no sections found')
        return 0

    if tier_map is None:
        tier_map = _load_hybrid_tier_map()

    # Resolve hybrid tier from the source file's repo-relative path
    try:
        rel_path = str(file_path.relative_to(_repo_root()))
    except ValueError:
        rel_path = str(file_path)
    file_tier = _hybrid_tier(rel_path, tier_map)

    ids       = [c['id']   for c in chunks]
    documents = [c['text'] for c in chunks]
    metadatas = []
    for c in chunks:
        meta = dict(c['metadata'])
        meta['hybrid_tier'] = file_tier
        metadatas.append(meta)

    # Upsert so re-indexing is idempotent
    collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
    print(f'  [OK] {file_label} ({file_tier}) — {len(chunks)} chunks indexed')
    return len(chunks)


def index_all(repo_root: Optional[Path] = None) -> int:
    root = repo_root or _repo_root()
    client     = _get_client()
    embed_fn   = _get_embedding_fn()
    collection = client.get_or_create_collection(
        name='crucible_corpus',
        embedding_function=embed_fn,
        metadata={'hnsw:space': 'cosine'},
    )

    tier_map = _load_hybrid_tier_map()
    total = 0
    print(f'Indexing corpus into Chroma at {_chroma_path()}')
    for rel_path, label, layer in CORPUS_FILES:
        total += index_file(root / rel_path, label, layer, collection, tier_map)

    # Also index any stage closeout files
    closeouts = sorted((root / 'docs' / 'governance').glob('stage_*_closeout.md'))
    for path in closeouts:
        label = path.stem
        total += index_file(path, label, 1, collection, tier_map)

    print(f'Total: {total} chunks indexed.')
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', default=None,
                        help='Index a single file (relative to repo root)')
    args = parser.parse_args()

    if args.file:
        root = _repo_root()
        path = root / args.file
        label = Path(args.file).stem
        client = _get_client()
        embed_fn = _get_embedding_fn()
        collection = client.get_or_create_collection(
            name='crucible_corpus',
            embedding_function=embed_fn,
            metadata={'hnsw:space': 'cosine'},
        )
        n = index_file(path, label, 1, collection)
        print(f'Indexed {n} chunks from {args.file}')
        return 0

    index_all()
    return 0


if __name__ == '__main__':
    sys.exit(main())
