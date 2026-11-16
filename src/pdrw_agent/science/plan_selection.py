"""Read-only H6 plan/choice contract for a *new* PD-RW research line.

The startup prompt supplies the user scope (H1/H2); AI investigates candidate
questions, data and task designs (H3-H5). Only a specific user choice made
*after seeing this plan card* can satisfy H6. This module checks declarations,
not message authenticity, scientific truth or execution permission.

A real WorkBuddy host must independently obtain the user's message and bind
it to the immutable plan digest before allowing dependent new-mainline effects.
MCP/CLI/Agent-supplied 'approved' fields can never perform that attestation.
"""
from __future__ import annotations

import hashlib
import json
import re

from ..schemas import AgentError

PLAN_VERSION = "pdrw-h6-plan-v2"
LEGACY_PLAN_VERSION = "pdrw-h6-plan-v1"
CHOICE_VERSION = "pdrw-h6-choice-v1"
FIT = frozenset({"SUPPORTED_BY_METADATA", "UNKNOWN_NEEDS_PROBE",
                 "CONTRADICTED_FOR_CLAIM"})
OPTION_FIELDS = frozenset({
    "id", "scientific_question", "core_task", "dataset_or_proof_path",
    "nearest_work_or_unknown", "truth_and_independence",
    "competing_explanation", "decisive_probe", "cost_and_risk",
    "science_fit", "primary_type", "route", "p_orientation",
})
PLAN_FIELDS = frozenset({
    "schema_version", "scope_ref", "options", "recommended_option_id",
    "recommendation_rationale",
})
# Rationale prose can change without invalidating an otherwise identical science scope.
MATERIAL_OPTION_KEYS = (
    "id", "scientific_question", "core_task", "dataset_or_proof_path",
    "nearest_work_or_unknown", "truth_and_independence",
    "competing_explanation", "decisive_probe", "cost_and_risk",
    "science_fit", "primary_type", "route", "p_orientation",
)
TYPES = frozenset(f"C{i:02d}" for i in range(1, 13))
ROUTES = frozenset(f"R{i}" for i in range(1, 7))
ORIENTATIONS = frozenset(f"P{i}" for i in range(1, 6))
CHOICE_FIELDS = frozenset({
    "schema_version", "plan_sha256", "kind", "original_user_message_ref",
    "selected_option_id", "allowed_option_ids", "delegated_scope",
})
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _required(value: object, label: str, size: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > size:
        raise AgentError("H6_PACKET_INVALID", f"{label}: required bounded text")
    return value.strip()


def validate_h6_plan(plan: dict) -> tuple[dict, str]:
    """Validate a compact option card and return its canonical SHA-256."""
    if not isinstance(plan, dict) or set(plan) != PLAN_FIELDS:
        raise AgentError("H6_PLAN_INVALID", "Missing or unexpected H6 plan fields")
    if plan["schema_version"] not in {PLAN_VERSION, LEGACY_PLAN_VERSION}:
        raise AgentError("H6_PLAN_VERSION_INVALID", "Unsupported plan version")
    _required(plan["scope_ref"], "scope_ref", 240)
    _required(plan["recommendation_rationale"], "recommendation_rationale", 1000)
    options = plan["options"]
    if not isinstance(options, list) or not 1 <= len(options) <= 3:
        raise AgentError("H6_PLAN_INVALID", "One to three evidenced options required")
    seen = set()
    for option in options:
        if not isinstance(option, dict) or set(option) != OPTION_FIELDS:
            raise AgentError("H6_OPTION_INVALID", "Option dimensions missing or extra")
        ident = option["id"]
        if not isinstance(ident, str) or not _ID.fullmatch(ident) or ident in seen:
            raise AgentError("H6_OPTION_INVALID", "Option IDs must be unique and bounded")
        seen.add(ident)
        for field in OPTION_FIELDS - {"id", "science_fit"}:
            _required(option[field], field, 1000)
        if not isinstance(option["science_fit"], str) or option["science_fit"] not in FIT:
            raise AgentError("H6_OPTION_INVALID", "Invalid science-fit evidence status")
        for field, vocabulary in (("primary_type", TYPES), ("route", ROUTES),
                                  ("p_orientation", ORIENTATIONS)):
            if not isinstance(option[field], str) or option[field] not in vocabulary:
                raise AgentError("H6_OPTION_INVALID", f"Invalid {field} classification")
    if len(options) > 1 and len({
            (o["scientific_question"].strip(), o["competing_explanation"].strip())
            for o in options}) < 2:
        raise AgentError("H6_OPTIONS_NOT_DISTINCT", "Options must differ in science or failure premise")
    if plan["recommended_option_id"] not in seen:
        raise AgentError("H6_RECOMMENDATION_INVALID", "Recommended option not found")
    encoded = json.dumps(plan, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")).encode("utf-8")
    if len(encoded) > 16000:
        raise AgentError("H6_PLAN_TOO_LARGE", "H6 option card exceeds size bound")
    # Material science scope, not whitespace/explanatory recommendation prose.
    material = {"schema_version": plan["schema_version"], "scope_ref": plan["scope_ref"],
                "recommended_option_id": plan["recommended_option_id"],
                "options": [{k: item[k] for k in MATERIAL_OPTION_KEYS}
                            for item in options]}
    canonical = json.dumps(material, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    # Backward compatibility: existing v1 choices were bound to the entire
    # serialized card. Do not silently invalidate their recorded replies.
    fingerprint = encoded if plan["schema_version"] == LEGACY_PLAN_VERSION else canonical
    return plan, hashlib.sha256(fingerprint).hexdigest()


def review_h6_plan_choice(plan: dict, choice: dict | None = None) -> dict:
    """Read-only advisory review; NEVER returns an authenticated approval."""
    card, fingerprint = validate_h6_plan(plan)
    ids = [x["id"] for x in card["options"]]
    base = {
        "plan_sha256": fingerprint,
        "recommended_option_id": card["recommended_option_id"],
        "available_option_ids": ids,
        "user_choice_authenticated": False,
        "scientific_truth_verified": False,
        "execution_authorized": False,
        "writes_performed": False,
        "next_user_interaction": "H6",
        "science_risk_flags": [
            {"option_id": opt["id"], "status": opt["science_fit"]}
            for opt in card["options"] if opt["science_fit"] != "SUPPORTED_BY_METADATA"
        ],
    }
    if card["options"][[o["id"] for o in card["options"]].index(
            card["recommended_option_id"])]["science_fit"] == "CONTRADICTED_FOR_CLAIM":
        return {**base, "status": "RECOMMENDED_SCIENCE_CONTRADICTED",
                "next": "REVISE_OR_NARROW_SCIENTIFIC_CLAIM_BEFORE_H6"}
    if choice is None:
        return {**base, "status": "AUTHOR_CHOICE_REQUIRED",
                "next": "SHOW_CARD_AND_WAIT_FOR_SPECIFIC_USER_RESPONSE"}
    if not isinstance(choice, dict) or set(choice) != CHOICE_FIELDS:
        raise AgentError("H6_CHOICE_INVALID", "Choice schema is incomplete or unexpected")
    if choice["schema_version"] != CHOICE_VERSION:
        raise AgentError("H6_CHOICE_VERSION_INVALID", "Unsupported choice version")
    digest = choice["plan_sha256"]
    if not isinstance(digest, str) or not _HASH.fullmatch(digest):
        raise AgentError("H6_CHOICE_INVALID", "Invalid referenced card digest")
    if digest != fingerprint:
        return {**base, "status": "CHOICE_PLAN_MISMATCH",
                "next": "ASK_AGAIN_FOR_CHANGED_H6_CARD"}
    _required(choice["original_user_message_ref"], "original_user_message_ref", 240)
    kind = choice["kind"]
    if kind == "USER_SELECTED":
        selected = choice["selected_option_id"]
        if selected not in ids or choice["allowed_option_ids"] != [] or choice["delegated_scope"] is not None:
            return {**base, "status": "CHOICE_SCOPE_INVALID",
                    "next": "RECHECK_SPECIFIC_SELECTION"}
        if next(o for o in card["options"] if o["id"] == selected)["science_fit"] == "CONTRADICTED_FOR_CLAIM":
            return {**base, "status": "SELECTED_SCIENCE_CONTRADICTED",
                    "next": "REVISE_CLAIM_BEFORE_RECORDING_H6"}
        declared = {"kind": kind, "selected_option_id": selected}
    elif kind == "USER_DELEGATED":
        allowed = choice["allowed_option_ids"]
        if (choice["selected_option_id"] is not None or
                not isinstance(allowed, list) or not allowed or
                any(not isinstance(x, str) or x not in ids for x in allowed) or
                len(allowed) != len(set(allowed))):
            return {**base, "status": "CHOICE_SCOPE_INVALID",
                    "next": "RECHECK_BOUNDED_DELEGATION"}
        _required(choice["delegated_scope"], "delegated_scope", 500)
        if any(o["id"] in allowed and o["science_fit"] == "CONTRADICTED_FOR_CLAIM"
               for o in card["options"]):
            return {**base, "status": "DELEGATION_INCLUDES_CONTRADICTED_CLAIM",
                    "next": "NARROW_OR_REFRAME_DELEGATED_OPTIONS"}
        declared = {"kind": kind, "allowed_option_ids": allowed}
    else:
        raise AgentError("H6_CHOICE_INVALID", "Only specific user choice/delegation is allowed")
    return {
        **base, "status": "DECLARED_CHOICE_UNAUTHENTICATED",
        "selection": declared, "choice_observed_declaration_only": True,
        "next_user_interaction": None,
        "original_user_message_ref_declared":
            choice["original_user_message_ref"],
        "next": "TRUSTED_HOST_MUST_VERIFY_ORIGINAL_MESSAGE_AND_PLAN_BINDING",
        "note": ("A model-authored choice packet cannot authenticate the user. "
                 "Do not use this result as a DEV admission or download permit."),
    }
