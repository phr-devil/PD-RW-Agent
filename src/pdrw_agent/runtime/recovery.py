"""Synthesize minimal resume hints; never start/restart a process autonomously."""
from __future__ import annotations
from ..config import Settings
from ..projects import get_project_context
from .receipts import execution_status
from .history import reconstruct_project_history
from .synthetic_executor import recent_synthetic_jobs
from .readiness import inspect_project_readiness
from ..host.supervisor import recent_host_diagnostics

def _raw_get_resume_context(settings: Settings, project_id: str) -> dict:
    project = get_project_context(settings, project_id)
    if project["status"] == "IDENTITY_CONFLICT":
        return {"status": "BLOCKED_PROJECT_IDENTITY", "project_id": project_id,
                "project": project, "next": "VERIFY_ORIGINAL_PROJECT_IDENTITY",
                "authorization_verified": False,
                "restart_permitted": False,
                "read_only_next_actions": ["VERIFY_ORIGINAL_PROJECT_IDENTITY"]}
    if project["status"] == "INCOMPLETE_CONTEXT":
        return {"status": "BLOCKED_INCOMPLETE_CONTEXT", "project_id": project_id,
                "project": project, "next": "RESTORE_MISSING_ORIGINAL_SOURCE_FILES",
                "authorization_verified": False,
                "restart_permitted": False,
                "read_only_next_actions": ["AUDIT_PROJECT_STATE", "RESTORE_ORIGINAL_SOURCES"]}
    history = reconstruct_project_history(settings, project_id)
    if history["status"] not in {"METADATA_CHAIN_MATCHED_ONLY",
                                  "HISTORY_SOURCES_MISSING"}:
        return {"status": "BLOCKED_HISTORY_INCONSISTENT",
                "project_id": project_id, "project": project,
                "history_status": history["status"],
                "authorization_verified": False,
                "restart_permitted": False,
                "read_only_next_actions": ["AUDIT_PROJECT_STATE",
                                           "REVIEW_RAW_EVENTS_NO_AUTO_REPAIR"]}
    readiness = inspect_project_readiness(settings, project_id)
    if readiness["status"] in {"STATE_IDENTITY_CONFLICT",
                               "MACHINE_LEDGER_CONFLICT", "MACHINE_STATE_INVALID"}:
        return {"status": "BLOCKED_MACHINE_READINESS",
                "project_id": project_id, "machine_readiness": readiness,
                "authorization_verified": False,
                "restart_permitted": False,
                "read_only_next_actions": ["REVIEW_ORIGINAL_STATE_AND_EVENTS"]}
    operations = execution_status(settings, project_id, limit=6)
    synthetic_runtime = recent_synthetic_jobs(settings, project_id, limit=6)
    host_runtime = recent_host_diagnostics(settings, project_id, limit=6)
    unresolved = [r for r in operations["operations"] if
                  r["recovery_class"] in {"VERIFY_ACTUAL_EXECUTION",
                                           "NEEDS_ARTIFACT_RECONCILIATION"}]
    pending_review = [r for r in operations["operations"]
                      if r["recovery_class"] == "PENDING_SCIENTIFIC_REVIEW"]
    changed = any(r.get("artifact_integrity") in {"CHANGED", "MISSING_OR_UNAVAILABLE"}
                  for r in unresolved)
    next_hint = ("RECONCILE_CHANGED_ARTIFACTS" if changed else
                 "VERIFY_REAL_PROCESS_AND_RUN_BEFORE_RESUMING" if unresolved else
                 "REVIEW_ORIGINAL_RUN_AND_SCOPE_NO_AUTO_RERUN" if pending_review else
                 "REVIEW_LATEST_SCIENTIFIC_EVIDENCE_AND_SCOPE")
    scientific_status = ("NEEDS_RECONCILIATION" if unresolved else
                         "ARTIFACT_REVIEW_PENDING" if pending_review else
                         "SOURCE_REVIEW_REQUIRED")
    host_review = bool(host_runtime.get("reconciliation_required"))
    synthetic_review = bool(synthetic_runtime.get("reconciliation_required"))
    # Preserve scientific status separately: fixed engineering diagnostics
    # must never be promoted to a scientific finding. Still surface a host
    # crash or corrupted output in the main resume decision.
    status = ("NEEDS_OPERATIONAL_RECONCILIATION"
              if host_review and scientific_status == "SOURCE_REVIEW_REQUIRED"
              else scientific_status)
    if host_review and not unresolved:
        next_hint = "RECONCILE_FIXED_HOST_ATTEMPT_NO_AUTO_RESTART"
    return {
        "status": status,
        "scientific_resume_status": scientific_status,
        "operational_reconciliation_required": bool(host_review or synthetic_review),
        "host_reconciliation_required": host_review,
        "synthetic_reconciliation_required": synthetic_review,
        "project_id": project_id,
        "project_status": project["status"],
        "rule_commit_local_only": project["workflow_commit_local_only"],
        "state_index": project["state_index"],
        "snapshot_excerpt": project["snapshot_excerpt"],
        "active_operations": unresolved[:6],
        "pending_scientific_review": pending_review[:6],
        "scientific_completion_verified": False,
        "receipt_status": operations["status"],
        "machine_readiness": readiness,
        "synthetic_selftest_checkpoints": synthetic_runtime,
        "host_fixed_cpu_checkpoints": host_runtime,
        "authorization_verified": False,
        "process_liveness_verified": False,
        "restart_permitted": False,
        "read_only_next_actions": ["VERIFY_ACTUAL_PROCESS_AND_ARTIFACTS",
                                   "REVIEW_ORIGINAL_RUN_AND_AUTHORIZATION"],
        "next": next_hint,
    }


