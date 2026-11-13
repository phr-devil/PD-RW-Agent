"""Bounded full-history experiment fingerprint search (secondary evidence only)."""
from __future__ import annotations
from .config import Settings, read_json, under_root
from .evidence import _events, sha256_file
from .schemas import AgentError

FIELDS = ("task_id", "protocol_id", "dataset_version", "evaluator_version",
          "code_sha256", "config_sha256", "sample_ids_hash", "seed")
MAX_CANDIDATES = 500


def check_duplicate_experiment(settings: Settings, project_id: str, spec: dict) -> dict:
    if not isinstance(spec, dict):
        raise AgentError("INVALID_EXPERIMENT_SPEC", "Experiment spec must be an object")
    missing = [k for k in FIELDS if k not in spec or spec[k] is None or spec[k] == ""]
    if missing:
        return {"status": "INSUFFICIENT_FINGERPRINT", "project_id": project_id,
                "missing_fields": missing, "matches": [],
                "recommendation": "DO_NOT_CONCLUDE_DUPLICATE"}
    expected = {k: spec[k] for k in FIELDS}
    if not all(isinstance(v, (str, int)) and not isinstance(v, bool)
               for v in expected.values()):
        raise AgentError("INVALID_EXPERIMENT_SPEC",
                         "Fingerprint fields must be scalar text or integer")
    root, _, _ = settings.project_paths(project_id)
    events = _events(root)
    matches = []
    checked = 0
    comparable = 0
    unverifiable = 0
    total_candidates = sum(
        1 for e in events if e.get("kind") == "run"
        and e.get("split") in {"dev", "validation"}
        and e.get("task_id") == str(spec["task_id"])
    )
    for entry in reversed(events):
        if (entry.get("kind") != "run" or
                entry.get("split") not in {"dev", "validation"} or
                entry.get("task_id") != str(spec["task_id"])):
            continue
        if checked >= MAX_CANDIDATES:
            break
        checked += 1
        path_ref = entry.get("artifact_path")
        if not isinstance(path_ref, str):
            unverifiable += 1
            continue
        try:
            path = under_root(root, path_ref, must_exist=True)
            obj = read_json(path, limit=2 * 1024 * 1024)
        except (AgentError, OSError, ValueError):
            unverifiable += 1
            continue
        if (obj.get("run_id") != entry.get("artifact_id") or
            obj.get("task_id") != entry.get("task_id") or
            obj.get("split") != entry.get("split") or
            obj.get("status") != entry.get("status")):
            unverifiable += 1
            continue
        stored = obj.get("experiment_fingerprint")
        if not isinstance(stored, dict) or any(k not in stored for k in FIELDS):
            unverifiable += 1
            continue
        comparable += 1
        if all(stored[k] == expected[k] for k in FIELDS):
            if (not isinstance(entry.get("artifact_sha256"), str) or
                    sha256_file(path) != entry["artifact_sha256"]):
                unverifiable += 1
                continue
            matches.append({"run_id": entry["artifact_id"], "artifact": str(path),
                            "status_declared": entry["status"]})
    exhaustive = checked == total_candidates
    status = ("DECLARED_DUPLICATE_CANDIDATE" if matches else
              "SEARCH_INCOMPLETE" if not exhaustive else
              "UNVERIFIABLE_HISTORY" if unverifiable else
              "NO_MATCH_WITHIN_INDEX" if comparable else "NOT_COMPARABLE")
    return {
        "status": status, "project_id": project_id, "matches": matches[:5],
        "checked_comparable_runs": comparable,
        "searched_recent_indexed_runs": checked,
        "total_indexed_candidates": total_candidates,
        "search_exhaustive": exhaustive,
        "unverifiable_candidates": unverifiable,
        "recommendation": "VERIFY_PROVENANCE_AND_ORIGINAL_RUN_BEFORE_REUSE" if matches
                          else "NO_PROOF_OF_UNIQUENESS",
        "scientific_equivalence_verified": False,
        "ledger_chain_verified": False,
        "sealed_access": "NOT_ATTEMPTED",
    }
