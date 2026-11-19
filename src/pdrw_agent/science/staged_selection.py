"""Read-only H3/H4 research-question and evidence-path choice cards.

The v1.4 author-selection chain is NOT an authorization service. Original
messages and action permissions must be authenticated by a trusted host.
"""
from __future__ import annotations

import hashlib
import json
import re

from ..schemas import AgentError

PLAN_VERSION = "pdrw-early-plan-v1"
CHOICE_VERSION = "pdrw-early-choice-v1"
STAGES = ("H3", "H4")
_OPTION = {"id", "question_or_evidence_path", "paper_value",
           "nearest_prior", "truth_and_independence", "discriminating_probe",
           "cost_and_risk"}
_PLAN = {"schema_version", "stage", "research_line_ref", "scope_ref",
         "upstream_choices", "options", "recommended_option_id",
         "recommendation_rationale"}
_CHOICE = {"schema_version", "plan_sha256", "kind",
           "original_user_message_ref", "selected_option_id",
           "allowed_option_ids", "delegated_scope"}
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")


def _text(value, key, bound=800):
    if not isinstance(value, str) or not value.strip() or len(value) > bound:
        raise AgentError("EARLY_CHOICE_INVALID", f"{key} requires bounded text")
    return value


def validate_upstream_choices(value, stages):
    """Structural binding only; hashes/user refs are not independently verified."""
    if not isinstance(value, dict) or set(value) != set(stages):
        raise AgentError("EARLY_UPSTREAM_INVALID", "Upstream stages mismatch")
    for step in stages:
        item = value[step]
        if not isinstance(item, dict) or set(item) != {
            "plan_sha256", "original_user_message_ref", "choice"
        }:
            raise AgentError("EARLY_UPSTREAM_INVALID", "Expected exact upstream selection")
        if not isinstance(item["plan_sha256"], str) or not _HASH.fullmatch(item["plan_sha256"]):
            raise AgentError("EARLY_UPSTREAM_INVALID", "Invalid upstream plan digest")
        _text(item["original_user_message_ref"], "original_user_message_ref", 240)
        _text(item["choice"], "choice", 500)
    sources = [value[s]["original_user_message_ref"] for s in stages]
    if len(sources) != len(set(sources)):
        raise AgentError("EARLY_UPSTREAM_INVALID", "Distinct stages require distinct replies")
    return value


def validate_early_plan(plan):
    if not isinstance(plan, dict) or set(plan) != _PLAN:
        raise AgentError("EARLY_PLAN_INVALID", "Unexpected plan fields")
    if plan.get("schema_version") != PLAN_VERSION or plan.get("stage") not in STAGES:
        raise AgentError("EARLY_PLAN_INVALID", "Unsupported early plan version/stage")
    for name in ("research_line_ref", "scope_ref", "recommendation_rationale"):
        _text(plan[name], name)
    upstream = () if plan["stage"] == "H3" else ("H3",)
    validate_upstream_choices(plan["upstream_choices"], upstream)
    options = plan["options"]
    if not isinstance(options, list) or not 1 <= len(options) <= 3:
        raise AgentError("EARLY_PLAN_INVALID", "Require 1..3 substantive options")
    identifiers = []
    for option in options:
        if not isinstance(option, dict) or set(option) != _OPTION:
            raise AgentError("EARLY_PLAN_INVALID", "Option dimensions missing")
        ident = option["id"]
        if not isinstance(ident, str) or not _ID.fullmatch(ident):
            raise AgentError("EARLY_PLAN_INVALID", "Invalid option id")
        identifiers.append(ident)
        for key in _OPTION - {"id"}:
            _text(option[key], key)
    if len(set(identifiers)) != len(identifiers) or plan["recommended_option_id"] not in identifiers:
        raise AgentError("EARLY_PLAN_INVALID", "Duplicated or missing recommended option")
    if len(options) > 1 and len({o["question_or_evidence_path"] for o in options}) < 2:
        raise AgentError("EARLY_PLAN_INVALID", "Options need different scientific paths")
    canonical = json.dumps(plan, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    if len(canonical) > 16000:
        raise AgentError("EARLY_PLAN_INVALID", "Card too large")
    return plan, hashlib.sha256(canonical).hexdigest()


def review_early_choice(plan, choice=None):
    plan, digest = validate_early_plan(plan)
    ids = [option["id"] for option in plan["options"]]
    base = {
        "stage": plan["stage"], "plan_sha256": digest,
        "upstream_choices_declared": plan["upstream_choices"],
        "recommended_option_id": plan["recommended_option_id"],
        "available_option_ids": ids,
        "user_choice_authenticated": False, "execution_authorized": False,
        "scientific_truth_verified": False, "writes_performed": False,
    }
    if choice is None:
        return {**base, "status": "AUTHOR_CHOICE_REQUIRED",
                "next_user_interaction": plan["stage"]}
    if not isinstance(choice, dict) or set(choice) != _CHOICE or choice.get("schema_version") != CHOICE_VERSION:
        raise AgentError("EARLY_CHOICE_INVALID", "Unexpected choice schema")
    if choice.get("plan_sha256") != digest:
        return {**base, "status": "CHOICE_PLAN_MISMATCH",
                "next_user_interaction": plan["stage"]}
    message = _text(choice["original_user_message_ref"], "original_user_message_ref", 240)
    if any(x["original_user_message_ref"] == message for x in plan["upstream_choices"].values()):
        return {**base, "status": "REUSED_UPSTREAM_AUTHOR_MESSAGE",
                "next_user_interaction": plan["stage"]}
    if choice["kind"] == "USER_SELECTED":
        value = choice["selected_option_id"]
        if value not in ids or choice["allowed_option_ids"] != [] or choice["delegated_scope"] is not None:
            raise AgentError("EARLY_CHOICE_INVALID", "Invalid selected choice scope")
    elif choice["kind"] == "USER_DELEGATED":
        allowed = choice["allowed_option_ids"]
        if (choice["selected_option_id"] is not None or not isinstance(allowed, list)
                or not allowed or len(allowed) != len(set(allowed))
                or any(x not in ids for x in allowed)):
            raise AgentError("EARLY_CHOICE_INVALID", "Invalid delegated options")
        value = _text(choice["delegated_scope"], "delegated_scope", 500)
    else:
        raise AgentError("EARLY_CHOICE_INVALID", "Only selected/delegated choices allowed")
    return {**base, "status": "DECLARED_CHOICE_UNAUTHENTICATED",
            "choice": value, "original_user_message_ref_declared": message,
            "next_user_interaction": None,
            "next": "TRUSTED_HOST_MUST_VERIFY_ORIGINAL_MESSAGE_AND_DISPLAYED_PLAN"}
