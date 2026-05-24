"""
Amendment 12 — Corpus Supremacy enforcement.

Layer 2 swap (signals.py / algorithm.py) without complete Hearing → VIOLATION
Direct edit to Layer 4 ephemeral files without corpus change          → VIOLATION

Hearing check uses the knowledge graph (crucible.corpus.query) when available,
which validates structural completeness (Attorney-A + Attorney-B + Justice sections).
Falls back to regex over case_law.md for projects that have not yet migrated to the
fragmented hearing format.
"""

import re
import subprocess
from typing import Optional
from pathlib import Path

LAYER_2 = {'src/signals.py', 'src/algorithm.py'}

LAYER_4 = {'src/events.py', 'src/analysis.py', 'src/plot.py'}
LAYER_4_PREFIX = 'test'   # any file under test/ is Layer 4


def _changed_files(base_ref: Optional[str]) -> set[str]:
    if base_ref:
        result = subprocess.run(
            ['git', 'diff', '--name-only', f'{base_ref}...HEAD'],
            capture_output=True, text=True
        )
    else:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only'],
            capture_output=True, text=True
        )
    return set(result.stdout.strip().splitlines())


def _hearing_present_graph(repo_root: Path) -> bool:
    """Graph-based check: requires a structurally complete Hearing (A + B + Justice)."""
    try:
        from crucible.corpus.query import has_valid_layer2_hearing
        return has_valid_layer2_hearing(repo_root)
    except ImportError:
        return False


def _hearing_present_regex(repo_root: Path) -> bool:
    """Regex fallback over monolithic case_law.md."""
    path = repo_root / 'docs' / 'governance' / 'case_law.md'
    if not path.exists():
        return False
    text = path.read_text()
    return bool(
        re.search(r'Judicial Hearing', text, re.IGNORECASE) and
        re.search(r'signals\.py|algorithm\.py|Layer 2', text, re.IGNORECASE)
    )


def _hearing_present(repo_root: Path) -> bool:
    """Check for a valid Layer 2 Judicial Hearing using graph first, then regex.

    The graph check is stricter: it validates that the hearing entry has all three
    required sections (Attorney-A, Attorney-B, Justice). The regex check only
    verifies presence of keywords — it cannot detect incomplete (informal) rulings.
    """
    # Graph check preferred: validates structural completeness.
    if _hearing_present_graph(repo_root):
        return True
    # Regex fallback: keyword presence only (weaker, but covers legacy case_law.md).
    return _hearing_present_regex(repo_root)


def _corpus_changed(changed: set[str]) -> bool:
    LAYER_1 = {
        'docs/device_context.md',
        'docs/governance/amendments.md',
        'docs/toolchain_config.md',
        'CONSTITUTION.md',
    }
    return bool(changed & LAYER_1)


def run(repo_root: Path, base_ref: Optional[str] = None) -> list[dict]:
    findings = []
    changed = _changed_files(base_ref)

    # Layer 2 swap check — requires a complete Judicial Hearing.
    layer2_touched = changed & LAYER_2
    if layer2_touched:
        if not _hearing_present(repo_root):
            findings.append({
                'severity': 'VIOLATION',
                'file': ', '.join(sorted(layer2_touched)),
                'message': (
                    'Layer 2 corpus file(s) changed without a recorded Judicial Hearing. '
                    'A complete Hearing (Attorney-A + Attorney-B + Justice ruling) is required '
                    'in docs/governance/case_law.md or docs/governance/hearings/ before '
                    'signals.py or algorithm.py may be committed. '
                    'Run /judicial hear. Amendment 12 — Corpus Supremacy.'
                ),
            })

    # Layer 4 direct edit check — ephemeral files must be regenerated from corpus changes.
    layer4_touched = {
        f for f in changed
        if f in LAYER_4 or Path(f).parts[0] == LAYER_4_PREFIX
    }
    if layer4_touched:
        if not _corpus_changed(changed):
            findings.append({
                'severity': 'VIOLATION',
                'file': ', '.join(sorted(layer4_touched)),
                'message': (
                    'Layer 4 ephemeral file(s) edited directly without a corresponding '
                    'corpus change (Layer 1/2). Correct path: change the corpus, then '
                    'regenerate via /toolchain scaffold. '
                    'Amendment 12 — Corpus Supremacy.'
                ),
            })

    return findings
