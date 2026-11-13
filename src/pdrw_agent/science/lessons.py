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
    "VALID_NEGATIVE", "VALID_POSITIVE",
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
    items, negatives = [], []
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
            "science_record_written": False,
        }
        if outcome == "VALID_NEGATIVE":
            premise = _nonempty(observation.get("tested_premise_id"),
                                "tested_premise_id", 80)
            scope = _scope(observation.get("scope"))
            identity = premise_fingerprint(premise, scope)
            item.update({
                "premise_id": premise, "scope": scope,
                "declared_premise_fingerprint_sha256": identity,
                "negative_scientific_evidence": "DECLARED_NOT_INDEPENDENTLY_VERIFIED",
                "scientific_equivalence_verified": False,
            })
            negatives.append({
                "premise_id": premise, "scope": scope,
                "validity": "VALID_NEGATIVE", "evidence_refs": refs,
                "fingerprint_sha256": identity,
            })
        else:
            item["next"] = ("FIX_ENGINEERING_OR_EVALUATION_FIRST"
                            if outcome in {"ENGINEERING_FAILURE", "INVALID_EXPERIMENT"}
                            else "REVIEW_ORIGINAL_EVIDENCE_NO_AUTO_SCIENTIFIC_INFERENCE")
        items.append(item)
    return {
        "status": "DECLARED_LESSONS_ONLY", "items": items,
        "candidate_prior_negative_lessons": negatives,
        "all_sources_verified": False,
        "semantic_equivalence_verified": False,
        "stop_or_go_authorized": False,
        "note": "Only VALID_NEGATIVE declarations yield candidates; verify original Run validity and scope before use.",
    }
