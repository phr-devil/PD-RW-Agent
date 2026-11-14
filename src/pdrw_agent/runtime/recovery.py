"""Synthesize minimal resume hints; never start/restart a process autonomously."""
from __future__ import annotations
from ..config import Settings
from ..projects import get_project_context
from .receipts import execution_status
from .history import reconstruct_project_history
from .synthetic_executor import recent_synthetic_jobs
from .readiness import inspect_project_readiness
from ..host.supervisor import recent_host_diagnostics

def get_resume_context(settings: Settings, project_id: str) -> dict:
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
