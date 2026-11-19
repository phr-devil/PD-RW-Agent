"""Read-only structural compiler for *declared* research outcomes.

Never learns a scientific fact from crash reports or failed evaluations.
No write to PD-RW, no auto-HOLD/GO/STOP, no training or citations fabricated.
"""
from __future__ import annotations

import hashlib
import json
from ..schemas import AgentError

OUTCOMES = {
    "ENGINEERING_FAILURE", "INVALID_EXPERIMENT", "INCONCLUSIVE",
    "VALID_NEGATIVE", "VALID_POSITIVE", "NOT_RUN",
}


def _nonempty(value, label: str, maximum: int = 160) -> str:
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise AgentError("LESSON_PACKET_INVALID", f"{label} requires bounded nonempty text")
    return value.strip()


def _scope(value) -> dict:
    if not isinstance(value, dict) or not 1 <= len(value) <= 12:
        raise AgentError("LESSON_PACKET_INVALID", "scope must contain 1..12 conditions")
    out = {}
    for key, item in value.items():
        out[_nonempty(key, "scope key", 60)] = _nonempty(item, "scope value", 160)
    return out


def _refs(value) -> list[str]:
    if not isinstance(value, list) or not 1 <= len(value) <= 8 or any(
        not isinstance(v, str) or not v.strip() or len(v) > 240 for v in value
    ):
        raise AgentError("LESSON_PACKET_INVALID", "1..8 existing evidence refs required")
    return value


def premise_fingerprint(premise_id: str, scope: dict) -> str:
    """Exact canonical JSON fingerprint, not a proof of scientific equivalence."""
    premise_id = _nonempty(premise_id, "premise_id", 80)
    scope = _scope(scope)
    canonical = json.dumps({"premise_id": premise_id, "scope": scope},
                           ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compile_declared_lessons(packet: dict) -> dict:
    if not isinstance(packet, dict):
        raise AgentError("LESSON_PACKET_INVALID", "Expected an object")
    entries = packet.get("observations")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 20:
        raise AgentError("LESSON_PACKET_INVALID", "1..20 observations are required")
    items, negatives, positives = [], [], []
    seen = set()
    for observation in entries:
        if not isinstance(observation, dict):
            raise AgentError("LESSON_PACKET_INVALID", "Expected observation objects")
        run_id = _nonempty(observation.get("run_id"), "run_id", 80)
        if run_id in seen:
            raise AgentError("LESSON_PACKET_INVALID", "Duplicate Run ID in input")
        seen.add(run_id)
        outcome = observation.get("outcome")
        if not isinstance(outcome, str) or outcome not in OUTCOMES:
            raise AgentError("LESSON_PACKET_INVALID", "Unsupported outcome class")
        refs = _refs(observation.get("evidence_refs", []))
        item = {
            "run_id": run_id, "outcome_declared": outcome,
            "evidence_refs": refs, "source_verified": False,
            "negative_scientific_evidence": False,
            "positive_scientific_evidence": False,
            "science_record_written": False,
        }
        # Positive as well as negative lessons are scoped only when actual
        # premise and applicability metadata are supplied. Both remain
        # unverified declarations; missing positive scope never becomes a
        # universal success rule.
        scoped = (outcome == "VALID_NEGATIVE"
                  or (outcome == "VALID_POSITIVE"
                      and observation.get("tested_premise_id") is not None
                      and observation.get("scope") is not None))
        if scoped:
            premise = _nonempty(observation.get("tested_premise_id"),
                                "tested_premise_id", 80)
            scope = _scope(observation.get("scope"))
            identity = premise_fingerprint(premise, scope)
            item.update({
                "premise_id": premise, "scope": scope,
                "declared_premise_fingerprint_sha256": identity,
                "scientific_equivalence_verified": False,
            })
            candidate = {
                "premise_id": premise, "scope": scope,
                "validity": outcome, "evidence_refs": refs,
                "fingerprint_sha256": identity,
            }
            if outcome == "VALID_NEGATIVE":
                item["negative_scientific_evidence"] = "DECLARED_NOT_INDEPENDENTLY_VERIFIED"
                negatives.append(candidate)
            else:
                item["positive_scientific_evidence"] = "DECLARED_NOT_INDEPENDENTLY_VERIFIED"
                positives.append(candidate)
        else:
            item["next"] = (
                "FIX_ENGINEERING_OR_EVALUATION_FIRST"
                if outcome in {"ENGINEERING_FAILURE", "INVALID_EXPERIMENT"}
                else "NOT_RUN_IS_NOT_SCIENTIFIC_EVIDENCE"
                if outcome == "NOT_RUN"
                else "POSITIVE_SCOPE_REQUIRED_FOR_TRANSFER"
                if outcome == "VALID_POSITIVE"
                else "REVIEW_ORIGINAL_EVIDENCE_NO_AUTO_SCIENTIFIC_INFERENCE"
            )
        items.append(item)
    return {
        "status": "DECLARED_LESSONS_ONLY", "items": items,
        "candidate_prior_negative_lessons": negatives,
        "candidate_prior_positive_lessons": positives,
        "all_sources_verified": False,
        "semantic_equivalence_verified": False,
        "stop_or_go_authorized": False,
        "automatic_project_stop": False,
        "note": ("Only scoped VALID_NEGATIVE/VALID_POSITIVE declarations yield lesson candidates; "
                 "verify original Run and exact applicability before reuse. "
                 "NOT_RUN, INVALID and INCONCLUSIVE are not evidence of scientific failure."),
    }
