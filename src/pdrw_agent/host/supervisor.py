"""v0.7.2 real OS child-process supervision, fixed CPU diagnostic only.

The host is an operator-launched *separate process* when invoked through
host.cli. It exposes no network service and no MCP execution tool. An in-
process instance may cancel its own child. Arbitrary DEV and GPU are disabled.

Crash semantics: a committed STARTING/RUNNING attempt is never retried
implicitly; status rechecks identity and output but does not adopt unknown
processes or infer a user's authorization.
"""
from __future__ import annotations

import hashlib
import json
import os
import signal
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path

from ..config import Settings
from ..runtime.plan import preflight_execution_plan, validate_execution_plan
from ..runtime.receipts import _db_path, _open, _utc
from ..schemas import AgentError
from .process_identity import observe_process

# Hardcoded worker. No user code, arbitrary command, package import, network,
# read of research data, environment variables or configurable file input.
WORKER = """import ctypes,json,os,pathlib,signal,sys,tempfile,time
out=pathlib.Path(sys.argv[1])
n=int(sys.argv[2]); scenario=sys.argv[3]; parent=int(sys.argv[4])
if sys.platform.startswith('linux'):
    libc=ctypes.CDLL(None)
    libc.prctl(1,signal.SIGKILL,0,0,0)
    if os.getppid()!=parent: os._exit(11)
if scenario=='EXIT_NONZERO': sys.exit(7)
if scenario=='SLEEP': time.sleep(30)
v={'schema_version':'host-cpu-selftest-v1','iterations':n,
   'sum_squares':sum(i*i for i in range(n))}
with tempfile.NamedTemporaryFile('w',dir=str(out.parent),suffix='.tmp',
                                 encoding='utf-8',delete=False) as f:
    json.dump(v,f,sort_keys=True); tmp=f.name
os.replace(tmp,out)
"""
TABLE = """CREATE TABLE IF NOT EXISTS host_jobs (
    project_id TEXT NOT NULL, operation_id TEXT NOT NULL,
    task_id TEXT NOT NULL, plan_sha256 TEXT NOT NULL,
    attempt_id TEXT NOT NULL, phase TEXT NOT NULL,
    pid INTEGER, start_token TEXT,
    exit_code INTEGER, output_sha256 TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
    PRIMARY KEY(project_id, operation_id)
)"""


def _public(row: sqlite3.Row) -> dict:
    return {key: row[key] for key in
            ("project_id", "operation_id", "task_id", "plan_sha256",
             "attempt_id", "phase", "pid", "start_token", "exit_code",
             "output_sha256", "updated_at")}


def _root(settings: Settings, project_id: str, create: bool) -> Path | None:
    db = _db_path(settings, project_id, create=create)
    if db is None:
        return None
    if db.is_symlink():
        raise AgentError("HOST_DB_SYMLINK", "Runtime database symlink forbidden")
    return db


def _scratch(root: Path, project_id: str, operation_id: str) -> Path:
    digest = hashlib.sha256(project_id.encode("utf-8")).hexdigest()
    dst = root / "host_jobs" / digest / operation_id
    for segment in (root / "host_jobs", root / "host_jobs" / digest, dst):
        if segment.is_symlink():
            raise AgentError("HOST_OUTPUT_SYMLINK", "Host scratch symlink forbidden")
    dst.mkdir(parents=True, exist_ok=True)
    if root.resolve() not in dst.resolve().parents:
        raise AgentError("HOST_SCRATCH_ESCAPE", "Private output escaped runtime root")
    return dst


def _inspect_result(db_path: Path, row: sqlite3.Row) -> str:
    digest = hashlib.sha256(row["project_id"].encode("utf-8")).hexdigest()
    file = db_path.parent / "host_jobs" / digest / row["operation_id"] / "result.json"
    try:
        if (not file.is_file() or file.is_symlink() or
                db_path.parent.resolve() not in file.resolve().parents or
                file.stat().st_size > 4096):
            return "MISSING_OR_UNTRUSTED"
        actual = hashlib.sha256(file.read_bytes()).hexdigest()
    except OSError:
        return "MISSING_OR_UNTRUSTED"
    return "MATCH" if actual == row["output_sha256"] else "TAMPERED"


