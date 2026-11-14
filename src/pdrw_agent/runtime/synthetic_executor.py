"""Bounded host-side synthetic CPU lifecycle / persistent checkpoints.

This is a fixed-code engineering self-test only: no model-provided command,
arbitrary script, data, GPU, network, or PD-RW scientific writes. The executor
is deliberately *not* exposed via MCP, service, or CLI. Python import itself
cannot authenticate a caller; real DEV execution remains disabled.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from ..config import Settings
from ..schemas import AgentError
from .plan import preflight_execution_plan, validate_execution_plan
from .receipts import _db_path, _open, _utc

# This code is fixed by the package, never assembled from user/task input.
_WORKER = """import json, os, pathlib, sys, tempfile, time
out = pathlib.Path(sys.argv[1])
n = int(sys.argv[2])
scenario = sys.argv[3]
if scenario == 'EXIT_NONZERO':
    sys.exit(7)
if scenario == 'SLEEP':
    time.sleep(3)
result = {'schema_version': 'synthetic-result-v1',
          'iterations': n, 'sum_squares': sum(i*i for i in range(n)),
          'profile': 'CPU_SELFTEST_V1'}
with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                 dir=str(out.parent), suffix='.partial',
                                 delete=False) as fp:
    tmp = fp.name
    json.dump(result, fp, sort_keys=True)
os.replace(tmp, out)
"""


def _table(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS synthetic_jobs (
       project_id TEXT NOT NULL,
       operation_id TEXT NOT NULL,
       task_id TEXT NOT NULL,
       plan_sha256 TEXT NOT NULL,
       phase TEXT NOT NULL,
       attempt_count INTEGER NOT NULL,
       output_ref TEXT NOT NULL DEFAULT '',
       output_sha256 TEXT NOT NULL DEFAULT '',
       created_at TEXT NOT NULL,
       updated_at TEXT NOT NULL,
       PRIMARY KEY(project_id, operation_id)
    )""")


