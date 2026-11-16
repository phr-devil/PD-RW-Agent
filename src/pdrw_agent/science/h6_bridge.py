"""Translate an advisory H6 card to PD-RW's existing science checkpoint schema.

This adapter never writes a research ledger and never upgrades a declared user
reply to an authenticated grant. Feed the output to PD-RW's authoritative
core.execution_preflight.science_checkpoint at the activity-03 handoff.
"""
from __future__ import annotations

from .plan_selection import validate_h6_plan, review_h6_plan_choice


def to_pd_rw_h6_checkpoint(plan: dict, choice: dict | None = None) -> dict:
    card, fingerprint = validate_h6_plan(plan)
    assessment = review_h6_plan_choice(plan, choice)
    # Never insert an invalid or contradicted selection into the checkpoint.
    usable = assessment["status"] == "DECLARED_CHOICE_UNAUTHENTICATED"
    selection = assessment.get("selection") if usable else None
    picked = (selection.get("selected_option_id") if selection and
              selection["kind"] == "USER_SELECTED" else None)
    allowed = (selection.get("allowed_option_ids") if selection and
               selection["kind"] == "USER_DELEGATED" else None)
    selected_id = (picked or
                   (card["recommended_option_id"] if not allowed or
                    card["recommended_option_id"] in allowed else allowed[0]))
    target = next(o for o in card["options"] if o["id"] == selected_id)
    items = [{
        "id": o["id"],
        "claim_or_task": o["core_task"],
        "primary_type": o["primary_type"],
        "route": o["route"],
        "p_orientation": o["p_orientation"],
        "independent_knowledge": "HYPOTHESIS: " + o["scientific_question"],
        "prior_gap": o["nearest_work_or_unknown"],
        "decisive_evidence": o["decisive_probe"],
        "science_value": o["scientific_question"],
        "cost_and_speed": o["cost_and_risk"],
        "failure_premise": o["competing_explanation"],
    } for o in card["options"]]
    review = {
        "options": items,
        "recommended_option_id": card["recommended_option_id"],
        "recommendation_rationale": card["recommendation_rationale"],
        "key_unknown": target["truth_and_independence"],
        "single_option_reason": card["recommendation_rationale"],
    }
    if usable:
        source = choice["original_user_message_ref"]
        if selection["kind"] == "USER_SELECTED":
            review["selection"] = {
                "kind": "USER_CONFIRMED",
                "original_user_message_ref": source,
                "chosen_option_id": selected_id,
                "secondary_option_ids": [],
            }
        else:
            review["selection"] = {
                "kind": "USER_DELEGATED",
                "original_user_message_ref": source,
                "allowed_option_ids": allowed,
                "delegated_scope": choice["delegated_scope"],
            }
    return {
        "trigger": "H6_TASK", "primary_type": target["primary_type"],
        "route": target["route"], "claim_or_question": target["scientific_question"],
        "nearest_neighbor_or_unknown": target["nearest_work_or_unknown"],
        "author_review": review,
        # Advisory metadata: PD-RW checker ignores unknown fields.
        "h6_card_sha256_declared": fingerprint,
        "h6_user_message_authenticated": False,
        "h6_packet_status": assessment["status"],
    }
