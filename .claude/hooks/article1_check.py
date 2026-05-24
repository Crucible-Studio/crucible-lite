#!/usr/bin/env python3
"""
Article I enforcement hook.

Blocks any Edit or Write to source files that introduces:
  - A bare numeric constant (empirical number)
  - An equation containing numeric operands
  - A comparison threshold
  - A named setting with an opaque value

...without an adjacent comment that cites a domain primitive from Amendment 1.

Receives tool call JSON on stdin. Exits 0 (allow) or 2 (block with message).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

# ─── Patterns that satisfy Article I ──────────────────────────────────────────
# If any of these appear within ±10 lines of a flagged value, it is cited.
CITATION_PATTERNS = [
    r'traces to',
    r'amendment\s*1',
    r'primitive\s*\d',
    r'domain primitive',
    r'derived from',
    r'physical derivation',
    r'unit[:\s]',
    r'[A-Z_]{3,}\s*\(',   # e.g. THRESHOLD_DPS( — annotated constant
]

# ─── Source files where Article I applies ─────────────────────────────────────
SOURCE_PATTERNS = [
    r'src/signals\.py$',
    r'src/algorithm\.py$',
    r'\.(c|h|cpp|hpp|ino)$',  # Error 17A: .ino added
]

# ─── Files to skip unconditionally ────────────────────────────────────────────
SKIP_PATTERNS = [
    r'test',
    r'spec',
    r'__init__',
    r'setup\.py$',
    r'conftest',
]

# ─── Trivial structural values that are NOT domain constants ──────────────────
# Error 18: skip initialisation defaults and structural numerics
TRIVIAL_VALUES = {0, 0.0, 0.5, 1, -1, 2, 3, 4, 5, 6}  # structural, not domain


def _is_trivial_value(val_str: str) -> bool:
    """Return True if val_str is a trivial structural value, not a domain constant."""
    try:
        return float(val_str) in TRIVIAL_VALUES
    except ValueError:
        return False


def _find_repo_root() -> Path | None:
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        capture_output=True, text=True
    )
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def _load_primitives() -> list[str]:
    """Load Amendment 1 primitive names from the ratified amendment file.

    Prefers fragmented amendments/amendment_01_domain_primitives.md.
    Falls back to the monolithic amendments.md for backward compatibility.
    """
    root = _find_repo_root()
    if not root:
        return []
    # Fragmented path first — loads only one small file.
    fragment = root / 'docs' / 'governance' / 'amendments' / 'amendment_01_domain_primitives.md'
    if fragment.exists():
        text = fragment.read_text()
        if 'NOT YET RATIFIED' in text or 'PROPOSED' in text:
            return []
        names = re.findall(r'^\s*\d+\.\s+([A-Z][^\(]+)', text, re.MULTILINE)
        return [n.strip() for n in names]
    # Monolithic fallback.
    amendments = root / 'docs' / 'governance' / 'amendments.md'
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


# Loaded once at module import — re-run of hook gets fresh module each invocation.
_PRIMITIVES: list[str] = _load_primitives()


def is_source_file(path: str) -> bool:
    path = path.replace('\\', '/')
    for skip in SKIP_PATTERNS:
        if re.search(skip, path, re.IGNORECASE):
            return False
    return any(re.search(p, path) for p in SOURCE_PATTERNS)


def has_citation(lines: list[str], idx: int) -> bool:
    """True if lines within ±10 of idx contain a primitive citation.

    Error 21B: window expanded from ±3 to ±10 lines.
    When Amendment 1 is ratified (_PRIMITIVES non-empty), the citation must name
    at least one actual primitive — a fake '# Traces to: sensor mismatch (empirical)'
    satisfies the keyword check but not the primitive-name check, so it fails.
    When Amendment 1 is not yet ratified, keyword-only check applies (graceful).
    """
    window = lines[max(0, idx - 10): idx + 11]   # Error 21B: ±10 lines
    combined = '\n'.join(window)
    has_keyword = any(re.search(p, combined, re.IGNORECASE) for p in CITATION_PATTERNS)
    if not has_keyword:
        return False
    if not _PRIMITIVES:
        return True
    return any(p.lower() in combined.lower() for p in _PRIMITIVES)


def _is_typed_default(line: str, val_str: str) -> bool:
    """Return True if the value is a typed function-signature default.

    Error 18: skip patterns like `name: type = 0.0` or `name=0` in signatures.
    """
    # Python typed default: `param: float = 0.0` or `param=0`
    if re.search(r'\w+\s*:\s*\w+\s*=\s*' + re.escape(val_str) + r'\b', line):
        return True
    # Function signature default (no type hint): `def f(x=0):` or `f(n_steps=1)`
    if re.search(r'\w+\s*=\s*' + re.escape(val_str) + r'\s*[,\)]', line):
        return True
    return False


def _is_round_precision(line: str, val_str: str) -> bool:
    """Return True if the value is a precision arg to round().

    Error 18: skip `round(x, N)` where N ∈ {0..6}.
    """
    return bool(re.search(r'\bround\s*\([^,]+,\s*' + re.escape(val_str) + r'\s*\)', line))


def find_violations(content: str) -> list[tuple[int, str, str]]:
    """
    Returns list of (line_number, line_text, matched_snippet) for every
    empirical value that lacks an Article I citation.
    """
    violations = []
    lines = content.split('\n')

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip blank lines
        if not stripped:
            continue

        # Skip pure comment lines
        if re.match(r'^\s*(#|//|\*|/\*)', line):
            continue

        # Skip string-only lines
        if re.match(r"""^\s*['"]""", stripped):
            continue

        # Error 21A: strip inline comment before applying rules — numbers in
        # comment text (e.g. "# At 208 Hz: floor(208 × 0.600)") must not fire.
        code_part = line.split('#')[0]

        # ── Rule 1: bare numeric constant or assignment ─────────────────────
        # Matches: THRESHOLD = 30.0  /  float x = 0.85  /  #define CUTOFF 10
        r1 = re.search(
            r'(?:(?:=|#define\s+\w+)\s*)(\b\d+\.?\d*\b)',
            code_part
        )

        # ── Rule 2: equation with numeric operand ───────────────────────────
        # Matches: result = a * 0.7 + b * 0.3  /  x / 9.81
        r2 = re.search(
            r'[\w\)]\s*[*/]\s*(\d+\.?\d+)',
            code_part
        )

        # ── Rule 3: comparison threshold ────────────────────────────────────
        # Matches: if value > 30  /  while count >= 100
        r3 = re.search(
            r'(?:>|<|>=|<=|==)\s*(\d+\.?\d*)\b',
            code_part
        )

        # ── Rule 4: opaque keyword setting ──────────────────────────────────
        # Matches: cutoff = 10  /  n_steps = 100  /  ODR = 104
        r4 = re.search(
            r'\b(?:cutoff|threshold|limit|rate|freq|odr|gain|scale|alpha|beta|gamma|n_steps|window|timeout)\s*=\s*(\d+\.?\d*)',
            code_part,
            re.IGNORECASE
        )

        hit = r1 or r2 or r3 or r4
        if not hit:
            continue

        val_str = hit.group(1)

        # Error 18: skip trivial structural values
        if _is_trivial_value(val_str):
            continue

        # Error 18: skip typed defaults in function signatures
        if _is_typed_default(line, val_str):
            continue

        # Error 18: skip round() precision arguments
        if _is_round_precision(line, val_str):
            continue

        if not has_citation(lines, i):
            violations.append((i + 1, line.rstrip(), hit.group(0)))

    return violations


def print_violation_report(file_path: str, violations: list[tuple[int, str, str]]) -> None:
    # Error 17B: all output in print_violation_report goes to stderr.
    # Claude Code reads the block message from stderr; stdout is discarded.
    print(file=sys.stderr)
    print("╔══════════════════════════════════════════════════════════════╗", file=sys.stderr)
    print("║  ARTICLE I VIOLATION — Human intervention required           ║", file=sys.stderr)
    print("╚══════════════════════════════════════════════════════════════╝", file=sys.stderr)
    print(file=sys.stderr)
    print(f"File: {file_path}", file=sys.stderr)
    print(file=sys.stderr)
    print("The following values have no domain primitive citation (Amendment 1):", file=sys.stderr)
    print(file=sys.stderr)
    for lineno, line_text, match in violations[:6]:
        print(f"  Line {lineno:>4}: {line_text.strip()}", file=sys.stderr)
        print(f"           ↳ '{match}' — empirical value, equation, or opaque setting", file=sys.stderr)
        print(file=sys.stderr)
    if len(violations) > 6:
        print(f"  ... and {len(violations) - 6} more.", file=sys.stderr)
        print(file=sys.stderr)
    print("Required action before this is permitted:", file=sys.stderr)
    print("  Add a comment on or above each flagged line citing the", file=sys.stderr)
    print("  Amendment 1 primitive that justifies the value. Format:", file=sys.stderr)
    print(file=sys.stderr)
    print("  Python:  # Traces to Amendment 1 primitive N: [derivation]", file=sys.stderr)
    print("  C/C++:   /* derived from [primitive name] ([unit]): [formula] */", file=sys.stderr)
    print(file=sys.stderr)
    print("Citation must appear on the SAME LINE as the constant, or within ±10 lines,", file=sys.stderr)
    print("and must name an actual Amendment 1 primitive (not just a keyword).", file=sys.stderr)
    print(file=sys.stderr)
    print("A value without a primitive citation is a guess.", file=sys.stderr)
    print("Guesses are not permitted under Article I — for agents AND engineers.", file=sys.stderr)
    print(file=sys.stderr)


def run_agent_mode() -> None:
    """Called by Claude Code PreToolUse hook — reads tool JSON from stdin."""
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get('tool_name', '')
    tool_input = data.get('tool_input', {})

    if tool_name == 'Write':
        file_path = tool_input.get('file_path', '')
        content = tool_input.get('content', '')
    elif tool_name == 'Edit':
        file_path = tool_input.get('file_path', '')
        content = tool_input.get('new_string', '')
    else:
        sys.exit(0)

    if not file_path or not content or not is_source_file(file_path):
        sys.exit(0)

    violations = find_violations(content)
    if violations:
        print_violation_report(file_path, violations)
        sys.exit(2)
    sys.exit(0)


def run_staged_mode() -> None:
    """Called by git pre-commit hook — checks all staged source files."""
    import subprocess

    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
        capture_output=True, text=True
    )
    staged_files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    source_files = [f for f in staged_files if is_source_file(f)]

    if not source_files:
        sys.exit(0)

    all_violations: list[tuple[str, list[tuple[int, str, str]]]] = []

    for file_path in source_files:
        content_result = subprocess.run(
            ['git', 'show', f':{file_path}'],
            capture_output=True, text=True
        )
        if content_result.returncode != 0:
            continue
        violations = find_violations(content_result.stdout)
        if violations:
            all_violations.append((file_path, violations))

    if all_violations:
        for file_path, violations in all_violations:
            print_violation_report(file_path, violations)
        # Error 17B: "Commit blocked." also goes to stderr
        print("Commit blocked. Fix the violations above, then recommit.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)


def main():
    if '--staged' in sys.argv:
        run_staged_mode()
    else:
        run_agent_mode()


if __name__ == '__main__':
    main()
