"""SCIENCE-03 stage A, before the fix: two frontier defects on real card shapes.

P1 reproduces CASE-08-adjacent behaviour: a LOW-cost probe that separates
nothing sits next to a MEDIUM-cost probe that does separate the hypotheses.
P2 reproduces CASE-02/CASE-12 behaviour: the probe's reference condition is a
test-time oracle, so it is not a legal decisive experiment, yet it is still a
candidate. Both packets are built from the same cards already used by
``evals/science02_probe_design.py``.

Run before the patch and keep the output; it is the reproduction record.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pdrw_agent.science.decision import assess_proposal  # noqa: E402

SCOPE = {"material": "unseen", "condition": "unseen", "evaluator": "ridge"}
BASE = {
    "claim_type": "MECHANISM/CAUSAL",
    "question": "Does the geometric mechanism or the observation budget explain the collapse?",
    "claim_evidence_refs": ["DEV/runs/RUN-011/metrics.json"],
    "hypotheses": ["H_mechanism", "H_budget"],
    "proposed_premise": {"premise_id": "MECHANISM", "scope": SCOPE},
    "prechecks": {"group_independence": {"status": "PASS", "evidence_refs": ["DEV/protocol.md"]}},
}

# P1: cheap but blind next to informative but medium.
P1 = dict(BASE, probes=[
    {"id": "CHEAP-BUT-BLIND", "observable": "R2", "evaluation_unit": "SPECIMEN",
     "comparison_reference": "VT_plain", "predictions": {}, "cost_band": "LOW"},
    {"id": "MEDIUM-BUT-DECIDES", "observable": "boundary error", "evaluation_unit": "SPECIMEN",
     "comparison_reference": "VT_plain",
     "predictions": {"H_mechanism": "DECREASE", "H_budget": "NO_CHANGE"}, "cost_band": "MEDIUM"},
])

# P2: illegal (oracle) reference that still separates the pair, next to a legal one.
P2 = dict(BASE, probes=[
    {"id": "ORACLE-UPPER-BOUND", "observable": "R2", "evaluation_unit": "SPECIMEN",
     "comparison_reference": "ORACLE_OFFSET_REMOVAL_DEV_VAL_LABELS",
     "predictions": {"H_mechanism": "INCREASE", "H_budget": "NO_CHANGE"}, "cost_band": "LOW"},
    {"id": "LEGAL-SPECIMEN-PROBE", "observable": "boundary error", "evaluation_unit": "SPECIMEN",
     "comparison_reference": "VT_plain",
     "predictions": {"H_mechanism": "DECREASE", "H_budget": "NO_CHANGE"}, "cost_band": "MEDIUM"},
])


def main() -> int:
    rows = []
    for name, packet in (("P1-blind-cheap", P1), ("P2-oracle-reference", P2)):
        result = assess_proposal(packet)
        eff = result["declared_probe_efficiency"]
        rows.append({
            "packet": name,
            "pair_counts": {p["id"]: p["pair_count"] for p in result["probe_comparisons"]},
            "frontier": eff["frontier_candidate_ids_as_declared"],
            "dominated": eff["dominated_candidates_as_declared"],
            "no_discriminating_probe": eff["no_discriminating_probe"],
            "probe_findings": [(f["probe_id"], f["codes"]) for f in result["probe_findings"]],
            "defect": (
                "a probe that separates nothing is listed as a frontier candidate"
                if name.startswith("P1") and "CHEAP-BUT-BLIND" in eff["frontier_candidate_ids_as_declared"]
                else "a probe whose reference needs test-time truth is listed as a legal candidate"
                if name.startswith("P2") and "ORACLE-UPPER-BOUND" in eff["frontier_candidate_ids_as_declared"]
                else None),
        })
    print(json.dumps({"stage": "A-prefix", "model_invoked": False, "rows": rows},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
