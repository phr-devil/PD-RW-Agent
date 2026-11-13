"""Bounded restoration from existing project snapshots, never a second memory store."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path
from .config import Settings, read_json
from .schemas import AgentError

MD_KEYS = ("PROJECT_ID", "ACTIVE_TASK", "NEXT", "BEST_VALID_RUN", "HOLDOUT", "RESEARCH_RECORD_REF",
           "PAPER_BLUEPRINT_REF", "NEXT_ACTION_OWNER", "MANUSCRIPT_WRITE_AUTH",
           "WORKFLOW", "USER_SCOPE")
JSON_KEYS = ("schema_version", "project_id", "active_task_id",
             "latest_valid_run_id", "last_event_id")

def rule_commit(root: Path) -> str | None:
    try:
        p = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
                           text=True, capture_output=True, timeout=5, check=False)
        return p.stdout.strip() if p.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None

def snapshot_head(path: Path) -> str | None:
    if not path.is_file():
        return None
    # Historic projects use both section 0 and "1. 当前状态快照".
    # An excerpt is advisory, never proof of machine STATE or Run validity.
    with path.open(encoding="utf-8-sig", errors="replace") as fp:
        data = fp.read(36_000)
    headers = list(re.finditer(r"(?m)^##\s+\d+[.、\s]", data))
    selected = next((h for h in headers if
        re.match(r"##\s+0[.、\s]", h.group(0)) or
        re.match(r"##\s+1[.、\s]*(?:当前状态快照|状态快照|Current(?: State)? Snapshot)",
                 data[h.start():h.start()+80], re.I)), None)
    if not selected:
        return None
    end = next((h.start() for h in headers if h.start() > selected.start()), len(data))
    return data[selected.start():end][:2600]

def get_project_context(settings: Settings, project_id: str) -> dict:
    root, item, paths = settings.project_paths(project_id)
    state_path = paths["state"]
    state: dict = {}
    if state_path.is_file():
        if state_path.suffix.lower() == ".json":
            obj = read_json(state_path, limit=2 * 1024 * 1024)
            state = {k: obj[k] for k in JSON_KEYS if k in obj}
            if isinstance(obj.get("evidence_refs"), list):
                state["evidence_count_declared"] = len(obj["evidence_refs"])
        else:
            with state_path.open(encoding="utf-8-sig", errors="replace") as fp:
                content = fp.read(32_000)
            for line in content.splitlines():
                line = line.strip().removeprefix("- ").strip()
                for key in MD_KEYS:
                    if line.startswith(key + ":"):
                        state[key] = line[len(key) + 1:].strip()[:280]
    expected = item.get("expected_state_project_id")
    if expected is not None and not isinstance(expected, str):
        raise AgentError("INVALID_EXPECTED_ID", "Expected state ID must be text")
    actual = state.get("project_id") or state.get("PROJECT_ID")
    mismatch = bool(expected and actual and expected != actual)
    paths_public = {k: {"path": str(p), "exists": p.is_file()} for k, p in paths.items()}
    missing = [k for k in ("state", "research_record") if not paths[k].is_file()]
    excerpt = snapshot_head(paths["research_record"])
    return {
        "status": "IDENTITY_CONFLICT" if mismatch else
                  "INCOMPLETE_CONTEXT" if missing or excerpt is None else "SOURCE_REVIEW_REQUIRED",
        "project_id": project_id,
        "identity": "DECLARED_ID_MISMATCH" if mismatch else "UNVERIFIED_REQUIRE_RAW_SOURCE",
        "workflow_commit_local_only": rule_commit(settings.workflow_root),
        "rule_freshness": "REMOTE_NOT_CHECKED",
        "project_root": str(root),
        "paths": paths_public,
        "state_index": state,
        "snapshot_excerpt": excerpt,
        "missing": missing,
        "state_integrity": "NOT_VERIFIED_AGAINST_EVENTS",
        "original_user_authorization": "UNVERIFIED",
        "scientific_evidence": "NOT_VERIFIED",
        "next": "CHECK_PROJECT_IDENTITY_ORIGINAL_AUTH_AND_RELEVANT_RUN",
    }
