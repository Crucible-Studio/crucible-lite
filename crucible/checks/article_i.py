"""
Article I — Physics First enforcement.

Scans diff lines in firmware source for new numeric constants.
Fails if a constant has no surrounding comment citing a domain primitive.
Primitives are extracted from docs/governance/amendments.md Amendment 1.
If Amendment 1 is not ratified, emits a warning but does not fail.
"""

import re
import subprocess
import sys
from typing import Optional
from pathlib import Path

FIRMWARE_EXTENSIONS = {'.c', '.cpp', '.h', '.ino'}

# Matches a bare numeric literal on a new (+) diff line.
# Excludes: array indices, version strings, port numbers, hex addresses.
# Error 14: re.IGNORECASE added so "Traces to" in any capitalisation is excluded.
_NUMERIC = re.compile(
    r'^\+(?!.*//.*traces to).*?'          # new line, not already cited
    r'(?<!["\'/\w#])(\d+\.?\d*|\.\d+)'   # numeric literal
    r'(?!["\'\w])',                        # not inside string/identifier
    re.IGNORECASE                          # Error 14: case-insensitive citation pre-check
)

# A comment on the same or adjacent line that names a primitive or cites Amendment 1.
_CITATION = re.compile(
    r'(?:traces to|primitive|Amendment\s+1|domain primitive)',
    re.IGNORECASE
)


def _extract_primitives(repo_root: Path) -> list[str]:
    """Return primitive names from ratified Amendment 1, or [] if not ratified."""
    amendments = repo_root / 'docs' / 'governance' / 'amendments.md'
    if not amendments.exists():
        return []
    text = amendments.read_text()
    # Amendment 1 is ratified when its block has no PROPOSED line.
    block_match = re.search(
        r'### Amendment 1[^\n]*\n(.*?)(?=\n### Amendment|\Z)', text, re.DOTALL
    )
    if not block_match:
        return []
    block = block_match.group(1)
    if 'PROPOSED' in block:
        return []
    # Extract primitive names: lines starting with a number followed by a dot.
    names = re.findall(r'^\s*\d+\.\s+([A-Z][^\(]+)', block, re.MULTILINE)
    return [n.strip() for n in names]


def _get_diff(base_ref: Optional[str]) -> str:
    if base_ref:
        result = subprocess.run(
            ['git', 'diff', f'{base_ref}...HEAD', '--unified=5'],
            capture_output=True, text=True
        )
    else:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--unified=5'],
            capture_output=True, text=True
        )
    return result.stdout


def run(repo_root: Path, base_ref: Optional[str] = None) -> list[dict]:
    """Return list of findings. Each finding: {file, line, constant, severity}."""
    primitives = _extract_primitives(repo_root)
    findings = []

    if not primitives:
        findings.append({
            'severity': 'WARNING',
            'file': 'docs/governance/amendments.md',
            'line': 0,
            'message': 'Amendment 1 not ratified — Article I primitive check skipped. '
                       'Run /spec collect to define domain primitives.',
        })
        return findings

    diff = _get_diff(base_ref)
    current_file = None
    context_lines = []

    for diff_line in diff.splitlines():
        if diff_line.startswith('--- ') or diff_line.startswith('+++ '):
            if diff_line.startswith('+++ '):
                path = diff_line[4:].lstrip('b/')
                current_file = path if Path(path).suffix in FIRMWARE_EXTENSIONS else None
            continue
        if diff_line.startswith('@@'):
            context_lines = []
            continue

        if current_file is None:
            continue

        # Keep a rolling window of context to check for adjacent citations.
        # Error 21B: context window expanded from 10 to 20 lines (±10 effective).
        context_lines.append(diff_line)
        if len(context_lines) > 20:
            context_lines.pop(0)

        match = _NUMERIC.match(diff_line)
        if not match:
            continue

        constant = match.group(1)
        # Error 18/21C: skip trivial structural values unlikely to be domain constants.
        # Extended set includes 0.5 and single-digit precision args to round().
        if float(constant) in {0, 0.5, 1, 2, 10, 100, 1000}:
            continue

        # Check surrounding context for a citation.
        context_text = '\n'.join(context_lines)
        if _CITATION.search(context_text):
            continue
        # Also check if any primitive name appears nearby.
        if any(p.lower() in context_text.lower() for p in primitives):
            continue

        findings.append({
            'severity': 'VIOLATION',
            'file': current_file,
            'line': diff_line,
            'constant': constant,
            'message': f'New constant {constant} in {current_file} has no primitive citation. '
                       f'Add inline comment: "// Traces to: [primitive name]"',
        })

    return findings
