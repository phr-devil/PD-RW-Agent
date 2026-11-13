"""Source-bound, read-only audit of one registered DEV/VAL Run.

Checks the PD-RW original Run contract via the authoritative core, event
metadata and SHA-256. No raw SEALED read, execution, permission or science claim.
"""
from __future__ import annotations

from ..config import Settings, read_json, under_root
from ..evidence import _events, sha256_file
from ..runtime.history import reconstruct_project_history
from ..runtime.registration import _run_contract
from ..schemas import AgentError

MAX_LINKS = 12
MAX_LINK_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 192 * 1024 * 1024


def verify_run_evidence(settings: Settings, project_id: str, run_id: str) -> dict:
    if not isinstance(run_id, str) or not 1 <= len(run_id) <= 100:
        raise AgentError("RUN_ID_INVALID", "Run ID must be bounded text")
    root, _ = settings.project(project_id)
    base = {
        "project_id": project_id, "run_id": run_id,
        "scientific_validity_verified": False,
        "original_authorization_verified": False,
        "sealed_access": "NOT_ATTEMPTED", "execution_authorized": False,
        "scope": "ORIGINAL_RUN_BYTES_AND_STRUCTURAL_CONTRACT_ONLY",
    }
    history = reconstruct_project_history(settings, project_id)
    if history["status"] != "METADATA_CHAIN_MATCHED_ONLY":
        return {**base, "status": "RUN_HISTORY_NOT_ATTESTABLE",
                "history_status": history["status"]}
    candidates = [e for e in _events(root)
                  if e.get("kind") == "run" and e.get("artifact_id") == run_id]
    if not candidates:
        return {**base, "status": "RUN_NOT_REGISTERED"}
    if len(candidates) != 1:
        return {**base, "status": "RUN_ID_CONFLICT"}
    event = candidates[0]
    if event.get("split") not in {"dev", "validation"}:
        return {**base, "status": "PROTECTED_RUN_NOT_OPENED"}
    try:
        source = under_root(root, event["artifact_path"], must_exist=True)
    except (AgentError, KeyError, OSError) as exc:
        return {**base, "status": "RUN_SOURCE_UNAVAILABLE",
                "reason": getattr(exc, "code", "INVALID_EVENT_PATH")}
    if source.stat().st_size > 2 * 1024 * 1024:
        return {**base, "status": "RUN_SOURCE_OVERSIZE"}
    if sha256_file(source).casefold() != event["artifact_sha256"].casefold():
        return {**base, "status": "RUN_HASH_MISMATCH"}
    try:
        obj = read_json(source, limit=2 * 1024 * 1024)
    except AgentError as exc:
        return {**base, "status": "RUN_JSON_INVALID", "reason": exc.code}
    if any(obj.get(key) != expected for key, expected in
           (("run_id", run_id), ("task_id", event["task_id"]),
            ("status", event["status"]), ("split", event["split"]))):
        return {**base, "status": "RUN_EVENT_METADATA_MISMATCH"}
    contract, ok = _run_contract(settings, obj)
    if not ok:
        return {**base, "status": "RUN_CONTRACT_UNAVAILABLE",
                "reason": contract.get("error", "BACKEND_UNAVAILABLE")}
    if not contract.get("valid"):
        return {**base, "status": "RUN_CONTRACT_INVALID",
                "reason": contract.get("reason", "INVALID")}
    status_declared = obj["status"]
    result = {**base, "run_status_declared": status_declared,
              "task_id_declared": obj["task_id"],
              "protocol_id_declared": obj["protocol_id"],
              "split_declared": obj["split"],
              "run_sha256_match": True,
              "original_contract_valid": True}
    if status_declared != "VALID":
        return {**result, "status": "RUN_SOURCE_MATCHED_ONLY",
                "note": "INVALID, INCONCLUSIVE and NOT_RUN are not scientific negatives"}
    references = obj.get("artifact_refs", {})
    if not isinstance(references, dict):
        return {**result, "status": "RUN_CONTRACT_INVALID"}
    paths = list(dict.fromkeys(references.values()))
    if obj.get("task_spec_ref"):
        paths.append(obj["task_spec_ref"])
    paths = list(dict.fromkeys(paths))
    if len(paths) > MAX_LINKS:
        return {**result, "status": "RUN_INSPECTION_LIMIT_REACHED"}
    links = event.get("linked_sha256")
    if not isinstance(links, dict):
        return {**result, "status": "RUN_LINK_HASHES_MISSING",
                "link_count": len(paths)}
    # Unlisted or protected linked paths must not be opened.
    if set(links) != set(paths):
        return {**result, "status": "RUN_LINK_REFERENCE_CONFLICT",
                "link_count": len(paths)}
    checked = 0
    bytes_checked = 0
    for rel in paths:
        if not isinstance(rel, str):
            return {**result, "status": "RUN_LINK_REFERENCE_INVALID"}
        try:
            path = under_root(root, rel, must_exist=True)
        except (AgentError, OSError):
            return {**result, "status": "RUN_LINK_UNAVAILABLE_OR_PROTECTED"}
        size = path.stat().st_size
        if size > MAX_LINK_BYTES or bytes_checked + size > MAX_TOTAL_BYTES:
            return {**result, "status": "RUN_INSPECTION_LIMIT_REACHED",
                    "links_checked": checked}
        declared = links[rel]
        if (not isinstance(declared, str) or len(declared) != 64
                or any(c not in "0123456789abcdefABCDEF" for c in declared)):
            return {**result, "status": "RUN_LINK_HASH_INVALID"}
        if sha256_file(path).casefold() != declared.casefold():
            return {**result, "status": "RUN_LINK_HASH_MISMATCH"}
        checked += 1
        bytes_checked += size
    return {**result, "status": "RUN_BYTES_MATCHED_ONLY",
            "links_checked": checked,
            "linked_hash_coverage": "ALL_DECLARED_REFERENCES_CHECKED",
            "note": ("Bytes/contract verified; experiment independence, legal "
                     "inputs and scientific conclusions remain unverified.")}
