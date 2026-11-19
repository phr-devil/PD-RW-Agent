"""Read-only adapter: H3/H4/H6 author cards -> advisory case gate.

The adapter never rewrites, approves or rejects a card and never creates a
second research-state ledger. It maps only fields whose meaning is identical
in both contracts; every other dimension is reported as UNKNOWN instead of
being inferred from prose. Early stages (H3/H4/H6) deliberately do not need a
complete experiment profile, because no real Run evidence exists yet.
"""
from __future__ import annotations

import hashlib
import json

from .schemas import AgentError
from . import case_gates

BRIDGE_VERSION = "1.0"
CARD_KINDS = {
    "pdrw-early-plan-v1": "H3_H4_EARLY_PLAN",
    "pdrw-h6-plan-v1": "H6_PLAN",
    "pdrw-h6-plan-v2": "H6_PLAN",
    "pdrw-h6-plan-v3": "H6_STAGED_PLAN",
}
STAGE_TO_GATE = {
    "H3": ("G1", "QUESTION_SELECTION"),
    "H4": ("G2", "PROTOCOL_FREEZE"),
    "H6": ("G2", "PROTOCOL_FREEZE"),
    "H7": ("G2", "PROTOCOL_FREEZE"),
    "H8": ("G3", "CLAIM_OR_CLOSURE"),
    "H9": ("G2", "PROTOCOL_RECHECK"),
    "H10": ("G3", "CLAIM_OR_CLOSURE"),
}
EARLY_STAGES = frozenset({"H3", "H4", "H6"})
DIMENSIONS = ("mechanisms", "legal_inputs", "labels", "grouping",
              "evaluation_unit", "baseline", "boundaries", "counterexamples")

# Only same-meaning mappings. Anything else would be an inference, so it is
# left undeclared and reported as UNKNOWN.
OPTION_FIELDS = {
    "decision": ("scientific_question", "question_or_evidence_path"),
    "counterexamples": ("competing_explanation",),
}


def _digest(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=True, sort_keys=True,
                     separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _clip(value, size: int = 600) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value).strip()[:size]


def _split_card(stage_card: dict) -> tuple[dict, dict | None, str]:
    if not isinstance(stage_card, dict):
        raise AgentError("STAGE_CARD_INVALID", "stage_card must be an object")
    plan = stage_card.get("plan")
    if isinstance(plan, dict):
        choice = stage_card.get("choice")
        stage = _clip(stage_card.get("stage") or plan.get("stage"), 8).upper()
    else:
        plan = {k: v for k, v in stage_card.items()
                if k not in {"choice", "stage", "project_id", "task_id",
                             "query", "filters", "signals", "hypothesis",
                             "case_profile", "known_h_stage",
                             "execution_evidence_refs"}}
        choice = stage_card.get("choice")
        stage = _clip(stage_card.get("stage") or plan.get("stage"), 8).upper()
    if choice is not None and not isinstance(choice, dict):
        raise AgentError("STAGE_CARD_INVALID", "choice must be an object or omitted")
    return plan, choice, stage


def _select_option(plan: dict, choice: dict | None) -> tuple[dict, str, str]:
    options = plan.get("options")
    if not isinstance(options, list) or not options:
        return {}, "", "NO_OPTION_DECLARED"
    by_id = {o.get("id"): o for o in options if isinstance(o, dict)}
    selected = (choice or {}).get("selected_option_id")
    if isinstance(selected, str) and selected in by_id:
        return by_id[selected], selected, "AUTHOR_SELECTED_DECLARED_UNAUTHENTICATED"
    recommended = plan.get("recommended_option_id")
    if isinstance(recommended, str) and recommended in by_id:
        return by_id[recommended], recommended, "RECOMMENDATION_ONLY_NOT_AUTHOR_CHOICE"
    first = options[0]
    return (first if isinstance(first, dict) else {}), _clip(
        (first or {}).get("id") if isinstance(first, dict) else "", 80), \
        "UNSPECIFIED_OPTION_USE_FIRST_CARD_OPTION"


def _profile_from_card(card: dict, option: dict) -> tuple[dict, dict]:
    """Map declared fields only; record where each dimension came from."""
    profile, basis = {}, {}
    declared = card.get("case_profile")
    if isinstance(declared, dict):
        for dim in DIMENSIONS + ("decision",):
            value = _clip(declared.get(dim), 600)
            if value:
                profile[dim] = value
                basis[dim] = "AUTHOR_DECLARED_CASE_PROFILE"
    for dim, fields in OPTION_FIELDS.items():
        if dim in profile:
            continue
        for field in fields:
            value = _clip(option.get(field), 600)
            if value:
                profile[dim] = value
                basis[dim] = f"OPTION.{field}"
                break
    return profile, basis


