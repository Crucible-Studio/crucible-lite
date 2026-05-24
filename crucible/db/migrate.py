"""
Migration runner.

Usage:
  python -m crucible.db.migrate           — create/migrate corpus.db
  python -m crucible.db.migrate --status  — print current schema version
  python -m crucible.db.migrate --seed    — seed amendments from docs/governance/amendments.md
"""

import argparse
import re
import sys
from pathlib import Path

from .conn import get as get_conn


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def status() -> int:
    conn = get_conn()
    row = conn.execute('SELECT version, applied_at FROM schema_version ORDER BY version DESC LIMIT 1').fetchone()
    if row:
        print(f'Schema version {row["version"]} — applied {row["applied_at"]}')
    else:
        print('No schema version found.')
    return 0


def seed_amendments() -> int:
    """Parse docs/governance/amendments.md and populate the amendments table."""
    amend_path = _repo_root() / 'docs' / 'governance' / 'amendments.md'
    if not amend_path.exists():
        print('docs/governance/amendments.md not found — nothing to seed.')
        return 1

    text = amend_path.read_text()
    conn = get_conn()

    # Pattern: ### Amendment N — Title
    blocks = re.split(r'(?=### Amendment \d+)', text)
    inserted = 0
    for block in blocks:
        m = re.match(r'### Amendment (\d+) — (.+)', block)
        if not m:
            continue
        number = int(m.group(1))
        title  = m.group(2).strip()

        status_match = re.search(r'\*Status:\s*(PROPOSED|RATIFIED|SUPERSEDED)', block, re.IGNORECASE)
        status = status_match.group(1).lower() if status_match else 'proposed'

        date_match = re.search(r'ratified.*?(\d{4}-\d{2}-\d{2})', block, re.IGNORECASE)
        ratified_date = date_match.group(1) if date_match else None

        traces_match = re.search(r'\*Traces to:\s*(.+)\*', block)
        traces_to = traces_match.group(1).strip() if traces_match else None

        conn.execute(
            '''INSERT OR REPLACE INTO amendments(number, title, status, ratified_date, traces_to)
               VALUES (?, ?, ?, ?, ?)''',
            (number, title, status, ratified_date, traces_to)
        )
        inserted += 1

    conn.commit()
    print(f'Seeded {inserted} amendment(s) into corpus.db.')
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--status', action='store_true')
    parser.add_argument('--seed',   action='store_true', help='Seed amendments from amendments.md')
    args = parser.parse_args()

    if args.status:
        return status()
    if args.seed:
        return seed_amendments()

    # Default: ensure schema exists
    conn = get_conn()
    row = conn.execute('SELECT version FROM schema_version ORDER BY version DESC LIMIT 1').fetchone()
    print(f'corpus.db ready — schema version {row["version"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
