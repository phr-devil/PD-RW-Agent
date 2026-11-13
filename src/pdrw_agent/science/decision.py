"""Bounded, qualitative checks on declared research hypotheses and negative lessons.

Inputs are researcher/Agent proposals; this module does NOT attest their truth.
Scientific rules and actual Run evidence remain with PD-RW.
"""
from __future__ import annotations
from itertools import combinations
from ..schemas import AgentError

OUTCOMES = {"INCREASE", "DECREASE", "NO_CHANGE", "UNKNOWN"}
COSTS = {"LOW", "MEDIUM", "HIGH", "UNKNOWN"}
CHECKS = ("label_provenance", "group_independence", "legal_inputs",
          "evaluation_integrity", "metric_appropriateness", "effect_size")
CHECK_STATES = {"PASS", "FAIL", "UNKNOWN", "NOT_CHECKED"}
CLAIMS = {"CAPABILITY", "MECHANISM", "LAW"}
MAX_PROBES = 6


def _id(value, label: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 80 or not value.strip():
        raise AgentError("SCIENCE_PACKET_INVALID", f"{label} must be 1..80 characters")
    return value


def _refs(value, label: str, limit: int = 8) -> list[str]:
    if not isinstance(value, list) or len(value) > limit or any(
        not isinstance(x, str) or not x.strip() or len(x) > 240 for x in value
    ):
        raise AgentError("SCIENCE_PACKET_INVALID", f"{label} must be a small list of cited source identifiers")
    return value


def _scope(value) -> dict[str, str]:
    if not isinstance(value, dict) or len(value) > 12 or any(
        not isinstance(k, str) or not k or len(k) > 60 or
        not isinstance(v, str) or not v.strip() or len(v) > 160
        for k, v in value.items()
    ):
        raise AgentError("SCIENCE_PACKET_INVALID", "scope must be a small nonempty-value dictionary")
    return value


def assess_proposal(packet: dict) -> dict:
    """Report discriminability, unresolved evidence and premise similarity.

    This does not rank candidates by scientific merit, infer numerical
    probabilities, or authorize any action. No permanent memory is written.
    """
    if not isinstance(packet, dict):
        raise AgentError("SCIENCE_PACKET_INVALID", "Expected a JSON object")
    if packet.get("claim_type") not in CLAIMS:
        raise AgentError("SCIENCE_PACKET_INVALID", "Use CAPABILITY, MECHANISM, or LAW")
    question = packet.get("question")
    if not isinstance(question, str) or not question.strip() or len(question) > 1000:
        raise AgentError("SCIENCE_PACKET_INVALID", "A bounded research question is required")
    claim_refs = _refs(packet.get("claim_evidence_refs", []), "claim_evidence_refs")
    hypotheses = packet.get("hypotheses", [])
    if not isinstance(hypotheses, list) or not 2 <= len(hypotheses) <= 6:
        raise AgentError("SCIENCE_PACKET_INVALID", "Use 2..6 distinct hypothesis IDs")
    ids = [_id(x, "hypothesis ID") for x in hypotheses]
    if len(set(ids)) != len(ids):
        raise AgentError("SCIENCE_PACKET_INVALID", "Hypothesis IDs must be unique")
    proposed = packet.get("proposed_premise", {})
    if not isinstance(proposed, dict):
        raise AgentError("SCIENCE_PACKET_INVALID", "proposed_premise must be an object")
    premise_id = _id(proposed.get("premise_id"), "premise_id")
    scope = _scope(proposed.get("scope", {}))
    if not scope:
        raise AgentError("SCIENCE_PACKET_INVALID", "Declared applicability scope is required")

    checks = packet.get("prechecks", {})
    if not isinstance(checks, dict) or set(checks) - set(CHECKS):
        raise AgentError("SCIENCE_PACKET_INVALID", "Unexpected precheck names")
    prechecks = {}
    for key in CHECKS:
        entry = checks.get(key, {"status": "NOT_CHECKED", "evidence_refs": []})
        if not isinstance(entry, dict) or entry.get("status") not in CHECK_STATES:
            raise AgentError("SCIENCE_PACKET_INVALID", f"Invalid check: {key}")
        refs = _refs(entry.get("evidence_refs", []), key)
        prechecks[key] = {
            "declared_status": entry["status"],
            "evidence_refs": refs,
            "review": ("SOURCE_REQUIRED" if entry["status"] == "PASS" and not refs
                       else "DECLARED_RISK" if entry["status"] == "FAIL"
                       else "SOURCE_NOT_VERIFIED" if refs
                       else "UNKNOWN_OR_UNCHECKED"),
            "independently_verified": False,
        }

    lessons = packet.get("prior_negative_lessons", [])
    if not isinstance(lessons, list) or len(lessons) > 10:
        raise AgentError("SCIENCE_PACKET_INVALID", "At most ten prior negative lessons")
    negative_candidates = []
    for lesson in lessons:
        if not isinstance(lesson, dict):
            raise AgentError("SCIENCE_PACKET_INVALID", "Negative lessons must be objects")
        old_id = _id(lesson.get("premise_id"), "prior premise ID")
        old_scope = _scope(lesson.get("scope", {}))
        refs = _refs(lesson.get("evidence_refs", []), "negative evidence refs")
        validity = lesson.get("validity")
        if validity not in {"VALID_NEGATIVE", "INVALID", "UNKNOWN"}:
            raise AgentError("SCIENCE_PACKET_INVALID", "Negative lesson validity must be explicit")
        if old_id != premise_id:
            continue
        category = ("DECLARED_SAME_PREMISE_SCOPE_CANDIDATE"
                    if old_scope == scope and validity == "VALID_NEGATIVE" and refs
                    else "SCOPE_DIFFERS_REVIEW"
                    if old_scope != scope
                    else "NEGATIVE_EVIDENCE_INSUFFICIENT")
        negative_candidates.append({
            "premise_id": old_id, "status": category,
            "prior_validity_declared": validity,
            "evidence_refs": refs, "scientific_equivalence_verified": False,
            "automatic_stop": False,
        })

    probes = packet.get("probes", [])
    if not isinstance(probes, list) or not 1 <= len(probes) <= MAX_PROBES:
        raise AgentError("SCIENCE_PACKET_INVALID", "Use 1..6 candidate probes")
    summaries = []
    seen = set()
    for probe in probes:
        if not isinstance(probe, dict):
            raise AgentError("SCIENCE_PACKET_INVALID", "Probe must be an object")
        pid = _id(probe.get("id"), "probe ID")
        if pid in seen:
            raise AgentError("SCIENCE_PACKET_INVALID", "Duplicate probe ID")
        seen.add(pid)
        predictions = probe.get("predictions")
        if not isinstance(predictions, dict) or set(predictions) - set(ids):
            raise AgentError("SCIENCE_PACKET_INVALID", "Prediction keys must reference named hypotheses")
        if any(v not in OUTCOMES for v in predictions.values()):
            raise AgentError("SCIENCE_PACKET_INVALID", "Prediction outcomes must be qualitative")
        cost = probe.get("cost_band", "UNKNOWN")
        if cost not in COSTS:
            raise AgentError("SCIENCE_PACKET_INVALID", "Invalid cost band")
        refs = _refs(probe.get("prediction_evidence_refs", []), "probe evidence refs")
        separated = []
        for a, b in combinations(ids, 2):
            pa, pb = predictions.get(a, "UNKNOWN"), predictions.get(b, "UNKNOWN")
            if pa != "UNKNOWN" and pb != "UNKNOWN" and pa != pb:
                separated.append([a, b])
        summaries.append({
            "id": pid, "distinguishable_hypothesis_pairs_as_declared": separated,
            "pair_count": len(separated),
            "missing_hypothesis_predictions": [
                h for h in ids if predictions.get(h, "UNKNOWN") == "UNKNOWN"
            ],
            "declared_cost_band": cost,
            "prediction_evidence_refs": refs,
            "prediction_source_verified": False,
            "recommended_action": "COMPARE_WITH_ORIGINAL_EVIDENCE_NOT_AUTORANK",
        })

    return {
        "status": "ADVISORY_REVIEW_ONLY",
        "question": question,
        "claim_type": packet["claim_type"],
        "claim_evidence_refs": claim_refs,
        "premise_candidates": negative_candidates,
        "prechecks": prechecks,
        "probe_comparisons": summaries,
        "no_claim_of_novelty_or_scientific_validity": True,
        "original_user_authorization": "UNVERIFIED",
        "automatic_stop": False,
        "guidance": ("Refer to PD-RW HIGH_VALUE_RESEARCH_DESIGN / SCIENCE_RESULT_HARVEST; "
                     "verify original Run and named literature before choosing a Task or Probe."),
    }
