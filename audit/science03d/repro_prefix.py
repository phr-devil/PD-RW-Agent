"""Reproduce the SCIENCE-03D premise-attribution defect on v0.9.11 (HEAD 16e7dd4).

Four packet shapes, one shared fixture project. Each is a legitimate-looking
proposal whose cited Run exists, is readable, and whose own status agrees with
the declaration. Only the *scientific premise* differs.

Run: python audit/science03d/repro_prefix.py > audit/science03d/repro_before.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fixture-project"
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pdrw_agent.science.decision import assess_proposal  # noqa: E402

SENSOR = "SENSOR_DRIFT_MECHANISM"
PREDICTS = {"H_drift": "DECREASE", "H_compliance": "NO_CHANGE"}


def probe(ident, run_ref, prior_premise, cost="LOW", record_ref=None):
    prior = {"status": "COMPLETED_VALID", "run_ref": run_ref, "premise_id": prior_premise}
    if record_ref:
        prior["record_ref"] = record_ref
    return {"id": ident, "observable": "subject-level MAE of contact force",
            "evaluation_unit": "SUBJECT",
            "comparison_reference": "same folds, load-cell-only arm",
            "predictions": dict(PREDICTS), "cost_band": cost, "prior_execution": prior}


LIVE = {"id": "SENSOR-DEV", "observable": "subject-level MAE of contact force",
        "evaluation_unit": "SUBJECT", "comparison_reference": "same folds, load-cell-only arm",
        "predictions": dict(PREDICTS), "cost_band": "MEDIUM"}


def packet(probes):
    return {"claim_type": "MECHANISM/CAUSAL",
            "question": "Is the residual drift, or beam compliance?",
            "hypotheses": ["H_drift", "H_compliance"],
            "proposed_premise": {"premise_id": SENSOR,
                                 "scope": {"dataset": "PRESS DEV 26",
                                           "input": "raw sensor channels"}},
            "prechecks": {"group_independence": {"status": "PASS"}},
            "probes": probes}


CASES = {
    # RUN-101 executed the BEAM plan. The caller says it answered the SENSOR
    # premise and repeats that claim in both id fields.
    "cross_plan": [probe("BEAM-RUN", "DEV/runs/RUN-101", SENSOR), LIVE],
    # Same files, but the directory is RUN-102 while the record says RUN-101.
    "run_id_conflict": [probe("COPIED-RUN", "DEV/runs/RUN-102", SENSOR), LIVE],
    # A directory holding aggregate metrics only: no identity, no status.
    "metrics_only": [probe("SCRATCH-RUN", "DEV/runs/RUN-103", SENSOR), LIVE],
    # The record names the beam plan; the probe declares no premise at all.
    "premise_unbound": [probe("BEAM-RUN2", "DEV/runs/RUN-101", None), LIVE],
}


def main() -> None:
    out = {}
    for name, probes in CASES.items():
        entry = probes[0]
        if "premise_id" not in entry["prior_execution"]:
            entry["prior_execution"].pop("premise_id", None)
        result = assess_proposal(packet(probes), project_root=ROOT)
        summary = next(s for s in result["probe_comparisons"] if s["id"] == entry["id"])
        prior = summary.get("prior_execution", {})
        out[name] = {
            "applicability": summary["applicability"],
            "next_action": summary["next_action"],
            "historical": entry["id"] in result["declared_probe_efficiency"]["historical_evidence_ids"],
            "frontier": result["declared_probe_efficiency"]["frontier_candidate_ids_as_declared"],
            "status_verified": prior.get("status_verified"),
            "file_binding": prior.get("file_binding"),
            "status_consistency": prior.get("status_consistency"),
            "premise_binding": prior.get("premise_binding"),
            "record_ref_echo": (prior.get("run_binding") or {}).get("record_ref"),
            "findings": summary["findings"],
        }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