def project_case_bridge(settings, stage_card: dict, stage: str = "",
                        detail: str = "compact") -> dict:
    """Map an unchanged H3/H4/H6 card to a bounded advisory case check."""
    if detail not in {"compact", "full"}:
        raise AgentError("DETAIL_INVALID", "detail must be 'compact' or 'full'")
    plan, choice, card_stage = _split_card(stage_card)
    stage = (_clip(stage, 8).upper() or card_stage
             or ("H6" if str(plan.get("schema_version", "")).startswith("pdrw-h6")
                 else ""))
    if stage not in STAGE_TO_GATE:
        raise AgentError("BRIDGE_STAGE_UNSUPPORTED",
                         "Declare stage H3, H4, H6, H7, H8, H9 or H10")
    gate, milestone = STAGE_TO_GATE[stage]
    kind = CARD_KINDS.get(str(plan.get("schema_version", "")), "UNRECOGNIZED_CARD")
    option, option_id, selection_basis = _select_option(plan, choice)
    profile, basis = _profile_from_card(stage_card, option)
    missing = [d for d in DIMENSIONS if d not in profile]
    known_stage = _clip(stage_card.get("known_h_stage"), 8).upper()

    event = {
        "project_id": _clip(stage_card.get("project_id"), 80),
        "task_id": _clip(stage_card.get("task_id"), 80) or f"{stage}-card",
        "h_stage": stage,
        "milestone": milestone,
        "decision": profile.get("decision", ""),
        "hypothesis": _clip(stage_card.get("hypothesis")
                            or choice_reason(choice) or plan.get("recommendation_rationale"), 600),
        "protocol": {"card_kind": kind, "plan_sha256": _digest(plan),
                     "selected_option_id": option_id},
        "task_profile": profile or None,
        # Retrieval must follow the declared question, not a generic gate
        # default, otherwise a relevant case looks like "no match".
        "query": _clip(stage_card.get("query"), 300)
                 or _clip(profile.get("decision"), 120),
        "filters": stage_card.get("filters") or {},
        "signals": stage_card.get("signals") or [],
    }
    if known_stage:
        event["known_h_stage"] = known_stage
    refs = stage_card.get("execution_evidence_refs")
    if isinstance(refs, list) and refs:
        event["execution_evidence_refs"] = [str(r)[:240] for r in refs[:8]]
    result = case_gates.case_gate_check(settings, event, detail)

    return {
        "status": "CARD_MAPPED_TO_ADVISORY_GATE",
        "bridge_version": BRIDGE_VERSION,
        "stage": stage,
        "gate": gate,
        "milestone": milestone,
        "card_kind": kind,
        "card_sha256": _digest(plan),
        "plan_sha256_declared": _clip(plan.get("plan_sha256"), 80) or None,
        "selected_option_id": option_id,
        "selection_basis": selection_basis,
        "upstream_choices_declared": plan.get("upstream_choices"),
        "hard_constraints_sha256_declared": _clip(plan.get("hard_constraints_sha256"), 80) or None,
        "choice_ref_declared": (_clip((choice or {}).get("original_user_message_ref"), 240)
                                or None),
        "task_profile": profile,
        "profile_basis": basis,
        "unknown_dimensions": missing,
        "unknown_note": ("UNKNOWN 表示卡片没有声明该维度，不是“与本任务不符”。"
                         "缺失维度不写入检索 profile，避免把 UNKNOWN 当成 NO_TEXT_OVERLAP，"
                         "从而误判 CONDITIONS_DIFFER。"),
        "early_stage_no_experiment_profile_required": stage in EARLY_STAGES,
        "gate_result": result,
        "authorization": {
            "card_rewritten": False, "choice_altered": False,
            "plan_approved": False, "execution_authorized": False,
            "authorization_verified": False,
        },
        "no_writes": True,
        "automatic_go_stop": False,
    }


def choice_reason(choice: dict | None) -> str:
    """Echo the declared choice text without treating it as authorization."""
    if not isinstance(choice, dict):
        return ""
    return _clip(choice.get("delegated_scope") or choice.get("selected_option_id"), 200)
