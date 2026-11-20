"""SCIENCE-01 comparison: v0.9.6 card checks vs the candidate review.

Same six frozen cards, same process, no model. The baseline is the *unchanged*
v0.9.6 code path; the comparison asks only whether a historically documented
defect is surfaced and whether a historically successful direction is left
alone. It does not measure model judgment or research quality.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from pdrw_agent.science.candidate_review import review_candidates  # noqa: E402
from pdrw_agent.science.plan_selection import review_h6_plan_choice  # noqa: E402
from pdrw_agent.science.staged_selection import review_early_choice  # noqa: E402

from science_value.baseline_v096 import H3_PLAN, H6_PLAN, h3_option, h6_option  # noqa: E402


def baseline_rows(cards: list[dict]) -> list[dict]:
    rows = []
    for card in cards:
        h3 = dict(H3_PLAN)
        h3["options"] = [h3_option(card)]
        h3["recommended_option_id"] = card["candidate_id"]
        early = review_early_choice(h3)
        h6 = dict(H6_PLAN)
        h6["options"] = [h6_option(card, "SUPPORTED_BY_METADATA")]
        h6["recommended_option_id"] = card["candidate_id"]
        late = review_h6_plan_choice(h6)
        rows.append({
            "candidate_id": card["candidate_id"],
            "h3_status": early["status"],
            "h3_science_flags": [f["warnings"] for f in early.get("science_risk_flags", [])],
            "h6_status": late["status"],
            "h6_science_flags": [f["warnings"] for f in late["science_risk_flags"]],
            "chars": len(json.dumps([early, late], ensure_ascii=False)),
        })
    return rows


def main() -> int:
    bundle = json.loads((HERE / "science_value" / "cards.json").read_text(encoding="utf-8"))
    cards = bundle["cards"]
    expected = json.loads(
        (HERE / "science_value" / "expectations.json").read_text(encoding="utf-8"))["cases"]

    base = {row["candidate_id"]: row for row in baseline_rows(cards)}
    review = review_candidates(cards)
    flags = {c["candidate_id"]: set(c["flags"]) for c in review["candidates"]}

    rows, missed, false_positive = [], [], []
    for card in cards:
        cid = card["candidate_id"]
        want = set(expected[cid]["expected_flags"])
        got = flags[cid]
        baseline_flagged = bool(base[cid]["h6_science_flags"] or base[cid]["h3_science_flags"])
        hit = bool(want & got)
        if want and not hit:
            missed.append(cid)
        if not want and got:
            false_positive.append({"candidate_id": cid, "flags": sorted(got)})
        rows.append({
            "candidate_id": cid,
            "historical_defect": expected[cid]["precedent"],
            "expected_flags": sorted(want),
            "baseline_flagged": baseline_flagged,
            "baseline_flags": base[cid]["h6_science_flags"],
            "review_flags": sorted(got),
            "review_localised": bool(want) and want.issubset(got),
            "clean_after_review": not got,
        })

    defect_rows = [r for r in rows if r["expected_flags"]]
    clean_rows = [r for r in rows if not r["expected_flags"]]
    summary = {
        "cards": len(rows),
        "defect_cards": len(defect_rows),
        "clean_cards": len(clean_rows),
        "baseline_flagged_defect_cards": sum(1 for r in defect_rows if r["baseline_flagged"]),
        "review_flagged_defect_cards": sum(1 for r in defect_rows if r["review_flags"]),
        "review_localised_defect_cards": sum(1 for r in defect_rows if r["review_localised"]),
        "review_false_positive_clean_cards": len(false_positive),
        "baseline_chars": sum(r["chars"] for r in base.values()),
        "review_chars": len(json.dumps(review, ensure_ascii=False)),
        "model_invoked": False,
        "research_value_measured": False,
    }
    print(json.dumps({
        "release": "0.9.7",
        "comparison": "same six frozen cards; unchanged v0.9.6 checks vs candidate_review",
        "rows": rows,
        "missed": missed,
        "false_positives": false_positive,
        "summary": summary,
        "limits": [
            "The cards reconstruct historical directions from CASE_LIBRARY premises; they are not verbatim model output.",
            "No LLM ran. This measures whether a documented defect is surfaced, not whether a model would avoid it.",
            "Research value, token cost in a real session and paper potential remain NOT_MEASURED.",
        ],
    }, ensure_ascii=False, indent=2))
    return 0 if not missed and not false_positive else 1


if __name__ == "__main__":
    sys.exit(main())
