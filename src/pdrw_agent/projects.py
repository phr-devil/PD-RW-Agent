"""Bounded restoration from existing project snapshots, never a second memory store."""
from __future__ import annotations
import re
import subprocess
from pathlib import Path
from .config import Settings, read_json
from .schemas import AgentError

MD_KEYS = ("PROJECT_ID", "ACTIVE_TASK", "NEXT", "BEST_VALID_RUN", "HOLDOUT", "RESEARCH_RECORD_REF",
           "PAPER_BLUEPRINT_REF", "NEXT_ACTION_OWNER", "MANUSCRIPT_WRITE_AUTH",
           "WORKFLOW", "USER_SCOPE", "PROJECT_ID")
JSON_KEYS = ("schema_version", "project_id", "active_task_id",
             "latest_valid_run_id", "last_event_id")

# Controlled Markdown identity variants. ``PROJECT_ID`` may be written as an
# ordinary KEY: field, as ``PROJECT_ID = 44``, or wrapped in backticks/bold
# inside a Chinese "项目身份" line (the format used by projects 42/43/44).
# Only a bounded ASCII identifier is accepted; prose mentioning other project
# numbers (e.g. "ws42/43 为不同研究线") must never be read as this project's ID.
_ID_TOKEN = r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}"
_MD_PROJECT_ID = re.compile(
    r"(?<![A-Za-z0-9_])PROJECT_ID\s*(?:=|:|：|＝)\s*[`'\"]?\s*(" + _ID_TOKEN + r")",
    re.IGNORECASE)
_MD_PROJECT_CN = re.compile(
    r"(?:项目身份|项目\s*ID|项目编号|项目标识)\s*[:：]\s*[`'\"]?\s*(" + _ID_TOKEN + r")",
    re.IGNORECASE)
_MAX_IDENTITY_LINES = 40


def markdown_project_id(content: str) -> tuple[str | None, str]:
    """Return (declared_id, basis) for controlled Markdown identity lines.

    basis is one of EXPLICIT_PROJECT_ID / CONTROLLED_CN_VARIANT / ABSENT /
    AMBIGUOUS. Conflicting declarations produce UNKNOWN, never a silent pass.
    """
    found: set[str] = set()
    basis = "ABSENT"
    for raw_line in content.splitlines()[:_MAX_IDENTITY_LINES]:
        # Markdown emphasis/backticks are formatting, not identity characters.
        line = raw_line.replace("**", "").replace("__", "").replace("`", "")
        explicit = _MD_PROJECT_ID.search(line)
        candidate = explicit.group(1) if explicit else None
        line_basis = "EXPLICIT_PROJECT_ID" if explicit else None
        if candidate is None:
            cn = _MD_PROJECT_CN.search(line)
            if cn:
                candidate, line_basis = cn.group(1), "CONTROLLED_CN_VARIANT"
        if candidate is None:
            continue
        found.add(candidate)
        if basis == "ABSENT":
            basis = line_basis or "ABSENT"
    if len(found) > 1:
        return None, "AMBIGUOUS"
    if not found:
        return None, basis
    return next(iter(found)), basis

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
    declared: str | None = None
    basis = "ABSENT"
    if state_path.is_file():
        if state_path.suffix.lower() == ".json":
            obj = read_json(state_path, limit=2 * 1024 * 1024)
            state = {k: obj[k] for k in JSON_KEYS if k in obj}
            if isinstance(obj.get("evidence_refs"), list):
                state["evidence_count_declared"] = len(obj["evidence_refs"])
            raw = obj.get("project_id")
            if isinstance(raw, str) and raw.strip():
                declared, basis = raw.strip(), "STATE_JSON"
        else:
            with state_path.open(encoding="utf-8-sig", errors="replace") as fp:
                content = fp.read(32_000)
            for line in content.splitlines():
                line = line.strip().removeprefix("- ").strip()
                for key in MD_KEYS:
                    if line.startswith(key + ":"):
                        state[key] = line[len(key) + 1:].strip()[:280]
            declared, basis = markdown_project_id(content)
            if declared:
                state["project_id"] = declared
    expected = item.get("expected_state_project_id")
    if expected is not None and not isinstance(expected, str):
        raise AgentError("INVALID_EXPECTED_ID", "Expected state ID must be text")
    # Both declaration sources count: the parsed STATE field/JSON key and the
    # Markdown identity line. Ambiguous Markdown declarations are neither
    # evidence of a match nor of a conflict, so they stay UNKNOWN.
    ambiguous = basis == "AMBIGUOUS"
    actual = None if ambiguous else (
        state.get("project_id") or state.get("PROJECT_ID") or declared)
    mismatch = bool(not ambiguous and expected and actual and expected != actual)
    # Three explicit identity states: conflict, unknown, or declared match.
    # UNKNOWN must never be silently promoted to a verified continuation.
    if ambiguous:
        identity = "UNKNOWN"
    elif mismatch:
        identity = "DECLARED_ID_MISMATCH"
    elif expected and actual and expected == actual:
        identity = "DECLARED_ID_MATCH"
    else:
        identity = "UNKNOWN"
    paths_public = {k: {"path": str(p), "exists": p.is_file()} for k, p in paths.items()}
    missing = [k for k in ("state", "research_record") if not paths[k].is_file()]
    excerpt = snapshot_head(paths["research_record"])
    if mismatch:
        status = "IDENTITY_CONFLICT"
    elif identity == "UNKNOWN" and expected:
        # The operator pinned an expected ID but STATE declares none. Do not
        # allow an unrelated project's Run/Claim to be resumed into this entry.
        status = "IDENTITY_UNKNOWN"
    else:
        status = ("INCOMPLETE_CONTEXT" if missing or excerpt is None
                  else "SOURCE_REVIEW_REQUIRED")
    return {
        "status": status,
        "project_id": project_id,
        "identity": identity,
        "identity_basis": basis,
        "expected_state_project_id": expected,
        "declared_state_project_id": declared,
        "identity_verified": False,
        "cross_project_run_or_claim_reuse": "NOT_ATTESTED",
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
        "next": ("VERIFY_PROJECT_IDENTITY_FROM_ORIGINAL_STATE" if status == "IDENTITY_UNKNOWN"
                 else "CHECK_PROJECT_IDENTITY_ORIGINAL_AUTH_AND_RELEVANT_RUN"),
    }