def get_resume_context(settings: Settings, project_id: str,
                       detail_level: str = "full") -> dict:
    """Resume hint, not execution authority. Keep legacy full result by default.

    Compact mode is for token-bounded agent entry; it preserves blockers,
    current declared scientific pointers and uncertainty while suppressing
    verbose synthetic/host diagnostic objects. Both modes examine the same
    sources and never restart operations.
    """
    if detail_level not in {"compact", "full"}:
        raise ValueError("RESUME_DETAIL_INVALID: use compact or full")
    result = _raw_get_resume_context(settings, project_id)
    declared = result.get("state_index") or result.get("project", {}).get("state_index") or {}
    scientific = {
        "active_task_id_declared": declared.get("active_task_id") or declared.get("ACTIVE_TASK"),
        "latest_valid_run_id_declared": declared.get("latest_valid_run_id") or declared.get("BEST_VALID_RUN"),
        "source_status": result.get("project_status") or result.get("project", {}).get("status"),
        "scientific_resume_status": result.get("scientific_resume_status", result["status"]),
        "original_run_validated_here": False,
    }
    active = result.get("active_operations", [])
    operation = {
        "unresolved": [{"operation_id": r.get("operation_id"),
                         "recovery_class": r.get("recovery_class")}
                        for r in active[:6]],
        "pending_scientific_review_count": len(result.get("pending_scientific_review", [])),
        "operational_reconciliation_required": result.get("operational_reconciliation_required", False),
        "host_reconciliation_required": result.get("host_reconciliation_required", False),
        "old_job_restart_authorized": False,
    }
    status = result["status"]
    if status.startswith("BLOCKED_"):
        action = "RECONCILE_AFFECTED_ORIGINAL_SOURCES"
    elif active or operation["operational_reconciliation_required"]:
        action = "RECONCILE_UNCERTAIN_PRIOR_OPERATION"
    else:
        action = "REVIEW_ORIGINAL_SCOPE_THEN_CONTINUE_PERMITTED_DEV"
    next_action = {
        "action": action,
        "source_hint": result.get("next"),
        "original_authorization_verified": False,
        "execution_authorized": False,
        "unknown_old_job_restart_permitted": False,
        "independent_permitted_read_only_review_allowed": True,
        "note": "This is a planning hint only; verify original PD-RW user scope. "
                "An uncertain prior job does not globally block independent permitted work.",
    }
    if detail_level == "full":
        return {**result, "scientific_context": scientific,
                "operation_context": operation, "next_action_hint": next_action}
    return {
        "status": status,
        "scientific_resume_status": scientific["scientific_resume_status"],
        "project_id": project_id,
        "rule_commit_local_only": result.get("rule_commit_local_only"),
        "state_index": declared,
        "snapshot_excerpt": (result.get("snapshot_excerpt")
                             or result.get("project", {}).get("snapshot_excerpt") or "")[:900],
        "scientific_context": scientific,
        "operation_context": operation,
        "next_action_hint": next_action,
        "authorization_verified": False,
        "restart_permitted": False,
        "missing": result.get("project", {}).get("missing", []),
    }
