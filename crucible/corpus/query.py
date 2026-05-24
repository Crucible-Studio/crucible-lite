"""
Corpus query functions for enforcement checks.

These are the stable API that corpus.py, bash_write_guard.py, and the police agent
call. They build the graph on each invocation (fast — pure file reads, no DB).
"""

from __future__ import annotations

from pathlib import Path

from .graph import CorpusGraph, Hearing


def has_valid_layer2_hearing(repo_root: Path) -> bool:
    """True if at least one complete Judicial Hearing covers src/signals.py or src/algorithm.py.

    'Complete' means all three sections present: Attorney-A, Attorney-B, Justice.
    Used by corpus.py Amendment 12 check.
    """
    graph = CorpusGraph(repo_root)
    return bool(graph.valid_layer2_hearings())


def find_informal_rulings(repo_root: Path) -> list[dict]:
    """Return hearings that are missing required sections (incomplete = informal ruling).

    Used by police agent JUDICIAL-INDEPENDENCE-VIOLATION detection.
    """
    graph = CorpusGraph(repo_root)
    return [
        {
            'id': h.id,
            'name': h.name,
            'date': h.date,
            'missing_sections': h.missing_sections(),
            'files_covered': sorted(h.files_covered),
        }
        for h in graph.incomplete_hearings()
    ]


def amendment_1_primitives(repo_root: Path) -> list[str]:
    """Return primitive names from ratified Amendment 1, or [] if not ratified.

    Used by article1_check.py and article_i.py to validate citations.
    """
    graph = CorpusGraph(repo_root)
    return [p.name for p in graph.primitives()]


def amendment_1_ratified(repo_root: Path) -> bool:
    """True if Amendment 1 is ratified and has at least one primitive defined."""
    graph = CorpusGraph(repo_root)
    return graph.amendment_1_ratified()
