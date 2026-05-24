"""
Connection helper — returns a sqlite3.Connection to corpus.db at repo root.
Creates the DB and runs schema migration on first call.
"""

import sqlite3
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _db_path() -> Path:
    return _repo_root() / 'corpus.db'


def _schema_path() -> Path:
    return Path(__file__).parent / 'schema.sql'


def get() -> sqlite3.Connection:
    """Return an open connection to corpus.db, creating it if necessary."""
    db = _db_path()
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
    if cur.fetchone() is None:
        schema = _schema_path().read_text()
        conn.executescript(schema)
        conn.commit()
