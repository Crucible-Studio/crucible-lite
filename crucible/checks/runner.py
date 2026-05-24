"""
Constitutional check runner.

Usage:
  python -m crucible.checks.runner [--base-ref <ref>] [--pre-commit]

  --base-ref   Git ref to diff against (CI: use PR base branch, e.g. origin/main)
  --pre-commit Staged files only; warnings do not block commit

Exits 0 if no VIOLATION found. Exits 1 if any VIOLATION found.
"""

import argparse
import subprocess
import sys
from typing import Optional
from pathlib import Path

from .article_i import run as check_article_i
from .corpus import run as check_corpus
from .stage_gate import run as check_stage_gate


def _resolve_repo_root() -> Path:
    """Resolve repo root from working directory, not from the installed package path.

    Path(__file__).parents[3] breaks when crucible is pip-installed into site-packages
    because the walk lands in the Python prefix, not the project root.
    git rev-parse always resolves relative to the CWD where the command is invoked.
    """
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        capture_output=True, text=True, cwd=Path.cwd()
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    # Fallback: works when running from a monolithic repo checkout (non-pip path)
    return Path(__file__).resolve().parents[3]


def _check_hooks_path() -> list[dict]:
    """Warn when core.hooksPath points to a directory that does not exist."""
    result = subprocess.run(
        ['git', 'config', 'core.hooksPath'],
        capture_output=True, text=True
    )
    configured = result.stdout.strip()
    if configured:
        hooks_dir = Path.cwd() / configured
        if not hooks_dir.exists():
            return [{
                'severity': 'WARNING',
                'file': '.git/config',
                'message': (
                    f'git core.hooksPath is set to "{configured}" but that directory '
                    f'does not exist — pre-commit hook is inactive. '
                    f'Run: git config core.hooksPath <correct-path>'
                ),
            }]
    return []


def _header(text: str) -> str:
    bar = '═' * 54
    return f'\n{bar}\n{text}\n{bar}'


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-ref', default=None,
                        help='Git ref to diff against (e.g. origin/main)')
    parser.add_argument('--pre-commit', action='store_true',
                        help='Pre-commit mode: staged files only, warnings allowed')
    args = parser.parse_args()

    repo_root = _resolve_repo_root()
    base_ref = args.base_ref
    pre_commit = args.pre_commit

    all_findings: list[dict] = []
    all_findings += _check_hooks_path()
    all_findings += check_article_i(repo_root, base_ref)
    all_findings += check_corpus(repo_root, base_ref)
    all_findings += check_stage_gate(repo_root, base_ref)

    violations = [f for f in all_findings if f['severity'] == 'VIOLATION']
    warnings   = [f for f in all_findings if f['severity'] == 'WARNING']

    label = 'PRE-COMMIT CHECK' if pre_commit else 'CONSTITUTIONAL CHECK — CI'
    print(_header(label))
    print(f'VIOLATIONS: {len(violations)}   WARNINGS: {len(warnings)}')

    for f in all_findings:
        sev = f['severity']
        print(f'\n[{sev}] {f.get("file", "")}')
        print(f'  {f["message"]}')
        if f.get('amendment_citation'):
            print(f'  → {f["amendment_citation"]}')

    print()
    if violations:
        print('═' * 54)
        if pre_commit:
            print('Commit blocked — resolve VIOLATIONS before committing.')
            print('Run /review code for full Article I audit.')
        else:
            print('Merge blocked — resolve VIOLATIONS before this PR can merge.')
            print('Run the police agent for a full audit: use Agent tool, subagent_type=police')
        print('═' * 54)
        return 1

    if warnings:
        print('Warnings present — review before stage gate exit.')

    print('Constitutional check passed.' if not pre_commit else 'Pre-commit check passed.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
