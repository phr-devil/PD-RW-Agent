"""Source compatibility assessment for historical and machine-indexed projects.

Diagnostic only: no automatic migration, scientific evidence validation,
author permission, or DEV execution. Never reads sealed artifacts.
"""
from __future__ import annotations

import re

from ..config import Settings, read_json, under_root
from ..projects import get_project_context
from ..schemas import AgentError
from .history import reconstruct_project_history

_MD_ID = re.compile(r"(?m)^\s*(?:-\s*)?PROJECT_ID\s*:\s*([^\s#]+)")


def inspect_project_readiness(settings: Settings, project_id: str) -> dict:
    root, item = settings.project(project_id)
    try:
        context = get_project_context(settings, project_id)
    except (AgentError, OSError, UnicodeError):
        # Corrupt STATE.json must be diagnosed, never silently reclassified as
        # an eligible legacy project or an authenticated project identity.
        context = {"status": "INCOMPLETE_CONTEXT"}
    state_json = under_root(root, "STATE.json")
    state_md = under_root(root, "STATE.md")
    events = under_root(root, "EVENTS.jsonl")
    declared_id = None
    json_id = None
    md_id = None
    if state_json.is_file():
        try:
            json_id = read_json(state_json, limit=2 * 1024 * 1024).get("project_id")
        except (AgentError, OSError, UnicodeError):
            return _result(project_id, "MACHINE_STATE_INVALID", "JSON_STATE_PARSE_FAILED",
                           context, False, state_md.is_file(), events.is_file())
        if not isinstance(json_id, str) or not json_id:
            return _result(project_id, "MACHINE_STATE_INVALID", "JSON_STATE_ID_INVALID",
                           context, False, state_md.is_file(), events.is_file())
    if state_md.is_file():
        # Legacy state metadata is advisory. Only read a bounded text prefix;
        # do not normalize missing fields into inferred author decisions.
        with state_md.open(encoding="utf-8-sig", errors="replace") as handle:
            match = _MD_ID.search(handle.read(32_000))
        md_id = match.group(1) if match else None
    declared_id = item.get("expected_state_project_id")
    if (context["status"] == "IDENTITY_CONFLICT" or
            json_id and declared_id and json_id != declared_id or
            md_id and json_id and md_id != json_id or
            md_id and declared_id and md_id != declared_id):
        return _result(project_id, "STATE_IDENTITY_CONFLICT",
                       "STATE_SOURCE_IDENTITIES_DISAGREE", context,
                       state_json.is_file(), state_md.is_file(), events.is_file())
    if not state_json.is_file():
        return _result(project_id,
                       "LEGACY_READ_ONLY" if state_md.is_file()
                       else "STATE_SOURCE_MISSING",
                       "MACHINE_LEDGER_NOT_CREATED",
                       context, False, state_md.is_file(), events.is_file())
    if not events.is_file():
        return _result(project_id, "MACHINE_LEDGER_INCOMPLETE",
                       "EVENTS_NOT_PRESENT", context, True,
                       state_md.is_file(), False)
    history = reconstruct_project_history(settings, project_id)
    if history["status"] != "METADATA_CHAIN_MATCHED_ONLY":
        return _result(project_id, "MACHINE_LEDGER_CONFLICT",
                       history["status"], context, True,
                       state_md.is_file(), True)
    return _result(project_id, "MACHINE_METADATA_READY",
                   "METADATA_CHAIN_MATCHED_ONLY", context, True,
                   state_md.is_file(), True)


def _result(project_id: str, status: str, reason: str, context: dict,
            machine: bool, legacy: bool, events: bool) -> dict:
    return {
        "status": status, "reason": reason,
        "project_id": project_id,
        "machine_state_present": machine, "legacy_state_present": legacy,
        "events_present": events,
        "source_context_status": context["status"],
        "machine_metadata_consistent": status == "MACHINE_METADATA_READY",
        "historical_read_only_allowed": status in {
            "MACHINE_METADATA_READY", "LEGACY_READ_ONLY", "MACHINE_LEDGER_INCOMPLETE",
            "STATE_SOURCE_MISSING", "MACHINE_LEDGER_CONFLICT",
        },
        "automatic_migration_performed": False,
        "original_authorization_verified": False,
        "original_evidence_verified": False,
        "execution_authorized": False,
        "next": "REVIEW_ORIGINAL_SOURCES_NOT_AUTOMATIC_PROJECT_INITIALIZATION",
    }
