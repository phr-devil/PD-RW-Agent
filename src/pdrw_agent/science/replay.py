"""Frozen-history A/B/C comparison contracts; no live Agent result is invented.

These structural validators guard against a few common replay mistakes.
They CANNOT prove content has no future leakage or that a decision is sound.
"""
from __future__ import annotations
import hashlib
import random
from datetime import datetime
from pathlib import Path
from ..schemas import AgentError

ARMS = ("A", "B", "C")
REQUIRED = (
    "ROUTE", "EVIDENCE_USED", "NEXT_ACTION", "AUTH",
    "DECISION_SCOPE", "CLAIM_BOUNDARY", "COST_CAP",
    "EXPECTED_DECISION_CHANGE",
)
PROTECTED = {"sealed", "holdout", "confirmation"}
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024


def _relative(root: Path, ref: str) -> Path:
    if not isinstance(ref, str) or not ref or Path(ref).is_absolute():
        raise AgentError("REPLAY_PATH_INVALID", "A relative frozen source path is required")
    absolute_root = root.resolve()
    target = (absolute_root / ref).resolve()
    if absolute_root not in target.parents:
        raise AgentError("REPLAY_PATH_INVALID", "Frozen source cannot escape fixture root")
    if any(any(partial in part.casefold() for partial in PROTECTED)
           for part in target.relative_to(absolute_root).parts):
        raise AgentError("REPLAY_PROTECTED_SOURCE", "No SEALED/holdout/confirmation source is allowed")
    return target


def validate_case(root: Path, manifest: dict) -> dict:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise AgentError("REPLAY_SCHEMA_INVALID", "Expected replay schema_version=1")
    case_id = manifest.get("case_id")
    if not isinstance(case_id, str) or not 1 <= len(case_id) <= 80:
        raise AgentError("REPLAY_SCHEMA_INVALID", "case_id required")
    frozen_at = manifest.get("frozen_at")
    try:
        dt = datetime.fromisoformat(frozen_at)
        if dt.tzinfo is None:
            raise ValueError("timezone required")
    except (ValueError, TypeError):
        raise AgentError("REPLAY_SCHEMA_INVALID", "frozen_at requires ISO timestamp with timezone")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not 1 <= len(sources) <= 20:
        raise AgentError("REPLAY_SCHEMA_INVALID", "1..20 frozen sources required")
    declared = set()
    verified = []
    errors = []
    for item in sources:
        if not isinstance(item, dict):
            raise AgentError("REPLAY_SCHEMA_INVALID", "Every source must be a JSON object")
        ref, digest = item.get("ref"), item.get("sha256")
        if not isinstance(ref, str) or ref in declared:
            raise AgentError("REPLAY_SCHEMA_INVALID", "Source reference must be unique")
        if not isinstance(digest, str) or len(digest) != 64 or any(
            x not in "0123456789abcdefABCDEF" for x in digest
        ):
            raise AgentError("REPLAY_SCHEMA_INVALID", "SHA-256 must be 64 hex characters")
        path = _relative(root, ref)
        declared.add(ref)
        if not path.is_file() or path.stat().st_size > MAX_SNAPSHOT_BYTES:
            errors.append(ref)
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual.casefold() != digest.casefold():
            errors.append(ref)
            continue
        verified.append(ref)
    allowed = manifest.get("allowed_evidence_refs")
    if not isinstance(allowed, list) or not allowed or len(allowed) > 20 or any(
        not isinstance(ref, str) or ref not in declared for ref in allowed
    ):
        raise AgentError("REPLAY_SCHEMA_INVALID", "Allowed evidence refs must point to frozen sources")
    if len(set(allowed)) != len(allowed):
        raise AgentError("REPLAY_SCHEMA_INVALID", "Evidence references must be unique")
    status = "STRUCTURAL_SNAPSHOT_VERIFIED" if not errors else "NOT_REPLAYABLE"
    return {
        "status": status, "case_id": case_id,
        "verified_source_refs": verified,
        "missing_or_changed_source_refs": errors,
        "allowed_evidence_refs": allowed,
        "historical_fidelity_verified": False,
        "permissions_verified": False,
        "future_information_leakage_excluded": False,
        "real_agent_behavior_measured": False,
    }


def blind_responses(root: Path, manifest: dict, responses: dict, seed: int) -> dict:
    validated = validate_case(root, manifest)
    if validated["status"] != "STRUCTURAL_SNAPSHOT_VERIFIED":
        raise AgentError("REPLAY_NOT_READY", "Frozen source files are missing or modified")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise AgentError("REPLAY_SCHEMA_INVALID", "Provide a fixed integer blind seed")
    if not isinstance(responses, dict) or set(responses) != set(ARMS):
        raise AgentError("REPLAY_SCHEMA_INVALID", "Require one response each from A, B and C")
    sanitized = {}
    allowed = set(validated["allowed_evidence_refs"])
    for arm, response in responses.items():
        if not isinstance(response, dict) or set(response) != set(REQUIRED):
            raise AgentError("REPLAY_RESPONSE_INVALID", "Responses must use exact PD-RW replay fields")
        refs = response["EVIDENCE_USED"]
        if not isinstance(refs, list) or len(refs) > 20 or any(
            not isinstance(ref, str) or ref not in allowed for ref in refs
        ):
            raise AgentError("REPLAY_EVIDENCE_OUT_OF_FREEZE", "Evidence outside frozen allowlist")
        if any(not isinstance(response[field], str) or not response[field].strip()
               or len(response[field]) > 2400
               for field in REQUIRED if field != "EVIDENCE_USED"):
            raise AgentError("REPLAY_RESPONSE_INVALID", "Response text must be nonempty and bounded")
        sanitized[arm] = {key: response[key] for key in REQUIRED}
    shuffled = list(ARMS)
    random.Random(seed).shuffle(shuffled)
    mapping = dict(zip(("X", "Y", "Z"), shuffled))
    packet = {
        "case_id": validated["case_id"],
        "review_status": "AWAITING_INDEPENDENT_BLIND_REVIEW",
        "responses": {blind_id: sanitized[arm] for blind_id, arm in mapping.items()},
        "warnings": [
            "Blinding removes arm metadata but cannot remove identities embedded in prose",
            "Future leakage, original permissions and scientific claims require human review",
            "Synthetic/unit test PASS is not empirical WorkBuddy improvement",
        ],
    }
    return {
        "review_packet": packet,
        "private_unblinding_key": mapping,
        "structural_validation": validated,
    }
