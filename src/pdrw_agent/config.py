"""Explicit local project registry; no disk-wide search or arbitrary tool paths."""
from __future__ import annotations
import json
import os
from dataclasses import dataclass
from pathlib import Path
from .schemas import AgentError

MAX_CONFIG_BYTES = 128 * 1024

def read_json(path: Path, limit: int = MAX_CONFIG_BYTES) -> dict:
    if not path.is_file() or path.stat().st_size > limit:
        raise AgentError("FILE_MISSING_OR_TOO_LARGE", "Expected a small existing JSON file")
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeError, ValueError) as exc:
        raise AgentError("INVALID_JSON", "Cannot parse JSON") from exc
    if not isinstance(obj, dict):
        raise AgentError("INVALID_JSON", "JSON root must be an object")
    return obj

def under_root(root: Path, value: str, *, must_exist: bool = False,
               protect_data: bool = True) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise AgentError("INVALID_PROJECT_PATH", "Expected a relative project path")
    candidate = (root / value).resolve()
    if candidate != root and root not in candidate.parents:
        raise AgentError("PATH_OUTSIDE_PROJECT", "Mapped path is outside project root")
    # A model/registry must not turn a known holdout subtree into a normal
    # evidence lookup merely by selecting a file path explicitly.
    protected = {"sealed", "holdout", "confirmation"}
    if protect_data and any(any(tag in part.casefold() for tag in protected)
                            for part in candidate.relative_to(root).parts):
        raise AgentError("PROTECTED_PROJECT_PATH", "Protected data subtree is not accessible by this adapter")
    if must_exist and not candidate.is_file():
        raise AgentError("PROJECT_FILE_MISSING", "Mapped file does not exist")
    return candidate

@dataclass(frozen=True)
class Settings:
    workflow_root: Path
    project_map: Path

    @classmethod
    def load(cls, project_map: str | None = None,
             workflow_root: str | None = None) -> "Settings":
        map_text = project_map or os.getenv("PDRW_AGENT_CONFIG")
        rule_text = workflow_root or os.getenv("PDRW_WORKFLOW_ROOT")
        if not map_text or not rule_text:
            raise AgentError("CONFIG_REQUIRED",
                             "Set PDRW_AGENT_CONFIG and PDRW_WORKFLOW_ROOT to local paths")
        mapping = Path(map_text).expanduser().resolve()
        rules = Path(rule_text).expanduser().resolve()
        if not mapping.is_file():
            raise AgentError("CONFIG_MISSING", "Private project map not found")
        if not (rules / "AGENTS.md").is_file() or not (rules / "WORKFLOW.md").is_file():
            raise AgentError("RULE_ROOT_INVALID", "PD-RW rule checkout is missing AGENTS.md/WORKFLOW.md")
        return cls(rules, mapping)

    def project(self, project_id: str) -> tuple[Path, dict]:
        if not isinstance(project_id, str) or not project_id.strip():
            raise AgentError("PROJECT_ID_REQUIRED", "Nonempty project ID is required")
        manifest = read_json(self.project_map)
        if manifest.get("schema_version") != 1 or not isinstance(manifest.get("projects"), dict):
            raise AgentError("CONFIG_SCHEMA_MISMATCH", "Expected schema_version=1 with projects map")
        item = manifest["projects"].get(project_id)
        if not isinstance(item, dict) or not isinstance(item.get("root"), str):
            raise AgentError("PROJECT_NOT_REGISTERED", "Project ID is not in the explicit local map")
        root = Path(item["root"]).expanduser().resolve()
        if not root.is_dir():
            raise AgentError("PROJECT_ROOT_MISSING", "Registered project directory does not exist")
        return root, item

    def project_paths(self, project_id: str) -> tuple[Path, dict, dict]:
        root, item = self.project(project_id)
        raw_state = item.get("state", "STATE.md")
        state = under_root(root, raw_state)
        if "state" not in item and not state.is_file():
            fallback = under_root(root, "STATE.json")
            if fallback.is_file():
                state = fallback
        paths = {
            "state": state,
            "research_record": under_root(root, item.get("research_record", "RESEARCH_RECORD.md")),
            "paper_blueprint": under_root(root, item.get("paper_blueprint", "PAPER_BLUEPRINT.md")),
        }
        return root, item, paths