def get_host_diagnostic_status(settings: Settings, project_id: str,
                               operation_id: str) -> dict:
    """Cross-session read-only status. Never assumes PID reuse means same job."""
    from ..runtime.receipts import _identifier
    _identifier(operation_id, "operation_id")
    path = _root(settings, project_id, create=False)
    if path is None or not path.is_file():
        return {"status": "HOST_JOB_NOT_FOUND", "execution_authorized": False}
    try:
        with _open(path, write=False) as db:
            row = db.execute(
                "SELECT * FROM host_jobs WHERE project_id=? AND operation_id=?",
                (project_id, operation_id)).fetchone()
            linked = None
            if row is not None:
                try:
                    linked = db.execute(
                        """SELECT attempt_id, plan_sha256, runtime_phase
                           FROM operation_attempts WHERE project_id=?
                           AND operation_id=? AND attempt_id=?""",
                        (project_id, operation_id, row["attempt_id"])).fetchone()
                except sqlite3.OperationalError as missing:
                    if "no such table" not in str(missing).lower():
                        raise
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return {"status": "HOST_JOB_NOT_FOUND", "execution_authorized": False}
        raise
    if row is None:
        return {"status": "HOST_JOB_NOT_FOUND", "execution_authorized": False}
    status = "HOST_TERMINAL_RECORDED"
    obj = _public(row)
    if linked is None:
        obj["attempt_link"] = "LEGACY_UNLINKED"
    else:
        consistent = (linked["runtime_phase"] == row["phase"] and
                      linked["plan_sha256"] == row["plan_sha256"] and
                      linked["attempt_id"] == row["attempt_id"])
        obj["attempt_link"] = "MATCHED" if consistent else "CONFLICT"
    if row["phase"] == "COMPLETED":
        obj["output_integrity"] = _inspect_result(path, row)
        status = ("HOST_COMPLETED_HASH_MATCHED_ONLY" if obj["output_integrity"] == "MATCH"
                  else "HOST_COMPLETION_ARTIFACT_CONFLICT")
    elif row["phase"] in {"STARTING_UNVERIFIED", "RUNNING_UNVERIFIED"}:
        # A fresh observer only knows PID + creation token, not ownership.
        observed = observe_process(row["pid"]) if row["pid"] else {}
        same = bool(row["start_token"] and
                    observed.get("start_token") == row["start_token"])
        live_snapshot = same and observed.get("liveness_verified") is True
        status = ("HOST_PROCESS_IDENTITY_OBSERVED_NOT_ADOPTED" if live_snapshot
                  else "HOST_RECONCILIATION_REQUIRED")
        obj["process_identity_matched"] = same
        obj["running_snapshot_observed"] = live_snapshot
    return {"status": status, "job": obj,
            "scientific_result": False, "execution_authorized": False,
            "host_ownership_verified": False,
            "safe_to_restart": False,
            "synthetic_only": True}


def _launch_worker(argv: list[str], scratch: Path):
    if sys.platform == "win32":
        from .winjob import launch_windows_job
        return launch_windows_job(argv, scratch)
    return subprocess.Popen(argv, cwd=str(scratch),
                            start_new_session=True,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)


def _terminate_tree(proc) -> None:
    """Terminate this host's known process group or Windows Job Object."""
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        proc.terminate()   # WinJobProcess uses TerminateJobObject.
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass


def _reap_or_kill(proc) -> None:
    """Escalate on POSIX; Windows Job close is kill-on-close."""
    if sys.platform != "win32":
        try:
            proc.wait(timeout=1)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=1)


