"""Private operational SQLite receipts, NOT authorization or scientific truth."""
from __future__ import annotations
import hashlib
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from ..config import Settings, under_root
from ..schemas import AgentError
from ..projects import get_project_context


def _assert_context(settings: Settings, project_id: str, task_id: str | None = None) -> None:
    """Guard new receipt writes against known project/Task mismatch.

    This is an identity guard, never a grant of author permission.
    """
    context = get_project_context(settings, project_id)
    if context["status"] != "SOURCE_REVIEW_REQUIRED":
        raise AgentError("PROJECT_CONTEXT_NOT_READY",
                         "Project identity/snapshot incomplete or conflicting; verify original evidence")
    active = context["state_index"].get("active_task_id")
    if task_id and active and active != task_id:
        raise AgentError("TASK_CONTEXT_CONFLICT",
                         "Operation Task differs from currently indexed project Task")

ACTIONS = {"DEV_CODE", "DEV_TRAIN", "DEV_EVALUATE", "DEV_FIX"}
TRANSITIONS = {
    "PLANNED": {"RUNNING_DECLARED", "ARTIFACT_REPORTED", "TECHNICAL_FAILED"},
    "RUNNING_DECLARED": {"ARTIFACT_REPORTED", "TECHNICAL_FAILED"},
    "ARTIFACT_REPORTED": set(), "TECHNICAL_FAILED": set(),
}
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
MAX_RECEIPT_ARTIFACT = 2 * 1024 * 1024


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise AgentError("INVALID_OPERATION_FIELD",
                         f"{label} must be an ASCII identifier (1-80 characters)")
    return value


def _db_path(settings: Settings, project_id: str, *, create: bool) -> Path | None:
    folder = os.environ.get("PDRW_RUNTIME_DIR", "")
    if not folder:
        if create:
            raise AgentError("RUNTIME_DIR_NOT_CONFIGURED",
                             "Set PDRW_RUNTIME_DIR outside research and Git repositories")
        return None
    raw = Path(folder).expanduser()
    if not raw.is_absolute():
        raise AgentError("RUNTIME_DIR_NOT_ABSOLUTE",
                         "PDRW_RUNTIME_DIR must be an absolute private directory")
    dest = raw.resolve()
    project, _ = settings.project(project_id)
    prohibited = (project, settings.workflow_root, settings.project_map.parent)
    for base in prohibited:
        base = base.resolve()
        if dest == base or base in dest.parents or dest in base.parents:
            raise AgentError("RUNTIME_DIR_OVERLAP",
                             "Choose an independent private runtime directory")
    if create:
        dest.mkdir(parents=True, exist_ok=True)
    # A configured but not-yet-created runtime directory is NO_RECEIPTS,
    # not RECEIPTS_NOT_CONFIGURED. Read operations never create directories.
    return dest / "runtime.sqlite"


@contextmanager
def _open(path: Path):
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("""
            CREATE TABLE IF NOT EXISTS operations (
              project_id TEXT NOT NULL, operation_id TEXT NOT NULL,
              task_id TEXT NOT NULL, action TEXT NOT NULL,
              phase TEXT NOT NULL, revision INTEGER NOT NULL,
              artifact_ref TEXT NOT NULL DEFAULT '',
              artifact_sha256 TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
              PRIMARY KEY (project_id, operation_id)
            )
        """)
        with connection:
            yield connection
    finally:
        connection.close()


def _public(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in ("project_id", "operation_id", "task_id",
            "action", "phase", "revision", "artifact_ref",
            "artifact_sha256", "created_at", "updated_at")}


def begin_operation(settings: Settings, project_id: str, operation_id: str,
                    task_id: str, action: str) -> dict:
    _identifier(operation_id, "operation_id")
    _identifier(task_id, "task_id")
    if action not in ACTIONS:
        raise AgentError("INVALID_ACTION", "Only ordinary DEV actions may create operational receipts")
    _assert_context(settings, project_id)
    path = _db_path(settings, project_id, create=True)
    with _open(path) as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            "SELECT * FROM operations WHERE project_id=? AND operation_id=?",
            (project_id, operation_id)).fetchone()
        if existing:
            if existing["task_id"] != task_id or existing["action"] != action:
                return {"status": "OPERATION_ID_CONFLICT",
                        "receipt": _public(existing), "execution_authorized": False}
            return {"status": "ALREADY_RECEIPTED", "receipt": _public(existing),
                    "execution_authorized": False}
        _assert_context(settings, project_id, task_id)
        now = _utc()
        db.execute("""INSERT INTO operations(project_id,operation_id,task_id,action,
                   phase,revision,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)""",
                   (project_id, operation_id, task_id, action, "PLANNED", 0, now, now))
        row = db.execute("SELECT * FROM operations WHERE project_id=? AND operation_id=?",
                         (project_id, operation_id)).fetchone()
    return {"status": "RECEIPT_CREATED", "receipt": _public(row),
            "execution_authorized": False}


def _artifact_digest(settings: Settings, project_id: str, rel: str) -> str:
    root, _ = settings.project(project_id)
    path = under_root(root, rel, must_exist=True)
    if path.stat().st_size > MAX_RECEIPT_ARTIFACT:
        raise AgentError("ARTIFACT_TOO_LARGE",
                         "Use a small metadata/Run JSON receipt, not model weights")
    sha = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(131072), b""):
            sha.update(chunk)
    return sha.hexdigest()


