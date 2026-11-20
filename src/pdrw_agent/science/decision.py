"""Bounded, qualitative checks on declared research hypotheses and negative lessons.

Inputs are researcher/Agent proposals; this module does NOT attest their truth.
Scientific rules and actual Run evidence remain with PD-RW.
"""
from __future__ import annotations
import re
from itertools import combinations
from ..schemas import AgentError
from .probe_frontier import summarize_declared_probe_frontier

OUTCOMES = {"INCREASE", "DECREASE", "NO_CHANGE", "UNKNOWN"}
COSTS = {"LOW", "MEDIUM", "HIGH", "UNKNOWN"}
CHECKS = ("label_provenance", "group_independence", "legal_inputs",
          "evaluation_integrity", "metric_appropriateness", "effect_size")
CHECK_STATES = {"PASS", "FAIL", "UNKNOWN", "NOT_CHECKED"}
CLAIMS = {"CAPABILITY/PERFORMANCE", "MECHANISM/CAUSAL", "LAW/BOUNDARY"}
CLAIM_ALIASES = {
    "CAPABILITY": "CAPABILITY/PERFORMANCE",
    "MECHANISM": "MECHANISM/CAUSAL",
    "LAW": "LAW/BOUNDARY",
}
MAX_PROBES = 6

# A probe's reference condition is its baseline. Two ways that stops being a
# legal comparison: the reference needs information unavailable at prediction
# time (CASE-02/CASE-12 oracle), or the evaluation unit repeats one subject
# while group independence is declared PASS (CASE-11/EXT-X3).
_ILLEGAL_REFERENCE = re.compile(
    r"(oracle|测试(集)?真值|test[- ]time (truth|labels)|future (information|labels)|"
    r"dev_val 标签|未来信息)", re.I)
_REPEATED_UNIT = frozenset({"WINDOW", "FRAME", "RECORD", "SEGMENT", "TOKEN", "ROW", "EPISODE"})
_PROBE_RULE = {
    "REFERENCE_NOT_LEGAL": "ALGORITHM_ENGINEERING §1 BASELINE / CASE-02",
    "PROBE_UNIT_NOT_INDEPENDENT": "HIGH_VALUE_RESEARCH_DESIGN §B INDEPENDENT_N / CASE-11",
    "EXECUTION_DECLARED_NOT_VERIFIED": "SCIENCE_RESULT_HARVEST §RUN_EVIDENCE / CASE-20",
}
_PROBE_PRECEDENT = {
    "REFERENCE_NOT_LEGAL": ["CASE-02", "CASE-12"],
    "PROBE_UNIT_NOT_INDEPENDENT": ["CASE-11", "EXT-X3"],
    "EXECUTION_DECLARED_NOT_VERIFIED": ["CASE-20", "CASE-21"],
}
_PROBE_QUESTION = {
    "REFERENCE_NOT_LEGAL": "Which reference is legal at prediction time, and does it exist already?",
    "PROBE_UNIT_NOT_INDEPENDENT": "How many independent units (not windows) does this probe compare?",
    "EXECUTION_DECLARED_NOT_VERIFIED": (
        "Which Run or record proves this probe already ran under this premise?"),
}
# What the probe may still be used for. A test-time-truth reference is a
# legitimate diagnostic upper bound and an illegitimate decisive comparison;
# an unresolved unit question asks for a count, not for a ban on the metric;
# an unverifiable closure is a record to check, not a reason to rerun.
_PROBE_USAGE = {
    "REFERENCE_NOT_LEGAL": "DIAGNOSTIC_UPPER_BOUND_ONLY",
    "PROBE_UNIT_NOT_INDEPENDENT": "VERIFY_INDEPENDENT_UNITS_FIRST",
    "EXECUTION_DECLARED_NOT_VERIFIED": "DO_NOT_TREAT_AS_CLOSED_OR_AS_NEW",
}
_DISQUALIFYING_FROM_FRONTIER = frozenset({"REFERENCE_NOT_LEGAL"})

# CASE-20/CASE-21: an experiment that already answered this premise cannot
# answer it again. The declared execution state decides what the next action is,
# and a state without a Run reference stays a claim, never a verified closure.
EXECUTION_STATUSES = {"NOT_EXECUTED", "COMPLETED_VALID", "COMPLETED_INVALID",
                      "INCONCLUSIVE", "BLOCKED"}
_PRIOR_EXECUTION_FIELDS = {"status", "run_ref", "record_ref", "premise_id",
                           "conclusion", "new_information", "requires_new_authorization"}
_MAX_PRIOR_TEXT = 240

