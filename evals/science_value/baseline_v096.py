"""SCIENCE-01 baseline: what v0.9.6 actually says about the frozen cards.

Read-only. No model is invoked; this records the deterministic output of the
existing card checks so the later comparison is reproducible.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from pdrw_agent.science.staged_selection import review_early_choice  # noqa: E402
from pdrw_agent.science.plan_selection import review_h6_plan_choice  # noqa: E402

CARDS = json.loads((Path(__file__).with_name("cards.json")).read_text(encoding="utf-8"))["cards"]
H3_PLAN = {
    "schema_version": "pdrw-early-plan-v1",
    "stage": "H3",
    "research_line_ref": "SCIENCE-01-BASELINE",
    "scope_ref": "user H1/H2 scope reconstructed from the historical project",
    "hard_constraints_sha256": "0" * 64,
    "upstream_choices": {},
    "options": [],
    "recommended_option_id": "",
    "recommendation_rationale": "Historical direction reproduced for a frozen comparison.",
}
H6_PLAN = {
    "schema_version": "pdrw-h6-plan-v2",
    "scope_ref": "user H1/H2 scope reconstructed from the historical project",
    "research_line_ref": "SCIENCE-01-BASELINE",
    "options": [],
    "recommended_option_id": "",
    "recommendation_rationale": "Historical direction reproduced for a frozen comparison.",
}


def h3_option(card: dict) -> dict:
    nearest = card["named_nearest"][0] if card["named_nearest"] else {"work": "", "covers": "", "remaining": ""}
    competing = card["competing_explanations"]
    return {
        "id": card["candidate_id"],
        "question_or_evidence_path": card["question"],
        "paper_value": f'{card["success_new_knowledge"]} / {card["refutation_consequence"]}',
        "nearest_prior": f'{nearest["work"]}: {nearest["covers"]}; remaining: {nearest["remaining"]}',
        "truth_and_independence": f'{card["truth_source"]}; unit={card["evaluation_unit"]} n={card["independent_units"]}',
        "discriminating_probe": " | ".join(x["predicted_observation"] for x in competing),
        "cost_and_risk": card["resources"],
    }


def h6_option(card: dict, science_fit: str = "UNKNOWN_NEEDS_PROBE") -> dict:
    nearest = card["named_nearest"][0] if card["named_nearest"] else {"work": "", "covers": "", "remaining": ""}
    return {
        "id": card["candidate_id"],
        "scientific_question": card["question"],
        "core_task": card["question"],
        "dataset_or_proof_path": card["evidence_path"],
        "nearest_work_or_unknown": f'{nearest["work"]} / {nearest["remaining"]}',
        "truth_and_independence": f'{card["truth_source"]} / {card["evaluation_unit"]}',
        "competing_explanation": " | ".join(x["explanation"] for x in card["competing_explanations"]),
        "decisive_probe": " | ".join(x["predicted_observation"] for x in card["competing_explanations"]),
        "cost_and_risk": card["resources"],
        "science_fit": science_fit,
        "primary_type": "C01",
        "route": "R1",
        "p_orientation": "P2",
    }


def main() -> int:
    rows = []
    for card in CARDS:
        h3 = dict(H3_PLAN)
        h3["options"] = [h3_option(card)]
        h3["recommended_option_id"] = card["candidate_id"]
        early = review_early_choice(h3)
        h6 = dict(H6_PLAN)
        h6["options"] = [h6_option(card)]
        h6["recommended_option_id"] = card["candidate_id"]
        late = review_h6_plan_choice(h6)
        # A confident card is the common case: the agent believes metadata fits.
        h6b = dict(H6_PLAN)
        h6b["options"] = [h6_option(card, "SUPPORTED_BY_METADATA")]
        h6b["recommended_option_id"] = card["candidate_id"]
        late_supported = review_h6_plan_choice(h6b)
        rows.append({
            "candidate_id": card["candidate_id"],
            "historical_verdict": card["precedent"],
            "expected_flags": card["expected_flags"],
            "h3_status": early["status"],
            "h3_science_warnings": early.get("science_risk_flags", []),
            "h6_status": late["status"],
            "h6_science_warnings": late["science_risk_flags"],
            "h6_supported_warnings": late_supported["science_risk_flags"],
        })
    print(json.dumps({
        "release": "0.9.6",
        "tooling": ["science.staged_selection.review_early_choice",
                    "science.plan_selection.review_h6_plan_choice"],
        "model_invoked": False,
        "rows": rows,
        "summary": {
            "cards": len(rows),
            "h6_flagged_cards": sum(1 for r in rows if r["h6_science_warnings"]),
            "h6_supported_flagged_cards": sum(1 for r in rows if r["h6_supported_warnings"]),
            "distinct_supported_warning_sets": len({
                json.dumps(r["h6_supported_warnings"], sort_keys=True) for r in rows}),
            "h3_cards_with_any_science_warning": sum(
                1 for r in rows if r["h3_science_warnings"]),
        },
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