def _public(row: sqlite3.Row) -> dict:
    return {
        "project_id": row["project_id"],
        "operation_id": row["operation_id"],
        "task_id": row["task_id"],
        "plan_sha256": row["plan_sha256"],
        "phase": row["phase"],
        "attempt_count": row["attempt_count"],
        "output_sha256": row["output_sha256"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "process_liveness_verified": False,
        "scientific_result": False,
    }


def _safe_private_subdir(base: Path, *parts: str) -> Path:
    """No symlink traversal into a protected project from private scratch."""
    dest = base
    for part in parts:
        dest = dest / part
        if dest.is_symlink():
            raise AgentError("RUNTIME_PATH_SYMLINK", "Private scratch symlink forbidden")
    dest.mkdir(parents=True, exist_ok=True)
    if dest.resolve() != base.resolve() and base.resolve() not in dest.resolve().parents:
        raise AgentError("RUNTIME_SCOPE_INVALID", "Output is outside runtime root")
    return dest


def get_synthetic_job_status(settings: Settings, project_id: str,
                             operation_id: str) -> dict:
    """Read-only checkpoint status; never asserts external process is alive."""
    from .receipts import _identifier
    _identifier(operation_id, "operation_id")
    db_path = _db_path(settings, project_id, create=False)
    if db_path is None or not db_path.is_file():
        return {"status": "SYNTHETIC_JOB_NOT_FOUND", "scientific_result": False}
    if db_path.is_symlink():
        raise AgentError("RUNTIME_DB_SYMLINK", "Private runtime DB symlink forbidden")
    try:
        with _open(db_path, write=False) as db:
            row = db.execute(
                "SELECT * FROM synthetic_jobs WHERE project_id=? AND operation_id=?",
                (project_id, operation_id)).fetchone()
    except sqlite3.OperationalError as exc:
        # Existing v0.6 receipt DB may predate the synthetic table.
        if "no such table" in str(exc).lower():
            return {"status": "SYNTHETIC_JOB_NOT_FOUND", "scientific_result": False}
        raise
    if row is None:
        return {"status": "SYNTHETIC_JOB_NOT_FOUND", "scientific_result": False}
    obj = _public(row)
    if row["phase"] == "RUNNING_UNVERIFIED":
        status = "RECONCILIATION_REQUIRED_NO_AUTOMATIC_RESTART"
    elif row["phase"] == "COMPLETED":
        project_key = hashlib.sha256(project_id.encode("utf-8")).hexdigest()
        private_root = db_path.parent.resolve()
        output = (private_root / "synthetic_jobs" / project_key /
                  operation_id / "result.json")
        # Status reads never create directories and never follow escaping
        # symlinks. A completed receipt alone does not prove output survives.
        try:
            resolved = output.resolve()
            scoped = (private_root in resolved.parents and
                      output.is_file() and not output.is_symlink() and
                      output.stat().st_size <= 4096)
            valid = (scoped and
                     hashlib.sha256(output.read_bytes()).hexdigest() ==
                     row["output_sha256"])
        except OSError:
            valid = False
        obj["output_integrity"] = "MATCH" if valid else "CHANGED_OR_MISSING"
        status = ("SYNTHETIC_JOB_COMPLETED_RECORDED" if valid
                  else "SYNTHETIC_CHECKPOINT_ARTIFACT_MISMATCH")
    else:
        status = "SYNTHETIC_JOB_TERMINAL_RECORDED"
    return {"status": status, "job": obj,
            "synthetic_only": True, "execution_authorized": False,
            "process_liveness_verified": False,
            "next": "NO_AUTOMATIC_RESTART"}


def recent_synthetic_jobs(settings: Settings, project_id: str,
                          limit: int = 6) -> dict:
    """Bounded read-only resume index for private engineering self-tests."""
    db_path = _db_path(settings, project_id, create=False)
    if db_path is None or not db_path.is_file():
        return {"status": "NO_SYNTHETIC_JOBS", "jobs": [],
                "reconciliation_required": False}
    if db_path.is_symlink():
        raise AgentError("RUNTIME_DB_SYMLINK", "Private runtime DB symlink forbidden")
    try:
        with _open(db_path, write=False) as db:
            rows = db.execute(
                """SELECT * FROM synthetic_jobs WHERE project_id=?
                   ORDER BY updated_at DESC, operation_id DESC LIMIT ?""",
                (project_id, max(1, min(limit, 10)))).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return {"status": "NO_SYNTHETIC_JOBS", "jobs": [],
                    "reconciliation_required": False}
        raise
    jobs = [_public(row) for row in rows]
    return {"status": "SYNTHETIC_JOBS_FOUND" if jobs else "NO_SYNTHETIC_JOBS",
            "jobs": jobs,
            "reconciliation_required": any(
                x["phase"] == "RUNNING_UNVERIFIED" for x in jobs),
            "execution_authorized": False,
            "synthetic_only": True,
            "process_liveness_verified": False}


def run_synthetic_in_host(settings: Settings, plan: dict) -> dict:
    """One bounded fixed-profile execution. Never used by WorkBuddy MCP.

    A caller with arbitrary local Python/terminal access can still import
    this function; it is *not* an OS sandbox or authorization primitive.
    """
    spec, digest = validate_execution_plan(plan)
    preflight = preflight_execution_plan(settings, spec)
    if preflight["status"] != "HOST_ONLY_SYNTHETIC_PREFLIGHT_READY":
        return {**preflight, "actual_synthetic_subprocess_executed": False}
    project_id, operation_id = spec["project_id"], spec["operation_id"]
    db_path = _db_path(settings, project_id, create=True)
    if db_path.is_symlink():
        raise AgentError("RUNTIME_DB_SYMLINK", "Private runtime DB symlink forbidden")

    with _open(db_path) as db:
        _table(db)
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT * FROM synthetic_jobs WHERE project_id=? AND operation_id=?",
            (project_id, operation_id)).fetchone()
        if row is not None:
            if row["plan_sha256"] != digest:
                return {"status": "SYNTHETIC_PLAN_CONFLICT",
                        "actual_synthetic_subprocess_executed": False,
                        "execution_authorized": False}
            status = ("ALREADY_COMPLETED_NO_REEXECUTION" if row["phase"] == "COMPLETED"
                      else "RECONCILIATION_REQUIRED_NO_AUTOMATIC_RESTART")
            return {"status": status, "job": _public(row),
                    "actual_synthetic_subprocess_executed": False,
                    "artifact_integrity": "NOT_RECHECKED",
                    "execution_authorized": False}
        now = _utc()
        db.execute("""INSERT INTO synthetic_jobs (
           project_id,operation_id,task_id,plan_sha256,phase,attempt_count,
           created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)""",
           (project_id, operation_id, spec["task_id"], digest,
            "RUNNING_UNVERIFIED", 1, now, now))

    private_root = db_path.parent.resolve()
    project_key = hashlib.sha256(project_id.encode("utf-8")).hexdigest()
    scratch = _safe_private_subdir(
        private_root, "synthetic_jobs", project_key, operation_id)
    output = scratch / "result.json"
    phase = "FAILED"
    output_digest = ""
    try:
        completed = subprocess.run(
            [sys.executable, "-I", "-B", "-c", _WORKER, str(output),
             str(spec["iterations"]), spec["scenario"]],
            cwd=str(scratch),
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            timeout=spec["timeout_seconds"], check=False,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if completed.returncode == 0 and output.is_file() and not output.is_symlink():
            if output.stat().st_size <= 4096:
                obj = json.loads(output.read_text(encoding="utf-8"))
                n = spec["iterations"]
                expected = (n - 1) * n * (2 * n - 1) // 6
                if (obj == {"schema_version": "synthetic-result-v1",
                            "iterations": n, "sum_squares": expected,
                            "profile": "CPU_SELFTEST_V1"}):
                    phase = "COMPLETED"
                    output_digest = hashlib.sha256(output.read_bytes()).hexdigest()
        elif completed.returncode != 0:
            phase = "FAILED_NONZERO_EXIT"
    except subprocess.TimeoutExpired:
        phase = "TIMED_OUT"
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        phase = "FAILED"

    with _open(db_path) as db:
        db.execute("BEGIN IMMEDIATE")
        result = db.execute(
            """UPDATE synthetic_jobs SET phase=?,output_sha256=?,updated_at=?
               WHERE project_id=? AND operation_id=? AND plan_sha256=?
               AND phase='RUNNING_UNVERIFIED' AND attempt_count=1""",
            (phase, output_digest, _utc(), project_id, operation_id, digest))
        if result.rowcount != 1:
            return {"status": "CHECKPOINT_REVISION_CONFLICT",
                    "actual_synthetic_subprocess_executed": True,
                    "execution_authorized": False}
    return {"status": ("SYNTHETIC_EXECUTION_COMPLETED" if phase == "COMPLETED"
                       else "SYNTHETIC_EXECUTION_FAILED"),
            "phase": phase, "output_sha256": output_digest,
            "attempt_count": 1, "actual_synthetic_subprocess_executed": True,
            "synthetic_only": True, "scientific_result": False,
            "execution_authorized": False, "process_liveness_verified": False,
            "next": "NO_AUTOMATIC_RESTART"}
