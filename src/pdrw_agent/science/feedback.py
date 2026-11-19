"""Read-only comparison of a declared *prior* probe and a later Run observation.

No filesystem writes, scientific validity certification, authorization, or
automatic GO/STOP. The proposal digest detects inconsistencies between supplied
objects; it does NOT prove the proposal existed before the observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from ..config import read_json
from ..schemas import AgentError, failure
from .decision import OUTCOMES, assess_proposal

SCHEMA = "pdrw-probe-feedback-v1"
VALIDITY = {"VALID", "INVALID", "INCONCLUSIVE", "NOT_RUN"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object, field: str, max_length: int = 240) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise AgentError("FEEDBACK_PACKET_INVALID", f"{field} must be a bounded nonempty string")
    return value


def _references(value: object) -> list[str]:
    if not isinstance(value, list) or len(value) > 12:
        raise AgentError("FEEDBACK_PACKET_INVALID", "At most 12 original evidence refs")
    out = [_text(ref, "evidence ref") for ref in value]
    if len(set(out)) != len(out):
        raise AgentError("FEEDBACK_PACKET_INVALID", "Duplicate evidence ref")
    return out


def proposal_sha256(proposal: dict) -> str:
    """Hash the exact declared proposal; byte identity is not time provenance."""
    assess_proposal(proposal)
    raw = json.dumps(proposal, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def review_probe_feedback(packet: dict) -> dict:
    """Compare matching measurement axes and declared categorical predictions.

    A Run's real validity, its original measurement, author grants and historical
    order must be verified externally. This function does not learn a new fact.
    """
    if not isinstance(packet, dict) or packet.get("schema_version") != SCHEMA:
        raise AgentError("FEEDBACK_PACKET_INVALID", "Unsupported feedback schema")
    decision_ref = _text(packet.get("prior_decision_ref"), "prior_decision_ref")
    proposal = packet.get("prior_proposal")
    if not isinstance(proposal, dict):
        raise AgentError("FEEDBACK_PACKET_INVALID", "prior_proposal must be an object")
    expected = _text(packet.get("prior_proposal_sha256"), "prior_proposal_sha256", 64)
    if not HEX64.fullmatch(expected) or proposal_sha256(proposal) != expected:
        raise AgentError("FEEDBACK_SNAPSHOT_MISMATCH",
                         "Prior proposal digest mismatch; do not interpret later results")
    observed = packet.get("observation")
    if not isinstance(observed, dict):
        raise AgentError("FEEDBACK_PACKET_INVALID", "observation must be an object")
    if observed.get("prior_proposal_sha256") != expected:
        raise AgentError("FEEDBACK_SNAPSHOT_MISMATCH", "Observation links a different proposal")
    run_ref = _text(observed.get("run_ref"), "run_ref")
    probe_id = _text(observed.get("probe_id"), "probe_id", 80)
    probe = next((p for p in proposal["probes"] if p["id"] == probe_id), None)
    if probe is None:
        raise AgentError("FEEDBACK_PROBE_UNKNOWN", "Run refers to a probe absent from the prior proposal")
    # Changed units/comparators are not a fair test of the originally stated
    # hypotheses. Never silently reinterpret a change as a negative result.
    for axis in ("observable", "evaluation_unit", "comparison_reference"):
        if observed.get(axis) != probe[axis]:
            raise AgentError("FEEDBACK_NOT_COMPARABLE", f"Changed {axis} since prior proposal")
    validity = observed.get("validity")
    if validity not in VALIDITY:
        raise AgentError("FEEDBACK_PACKET_INVALID", "Invalid declared Run validity")
    outcome = observed.get("outcome", "UNKNOWN")
    if outcome not in OUTCOMES:
        raise AgentError("FEEDBACK_PACKET_INVALID", "Invalid qualitative outcome")
    refs = _references(observed.get("evidence_refs", []))
    if validity == "VALID" and (not refs or outcome == "UNKNOWN"):
        raise AgentError("FEEDBACK_EVIDENCE_MISSING",
                         "Declared valid Run requires a cited result and known outcome")
    if validity != "VALID" and outcome != "UNKNOWN":
        raise AgentError("FEEDBACK_INVALID_OUTCOME",
                         "Invalid, inconclusive or unrun probes cannot supply a scientific outcome")

    consulted = packet.get("consulted_case_ids", [])
    if not isinstance(consulted, list) or len(consulted) > 8:
        raise AgentError("FEEDBACK_PACKET_INVALID", "At most 8 consulted case IDs")
    consulted = [_text(item, "case_id", 80) for item in consulted]
    if len(set(consulted)) != len(consulted):
        raise AgentError("FEEDBACK_PACKET_INVALID", "Duplicate consulted case ID")

    compatible, contradicted, unspecified = [], [], []
    if validity == "VALID":
        for hid in proposal["hypotheses"]:
            predicted = probe["predictions"].get(hid, "UNKNOWN")
            if predicted == "UNKNOWN":
                unspecified.append(hid)
            elif predicted == outcome:
                compatible.append(hid)
            else:
                contradicted.append(hid)
        distinction = ("DECLARED_PREDICTION_CONTRAST" if compatible and contradicted
                       else "NO_DISCRIMINATING_CONTRAST")
    else:
        distinction = "NO_VALID_SCIENTIFIC_INFERENCE"
    # Do not promote declared results to verified science or recommend execution.
    return {
        "status": "ADVISORY_FEEDBACK_ONLY",
        "prior_decision_ref": decision_ref,
        "prior_proposal_sha256": expected,
        "run_ref": run_ref,
        "probe_id": probe_id,
        "declared_run_validity": validity,
        "declared_outcome": outcome,
        "measurement_axes_matched": True,
        "declared_prediction_review": distinction,
        "compatible_predictions": compatible,
        "contradicted_predictions": contradicted,
        "unspecified_predictions": unspecified,
        "evidence_refs": refs,
        "consulted_case_ids": consulted,
        "next_science_action": (
            "VERIFY_ORIGINAL_RUN_AND_RECONSIDER_COMPETING_EXPLANATIONS"
            if distinction == "DECLARED_PREDICTION_CONTRAST"
            else "VERIFY_ORIGINAL_RUN_AND_DESIGN_DIFFERENTIATING_PROBE"
            if validity == "VALID"
            else "REPAIR_OR_REASSESS_EVIDENCE_BEFORE_SCIENTIFIC_UPDATE"
        ),
        "historical_order_verified": False,
        "original_run_verified": False,
        "scientific_inference_verified": False,
        "permission_to_execute": False,
        "automatic_go": False,
        "automatic_stop": False,
        "writes_performed": False,
        "note": ("Check the original pre-result decision record, exact Run, "
                 "prediction-time inputs and independent groups. Hypothesis "
                 "prediction agreement alone is not causal evidence."),
    }


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="Review declared probe feedback without writes")
    cli.add_argument("--packet", type=Path, required=True)
    args = cli.parse_args(argv)
    try:
        result = review_probe_feedback(read_json(args.packet, limit=128 * 1024))
    except (ValueError, OSError, TypeError, KeyError) as exc:
        result = failure(exc)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result["status"] == "ERROR" else 0


if __name__ == "__main__":
    sys.exit(main())
