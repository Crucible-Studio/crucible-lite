#!/usr/bin/env python3
"""
Bash write guard — Amendment 12 Corpus Supremacy for shell-path writes.

Blocks Bash tool calls whose command writes to Layer 2 files (src/signals.py,
src/algorithm.py) when no Judicial Hearing is recorded in the corpus.

An agent that bypasses Edit/Write by using Bash redirection, tee, or sed -i
would otherwise sidestep the article1_check.py PreToolUse hook entirely.
This guard closes that path.

Receives tool call JSON on stdin. Exits 0 (allow) or 2 (block with message).
"""

import json
import re
import subprocess
import sys
from pathlib import Path


_LAYER2_WRITE_RE = re.compile(
    r'(?:'
    r'>{1,2}\s*(?:src/signals\.py|src/algorithm\.py)'   # redirect
    r'|tee\s+(?:src/signals\.py|src/algorithm\.py)'      # tee
    r'|sed\s+.*-i.*(?:src/signals\.py|src/algorithm\.py)'  # sed -i
    r'|python[23]?\s+.*\s+(?:src/signals\.py|src/algorithm\.py)\s*$'  # python write script
    r')'
)


def _repo_root() -> Path | None:
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        capture_output=True, text=True
    )
    return Path(result.stdout.strip()) if result.returncode == 0 else None


def _hearing_present() -> bool:
    root = _repo_root()
    if not root:
        return False
    # Check fragmented hearings manifest first (knowledge graph path).
    manifest = root / 'docs' / 'governance' / 'hearings' / 'MANIFEST.md'
    if manifest.exists():
        text = manifest.read_text()
        # A valid hearing row has Has-A, Has-B, Has-J all TRUE and mentions Layer 2.
        for line in text.splitlines():
            if re.search(r'signals\.py|algorithm\.py|Layer\s*2', line, re.IGNORECASE):
                if line.count('TRUE') >= 3:
                    return True
    # Fallback: monolithic case_law.md regex check.
    case_law = root / 'docs' / 'governance' / 'case_law.md'
    if not case_law.exists():
        return False
    text = case_law.read_text()
    return bool(
        re.search(r'Judicial Hearing', text, re.IGNORECASE) and
        re.search(r'signals\.py|algorithm\.py|Layer 2', text, re.IGNORECASE)
    )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if data.get('tool_name') != 'Bash':
        sys.exit(0)

    command = data.get('tool_input', {}).get('command', '')
    if not _LAYER2_WRITE_RE.search(command):
        sys.exit(0)

    if _hearing_present():
        sys.exit(0)

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  CORPUS SUPREMACY VIOLATION — Bash write to Layer 2 blocked  ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("This Bash command writes to a Layer 2 corpus file (signals.py or algorithm.py).")
    preview = command[:120] + ('...' if len(command) > 120 else '')
    print(f"  Command: {preview}")
    print()
    print("A Judicial Hearing entry for signals.py or algorithm.py is required")
    print("in docs/governance/case_law.md (or docs/governance/hearings/) before")
    print("this write is permitted.")
    print()
    print("Required action:")
    print("  Run /judicial hear before modifying Layer 2 files.")
    print("  Amendment 12 — Corpus Supremacy.")
    print()
    sys.exit(2)


if __name__ == '__main__':
    main()
