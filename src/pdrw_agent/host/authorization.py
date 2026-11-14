"""Read-only DEV admission preview; denies all real execution.

A caller-supplied JSON, local user setting, model statement or unsigned
approval field is never accepted as authorization. Independent OS identity,
private user grants and enforced filesystem policy are not implemented yet.
"""
from __future__ import annotations

from ..config import Settings
from ..runtime.readiness import inspect_project_readiness
from ..schemas import AgentError
from .contracts import validate_dev_proposal


def preview_dev_admission(settings: Settings, proposal: dict) -> dict:
    plan, fingerprint = validate_dev_proposal(proposal)
    state = inspect_project_readiness(settings, plan["project_id"])
    return {
        "status": ("PROJECT_MACHINE_STATE_BLOCKED"
                   if state["status"] != "MACHINE_METADATA_READY"
                   else "TRUSTED_HOST_NOT_CONNECTED"),
        "project_id": plan["project_id"], "operation_id": plan["operation_id"],
        "task_id": plan["task_id"], "action": plan["action"],
        "runner_id": plan["runner_id"], "plan_sha256": fingerprint,
        "project_machine_readiness": state["status"],
        "authorization_state": "UNVERIFIED",
        "runtime_state": "UNSTARTED",
        "evidence_state": "NOT_REVIEWED",
        "science_state": "NOT_REVIEWED",
        "original_user_grant_verified": False,
        "host_os_identity_verified": False,
        "os_acl_enforced": False,
        "job_supervisor_connected": False,
        "gpu_limits_enforced": False,
        "execution_authorized": False,
        "execute_performed": False,
        "next": "CONFIGURE_SEPARATE_OS_RESTRICTED_HOST_AND_VERIFY_ORIGINAL_GRANTS",
    }


def submit_dev_in_trusted_host(*_args, **_kwargs) -> dict:
    """Fail-closed placeholder. Intentionally not published to MCP or CLI."""
    return {
        "status": "TRUSTED_HOST_NOT_CONNECTED",
        "execute_performed": False, "execution_authorized": False,
        "original_user_grant_verified": False,
    }