# The next action each declared state implies. Nothing here runs, stops, or
# approves anything: it names what would have to be true before a rerun.
_NEXT_ACTION = {
    "NOT_YET_RUN": "RUN_IF_LEGAL_AND_DISCRIMINATING",
    "NEEDS_AUTHORIZATION": "OBTAIN_AUTHORIZATION_FIRST",
    "HISTORICAL_EVIDENCE_ONLY": "KEEP_AS_RECORDED_EVIDENCE_DO_NOT_RERUN",
    "CLOSURE_DECLARED_NOT_VERIFIED": "VERIFY_RUN_BEFORE_DECIDING",
    "TARGETED_REPAIR": "REPAIR_NAMED_DEFECT_FIRST",
    "REVISIT_ON_NEW_INFORMATION": "REVISIT_ONLY_IF_NEW_INFORMATION_CHANGES_JUDGMENT",
    "AWAIT_NEW_INFORMATION": "HOLD_UNTIL_NEW_INFORMATION_EXISTS",
    "BLOCKER_UNRESOLVED": "RESOLVE_BLOCKER_FIRST",
}


def _prior_execution(value, premise_id: str) -> dict:
    """Read the declared execution state of one probe without trusting it.

    Absent means "not run", which is the only reading that keeps old packets
    valid. Everything else is echoed back with an explicit `status_verified`
    flag: a Run reference makes the claim checkable, never checked.
    """
    if value is None:
        return {
            "declared_status": "NOT_EXECUTED",
            "run_ref": None,
            "status_verified": False,
            "premise_match": None,
            "history_applicable": False,
            "requires_new_authorization": False,
            "new_information_declared": False,
            "applicability": "NOT_YET_RUN",
            "next_action": _NEXT_ACTION["NOT_YET_RUN"],
        }
    if not isinstance(value, dict) or set(value) - _PRIOR_EXECUTION_FIELDS:
        raise AgentError("SCIENCE_PACKET_INVALID",
                         "prior_execution accepts only declared execution fields")
    status = value.get("status", "NOT_EXECUTED")
    if not isinstance(status, str) or status not in EXECUTION_STATUSES:
        raise AgentError("SCIENCE_PACKET_INVALID", "Unsupported declared execution status")
    texts = {}
    for key in ("run_ref", "record_ref", "conclusion", "new_information"):
        item = value.get(key)
        if item is None:
            texts[key] = None
            continue
        if not isinstance(item, str) or not item.strip() or len(item) > _MAX_PRIOR_TEXT:
            raise AgentError("SCIENCE_PACKET_INVALID", f"prior_execution.{key} must be bounded text")
        texts[key] = item
    prior_premise = value.get("premise_id")
    if prior_premise is not None:
        _id(prior_premise, "prior_execution.premise_id")
    needs_auth = value.get("requires_new_authorization", False)
    if not isinstance(needs_auth, bool):
        raise AgentError("SCIENCE_PACKET_INVALID",
                         "requires_new_authorization must be boolean")

    verified = status != "NOT_EXECUTED" and bool(texts["run_ref"])
    # A closure recorded under another premise says nothing about this one.
    premise_match = None if prior_premise is None else prior_premise == premise_id
    if status == "NOT_EXECUTED":
        applicability = "NEEDS_AUTHORIZATION" if needs_auth else "NOT_YET_RUN"
    elif premise_match is False:
        applicability = "NOT_YET_RUN"
    elif status == "COMPLETED_VALID":
        applicability = "HISTORICAL_EVIDENCE_ONLY" if verified else "CLOSURE_DECLARED_NOT_VERIFIED"
    elif status == "COMPLETED_INVALID":
        applicability = "TARGETED_REPAIR"
    elif status == "INCONCLUSIVE":
        applicability = ("REVISIT_ON_NEW_INFORMATION" if texts["new_information"]
                         else "AWAIT_NEW_INFORMATION")
    else:
        applicability = "BLOCKER_UNRESOLVED"
    return {
        "declared_status": status,
        "run_ref": texts["run_ref"],
        "status_verified": verified,
        "premise_match": premise_match,
        "history_applicable": premise_match is not False and status != "NOT_EXECUTED",
        "requires_new_authorization": needs_auth,
        "new_information_declared": bool(texts["new_information"]),
        "applicability": applicability,
        "next_action": _NEXT_ACTION[applicability],
    }


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
    raw_type = packet.get("claim_type")
    if not isinstance(raw_type, str):
        raise AgentError("SCIENCE_PACKET_INVALID", "Claim type must be textual")
    claim_type = CLAIM_ALIASES.get(raw_type, raw_type)
    if claim_type not in CLAIMS:
        raise AgentError("SCIENCE_PACKET_INVALID", "Use a PD-RW capability, mechanism, or boundary claim type")
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
        if not isinstance(entry, dict) or not isinstance(entry.get("status"), str) or entry["status"] not in CHECK_STATES:
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
        if not isinstance(validity, str) or validity not in {"VALID_NEGATIVE", "INVALID", "UNKNOWN"}:
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

    # A verified-looking *declared* success is not a universally applicable
    # mechanism or automatic GO. Only exact premise/scope yields an advisory
    # candidate; actual Run evidence and scientific transfer need review.
    positive_lessons = packet.get("prior_positive_lessons", [])
    if not isinstance(positive_lessons, list) or len(positive_lessons) > 10:
        raise AgentError("SCIENCE_PACKET_INVALID", "At most ten prior positive lessons")
    positive_candidates = []
    for lesson in positive_lessons:
        if not isinstance(lesson, dict):
            raise AgentError("SCIENCE_PACKET_INVALID", "Positive lessons must be objects")
        old_id = _id(lesson.get("premise_id"), "prior positive premise ID")
        old_scope = _scope(lesson.get("scope", {}))
        refs = _refs(lesson.get("evidence_refs", []), "positive evidence refs")
        validity = lesson.get("validity")
        if not isinstance(validity, str) or validity not in {"VALID_POSITIVE", "INVALID", "UNKNOWN"}:
            raise AgentError("SCIENCE_PACKET_INVALID", "Positive lesson validity must be explicit")
        if old_id != premise_id:
            continue
        category = ("DECLARED_SAME_PREMISE_SCOPE_POSITIVE_CANDIDATE"
                    if old_scope == scope and validity == "VALID_POSITIVE" and refs
                    else "SCOPE_DIFFERS_REVIEW" if old_scope != scope
                    else "POSITIVE_EVIDENCE_INSUFFICIENT")
        positive_candidates.append({
            "premise_id": old_id, "status": category,
            "prior_validity_declared": validity,
            "evidence_refs": refs, "scientific_equivalence_verified": False,
            "automatic_go": False,
        })

    probes = packet.get("probes", [])
    if not isinstance(probes, list) or not 1 <= len(probes) <= MAX_PROBES:
        raise AgentError("SCIENCE_PACKET_INVALID", "Use 1..6 candidate probes")
    summaries = []
    probe_findings = []
    repeated_unit_probes = []
    seen = set()
    for probe in probes:
        if not isinstance(probe, dict):
            raise AgentError("SCIENCE_PACKET_INVALID", "Probe must be an object")
        pid = _id(probe.get("id"), "probe ID")
        if pid in seen:
            raise AgentError("SCIENCE_PACKET_INVALID", "Duplicate probe ID")
        seen.add(pid)
        # All competing hypotheses must predict the same observable,
        # evaluation unit and reference condition. No metric is invented.
        observable = _id(probe.get("observable"), "probe observable")
        evaluation_unit = _id(probe.get("evaluation_unit"), "evaluation_unit")
        comparison_reference = _id(probe.get("comparison_reference"), "comparison_reference")
        predictions = probe.get("predictions")
        if not isinstance(predictions, dict) or set(predictions) - set(ids):
            raise AgentError("SCIENCE_PACKET_INVALID", "Prediction keys must reference named hypotheses")
        if any(not isinstance(v, str) or v not in OUTCOMES for v in predictions.values()):
            raise AgentError("SCIENCE_PACKET_INVALID", "Prediction outcomes must be qualitative")
        cost = probe.get("cost_band", "UNKNOWN")
        if not isinstance(cost, str) or cost not in COSTS:
            raise AgentError("SCIENCE_PACKET_INVALID", "Invalid cost band")
        refs = _refs(probe.get("prediction_evidence_refs", []), "probe evidence refs")
        separated = []
        for a, b in combinations(ids, 2):
            pa, pb = predictions.get(a, "UNKNOWN"), predictions.get(b, "UNKNOWN")
            if pa != "UNKNOWN" and pb != "UNKNOWN" and pa != pb:
                separated.append([a, b])
        # Declaration-level contradictions only: no file is read and nothing is
        # promoted. A probe whose reference needs test-time truth, or whose unit
        # repeats one subject while group independence is declared PASS, is not
        # a clean comparison even if it separates every hypothesis pair.
        findings = []
        if _ILLEGAL_REFERENCE.search(comparison_reference):
            findings.append("REFERENCE_NOT_LEGAL")
        if evaluation_unit.strip().upper() in _REPEATED_UNIT:
            if prechecks["group_independence"]["declared_status"] == "PASS":
                repeated_unit_probes.append(pid)
                findings.append("PROBE_UNIT_NOT_INDEPENDENT")
        # A claimed closure that cannot be traced to a Run is a record to
        # check, not a finished experiment and not a free rerun (CASE-20).
        prior = _prior_execution(probe.get("prior_execution"), premise_id)
        if prior["applicability"] == "CLOSURE_DECLARED_NOT_VERIFIED":
            findings.append("EXECUTION_DECLARED_NOT_VERIFIED")
        if findings:
            probe_findings.append({
                "probe_id": pid,
                "codes": findings,
                "rules": [_PROBE_RULE[code] for code in findings],
                "precedent": sorted({c for code in findings for c in _PROBE_PRECEDENT[code]}),
                "questions": [_PROBE_QUESTION[code] for code in findings],
                "usage": [_PROBE_USAGE[code] for code in findings],
                "blocks_decisive_frontier": any(
                    code in _DISQUALIFYING_FROM_FRONTIER for code in findings),
                "independently_verified": False,
            })
        summary = {
            "id": pid, "observable": observable,
            "evaluation_unit": evaluation_unit,
            "comparison_reference": comparison_reference,
            "distinguishable_hypothesis_pairs_as_declared": separated,
            "pair_count": len(separated),
            "missing_hypothesis_predictions": [
                h for h in ids if predictions.get(h, "UNKNOWN") == "UNKNOWN"
            ],
            "declared_cost_band": cost,
            "prediction_evidence_refs": refs,
            "prediction_source_verified": False,
            "findings": findings,
            "applicability": prior["applicability"],
            "next_action": prior["next_action"],
            "recommended_action": "COMPARE_WITH_ORIGINAL_EVIDENCE_NOT_AUTORANK",
        }
        # Only echo an execution history the caller actually declared.
        if "prior_execution" in probe:
            summary["prior_execution"] = prior
        summaries.append(summary)

    # A precheck cannot stay "declared PASS" while the probe it is attached to
    # counts repeated windows as independent units: that is the CASE-11 defect
    # reappearing one layer down.
    if repeated_unit_probes:
        prechecks["group_independence"]["review"] = "DECLARED_CONFLICT"
        prechecks["group_independence"]["conflict_with_probe_units"] = repeated_unit_probes
    no_decisive = bool(summaries) and all(s["pair_count"] == 0 for s in summaries)
    efficiency = summarize_declared_probe_frontier(summaries)
    no_legal = efficiency["no_legal_decisive_probe"]
    no_executable = efficiency["no_executable_next_probe"]

    return {
        "status": "ADVISORY_REVIEW_ONLY",
        "question": question,
        "claim_type": claim_type,
        "claim_evidence_refs": claim_refs,
        "premise_candidates": negative_candidates,
        "positive_premise_candidates": positive_candidates,
        "prechecks": prechecks,
        "probe_comparisons": summaries,
        "declared_probe_efficiency": efficiency,
        "probe_findings": probe_findings,
        "no_decisive_probe": no_decisive,
        "no_decisive_probe_question": (
            "Which observable would separate at least one pair of the named hypotheses? "
            "Without one, running any of these probes cannot change the judgment."
            if no_decisive else None),
        "no_legal_decisive_probe": no_legal,
        "no_legal_decisive_probe_question": (
            "Which reference condition is available at prediction time? A probe that "
            "separates the hypotheses only against test-time truth can bound what is "
            "achievable, but cannot decide between them."
            if no_legal and not no_decisive else None),
        # Distinct from the two flags above: the probes can decide and are legal,
        # but none of them is a step you can take now (already answered, needs a
        # repair, needs new information, or needs an authorization).
        "no_executable_next_probe": no_executable,
        "no_executable_next_probe_question": (
            "Which listed probe has not already answered this premise and can start "
            "under the current authorization? A closed probe is recorded evidence, an "
            "invalid one needs its named defect repaired, and an ungranted one is a "
            "candidate rather than a next action."
            if no_executable else None),
        "no_claim_of_novelty_or_scientific_validity": True,
        "original_user_authorization": "UNVERIFIED",
        "automatic_stop": False,
        "automatic_go": False,
        "guidance": ("Refer to PD-RW HIGH_VALUE_RESEARCH_DESIGN / SCIENCE_RESULT_HARVEST; "
                     "verify original Run and named literature before choosing a Task or Probe."),
    }
