"""v0.7 host-execution planning: strict profiles and source-bound preflight.

No plans, policy strings, receipts or model claims authorize research execution.
For v0.7 the *only* execution profile is a fixed synthetic CPU self-test.
"""
from __future__ import annotations

import hashlib
import json

from ..config import Settings
from ..projects import get_project_context
from ..runtime.history import reconstruct_project_history
from ..schemas import AgentError
from .receipts import _identifier

PROFILE = "CPU_SELFTEST_V1"
REQUIRED = frozenset({
    "schema_version", "project_id", "operation_id", "task_id",
    "profile", "scenario", "iterations", "timeout_seconds",
    "network", "gpu",
})
SCENARIOS = frozenset({"SUCCESS", "EXIT_NONZERO", "SLEEP"})


def validate_execution_plan(plan: dict) -> tuple[dict, str]:
    if not isinstance(plan, dict) or set(plan) != REQUIRED:
        raise AgentError("PLAN_SCHEMA_INVALID", "Unexpected or missing execution plan fields")
    if plan["schema_version"] != "pdrw-exec-plan-v1" or plan["profile"] != PROFILE:
        raise AgentError("UNSUPPORTED_EXECUTION_PROFILE", "Only fixed CPU self-test supported")
    for key in ("project_id", "operation_id", "task_id"):
        _identifier(plan[key], key)
    if plan["scenario"] not in SCENARIOS:
        raise AgentError("SCENARIO_INVALID", "Unknown synthetic scenario")
    if (type(plan["iterations"]) is not int or
            not 1 <= plan["iterations"] <= 100_000):
        raise AgentError("ITERATIONS_INVALID", "Synthetic iteration budget exceeded")
    if (type(plan["timeout_seconds"]) is not int or
            not 1 <= plan["timeout_seconds"] <= 5):
        raise AgentError("TIMEOUT_INVALID", "Synthetic runtime budget exceeded")
    if plan["network"] is not False or plan["gpu"] is not False:
        raise AgentError("SYNTHETIC_SCOPE_ONLY", "Network and GPU execution not supported")
    encoded = json.dumps(plan, ensure_ascii=True, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    if len(encoded) > 4096:
        raise AgentError("PLAN_TOO_LARGE", "Plan exceeds fixed size")
    return plan, hashlib.sha256(encoded).hexdigest()


def preflight_execution_plan(settings: Settings, plan: dict) -> dict:
    spec, fingerprint = validate_execution_plan(plan)
    project_id = spec["project_id"]
    context = get_project_context(settings, project_id)
    history = reconstruct_project_history(settings, project_id)
    base = {
        "project_id": project_id, "operation_id": spec["operation_id"],
        "task_id": spec["task_id"], "plan_sha256": fingerprint,
        "profile": PROFILE, "execution_authorized": False,
        "original_authorization_verified": False, "scientific_run": False,
        "gpu_enabled": False, "network_enabled": False,
        "synthetic_only": True,
    }
    if context["status"] != "SOURCE_REVIEW_REQUIRED":
        return {**base, "status": "BLOCKED_PROJECT_CONTEXT",
                "context_status": context["status"]}
    if history["status"] != "METADATA_CHAIN_MATCHED_ONLY":
        return {**base, "status": "BLOCKED_PROJECT_HISTORY",
                "history_status": history["status"]}
    active = context["state_index"].get("active_task_id")
    if active and active != spec["task_id"]:
        return {**base, "status": "BLOCKED_TASK_MISMATCH",
                "active_task_id": active}
    return {
        **base, "status": "HOST_ONLY_SYNTHETIC_PREFLIGHT_READY",
        "task_binding": ("MATCHED_ACTIVE_TASK" if active else
                         "SYNTHETIC_SELFTEST_WITH_NO_ACTIVE_TASK"),
        "requires_external_trusted_host_for_research": True,
        "note": ("Diagnostic planning only. Actual scientific DEV runs require "
                 "separately authenticated host policy; this plan grants none."),
    }
