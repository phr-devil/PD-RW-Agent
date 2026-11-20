"""SCIENCE-03C prefix: what `status_verified` actually verifies.

Runs the same four declarations through `assess_proposal` with and without a
project root. Before the fix the only input is a non-empty string, so a Run that
does not exist, a Run from another project, and a Run whose own record says
INVALID all come back `status_verified: true`.

Usage: PYTHONPATH=src python audit/science03c/binding_prefix.py [--root <project>]
"""
import json
import sys
from pathlib import Path

from pdrw_agent.science.decision import assess_proposal

ROOT = Path("D:/workbuddy-work/48")

PREDICTS = {"H_deployable": "DECREASE", "H_prior_only": "NO_CHANGE"}


def probe(ident, prior, cost="HIGH"):
    return {"id": ident, "observable": "intensity MAE under the same folds",
            "evaluation_unit": "SUBJECT", "comparison_reference": "same protocol, same folds",
            "predictions": dict(PREDICTS), "cost_band": cost,
            "prior_execution": prior}


def packet(probes):
    return {"claim_type": "MECHANISM/CAUSAL",
            "question": "Is there a deployable increment beyond the posture prior?",
            "hypotheses": ["H_deployable", "H_prior_only"],
            "proposed_premise": {"premise_id": "POPU_LOWER72",
                                 "scope": {"dataset": "PoPu DEV 12", "input": "lower 72"}},
            "prechecks": {"group_independence": {"status": "PASS"}},
            "probes": probes}


LIVE = {"id": "LIVE", "observable": "cross-library ranking",
        "evaluation_unit": "SUBJECT", "comparison_reference": "same protocol, second library",
        "predictions": dict(PREDICTS), "cost_band": "HIGH"}

CASES = {
    # 1. the cited Run does not exist anywhere
    "run_ref_missing": {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-999",
                        "premise_id": "POPU_LOWER72"},
    # 2. the cited Run belongs to another project (escapes the project root)
    "run_ref_wrong_project": {"status": "COMPLETED_VALID",
                              "run_ref": "../MCS-HEMO-26/research/dev_audit",
                              "premise_id": "POPU_LOWER72"},
    # 3. the cited Run exists but its own record says the attempt was invalid
    "run_status_conflict": {"status": "COMPLETED_VALID",
                            "run_ref": "DEV/runs/RUN-005/attempt-1-invalid-anchor",
                            "premise_id": "POPU_LOWER72"},
    # 4. a real, consistent Run -- the only one that should read as verified
    "run_ref_ok": {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-005",
                   "premise_id": "POPU_LOWER72"},
    # 5. real Run, but the premise is never stated: is this closure evidence?
    "premise_missing": {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-005"},
    # 6. real Run under a different premise: must not close this one
    "premise_other": {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-005",
                      "premise_id": "SOME_OTHER_PREMISE"},
}


def run(with_root: bool):
    out = {}
    for name, prior in CASES.items():
        pkt = packet([probe(name, prior), LIVE])
        try:
            result = (assess_proposal(pkt, project_root=ROOT) if with_root
                      else assess_proposal(pkt))
        except TypeError:
            result = assess_proposal(pkt)
        entry = next(s for s in result["probe_comparisons"] if s["id"] == name)
        prior_out = entry["prior_execution"]
        out[name] = {
            "status_verified": prior_out["status_verified"],
            "applicability": entry["applicability"],
            "next_action": entry["next_action"],
            "file_binding": prior_out.get("file_binding"),
            "status_consistency": prior_out.get("status_consistency"),
            "premise_binding": prior_out.get("premise_binding"),
            "history_applicable": prior_out["history_applicable"],
            "in_frontier": name in result["declared_probe_efficiency"][
                "frontier_candidate_ids_as_declared"],
            "live_still_in_frontier": "LIVE" in result["declared_probe_efficiency"][
                "frontier_candidate_ids_as_declared"],
            "authorization_basis": prior_out.get("authorization_basis"),
        }
    out["_authorization"] = result.get("authorization_basis")
    return out


if __name__ == "__main__":
    print(json.dumps({"declared_only": run(False), "with_project_root": run(True)},
                     ensure_ascii=False, indent=1))