def recent_host_diagnostics(settings: Settings, project_id: str,
                            limit: int = 6) -> dict:
    """Private read-only resume hints; no process adoption or automatic retry."""
    path = _root(settings, project_id, create=False)
    if path is None or not path.is_file():
        return {"status": "NO_HOST_DIAGNOSTICS", "jobs": [],
                "reconciliation_required": False}
    try:
        with _open(path, write=False) as db:
            rows = db.execute(
                """SELECT * FROM host_jobs WHERE project_id=?
                   ORDER BY updated_at DESC, operation_id DESC LIMIT ?""",
                (project_id, max(1, min(limit, 10)))).fetchall()
            try:
                links = db.execute(
                    """SELECT operation_id, attempt_id, runtime_phase, plan_sha256
                       FROM operation_attempts WHERE project_id=?
                       ORDER BY updated_at DESC LIMIT 40""",
                    (project_id,)).fetchall()
            except sqlite3.OperationalError as missing:
                if "no such table" not in str(missing).lower():
                    raise
                links = []
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return {"status": "NO_HOST_DIAGNOSTICS", "jobs": [],
                    "reconciliation_required": False}
        raise
    index = {(link["operation_id"], link["attempt_id"]): link for link in links}
    jobs = []
    for row in rows:
        item = _public(row)
        link = index.get((row["operation_id"], row["attempt_id"]))
        item["attempt_link"] = (
            "LEGACY_UNLINKED" if link is None else
            "MATCHED" if link["runtime_phase"] == row["phase"] and
            link["plan_sha256"] == row["plan_sha256"] else "CONFLICT")
        if row["phase"] == "COMPLETED":
            item["output_integrity"] = _inspect_result(path, row)
        jobs.append(item)
    pending = any(
        item["phase"] in {"STARTING_UNVERIFIED", "RUNNING_UNVERIFIED"} or
        item.get("output_integrity") in {"MISSING_OR_UNTRUSTED", "TAMPERED"} or
        item["attempt_link"] == "CONFLICT" for item in jobs)
    return {"status": "HOST_DIAGNOSTICS_FOUND" if jobs else "NO_HOST_DIAGNOSTICS",
            "jobs": jobs, "reconciliation_required": pending,
            "scientific_result": False, "execution_authorized": False,
            "safe_to_auto_restart": False}


