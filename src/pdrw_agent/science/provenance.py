"""Bind declared citation IDs to hash-checked, locally frozen source files.

Byte integrity + source allowlist only; no truth, original authorship, history,
semantic premise equivalence or real operational permission is certified.
"""
from __future__ import annotations

from pathlib import Path
from ..schemas import AgentError
from .replay import validate_case


def proposal_refs(packet: dict) -> list[str]:
    """Collect bounded reference IDs from a prevalidated scientific decision."""
    if not isinstance(packet, dict):
        raise AgentError("SCIENCE_PACKET_INVALID", "Expected a decision object")
    collected: list[str] = []
    collected.extend(packet.get("claim_evidence_refs", []))
    for item in packet.get("probes", []):
        collected.extend(item.get("prediction_evidence_refs", []))
    for item in packet.get("prior_negative_lessons", []):
        collected.extend(item.get("evidence_refs", []))
    for item in packet.get("prechecks", {}).values():
        collected.extend(item.get("evidence_refs", []))
    return list(dict.fromkeys(collected))


def bind_source_refs(root: Path, manifest: dict, references: list[str]) -> dict:
    """Refuse changed/unlisted frozen sources; no source content interpretation."""
    if not isinstance(references, list) or len(references) > 60 or any(
        not isinstance(ref, str) or not ref.strip() or len(ref) > 240
        for ref in references
    ):
        raise AgentError("EVIDENCE_REFS_INVALID", "Expected at most 60 bounded source identifiers")
    case = validate_case(root, manifest)
    if case["status"] != "STRUCTURAL_SNAPSHOT_VERIFIED":
        return {
            "status": "NOT_REPLAYABLE", "case_id": case["case_id"],
            "missing_or_changed_source_refs": case["missing_or_changed_source_refs"],
            "historical_fidelity_verified": False,
            "scientific_claims_verified": False,
        }
    references = list(dict.fromkeys(references))
    allowed = set(case["allowed_evidence_refs"])
    outside = [ref for ref in references if ref not in allowed]
    return {
        "status": "EVIDENCE_OUT_OF_FREEZE" if outside
                  else "SOURCE_BYTES_MATCHED_ONLY" if references
                  else "NO_REFERENCES_DECLARED",
        "case_id": case["case_id"],
        "referenced": references,
        "unlisted_refs": outside,
        "source_content_semantics_verified": False,
        "scientific_claims_verified": False,
        "original_user_authorization": "UNVERIFIED",
        "historical_fidelity_verified": False,
        "future_information_leakage_excluded": False,
        "permission_to_execute": False,
    }


def bind_frozen_evidence(root: Path, manifest: dict, packet: dict) -> dict:
    return bind_source_refs(root, manifest, proposal_refs(packet))
