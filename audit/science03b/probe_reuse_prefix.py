"""Reproduce the closed-probe defect on the real RCT-CONTACT-26 case.

Run against v0.9.9 (HEAD c6e045e) *before* any change. Three packets, each a
real situation from `RCT-CONTACT-26/research/RESEARCH_RECORD.md`:

REUSE-A  the DEV-only slope probe was executed and closed by user decision
         (`R1_BRANCH = CLOSED_BY_USER_DECISION`, `NO_USEFUL_NEXT_PROBE = TRUE`).
         It is LOW cost and separates the same pair, so it dominates both the
         decisive controlled press and the sensor-swap probe that is actually
         feasible today.
REUSE-B  a probe whose earlier execution was INVALID (protocol defect) is
         still recommended as the next experiment instead of "repair first".
REUSE-C  a probe declared "already closed" with no Run reference at all: a
         caller declaration that must not be promoted to verified closure.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from pdrw_agent.science.decision import assess_proposal  # noqa: E402

QUESTION = ("Does the tactile contact response identify a material property rather "
            "than the sensor instance or the press trajectory, in the RCT-CONTACT DEV pool?")
SCOPE = {"dataset": "RCT-CONTACT DEV zone A", "rig": "DIGIT position_1..18",
         "condition": "robot press sequences"}
HYPOTHESES = ["H_material", "H_sensor_trajectory"]
PREDICTS = {"H_material": "INCREASE", "H_sensor_trajectory": "NO_CHANGE"}


def packet(probes):
    return {
        "claim_type": "MECHANISM/CAUSAL",
        "question": QUESTION,
        "claim_evidence_refs": ["RCT-CONTACT-26/research/dev_audit/contrast_table.json"],
        "hypotheses": HYPOTHESES,
        "proposed_premise": {"premise_id": "CONTACT_MECHANISM", "scope": SCOPE},
        "prechecks": {"group_independence": {"status": "UNKNOWN", "evidence_refs": []}},
        "probes": probes,
    }


def probe(ident, cost, observable, reference, unit="SEQUENCE", prior=None):
    entry = {
        "id": ident,
        "observable": observable,
        "evaluation_unit": unit,
        "comparison_reference": reference,
        "predictions": dict(PREDICTS),
        "cost_band": cost,
        "prediction_evidence_refs": ["RCT-CONTACT-26/research/STATE.md#9"],
    }
    if prior is not None:
        entry["prior_execution"] = prior
    return entry


CLOSED = {"status": "COMPLETED_VALID", "run_ref": "EXP-006/V1-R",
          "record_ref": "RESEARCH_RECORD.md#6",
          "premise_id": "CONTACT_MECHANISM",
          "conclusion": "NO_REPEATABLE_STABLE_OBSERVED_LAW; NO_USEFUL_NEXT_PROBE"}
INVALID = {"status": "COMPLETED_INVALID", "run_ref": "EXP-005/V1-R-run2",
           "record_ref": "RESEARCH_RECORD.md#5",
           "premise_id": "CONTACT_MECHANISM",
           "conclusion": "sign transform under fixed per-sensor offset: 0/979 determinable"}
DECLARED_ONLY = {"status": "COMPLETED_VALID", "premise_id": "CONTACT_MECHANISM",
                 "conclusion": "caller says this was already run"}

SLOPE = probe("R1-DEV-SLOPE", "LOW", "per-material force-Z slope across sensors",
              "same-material repeat press replicates", "FRAME", CLOSED)
PRESS = probe("R2-CONTROLLED-PRESS", "HIGH", "force-Z slope vs external modulus",
              "external modulus of the same material", "MATERIAL")
SWAP = probe("R3-SENSOR-SWAP", "MEDIUM", "per-material slope difference between sensors",
             "other sensor instance, same material and position", "SEQUENCE")

CASES = {
    "REUSE-A": packet([SLOPE, PRESS, SWAP]),
    "REUSE-B": packet([
        probe("R1-INVALID-TRANSFORM", "LOW", "per-sensor sign consistency of raw_fz",
              "fixed per-sensor sign transform", "FRAME", INVALID),
        PRESS,
        SWAP,
    ]),
    "REUSE-C": packet([
        probe("R1-DECLARED-CLOSED", "LOW", "per-material force-Z slope across sensors",
              "same-material repeat press replicates", "FRAME", DECLARED_ONLY),
        PRESS,
    ]),
}


def main() -> int:
    out = {}
    for name, pack in CASES.items():
        result = assess_proposal(pack)
        eff = result["declared_probe_efficiency"]
        out[name] = {
            "frontier": eff["frontier_candidate_ids_as_declared"],
            "dominated": eff["dominated_candidates_as_declared"],
            "exploratory": eff["exploratory_probe_ids"],
            "historical_evidence": eff.get("historical_evidence_ids"),
            "repair_required": eff.get("repair_required_ids"),
            "unverified_closure": eff.get("unverified_closure_ids"),
            "needs_authorization": eff.get("needs_authorization_ids"),
            "no_legal_decisive_probe": eff["no_legal_decisive_probe"],
            "no_executable_next_probe": eff.get("no_executable_next_probe"),
            "applicability": {s["id"]: s.get("applicability") for s in result["probe_comparisons"]},
            "payload_chars": len(json.dumps(result, ensure_ascii=False, separators=(",", ":"))),
        }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
