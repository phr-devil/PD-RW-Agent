"""Only read already indexed machine Run metadata; never scan SEALED data directories."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from .config import Settings, under_root
from .schemas import AgentError

MAX_LEDGER_BYTES = 12 * 1024 * 1024

def _events(root: Path) -> list[dict]:
    file = under_root(root, "EVENTS.jsonl")
    if not file.is_file():
        return []
    if file.stat().st_size > MAX_LEDGER_BYTES:
        raise AgentError("LEDGER_TOO_LARGE", "Explicit indexing/pagination required for large event ledger")
    items = []
    with file.open(encoding="utf-8", errors="replace") as fp:
        for n, line in enumerate(fp, 1):
            try:
                entry = json.loads(line)
            except ValueError as exc:
                raise AgentError("LEDGER_INVALID", f"Malformed event at line {n}") from exc
            if not isinstance(entry, dict):
                raise AgentError("LEDGER_INVALID", "Expected JSON objects in event ledger")
            items.append(entry)
    return items

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()

def indexed_runs(settings: Settings, project_id: str, task_id: str = "",
                 run_id: str = "", limit: int = 6) -> tuple[Path, list[dict]]:
    root, _, _ = settings.project_paths(project_id)
    results = []
    for entry in reversed(_events(root)):
        if (entry.get("kind") != "run"
                or entry.get("split") not in {"dev", "validation"}):
            continue
        if task_id and entry.get("task_id") != task_id:
            continue
        if run_id and entry.get("artifact_id") != run_id:
            continue
        artifact_ref = entry.get("artifact_path")
        if not isinstance(artifact_ref, str):
            continue
        try:
            path = under_root(root, artifact_ref)
        except AgentError:
            continue
        if any(any(tag in part.casefold() for tag in ("sealed", "holdout", "confirmation"))
               for part in path.relative_to(root).parts):
            continue
        exists = path.is_file()
        hash_status = "MISSING"
        hash_detail = "ARTIFACT_MISSING"
        if exists and path.stat().st_size <= 2 * 1024 * 1024:
            declared = entry.get("artifact_sha256")
            if not isinstance(declared, str) or not declared:
                hash_status = "MISMATCH_OR_UNKNOWN"  # Legacy field retained.
                hash_detail = "HASH_UNKNOWN"
            elif sha256_file(path) == declared:
                hash_status = "MATCH"
                hash_detail = "HASH_MATCH"
            else:
                hash_status = "MISMATCH_OR_UNKNOWN"
                hash_detail = "HASH_MISMATCH"
        elif exists:
            hash_status = "NOT_CHECKED_OVERSIZE"
            hash_detail = "NOT_CHECKED_OVERSIZE"
        results.append({"run_id": entry.get("artifact_id"), "task_id": entry.get("task_id"),
                        "status_declared": entry.get("status"), "split_declared": entry.get("split"),
                        "artifact": str(path), "artifact_exists": exists,
                        "artifact_sha256_status": hash_status,
                        "hash_detail": hash_detail})
        if len(results) >= max(1, min(limit, 10)):
            break
    return root, results

def find_experiment_evidence(settings: Settings, project_id: str,
                             task_id: str = "", run_id: str = "", limit: int = 6) -> dict:
    root, entries = indexed_runs(settings, project_id, task_id, run_id, limit)
    return {"status": "INDEXED_RUNS_FOUND" if entries else "NO_INDEXED_DEV_RUN",
            "project_id": project_id, "project_root": str(root),
            "matches": entries, "source": "Existing EVENTS.jsonl, not disk search",
            "run_validity_verified": False,
            "sealed_access": "NOT_ATTEMPTED",
            "next": "CHECK_ORIGINAL_RUN_PROTOCOL_AND_SPLIT_BEFORE_SCIENTIFIC_REUSE"}
