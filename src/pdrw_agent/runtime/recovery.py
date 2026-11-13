"""Synthesize minimal resume hints; never start/restart a process autonomously."""
from __future__ import annotations
from ..config import Settings
from ..projects import get_project_context
from .receipts import execution_status

def get_resume_context(settings: Settings, project_id: str) -> dict:
    project = get_project_context(settings, project_id)
    if project["status"] == "IDENTITY_CONFLICT":
        return {"status": "BLOCKED_PROJECT_IDENTITY", "project_id": project_id,
                "project": project, "next": "VERIFY_ORIGINAL_PROJECT_IDENTITY",
                "authorization_verified": False}
    if project["status"] == "INCOMPLETE_CONTEXT":
        return {"status": "BLOCKED_INCOMPLETE_CONTEXT", "project_id": project_id,
                "project": project, "next": "RESTORE_MISSING_ORIGINAL_SOURCE_FILES",
                "authorization_verified": False}
    operations = execution_status(settings, project_id, limit=6)
    unresolved = [r for r in operations["operations"]
                  if r["phase"] in {"PLANNED", "RUNNING_DECLARED", "ARTIFACT_REPORTED"}]
    changed = any(r.get("artifact_integrity") in {"CHANGED", "MISSING_OR_UNAVAILABLE"}
                  for r in unresolved)
    next_hint = ("RECONCILE_CHANGED_ARTIFACTS" if changed else
                 "VERIFY_REAL_PROCESS_AND_RUN_BEFORE_RESUMING" if unresolved else
                 "REVIEW_LATEST_SCIENTIFIC_EVIDENCE_AND_SCOPE")
    return {
        "status": "NEEDS_RECONCILIATION" if unresolved else "SOURCE_REVIEW_REQUIRED",
        "project_id": project_id,
        "project_status": project["status"],
        "rule_commit_local_only": project["workflow_commit_local_only"],
        "state_index": project["state_index"],
        "snapshot_excerpt": project["snapshot_excerpt"],
        "active_operations": unresolved[:6],
        "receipt_status": operations["status"],
        "authorization_verified": False,
        "process_liveness_verified": False,
        "next": next_hint,
    }
