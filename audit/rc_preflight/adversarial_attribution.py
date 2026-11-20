"""Bounded adversarial cases for the premise-attribution question (RC preflight).

Nothing here executes an experiment, edits a Run, a frozen protocol or a hash.
Each case asks one question: can a probe that was *never run* be retired from
the frontier by a caller-supplied attribution?

Run: PYTHONPATH=src python audit/rc_preflight/adversarial_attribution.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pdrw_agent.science.decision import assess_proposal  # noqa: E402

P48 = Path("D:/workbuddy-work/48")
P19 = Path("D:/workbuddy-work/19")


def packet(*, premise_id, observable, unit, comparison, predictions, prior):
    return {
        "claim_type": "MECHANISM/CAUSAL",
        "question": "Does the target scale dominate the measured reliability gain?",
        "hypotheses": ["H_SCALE", "H_PRIOR"],
        "proposed_premise": {
            "premise_id": premise_id,
            "scope": {"dataset": "DEV 12 subjects", "unit": unit, "outcome": "subject MAE"},
        },
        "probes": [{
            "id": "P_KGRID",
            "observable": observable,
            "evaluation_unit": unit,
            "comparison_reference": comparison,
            "predictions": predictions,
            "cost_band": "MEDIUM",
            "prior_execution": prior,
        }],
    }


CASES = {
    # The probe is a k-scale grid. RUN-005's frozen plan fixes one scale only.
    "AD1_cites_run_without_plan": packet(
        premise_id="PREM-K-SCALE",
        observable="subject-level MAE across k in {18, 173, 1728}",
        unit="SUBJECT",
        comparison="same folds, POSTUREVALUE baseline at the same k",
        predictions={"H_SCALE": "DECREASE", "H_PRIOR": "NO_CHANGE"},
        prior={"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-005",
               "premise_id": "PREM-K-SCALE"},
    ),
    # Same probe, but the caller names the frozen plan RUN-005 really executed.
    # The plan has no premise_id, and its primary outcome is a single scale.
    "AD2_names_the_plan_that_ran": packet(
        premise_id="PREM-K-SCALE",
        observable="subject-level MAE across k in {18, 173, 1728}",
        unit="SUBJECT",
        comparison="same folds, POSTUREVALUE baseline at the same k",
        predictions={"H_SCALE": "DECREASE", "H_PRIOR": "NO_CHANGE"},
        prior={"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-005",
               "premise_ref": "protocol/PROTO-POPU-RELIABILITY-v5-DEV005.json",
               "premise_id": "PREM-K-SCALE"},
    ),
    # Project 19's only Run-shaped artifact is a metrics file: no run_id, no
    # status. It is a real experiment, and it is not a Run record.
    "AD3_metrics_only_artifact": packet(
        premise_id="PREM-HIER-CONTEXT",
        observable="17-object LODO segmental F1",
        unit="SUBJECT",
        comparison="SF|lag3 single-frame LR baseline",
        predictions={"H_SCALE": "INCREASE", "H_PRIOR": "NO_CHANGE"},
        prior={"status": "COMPLETED_VALID", "run_ref": "CRFW_RUN1/results.json",
               "premise_id": "PREM-HIER-CONTEXT"},
    ),
    # The directory holds an invalid attempt, declared as a valid closure.
    "AD4_invalid_attempt_declared_valid": packet(
        premise_id="PREM-K-SCALE",
        observable="subject-level MAE across k in {18, 173, 1728}",
        unit="SUBJECT",
        comparison="same folds, POSTUREVALUE baseline at the same k",
        predictions={"H_SCALE": "DECREASE", "H_PRIOR": "NO_CHANGE"},
        prior={"status": "COMPLETED_VALID",
               "run_ref": "DEV/runs/RUN-005/attempt-1-invalid-anchor",
               "premise_id": "PREM-K-SCALE"},
    ),
}


def main() -> int:
    out = {}
    for name, pkt in CASES.items():
        root = P19 if name.startswith("AD3") else P48
        try:
            res = assess_proposal(pkt, project_root=root)
        except Exception as exc:  # noqa: BLE001 - report, do not fail the run
            out[name] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        probe = res["probe_comparisons"][0]
        prior = probe.get("prior_execution") or {}
        eff = res["declared_probe_efficiency"]
        out[name] = {
            "applicability": probe["applicability"],
            "next_action": probe["next_action"],
            "execution_verified": prior.get("execution_verified"),
            "premise_verified": prior.get("premise_verified"),
            "closure_verified": prior.get("closure_verified"),
            "status_verified": prior.get("status_verified"),
            "premise_binding": prior.get("premise_binding"),
            "premise_binding_basis": prior.get("premise_binding_basis"),
            "premise_evidence": prior.get("premise_evidence"),
            "premise_plan_match": (prior.get("run_binding") or {}).get("premise_plan_match"),
            "record_structure": (prior.get("run_binding") or {}).get("record_structure"),
            "in_frontier": probe["id"] in eff["frontier_candidate_ids_as_declared"],
            "in_historical_evidence": probe["id"] in eff["historical_evidence_ids"],
            "in_premise_assumed": probe["id"] in eff.get("attribution_unchecked_ids", []),
            "no_executable_next_probe": eff["no_executable_next_probe"],
            "findings": probe["findings"],
        }
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
