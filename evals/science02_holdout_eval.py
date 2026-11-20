"""SCIENCE-02 stage A: holdout comparison of the H3 candidate checks.

Two arms on the same six holdout cards, no model invoked:

* ``0.9.6`` — ``staged_selection.review_early_choice`` and
  ``plan_selection.review_h6_plan_choice``, i.e. every science check that
  existed before SCIENCE-01;
* ``0.9.7`` — ``candidate_review.review_candidate``.

It also runs the two non-experimental directions. A card that cannot be
*represented* is a different failure from a card that is flagged, and is
reported separately.

Labels come from ``holdout_expectations.json`` (the library's documented
defect), never from the checker's own output.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE / "science_value"))

from pdrw_agent.schemas import AgentError  # noqa: E402
from pdrw_agent.science.candidate_review import review_candidate  # noqa: E402
from pdrw_agent.science.plan_selection import review_h6_plan_choice  # noqa: E402
from pdrw_agent.science.staged_selection import review_early_choice  # noqa: E402

from baseline_v096 import H3_PLAN, H6_PLAN, h3_option, h6_option  # noqa: E402

CARDS = json.loads((HERE / "science_value" / "holdout_cards.json").read_text(encoding="utf-8"))["cards"]
LABELS = json.loads((HERE / "science_value" / "holdout_expectations.json").read_text(encoding="utf-8"))["cases"]
NON_EXPERIMENTAL = json.loads(
    (HERE / "science_value" / "non_experimental_cards.json").read_text(encoding="utf-8"))["cards"]


def arm_096(card: dict) -> dict:
    h3 = dict(H3_PLAN)
    h3["options"] = [h3_option(card)]
    h3["recommended_option_id"] = card["candidate_id"]
    early = review_early_choice(h3)
    h6 = dict(H6_PLAN)
    h6["options"] = [h6_option(card, "SUPPORTED_BY_METADATA")]
    h6["recommended_option_id"] = card["candidate_id"]
    late = review_h6_plan_choice(h6)
    warnings = list(early.get("science_risk_flags", [])) + list(late["science_risk_flags"])
    return {"h3_status": early["status"], "h6_status": late["status"],
            "warnings": warnings, "flagged": bool(warnings)}


def arm_097(card: dict) -> dict:
    try:
        result = review_candidate(card)
    except AgentError as exc:
        return {"represented": False, "error_code": exc.code if hasattr(exc, "code") else str(exc),
                "flags": [], "flagged": False}
    return {"represented": True, "flags": result["flags"], "flagged": bool(result["flags"]),
            "checks": result["checks"]}


def main() -> int:
    rows = []
    for card in CARDS:
        label = LABELS[card["candidate_id"]]
        old = arm_096(card)
        new = arm_097(card)
        primary = label["primary"]
        rows.append({
            "candidate_id": card["candidate_id"],
            "source_case": label["source_case"],
            "historical_verdict": label["historical_verdict"],
            "expected_primary": primary,
            "arm_096_flagged": old["flagged"],
            "arm_096_warnings": old["warnings"],
            "arm_097_flagged": new["flagged"],
            "arm_097_flags": new["flags"],
            "arm_097_primary_hit": bool(primary) and bool(set(primary) & set(new["flags"])),
            "arm_097_false_positive": (not primary) and new["flagged"],
        })

    non_exp = []
    for card in NON_EXPERIMENTAL:
        result = arm_097(card)
        non_exp.append({
            "candidate_id": card["candidate_id"],
            "contribution_form": card["contribution_form"],
            "truth_kind": card["truth_kind"],
            "evaluation_unit": card["evaluation_unit"],
            "represented": result["represented"],
            "error_code": result.get("error_code"),
            "flags": result["flags"],
        })

    defective = [r for r in rows if r["expected_primary"]]
    clean = [r for r in rows if not r["expected_primary"]]
    summary = {
        "holdout_cards": len(rows),
        "defective_cards": len(defective),
        "clean_cards": len(clean),
        "arm_096_flagged_defective": sum(1 for r in defective if r["arm_096_flagged"]),
        "arm_097_flagged_defective": sum(1 for r in defective if r["arm_097_flagged"]),
        "arm_097_primary_hits": sum(1 for r in defective if r["arm_097_primary_hit"]),
        "arm_097_false_positives": sum(1 for r in clean if r["arm_097_false_positive"]),
        "non_experimental_cards": len(non_exp),
        "non_experimental_represented": sum(1 for r in non_exp if r["represented"]),
        "payload_chars_097": sum(
            len(json.dumps(arm_097(c), ensure_ascii=False)) for c in CARDS),
    }
    print(json.dumps({
        "stage": "A",
        "model_invoked": False,
        "note": ("Deterministic checker output on frozen cards. This measures what the checks "
                 "can represent and flag; it does not measure a model's research judgement."),
        "rows": rows,
        "non_experimental": non_exp,
        "summary": summary,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
