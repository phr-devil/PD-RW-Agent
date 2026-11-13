"""Read-only reconstruction of PD-RW STATE.json from existing EVENTS.jsonl.

This is a metadata consistency diagnostic, not a competing event writer.
PD-RW core.state remains the authority. SEALED artifacts are never opened.
"""
from __future__ import annotations

from ..config import Settings, read_json, under_root
from ..evidence import _events
from ..schemas import AgentError

MAX_EVENTS = 5000
SHA_LENGTH = 64


def reconstruct_project_history(settings: Settings, project_id: str) -> dict:
    root, item = settings.project(project_id)
    state_path = under_root(root, "STATE.json")
    events_path = under_root(root, "EVENTS.jsonl")
    missing = [name for name, path in
               (("STATE.json", state_path), ("EVENTS.jsonl", events_path))
               if not path.is_file()]
    base = {
        "project_id": project_id, "project_root": str(root),
        "original_authorization_verified": False,
        "scientific_claims_verified": False,
        "event_artifacts_verified": False,
        "sealed_artifacts_opened": False,
        "execution_authorized": False,
        "source": "PD_RW_STATE_EVENTS_METADATA_ONLY",
    }
    if missing:
        return {**base, "status": "HISTORY_SOURCES_MISSING", "missing": missing,
                "event_chain_valid": False, "state_matches_events": False}
    try:
        state = read_json(state_path, limit=2 * 1024 * 1024)
        events = _events(root)
    except (AgentError, UnicodeError, OSError) as exc:
        return {**base, "status": "HISTORY_SOURCE_INVALID",
                "reason": getattr(exc, "code", "READ_ERROR"),
                "event_chain_valid": False, "state_matches_events": False}
    if len(events) > MAX_EVENTS:
        return {**base, "status": "HISTORY_LIMIT_REACHED",
                "event_count": len(events),
                "event_chain_valid": False, "state_matches_events": False}
    if state.get("schema_version") != "1.4" or not isinstance(state.get("project_id"), str):
        return {**base, "status": "STATE_SCHEMA_INVALID",
                "event_chain_valid": False, "state_matches_events": False}
    expected_id = item.get("expected_state_project_id")
    if expected_id and state["project_id"] != expected_id:
        return {**base, "status": "STATE_PROJECT_ID_CONFLICT",
                "event_chain_valid": False, "state_matches_events": False}
    reconstructed = {
        "schema_version": "1.4", "project_id": state["project_id"],
        "active_task_id": None, "latest_valid_run_id": None,
        "last_event_id": None, "evidence_refs": [],
    }
    previous = None
    identifiers: set[str] = set()
    run_identifiers: set[str] = set()
    protected_events = 0
    for index, event in enumerate(events, 1):
        eid = event.get("event_id")
        kind = event.get("kind")
        if (not isinstance(eid, str) or not eid or eid in identifiers
                or event.get("prev_event_id") != previous
                or event.get("project_id") != state["project_id"]
                or kind not in {"note", "run", "claim"}):
            return {**base, "status": "EVENT_CHAIN_INVALID",
                    "first_invalid_line": index,
                    "event_chain_valid": False, "state_matches_events": False}
        identifiers.add(eid)
        previous = eid
        reconstructed["last_event_id"] = eid
        if kind == "note":
            continue
        aid = event.get("artifact_id")
        ref = event.get("artifact_path")
        digest = event.get("artifact_sha256")
        task_id = event.get("task_id")
        if (not all(isinstance(v, str) and v for v in (aid, ref, task_id))
                or not isinstance(digest, str) or len(digest) != SHA_LENGTH
                or any(c not in "0123456789abcdefABCDEF" for c in digest)
                or kind == "run" and (event.get("split") not in
                                      {"dev", "validation", "sealed"}
                                      or event.get("status") not in
                                      {"VALID", "INVALID", "INCONCLUSIVE", "NOT_RUN"})
                or kind == "claim" and event.get("status") not in
                   {"HYPOTHESIZED", "EVIDENCE_CANDIDATE", "SUPPORTED", "CONFIRMED"}
                or kind == "run" and aid in run_identifiers):
            return {**base, "status": "EVENT_METADATA_INVALID",
                    "first_invalid_line": index,
                    "event_chain_valid": False, "state_matches_events": False}
        if kind == "run":
            run_identifiers.add(aid)
            if event["split"] == "sealed":
                protected_events += 1
        reconstructed["evidence_refs"].append({
            "kind": kind, "id": aid, "path": ref, "sha256": digest
        })
        reconstructed["active_task_id"] = task_id
        if kind == "run" and event["status"] == "VALID" and event["split"] != "sealed":
            reconstructed["latest_valid_run_id"] = aid

    differences = sorted(k for k in set(state) | set(reconstructed)
                         if state.get(k) != reconstructed.get(k))
    consistent = not differences
    return {
        **base,
        "status": ("METADATA_CHAIN_MATCHED_ONLY" if consistent
                   else "STATE_EVENTS_MISMATCH"),
        "event_count": len(events),
        "protected_event_count_metadata_only": protected_events,
        "event_chain_valid": True,
        "state_matches_events": consistent,
        "differing_state_fields": differences,
        "reconstructed_index": {
            "project_id": reconstructed["project_id"],
            "last_event_id": reconstructed["last_event_id"],
            "active_task_id": reconstructed["active_task_id"],
            "latest_valid_run_id": reconstructed["latest_valid_run_id"],
            "evidence_count": len(reconstructed["evidence_refs"]),
        },
        "note": ("Exact metadata parity is not proof of Run bytes, original "
                 "permissions, scientific validity or SEALED isolation."),
    }
