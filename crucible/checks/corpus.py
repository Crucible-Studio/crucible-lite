"""
Amendment 12 — Corpus Supremacy enforcement.

Layer 2 swap (signals.py / algorithm.py) without Hearing       → VIOLATION
Layer 2 Hearing found but no api-reviewer evidence             → WARNING
Direct edit to Layer 4 ephemeral files without corpus change   → VIOLATION
Layer 4 corpus-change is semantically unrelated                → WARNING
Direct edit to Layer 3 firmware files without a Bill           → VIOLATION
"""

import re
import subprocess
from typing import Optional
from pathlib import Path

LAYER_2 = {'src/signals.py', 'src/algorithm.py'}

LAYER_3_EXTS = {'.c', '.cpp', '.h', '.hpp', '.ino', '.resc'}

LAYER_4 = {'src/events.py', 'src/analysis.py', 'src/plot.py'}
LAYER_4_PREFIX = 'test'   # any file under test/ is Layer 4

LAYER_1 = {
    'docs/device_context.md',
    'docs/governance/amendments.md',
    'docs/toolchain_config.md',
    'CONSTITUTION.md',
}


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


def _commit_message(base_ref: Optional[str]) -> str:
    if base_ref:
        result = subprocess.run(
            ['git', 'log', '--format=%B', f'{base_ref}...HEAD'],
            capture_output=True, text=True
        )
    else:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%B'],
            capture_output=True, text=True
        )
    return result.stdout


def _case_law_text(repo_root: Path) -> str:
    path = repo_root / 'docs' / 'governance' / 'case_law.md'
    return path.read_text() if path.exists() else ''


def _hearing_present(case_law: str) -> bool:
    return bool(
        re.search(r'Judicial Hearing', case_law, re.IGNORECASE) and
        re.search(r'signals\.py|algorithm\.py|Layer 2', case_law, re.IGNORECASE)
    )


def _api_reviewer_evidence_present(case_law: str) -> bool:
    """True if the Layer 2 Hearing entry also cites api-reviewer evidence."""
    return bool(
        re.search(r'api.reviewer|derivation.chain', case_law, re.IGNORECASE)
    )


def _bill_present_for_layer3(case_law: str, changed_firmware: set[str]) -> bool:
    """True if case_law contains an enacted Bill referencing Layer 3 or a changed file."""
    if re.search(r'Layer 3', case_law, re.IGNORECASE):
        return True
    for f in changed_firmware:
        stem = Path(f).name
        if re.search(re.escape(stem), case_law, re.IGNORECASE):
            return True
    return False


def _corpus_changed(changed: set[str]) -> bool:
    return bool(changed & LAYER_1)


def _corpus_change_is_related(changed: set[str], layer4_touched: set[str],
                               commit_msg: str) -> bool:
    """
    Check whether the Layer 1 change in this diff is semantically related to
    the Layer 4 files being edited. Minimum viable heuristic: the commit message
    or the name of the changed Layer 1 file mentions the Layer 4 filename (stem),
    "scaffold", or "regenerat".
    """
    triggers = {'scaffold', 'regenerat'}
    for word in triggers:
        if re.search(word, commit_msg, re.IGNORECASE):
            return True
    for l4 in layer4_touched:
        stem = Path(l4).stem
        if re.search(re.escape(stem), commit_msg, re.IGNORECASE):
            return True
    return False


def run(repo_root: Path, base_ref: Optional[str] = None) -> list[dict]:
    findings = []
    changed = _changed_files(base_ref)
    case_law = _case_law_text(repo_root)
    commit_msg = _commit_message(base_ref)

    # ── Layer 2 swap check ──────────────────────────────────────────────────
    layer2_touched = changed & LAYER_2
    if layer2_touched:
        if not _hearing_present(case_law):
            findings.append({
                'severity': 'VIOLATION',
                'file': ', '.join(sorted(layer2_touched)),
                'message': (
                    'Layer 2 corpus file(s) changed without a recorded Judicial Hearing. '
                    'Run /judicial hear before swapping signals.py or algorithm.py. '
                    'Amendment 12 — Corpus Supremacy §Layer 2.'
                ),
            })
        elif not _api_reviewer_evidence_present(case_law):
            findings.append({
                'severity': 'WARNING',
                'file': ', '.join(sorted(layer2_touched)),
                'message': (
                    'Layer 2 Hearing found in case_law.md but no api-reviewer evidence citation. '
                    'Amendment 12 lines 288–291 require api-reviewer to produce a derivation '
                    'chain report before the Hearing is declared. '
                    'Run api-reviewer on the changed file before the next Layer 2 swap.'
                ),
            })

    # ── Layer 3 firmware check ──────────────────────────────────────────────
    layer3_touched = {
        f for f in changed
        if Path(f).suffix in LAYER_3_EXTS
    }
    if layer3_touched:
        if not _bill_present_for_layer3(case_law, layer3_touched):
            findings.append({
                'severity': 'VIOLATION',
                'file': ', '.join(sorted(layer3_touched)),
                'message': (
                    'Layer 3 firmware file(s) changed without an enacted Bill in case_law.md. '
                    'Firmware edits require a Bill through the Legislative Process. '
                    'Run /judicial bill <description> to produce the Bill. '
                    'Amendment 12 — Corpus Supremacy §Layer 3.'
                ),
            })

    # ── Layer 4 direct edit check ───────────────────────────────────────────
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
                    'regenerate. Amendment 12 — Corpus Supremacy §Layer 4.'
                ),
            })
        elif not _corpus_change_is_related(changed, layer4_touched, commit_msg):
            findings.append({
                'severity': 'WARNING',
                'file': ', '.join(sorted(layer4_touched)),
                'message': (
                    'Layer 4 file(s) changed alongside a Layer 1 corpus file, but the '
                    'commit message does not reference the Layer 4 filename, "scaffold", '
                    'or "regenerat". Confirm the corpus change actually authorizes this '
                    'Layer 4 edit — Amendment 12 §Layer 4 requires the corpus change to '
                    'be the cause, not a coincident edit in the same commit.'
                ),
            })

    return findings
