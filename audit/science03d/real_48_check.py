"""Check the 0.9.12 premise evidence against a real project (48, RUN-005).

Two questions, one project, no writes:

1. does the RUN-005 closure still stand when the caller names the frozen plan it
   executed (`premise_ref` -> PROTO-POPU-RELIABILITY-v5-DEV005)?
2. is a citation of RUN-005 caught when the premise under study belongs to a
   different line with its own frozen plan (PROTO-POPU-DEPLOY-v3-DEV003)?

Run: python audit/science03d/real_48_check.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pdrw_agent.science.decision import assess_proposal  # noqa: E402

ROOT = Path("D:/workbuddy-work/48")
RUN = "DEV/runs/RUN-005"
V5 = "protocol/PROTO-POPU-RELIABILITY-v5-DEV005.json"
V3 = "protocol/PROTO-POPU-DEPLOY-v3-DEV003.json"
PREDICTS = {"H_mechanism": "DECREASE", "H_null": "NO_CHANGE"}


def packet(premise_id, premise_ref):
    prior = {"status": "COMPLETED_VALID", "run_ref": RUN, "premise_id": premise_id,
             "premise_ref": premise_ref}
    return {"claim_type": "MECHANISM/CAUSAL",
            "question": "Does the reliability mechanism add information over the base?",
            "hypotheses": ["H_mechanism", "H_null"],
            "proposed_premise": {"premise_id": premise_id,
                                 "scope": {"dataset": "PoPu DEV 12", "input": "lower 72"}},
            "prechecks": {"group_independence": {"status": "PASS"}},
            "probes": [{"id": "RELIABILITY-DEV", "observable": "subject-level MAE",
                        "evaluation_unit": "SUBJECT",
                        "comparison_reference": "same folds, base arm",
                        "predictions": dict(PREDICTS), "cost_band": "MEDIUM",
                        "prior_execution": prior}]}


def main() -> None:
    out = {}
    for name, premise, ref in (
            ("same_plan", "POPU_LOWER72_RECOVERY", V5),
            ("other_plan", "POPU_DEPLOY_UPPER72", V3)):
        result = assess_proposal(packet(premise, ref), project_root=ROOT)
        entry = result["probe_comparisons"][0]
        prior = entry["prior_execution"]
        binding = prior["run_binding"]
        out[name] = {
            "applicability": entry["applicability"],
            "next_action": entry["next_action"],
            "frontier": result["declared_probe_efficiency"]["frontier_candidate_ids_as_declared"],
            "historical": result["declared_probe_efficiency"]["historical_evidence_ids"],
            "status_verified": prior["status_verified"],
            "premise_binding": prior["premise_binding"],
            "premise_binding_basis": prior["premise_binding_basis"],
            "premise_verified": prior["premise_verified"],
            "premise_contradicted": prior["premise_contradicted"],
            "plan": binding["plan"],
            "premise_plan": binding["premise_plan"],
            "premise_plan_match": binding["premise_plan_match"],
            "run_id_consistency": binding["run_id_consistency"],
            "record_structure": binding["record_structure"],
            "findings": entry["findings"],
        }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
