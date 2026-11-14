"""Versioned private operation DB migrations (never a scientific ledger).

Upgrade only on a write-mode connection. Read-only status deliberately
leaves older SQLite files unchanged; no synthetic research state migration.
"""
from __future__ import annotations

import sqlite3

from ..schemas import AgentError

CURRENT_RUNTIME_SCHEMA = 2


def migrate_runtime_db(db: sqlite3.Connection) -> None:
    version = int(db.execute("PRAGMA user_version").fetchone()[0])
    if version > CURRENT_RUNTIME_SCHEMA:
        raise AgentError("RUNTIME_SCHEMA_TOO_NEW",
                         "Newer runtime DB requires a compatible installed agent")
    if version < 1:
        # The v0.5 operational receipts table is created by the existing
        # _open writer. Do not rewrite or rename legacy evidence.
        db.execute("PRAGMA user_version=1")
    if version < 2:
        db.execute("""CREATE TABLE IF NOT EXISTS operation_attempts (
            project_id TEXT NOT NULL,
            operation_id TEXT NOT NULL,
            attempt_id TEXT NOT NULL,
            plan_sha256 TEXT NOT NULL,
            runtime_phase TEXT NOT NULL,
            process_pid INTEGER,
            process_start_token TEXT,
            exit_code INTEGER,
            output_sha256 TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(project_id, operation_id, attempt_id)
        )""")
        db.execute("""CREATE INDEX IF NOT EXISTS operation_attempts_lookup
                   ON operation_attempts(project_id, operation_id, updated_at)""")
        db.execute("PRAGMA user_version=2")
