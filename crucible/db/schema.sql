-- Crucible corpus database schema
-- SQLite; created by crucible/db/migrate.py at repo root as corpus.db
-- Gitignored at runtime. Schema is version-controlled.

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- ── Cases ────────────────────────────────────────────────────────────────────
-- All judicial events: hearings, bills, violations, stage closeouts.

CREATE TABLE IF NOT EXISTS cases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT    NOT NULL,
    date        TEXT    NOT NULL,               -- ISO8601 YYYY-MM-DD
    stage       INTEGER,                        -- 0-4 or NULL (framework-level)
    type        TEXT    NOT NULL                -- 'hearing'|'bill'|'violation'|'closeout'
                CHECK(type IN ('hearing','bill','violation','closeout')),
    summary     TEXT,
    full_text_path TEXT,                        -- anchor or file path in case_law.md
    status      TEXT    NOT NULL DEFAULT 'open' -- 'open'|'settled'|'frozen'
                CHECK(status IN ('open','settled','frozen')),
    layer       INTEGER,                        -- corpus layer affected (1-4) or NULL
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cases_type  ON cases(type);
CREATE INDEX IF NOT EXISTS idx_cases_stage ON cases(stage);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);

-- ── Amendments ───────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS amendments (
    number          INTEGER PRIMARY KEY,
    title           TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'proposed'
                    CHECK(status IN ('proposed','ratified','superseded')),
    ratified_date   TEXT,                       -- ISO8601 or NULL
    traces_to       TEXT,                       -- 'Article I'|'Article II'|'Article I + II'
    citation_count  INTEGER NOT NULL DEFAULT 0,
    summary         TEXT
);

-- ── Violations ───────────────────────────────────────────────────────────────
-- Constitutional violations found by CI or police agent.

CREATE TABLE IF NOT EXISTS violations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    class           TEXT    NOT NULL,           -- e.g. 'ARTICLE-I-VIOLATION'
    severity        TEXT    NOT NULL
                    CHECK(severity IN ('VIOLATION','WARNING','INFO')),
    evidence_path   TEXT,                       -- file:line or commit hash
    session_id      TEXT,                       -- FK to session_log.id (nullable)
    commit_hash     TEXT,
    resolved_at     TEXT,                       -- ISO8601 or NULL (open if NULL)
    resolution_note TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_violations_class    ON violations(class);
CREATE INDEX IF NOT EXISTS idx_violations_resolved ON violations(resolved_at);

-- ── Session log ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS session_log (
    id                  TEXT PRIMARY KEY,       -- UUID
    started             TEXT NOT NULL,          -- ISO8601
    ended               TEXT,                   -- ISO8601 or NULL
    stage               INTEGER,
    agents_invoked      TEXT,                   -- JSON array of {name, invoked_at, status}
    evidence_generated  TEXT,                   -- JSON array of {type, profile, path}
    violation_ids       TEXT,                   -- JSON array of violation IDs
    outcome             TEXT                    -- 'clean'|'violations'|'warnings'|NULL
);

-- ── Knowledge map nodes ──────────────────────────────────────────────────────
-- Mirrors docs/knowledge_map.json but queryable.

CREATE TABLE IF NOT EXISTS km_nodes (
    id      TEXT PRIMARY KEY,       -- slug: 'primitive:cadence', 'signal:accel_z'
    type    TEXT NOT NULL,          -- 'primitive'|'signal'|'threshold'|'failure_mode'|'amendment'|'bill'
    label   TEXT NOT NULL,
    unit    TEXT,
    notes   TEXT
);

CREATE TABLE IF NOT EXISTS km_edges (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   TEXT NOT NULL REFERENCES km_nodes(id),
    target_id   TEXT NOT NULL REFERENCES km_nodes(id),
    relation    TEXT NOT NULL        -- 'traces_to'|'caught_by'|'authorized_by'|'measured_via'
);

CREATE INDEX IF NOT EXISTS idx_km_edges_source ON km_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_km_edges_target ON km_edges(target_id);

-- ── Schema version ───────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS schema_version (
    version     INTEGER NOT NULL,
    applied_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO schema_version(version) VALUES (1);