class HostSupervisor:
    """A single live host instance; handles are not reconstructed from JSON."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._live: dict[tuple[str, str], object] = {}
        self._cancelled: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    def cancel(self, project_id: str, operation_id: str) -> dict:
        """Only cancel an owned live fixed diagnostic process handle."""
        key = (project_id, operation_id)
        with self._lock:
            child = self._live.get(key)
        if child is None:
            return {"status": "NOT_OWNED_BY_THIS_HOST", "cancelled": False}
        if child.poll() is None:
            with self._lock:
                self._cancelled.add(key)
            _terminate_tree(child)
            return {"status": "HOST_TERMINATION_REQUESTED", "cancelled": True}
        return {"status": "ALREADY_EXITED", "cancelled": False}

    def run_fixed_diagnostic(self, plan: dict) -> dict:
        spec, plan_sha = validate_execution_plan(plan)
        preflight = preflight_execution_plan(self.settings, spec)
        if preflight["status"] != "HOST_ONLY_SYNTHETIC_PREFLIGHT_READY":
            return {"status": preflight["status"], "execute_performed": False,
                    "execution_authorized": False}
        project_id, operation_id = spec["project_id"], spec["operation_id"]
        dbpath = _root(self.settings, project_id, create=True)
        with _open(dbpath) as db:
            db.execute(TABLE)
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM host_jobs WHERE project_id=? AND operation_id=?",
                (project_id, operation_id)).fetchone()
            if row:
                return {"status": ("HOST_PLAN_CONFLICT" if row["plan_sha256"] != plan_sha
                                   else "HOST_ALREADY_RECORDED_NO_RELAUNCH"),
                        "execute_performed": False, "execution_authorized": False}
            # A logical operation identifier must not simultaneously name
            # a research receipt and a fixed engineering diagnostic.
            occupied = db.execute(
                "SELECT 1 FROM operations WHERE project_id=? AND operation_id=?",
                (project_id, operation_id)).fetchone()
            if occupied:
                return {"status": "HOST_OPERATION_ID_RESERVED_BY_RECEIPT",
                        "execute_performed": False, "execution_authorized": False}
            attempt = uuid.uuid4().hex
            now = _utc()
            db.execute("""INSERT INTO host_jobs
               (project_id,operation_id,task_id,plan_sha256,attempt_id,
                phase,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)""",
               (project_id, operation_id, spec["task_id"], plan_sha,
                attempt, "STARTING_UNVERIFIED", now, now))
            db.execute("""INSERT INTO operation_attempts (
                project_id,operation_id,attempt_id,plan_sha256,runtime_phase,
                created_at,updated_at) VALUES (?,?,?,?,?,?,?)""",
                (project_id, operation_id, attempt, plan_sha,
                 "STARTING_UNVERIFIED", now, now))
        # The durable STARTING record precedes any OS process launch.
        scratch = _scratch(dbpath.parent.resolve(), project_id, operation_id)
        output = scratch / "result.json"
        proc = None
        phase = "FAILED"
        exit_code = None
        result_hash = ""
        key = (project_id, operation_id)
        try:
            argv = [sys.executable, "-I", "-B", "-c", WORKER, str(output),
                    str(spec["iterations"]), spec["scenario"], str(os.getpid())]
            proc = _launch_worker(argv, scratch)
            observed = observe_process(proc.pid)
            with self._lock:
                self._live[key] = proc
            with _open(dbpath) as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("""UPDATE host_jobs
                     SET phase='RUNNING_UNVERIFIED',pid=?,start_token=?,updated_at=?
                     WHERE project_id=? AND operation_id=? AND attempt_id=?
                     AND phase='STARTING_UNVERIFIED'""",
                     (proc.pid, observed.get("start_token"), _utc(),
                      project_id, operation_id, attempt))
                db.execute("""UPDATE operation_attempts SET
                     runtime_phase='RUNNING_UNVERIFIED',process_pid=?,
                     process_start_token=?,updated_at=?
                     WHERE project_id=? AND operation_id=? AND attempt_id=?
                     AND runtime_phase='STARTING_UNVERIFIED'""",
                     (proc.pid, observed.get("start_token"), _utc(),
                      project_id, operation_id, attempt))
            deadline = time.monotonic() + spec["timeout_seconds"]
            while proc.poll() is None:
                if time.monotonic() > deadline:
                    phase = "TIMED_OUT"
                    _terminate_tree(proc)
                    break
                time.sleep(0.02)
            if proc.poll() is None:
                time.sleep(0.05)
            exit_code = proc.poll()
            with self._lock:
                cancelled = key in self._cancelled
            if phase == "TIMED_OUT":
                pass
            elif cancelled:
                phase = "CANCELLED"
            elif exit_code == 0 and output.is_file() and not output.is_symlink():
                data = output.read_bytes()
                if len(data) <= 4096:
                    expected = ((spec["iterations"] - 1) * spec["iterations"] *
                                (2 * spec["iterations"] - 1) // 6)
                    value = json.loads(data)
                    if value == {"schema_version": "host-cpu-selftest-v1",
                                 "iterations": spec["iterations"],
                                 "sum_squares": expected}:
                        phase = "COMPLETED"
                        result_hash = hashlib.sha256(data).hexdigest()
            elif exit_code is not None:
                phase = "FAILED_NONZERO_EXIT"
        except (KeyboardInterrupt, SystemExit):
            # An operator interruption is not scientific failure. Keep a
            # distinct terminal checkpoint and clean up the owned process;
            # a restart is never automatic.
            phase = "INTERRUPTED"
            raise
        except (OSError, ValueError, json.JSONDecodeError, AgentError):
            phase = "FAILED"
        finally:
            if proc is not None:
                try:
                    if proc.poll() is None:
                        _terminate_tree(proc)
                    _reap_or_kill(proc)
                except (OSError, AgentError, subprocess.TimeoutExpired):
                    pass
                if hasattr(proc, "close"):
                    proc.close()
                with self._lock:
                    self._live.pop(key, None)
                    self._cancelled.discard(key)
            with _open(dbpath) as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute("""UPDATE host_jobs SET phase=?,exit_code=?,
                     output_sha256=?,updated_at=? WHERE project_id=?
                     AND operation_id=? AND attempt_id=?
                     AND phase IN ('RUNNING_UNVERIFIED','STARTING_UNVERIFIED')""",
                     (phase, exit_code, result_hash, _utc(),
                      project_id, operation_id, attempt))
                db.execute("""UPDATE operation_attempts SET runtime_phase=?,
                     exit_code=?,output_sha256=?,updated_at=?
                     WHERE project_id=? AND operation_id=? AND attempt_id=?
                     AND runtime_phase IN ('RUNNING_UNVERIFIED',
                                           'STARTING_UNVERIFIED')""",
                     (phase, exit_code, result_hash, _utc(),
                      project_id, operation_id, attempt))
        return {"status": ("HOST_DIAGNOSTIC_COMPLETED" if phase == "COMPLETED"
                           else "HOST_DIAGNOSTIC_FAILED"),
                "phase": phase, "pid": proc.pid if proc else None,
                "exit_code": exit_code, "output_sha256": result_hash,
                "attempt_id": attempt,
                "execute_performed": proc is not None,
                "scientific_result": False,
                "execution_authorized": False, "synthetic_only": True}
