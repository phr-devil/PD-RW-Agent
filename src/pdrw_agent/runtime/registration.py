"""Read-only Run registration preview and host-only PD-RW ledger adapter.

Model-supplied approval is NEVER permission. Do not expose registration as
WorkBuddy/MCP write tool until an independently secured host exists.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable
from ..config import Settings, read_json, under_root
from ..evidence import _events
from ..projects import get_project_context
from ..schemas import AgentError
from .receipts import _identifier

MAX_RUN_BYTES = 2 * 1024 * 1024
MAX_STATUS_SECONDS = 25


def _invoke_rules(settings: Settings, args: list[str], *, payload: str = "") -> tuple[dict, bool]:
    try:
        proc = subprocess.run(
            [sys.executable, *args], input=payload,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(settings.workflow_root), timeout=MAX_STATUS_SECONDS, check=False)
    except subprocess.TimeoutExpired as exc:
        raise AgentError("PD_RW_CHECK_TIMEOUT", "Authoritative PD-RW check exceeded time budget") from exc
    if proc.returncode:
        return {"error": "PD_RW_VALIDATION_FAILED",
                "detail": proc.stderr.strip()[:180]}, False
    try:
        value = json.loads(proc.stdout)
    except (ValueError, UnicodeError) as exc:
        raise AgentError("PD_RW_INVALID_RESPONSE", "Authoritative PD-RW tool returned malformed JSON") from exc
    if not isinstance(value, dict):
        raise AgentError("PD_RW_INVALID_RESPONSE", "PD-RW output was not an object")
    return value, True


def _run_contract(settings: Settings, obj: dict) -> tuple[dict, bool]:
    # This code is a fixed constant, never built from user inputs.
    code = ("import json,sys\n"
            "from core.contracts import validate_run\n"
            "from core.contracts import ContractError\n"
            "try:\n"
            " obj=validate_run(json.load(sys.stdin))\n"
            " print(json.dumps({'valid':True}))\n"
            "except (ValueError,TypeError,ContractError) as e:\n"
            " print(json.dumps({'valid':False,'reason':str(e)[:180]}))\n")
    return _invoke_rules(settings, ["-c", code], payload=json.dumps(obj, ensure_ascii=True))


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for part in iter(lambda: fp.read(256 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def _safe_history(root: Path, events: list[dict]) -> bool:
    # Reject potentially protected or symlink-routed event artifacts BEFORE
    # running PD-RW status(), which hashes referenced original files.
    for e in events:
        if e.get("split") == "sealed":
            return False
        refs = [e.get("artifact_path")] if e.get("kind") != "note" else []
        if isinstance(e.get("linked_sha256"), dict):
            refs.extend(e["linked_sha256"])
        for ref in refs:
            if not isinstance(ref, str):
                return False
            try:
                under_root(root, ref, must_exist=True)
            except AgentError:
                return False
    return True


def preview_experiment_record(settings: Settings, project_id: str,
                              artifact_ref: str) -> dict:
    context = get_project_context(settings, project_id)
    if context["status"] == "IDENTITY_CONFLICT":
        return {"status": "IDENTITY_CONFLICT", "project_id": project_id,
                "write_authorized": False}
    root, _ = settings.project(project_id)
    path = under_root(root, artifact_ref, must_exist=True)
    obj = read_json(path, limit=MAX_RUN_BYTES)
    if obj.get("split") not in {"dev", "validation"}:
        return {"status": "PROTECTED_OR_UNKNOWN_SPLIT", "write_authorized": False}
    if obj.get("status") == "NOT_RUN":
        return {"status": "NOT_RUN_IS_NOT_A_COMPLETED_EXPERIMENT", "write_authorized": False}
    refs = obj.get("artifact_refs")
    if isinstance(refs, dict):
        for ref in refs.values():
            under_root(root, ref)
    if isinstance(obj.get("task_spec_ref"), str):
        under_root(root, obj["task_spec_ref"])
    run_id = obj.get("run_id")
    task_id = obj.get("task_id")
    contract, ok = _run_contract(settings, obj)
    if not ok or contract.get("valid") is not True:
        return {"status": "INVALID_RUN_CONTRACT", "project_id": project_id,
                "reason": contract.get("reason", contract.get("error", "UNKNOWN")),
                "write_authorized": False}
    if not (root / "STATE.json").is_file() or not (root / "EVENTS.jsonl").is_file():
        return {"status": "MACHINE_LEDGER_NOT_INITIALIZED", "project_id": project_id,
                "write_authorized": False}
    events = _events(root)
    if not _safe_history(root, events):
        return {"status": "PROTECTED_HISTORY_REQUIRES_ISOLATED_HOST",
                "project_id": project_id, "write_authorized": False}
    status, consistent = _invoke_rules(
        settings, ["-m", "core.cli", "status", "--root", str(root)])
    if not consistent or status.get("status") != "CONSISTENT":
        return {"status": "RECONCILIATION_REQUIRED", "project_id": project_id,
                "reason": "STATE_EVENTS_OR_ARTIFACT_INTEGRITY_NOT_VERIFIED",
                "write_authorized": False, "auto_recover": False}
    relative = path.relative_to(root).as_posix()
    digest = _sha(path)
    hits = [e for e in events if e.get("kind") == "run" and e.get("artifact_id") == run_id]
    if hits:
        same = (len(hits) == 1 and hits[0].get("artifact_sha256") == digest
                and hits[0].get("artifact_path") == relative
                and hits[0].get("task_id") == task_id
                and hits[0].get("status") == obj.get("status"))
        return {"status": "ALREADY_RECORDED" if same else "RUN_ID_CONFLICT",
                "project_id": project_id, "run_id": run_id,
                "artifact_sha256": digest, "write_authorized": False,
                "ledger_consistent": True}
    return {"status": "READY_FOR_TRUSTED_HOST_REVIEW", "project_id": project_id,
            "run_id": run_id, "task_id": task_id, "run_status": obj["status"],
            "split": obj["split"], "artifact_ref": relative,
            "artifact_sha256": digest, "ledger_consistent": True,
            "run_contract_checked": True, "scientific_truth_verified": False,
            "write_authorized": False, "next": "TRUSTED_HOST_MUST_VERIFY_ORIGINAL_AUTH"}


def register_run_in_trusted_host(
    settings: Settings, project_id: str, artifact_ref: str, operation_id: str,
    authenticate: Callable[[str, str, str, str], bool] | None,
) -> dict:
    """Integration point for an independently secured operator host ONLY.

    The host must independently check original author permissions and enforce
    OS/tool ACLs. A caller-created lambda in an unrestricted WorkBuddy shell
    is NOT an authorization mechanism. This function is NOT an MCP/CLI tool.
    """
    _identifier(operation_id, "operation_id")
    if authenticate is None or not callable(authenticate):
        return {"status": "TRUSTED_HOST_NOT_CONFIGURED", "write_performed": False}
    if not authenticate(project_id, operation_id, "RECORD_DEV_RUN", artifact_ref):
        return {"status": "AUTHORIZATION_NOT_ATTESTED", "write_performed": False}
    pre = preview_experiment_record(settings, project_id, artifact_ref)
    if pre["status"] == "ALREADY_RECORDED":
        return {"status": "ALREADY_RECORDED", "write_performed": False,
                "run_id": pre.get("run_id")}
    if pre["status"] != "READY_FOR_TRUSTED_HOST_REVIEW":
        return {"status": pre["status"], "write_performed": False,
                "reconciliation_required": pre["status"] == "RECONCILIATION_REQUIRED"}
    root, _ = settings.project(project_id)
    result, succeeded = _invoke_rules(
        settings, ["-m", "core.cli", "record", "--root", str(root),
                   "--kind", "run", "--artifact", pre["artifact_ref"],
                   "--note", "Agent operation " + operation_id])
    post = preview_experiment_record(settings, project_id, artifact_ref)
    if post["status"] == "ALREADY_RECORDED":
        return {"status": "RECORDED" if succeeded else "ALREADY_RECORDED",
                "write_performed": bool(succeeded),
                "run_id": pre["run_id"],
                "event_id": result.get("event_id") if succeeded else None,
                "ledger_consistent": True}
    return {"status": "RECONCILIATION_REQUIRED" if post["status"] == "RECONCILIATION_REQUIRED"
            else "RECORD_INDETERMINATE", "write_performed": bool(succeeded),
            "reconciliation_required": True, "auto_recover": False}
