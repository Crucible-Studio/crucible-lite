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

# Python Layer 2 files: the physics model and algorithm — same Article I bar as firmware.
FIRMWARE_PYTHON_PATHS = {'src/signals.py', 'src/algorithm.py'}

# Matches a bare numeric literal on a new (+) diff line.
# Excludes: array indices, version strings, port numbers, hex addresses.
_NUMERIC = re.compile(
    r'^\+(?!.*//.*traces to).*?'          # new line, not already cited
    r'(?<!["\'/\w#])(\d+\.?\d*|\.\d+)'   # numeric literal
    r'(?!["\'\w])'                         # not inside string/identifier
)

# A comment on the same or adjacent line that names a primitive or cites Amendment 1.
_CITATION = re.compile(
    r'(?:traces to|primitive|Amendment\s+1|domain primitive)',
    re.IGNORECASE
)


def _extract_primitives(repo_root: Path) -> list[str]:
    """Return primitive names from ratified Amendment 1, or [] if not ratified.

    Prefers the fragmented amendments/amendment_01_domain_primitives.md when the
    amendments/ directory exists. Falls back to scanning the monolithic amendments.md.
    """
    # Fragmented path: load only the Amendment 1 file directly — no need to scan all amendments.
    fragment = repo_root / 'docs' / 'governance' / 'amendments' / 'amendment_01_domain_primitives.md'
    if fragment.exists():
        text = fragment.read_text()
        if 'NOT YET RATIFIED' in text or 'PROPOSED' in text:
            return []
        names = re.findall(r'^\s*\d+\.\s+([A-Z][^\(]+)', text, re.MULTILINE)
        return [n.strip() for n in names]

    # Monolithic fallback.
    amendments = repo_root / 'docs' / 'governance' / 'amendments.md'
    if not amendments.exists():
        return []
    text = amendments.read_text()
    block_match = re.search(
        r'### Amendment 1[^\n]*\n(.*?)(?=\n### Amendment|\Z)', text, re.DOTALL
    )
    if not block_match:
        return []
    block = block_match.group(1)
    if 'PROPOSED' in block:
        return []
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


def _is_firmware_path(path: str) -> bool:
    """True for firmware source or Python Layer 2 files."""
    if Path(path).suffix in FIRMWARE_EXTENSIONS:
        return True
    return any(path == p or path.endswith('/' + p) for p in FIRMWARE_PYTHON_PATHS)


def run(repo_root: Path, base_ref: Optional[str] = None) -> list[dict]:
    """Return list of findings. Each finding: {file, line, constant, severity}."""
    primitives = _extract_primitives(repo_root)
    findings = []

    if not primitives:
        diff = _get_diff(base_ref)
        # Committing firmware/Python source before domain primitives are defined is a VIOLATION.
        has_firmware = any(
            _is_firmware_path(line[4:].lstrip('b/'))
            for line in diff.splitlines() if line.startswith('+++ ')
        )
        findings.append({
            'severity': 'VIOLATION' if has_firmware else 'WARNING',
            'file': 'docs/governance/amendments.md',
            'line': 0,
            'message': (
                'Amendment 1 not ratified — Article I cannot be enforced. '
                'No source commits are permitted until domain primitives are defined. '
                'Run /spec collect to define domain primitives before proceeding.'
            ) if has_firmware else (
                'Amendment 1 not ratified — Article I primitive check skipped. '
                'Run /spec collect to define domain primitives.'
            ),
        })
        return findings

    diff = _get_diff(base_ref)
    current_file = None
    context_lines = []

    for diff_line in diff.splitlines():
        if diff_line.startswith('--- ') or diff_line.startswith('+++ '):
            if diff_line.startswith('+++ '):
                path = diff_line[4:].lstrip('b/')
                current_file = path if _is_firmware_path(path) else None
            continue
        if diff_line.startswith('@@'):
            context_lines = []
            continue

        if current_file is None:
            continue

        # Keep a rolling window of context to check for adjacent citations.
        context_lines.append(diff_line)
        if len(context_lines) > 10:
            context_lines.pop(0)

        match = _NUMERIC.match(diff_line)
        if not match:
            continue

        constant = match.group(1)
        # Skip trivial values unlikely to be domain constants.
        if float(constant) in (0, 1, 2, 10, 100, 1000):
            continue

        # Require citation keyword AND at least one actual primitive name from Amendment 1.
        # Keyword alone (e.g. "# Traces to: sensor mismatch (empirical)") is not enough —
        # the primitive name closes the fake-comment bypass.
        context_text = '\n'.join(context_lines)
        has_keyword = bool(_CITATION.search(context_text))
        has_primitive = any(p.lower() in context_text.lower() for p in primitives)
        if has_keyword and has_primitive:
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