def checkpoint_operation(settings: Settings, project_id: str, operation_id: str,
                         expected_revision: int, phase: str,
                         artifact_ref: str = "") -> dict:
    _identifier(operation_id, "operation_id")
    if type(expected_revision) is not int or expected_revision < 0:
        raise AgentError("REVISION_INVALID", "expected_revision must be a nonnegative integer")
    if phase not in {"RUNNING_DECLARED", "ARTIFACT_REPORTED", "TECHNICAL_FAILED"}:
        raise AgentError("PHASE_INVALID", "Unsupported receipt transition")
    if artifact_ref and phase != "ARTIFACT_REPORTED":
        raise AgentError("ARTIFACT_REF_NOT_ALLOWED", "Only ARTIFACT_REPORTED may reference an artifact")
    if phase == "ARTIFACT_REPORTED" and not artifact_ref:
        raise AgentError("ARTIFACT_REQUIRED", "Report an existing non-protected local artifact")
    _assert_context(settings, project_id)
    digest = (_artifact_digest(settings, project_id, artifact_ref)
              if artifact_ref else "")
    path = _db_path(settings, project_id, create=False)
    if path is None or not path.is_file():
        raise AgentError("RECEIPT_NOT_FOUND", "No operational receipt database exists")
    with _open(path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT * FROM operations WHERE project_id=? AND operation_id=?",
                         (project_id, operation_id)).fetchone()
        if row is None:
            raise AgentError("RECEIPT_NOT_FOUND", "Operation ID not found")
        _assert_context(settings, project_id, row["task_id"])
        if (row["revision"] == expected_revision + 1 and
                row["phase"] == phase and row["artifact_ref"] == artifact_ref and
                row["artifact_sha256"] == digest):
            return {"status": "ALREADY_CHECKPOINTED", "receipt": _public(row),
                    "scientific_evidence_verified": False}
        if row["revision"] != expected_revision:
            return {"status": "REVISION_CONFLICT", "receipt": _public(row),
                    "scientific_evidence_verified": False}
        if phase not in TRANSITIONS[row["phase"]]:
            return {"status": "INVALID_TRANSITION", "receipt": _public(row),
                    "scientific_evidence_verified": False}
        now = _utc()
        db.execute("""UPDATE operations SET phase=?,revision=?,artifact_ref=?,
                      artifact_sha256=?,updated_at=?
                      WHERE project_id=? AND operation_id=? AND revision=?""",
                   (phase, expected_revision + 1, artifact_ref, digest, now,
                    project_id, operation_id, expected_revision))
        row = db.execute("SELECT * FROM operations WHERE project_id=? AND operation_id=?",
                         (project_id, operation_id)).fetchone()
    return {"status": "CHECKPOINT_SAVED", "receipt": _public(row),
            "scientific_evidence_verified": False}


def execution_status(settings: Settings, project_id: str,
                     operation_id: str = "", limit: int = 6) -> dict:
    if operation_id:
        _identifier(operation_id, "operation_id")
    path = _db_path(settings, project_id, create=False)
    if path is None:
        return {"status": "RECEIPTS_NOT_CONFIGURED", "operations": [],
                "process_liveness_verified": False}
    if not path.is_file():
        return {"status": "NO_RECEIPTS", "operations": [],
                "process_liveness_verified": False}
    count = max(1, min(10, limit))
    with _open(path) as db:
        if operation_id:
            rows = db.execute("SELECT * FROM operations WHERE project_id=? AND operation_id=?",
                              (project_id, operation_id)).fetchall()
        else:
            rows = db.execute("""SELECT * FROM operations WHERE project_id=?
                                 ORDER BY
                                   CASE
                                     WHEN phase IN ('PLANNED','RUNNING_DECLARED') THEN 0
                                     WHEN phase='ARTIFACT_REPORTED' THEN 1
                                     ELSE 2
                                   END,
                                   updated_at DESC, operation_id DESC LIMIT ?""",
                              (project_id, count)).fetchall()
    operations = []
    for row in rows:
        item = _public(row)
        if row["artifact_ref"]:
            try:
                current = _artifact_digest(settings, project_id, row["artifact_ref"])
                item["artifact_integrity"] = ("MATCH" if current == row["artifact_sha256"]
                                               else "CHANGED")
            except (OSError, AgentError):
                item["artifact_integrity"] = "MISSING_OR_UNAVAILABLE"
        else:
            item["artifact_integrity"] = "NOT_REPORTED"
        item["process_liveness_verified"] = False
        item["science_registration_verified"] = False
        # A matching checksum proves byte stability only. It can advance the
        # OPERATIONAL follow-up, but NEVER certifies experiment completion.
        if item["phase"] == "ARTIFACT_REPORTED":
            item["recovery_class"] = ("PENDING_SCIENTIFIC_REVIEW"
                                      if item["artifact_integrity"] == "MATCH"
                                      else "NEEDS_ARTIFACT_RECONCILIATION")
        elif item["phase"] in {"PLANNED", "RUNNING_DECLARED"}:
            item["recovery_class"] = "VERIFY_ACTUAL_EXECUTION"
        else:
            item["recovery_class"] = "REVIEW_TECHNICAL_FAILURE"
        operations.append(item)
    return {"status": "RECEIPTS_FOUND" if operations else "NO_RECEIPTS",
            "operations": operations, "process_liveness_verified": False,
            "source": "PRIVATE_OPERATIONAL_RECEIPTS_NOT_SCIENTIFIC_LEDGER"}
