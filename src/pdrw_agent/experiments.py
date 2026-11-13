"""Conservative repeat check from declared metadata, without accessing SEALED."""
from __future__ import annotations
import json
from .config import Settings, read_json, under_root
from .evidence import indexed_runs
from .schemas import AgentError

FIELDS = ("task_id", "protocol_id", "dataset_version", "evaluator_version",
          "code_sha256", "config_sha256", "sample_ids_hash", "seed")

def check_duplicate_experiment(settings: Settings, project_id: str, spec: dict) -> dict:
    if not isinstance(spec, dict):
        raise AgentError("INVALID_EXPERIMENT_SPEC", "Experiment spec must be an object")
    missing = [f for f in FIELDS if f not in spec or spec[f] is None or spec[f] == ""]
    if missing:
        return {"status": "INSUFFICIENT_FINGERPRINT", "project_id": project_id,
                "missing_fields": missing, "matches": [],
                "recommendation": "DO_NOT_CONCLUDE_DUPLICATE"}
    normalized = {k: spec[k] for k in FIELDS}
    if not all(isinstance(v, (str, int)) and not isinstance(v, bool) for v in normalized.values()):
        raise AgentError("INVALID_EXPERIMENT_SPEC", "Fingerprint fields must be scalar text or integer")
    root, candidates = indexed_runs(settings, project_id, task_id=str(spec["task_id"]), limit=10)
    comparable = 0
    hits = []
    for item in candidates:
        if (not item["artifact_exists"]
                or item["artifact_sha256_status"] != "MATCH"):
            continue
        try:
            path = under_root(root, str(__import__("pathlib").Path(item["artifact"]).relative_to(root)))
            obj = read_json(path, limit=2 * 1024 * 1024)
        except (AgentError, ValueError):
            continue
        # Only explicit stored fingerprint metadata can be compared; never guess.
        stored = obj.get("experiment_fingerprint")
        if not isinstance(stored, dict) or any(k not in stored for k in FIELDS):
            continue
        comparable += 1
        if all(stored[k] == normalized[k] for k in FIELDS):
            hits.append({"run_id": item["run_id"], "artifact": item["artifact"],
                         "status_declared": item["status_declared"]})
    return {"status": "DECLARED_DUPLICATE_CANDIDATE" if hits
            else "NO_MATCH_WITHIN_INDEX" if comparable else "NOT_COMPARABLE",
            "project_id": project_id, "matches": hits[:5],
            "checked_comparable_runs": comparable,
            "searched_recent_indexed_runs": len(candidates),
            "recommendation": "VERIFY_PROVENANCE_AND_ORIGINAL_RUN_BEFORE_REUSE" if hits
                              else "NO_PROOF_OF_UNIQUENESS",
            "scientific_equivalence_verified": False,
            "sealed_access": "NOT_ATTEMPTED"}
