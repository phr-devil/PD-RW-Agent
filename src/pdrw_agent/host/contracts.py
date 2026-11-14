"""Frozen DEV job proposal and bounded typed runtime/evidence dimensions.

This module only validates declarations and records a plan fingerprint.
It does not authorize the operator, launch scripts, or authenticate artifacts.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Literal, TypedDict

from ..schemas import AgentError

IDENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
HEX = re.compile(r"^[0-9a-fA-F]{64}$")
ACTIONS = frozenset({"DEV_CODE", "DEV_TRAIN", "DEV_EVALUATE", "DEV_FIX"})
FIELDS = frozenset({
    "schema_version", "project_id", "operation_id", "task_id", "action",
    "runner_id", "task_spec_sha256", "code_sha256",
    "dataset_manifest_sha256", "time_limit_seconds", "cpu_limit",
    "gpu_count", "network", "data_split",
})
MAX_PLAN_BYTES = 8192


class ExecutionDimensions(TypedDict):
    runtime_state: Literal["UNSTARTED", "RUNNING", "EXITED", "INTERRUPTED", "UNKNOWN"]
    evidence_state: Literal["NOT_REVIEWED", "VERIFIED_SCOPED", "INCOMPLETE", "CONFLICT"]
    science_state: Literal["NOT_REVIEWED", "VALID", "INVALID", "INCONCLUSIVE"]
    authorization_state: Literal["UNVERIFIED", "IN_SCOPE", "OUT_OF_SCOPE"]


def validate_dev_proposal(proposal: dict) -> tuple[dict, str]:
    if not isinstance(proposal, dict) or set(proposal) != FIELDS:
        raise AgentError("DEV_PLAN_SCHEMA_INVALID", "Missing or unexpected fields")
    if proposal["schema_version"] != "pdrw-dev-plan-v1":
        raise AgentError("DEV_PLAN_VERSION_INVALID", "Unsupported DEV plan version")
    for key in ("project_id", "operation_id", "task_id", "runner_id"):
        value = proposal[key]
        if not isinstance(value, str) or not IDENT.fullmatch(value):
            raise AgentError("DEV_PLAN_IDENTIFIER_INVALID", "Invalid bounded identifier")
    if proposal["action"] not in ACTIONS or proposal["data_split"] != "dev":
        raise AgentError("DEV_PLAN_SCOPE_RESTRICTED", "Only bounded DEV proposals supported")
    if any(not isinstance(proposal[k], str) or not HEX.fullmatch(proposal[k])
           for k in ("task_spec_sha256", "code_sha256", "dataset_manifest_sha256")):
        raise AgentError("DEV_PLAN_HASH_INVALID", "Canonical 64-character hashes required")
    if (type(proposal["time_limit_seconds"]) is not int or
            not 1 <= proposal["time_limit_seconds"] <= 24 * 3600 or
            type(proposal["cpu_limit"]) is not int or
            not 1 <= proposal["cpu_limit"] <= 64 or
            type(proposal["gpu_count"]) is not int or
            not 0 <= proposal["gpu_count"] <= 1 or
            proposal["network"] is not False):
        raise AgentError("DEV_PLAN_BUDGET_INVALID",
                         "Only local no-network bounded DEV budgets supported")
    encoded = json.dumps(proposal, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode("utf-8")
    if len(encoded) > MAX_PLAN_BYTES:
        raise AgentError("DEV_PLAN_TOO_LARGE", "DEV plan exceeds fixed bound")
    return proposal, hashlib.sha256(encoded).hexdigest()
