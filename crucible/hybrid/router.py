"""
router.py — Corpus tier filter for the Crucible hybrid RAG system.

Every agent carries a `contract.retrieves` block in its YAML frontmatter
declaring which corpus tiers it is permitted to access. This module enforces
that boundary: given an agent name and a query, it returns only the corpus
entries the agent is contractually allowed to retrieve.

Tiers (Amendment 13):
  PRIVATE    — local execution only; never forwarded to cloud agents
  DERIVED-OK — safe for cloud forwarding (scalars, summaries, plot paths)
  PUBLIC     — unrestricted (governance docs, agent definitions)

Usage:
    from crucible.hybrid.router import get_permitted_chunks

    chunks = get_permitted_chunks("police", "corpus signals")
    # → includes PRIVATE entries (police contract allows it)

    chunks = get_permitted_chunks("attorney-A", "corpus signals")
    # → PRIVATE entries filtered out (attorney-A runs on cloud)

CLI smoke test:
    python -m crucible.hybrid.router --agent police --query "corpus"
    python -m crucible.hybrid.router --agent attorney-A --query "signals"
    python -m crucible.hybrid.router --agent attorney-A --all

Constitutional grounding:
    docs/hybrid/corpus_classification.md — tier definitions
    docs/hybrid/skill_contract_spec.md   — contract.retrieves format
    Amendment 13                         — hybrid execution tiers
"""

import argparse
import fnmatch
import json
import os
import re
from pathlib import Path
from typing import Optional

_REPO_ROOT        = Path(__file__).resolve().parents[2]
CORPUS_INDEX_PATH = _REPO_ROOT / "docs" / "hybrid" / "corpus_index.json"
AGENTS_DIR        = _REPO_ROOT / ".claude" / "agents"

TIER_ORDER = {"PUBLIC": 0, "DERIVED-OK": 1, "PRIVATE": 2}


# ── Index loading ──────────────────────────────────────────────────────────────

def load_corpus_index() -> list:
    """Return the full corpus index as a list of {path, tier} dicts."""
    with open(CORPUS_INDEX_PATH) as f:
        return json.load(f)


# ── Contract parsing ───────────────────────────────────────────────────────────

def _parse_yaml_retrieves(agent_md_path: Path) -> list:
    """Extract permitted tiers from the contract.retrieves block in agent frontmatter.

    Uses a line-by-line state machine so it never picks up tier values from
    receives:, produces:, or must_not_forward: sections.
    """
    lines = agent_md_path.read_text().splitlines(keepends=True)

    fm_lines = []
    dashes_seen = 0
    for line in lines:
        if line.strip() == "---":
            dashes_seen += 1
            if dashes_seen == 2:
                break
            continue
        if dashes_seen == 1:
            fm_lines.append(line)

    retrieves_tiers = set()
    in_retrieves    = False
    retrieves_indent: Optional[int] = None

    for line in fm_lines:
        stripped = line.lstrip()
        indent   = len(line) - len(stripped)

        if stripped.startswith("retrieves:"):
            in_retrieves     = True
            retrieves_indent = indent
            continue

        if in_retrieves:
            if stripped and not stripped.startswith("-") and not stripped.startswith("#"):
                if retrieves_indent is not None and indent <= retrieves_indent and ":" in stripped.split("#")[0]:
                    in_retrieves = False
                    continue

            tier_match = re.search(r"tier:\s*(PUBLIC|DERIVED-OK|PRIVATE)", line)
            if tier_match:
                retrieves_tiers.add(tier_match.group(1))

    return list(retrieves_tiers)


def load_contract_tiers(agent_name: str) -> list:
    """Return the tiers the named agent is permitted to retrieve.

    Raises FileNotFoundError if agent definition is missing.
    Raises ValueError if the agent has no contract block.
    """
    candidates = [
        AGENTS_DIR / f"{agent_name}.md",
        AGENTS_DIR / f"{agent_name.lower()}.md",
    ]
    agent_path = next((c for c in candidates if c.exists()), None)

    if agent_path is None:
        raise FileNotFoundError(
            f"Agent definition not found for '{agent_name}' in {AGENTS_DIR}"
        )

    tiers = _parse_yaml_retrieves(agent_path)
    if not tiers:
        raise ValueError(
            f"Agent '{agent_name}' has no contract.retrieves block in {agent_path}"
        )
    return tiers


# ── Chunk filtering ────────────────────────────────────────────────────────────

def _path_matches(entry_path: str, query: str) -> bool:
    """Simple keyword match: all query words appear in the path."""
    words  = query.lower().split()
    target = entry_path.lower()
    return all(w in target for w in words)


def get_permitted_chunks(agent_name: str, query: str,
                         require_match: bool = True) -> list:
    """Return corpus entries the agent may retrieve that match the query.

    Args:
        agent_name:    Name of the agent (must match .claude/agents/<name>.md)
        query:         Keyword query — matched against entry paths
        require_match: If True, only entries whose path contains all query words.
                       If False, return the full permitted set (no query filter).

    Returns:
        List of {path, tier} dicts sorted by tier (PUBLIC → DERIVED-OK → PRIVATE).
    """
    permitted_tiers = set(load_contract_tiers(agent_name))
    index           = load_corpus_index()

    filtered = [e for e in index if e["tier"] in permitted_tiers]

    if require_match and query:
        filtered = [e for e in filtered if _path_matches(e["path"], query)]

    return sorted(filtered, key=lambda e: TIER_ORDER.get(e["tier"], 99))


def get_all_permitted(agent_name: str) -> list:
    """Return all corpus entries the agent may access (no query filter)."""
    return get_permitted_chunks(agent_name, query="", require_match=False)


# ── CLI smoke test ─────────────────────────────────────────────────────────────

def _cli():
    parser = argparse.ArgumentParser(
        description="Crucible RAG tier filter — test corpus access for an agent"
    )
    parser.add_argument("--agent", required=True, help="Agent name (e.g. police)")
    parser.add_argument("--query", default="",    help="Keyword query (e.g. 'signals')")
    parser.add_argument("--all",   action="store_true",
                        help="Show full permitted corpus (no query filter)")
    args = parser.parse_args()

    print(f"\nRAG Router — agent={args.agent}  query='{args.query}'")
    try:
        permitted_tiers = load_contract_tiers(args.agent)
        print(f"Permitted tiers: {permitted_tiers}")
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}")
        return

    chunks = get_all_permitted(args.agent) if args.all else \
             get_permitted_chunks(args.agent, args.query)

    if not chunks:
        print("No matching chunks — query filtered out or tier boundary enforced.\n")
        return

    print(f"\n{'Path':<70}  {'Tier':<12}")
    print("─" * 85)
    for c in chunks:
        print(f"{c['path']:<70}  {c['tier']:<12}")
    print(f"\n{len(chunks)} chunk(s) returned.\n")


if __name__ == "__main__":
    _cli()
