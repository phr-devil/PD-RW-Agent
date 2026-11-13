#!/usr/bin/env python3
"""Read-only PD-RW local checkout and project snapshot locator (Python 3.9+).

This is not a user-authorisation validator, a sealed-data guard, or a research
executor. Prints bounded JSON; never creates or modifies project files.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

STATE_KEYS = (
    "WORKFLOW", "USER_SCOPE", "ACTIVE_TASK", "AUTH/BUDGET", "HOLDOUT",
    "BEST_VALID_RUN", "NEXT", "RESEARCH_RECORD_REF", "PAPER_BLUEPRINT_REF",
    "HUMAN_REVIEW_CURRENT", "NEXT_ACTION_OWNER", "MANUSCRIPT_WRITE_AUTH",
)
REQUIRED_RULES = ("AGENTS.md", "WORKFLOW.md")


def emit(payload, code=0):
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


def local_head(root):
    try:
        run = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, check=False, timeout=5,
        )
        return run.stdout.strip() if run.returncode == 0 else None
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def doctor(root):
    root = Path(root).expanduser().resolve()
    missing = [f for f in REQUIRED_RULES if not (root / f).is_file()]
    head = local_head(root) if not missing else None
    return {
        "status": "OK" if not missing else "ERROR",
        "error_code": None if not missing else "WORKFLOW_NOT_FOUND",
        "workflow_root": str(root),
        "missing_rules": missing,
        "local_rule_commit": head,
        "rule_version_status": "LOCAL_HEAD_ONLY_REMOTE_NOT_CHECKED" if head
                               else "RULE_VERSION_UNVERIFIED",
        "authorization_status": "NOT_AUTHENTICATED",
    }


def inside(root, relative):
    rel = Path(relative)
    if rel.is_absolute() or not str(relative).strip():
        raise ValueError("project file mapping must be a nonempty relative path")
    target = (root / rel).resolve()
    if target != root and root not in target.parents:
        raise ValueError("project file mapping escapes project root")
    return target


def project_entry(mapping_path, project_id):
    data = json.loads(Path(mapping_path).expanduser().read_text(encoding="utf-8-sig"))
    if data.get("schema_version") != 1 or not isinstance(data.get("projects"), dict):
        raise ValueError("unsupported project mapping schema")
    item = data["projects"].get(project_id)
    if not isinstance(item, dict) or not item.get("root"):
        raise ValueError("project ID not found or root missing in explicit mapping")
    root = Path(item["root"]).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("mapped project root does not exist")
    defaults = {
        "state": "STATE.md",
        "research_record": "RESEARCH_RECORD.md",
        "paper_blueprint": "PAPER_BLUEPRINT.md",
    }
    result = {name: inside(root, item.get(name, default))
              for name, default in defaults.items()}
    return root, result


def read_limited(path, cap=131072):
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        return handle.read(cap + 1)[:cap]


def current_snapshot(text):
    if text is None:
        return None
    match = re.search(r"(?m)^##\s+0[.、\s]", text)
    if not match:
        return None
    tail = text[match.start():]
    following = re.search(r"(?m)^##\s+1[.、\s]", tail)
    return tail[:following.start() if following else 5000][:5000]


def state_index(path):
    raw = read_limited(path)
    if raw is None:
        return None
    if path.suffix.lower() == ".json":
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("STATE JSON must be an object")
        return {k: data[k] for k in STATE_KEYS if k in data}
    found = {}
    for line in raw.splitlines():
        value = line.strip().removeprefix("- ").strip()
        for key in STATE_KEYS:
            if value.startswith(key + ":"):
                found[key] = value[len(key) + 1:].strip()[:500]
    return found


def resume(workflow_root, project_map, project_id):
    check = doctor(workflow_root)
    if check["status"] != "OK":
        return check
    root, files = project_entry(project_map, project_id)
    paths = {name: {"path": str(p), "exists": p.is_file()} for name, p in files.items()}
    snapshot = current_snapshot(read_limited(files["research_record"]))
    state = state_index(files["state"])
    missing = [name for name in ("state", "research_record") if not paths[name]["exists"]]
    return {
        "status": "READY_FOR_SOURCE_REVIEW" if not missing and snapshot is not None
                  else "INCOMPLETE_CONTEXT",
        "project_id": project_id,
        "project_root": str(root),
        "project_identity_status": "UNVERIFIED_REQUIRE_ORIGINAL_SOURCE",
        "workflow": check,
        "paths": paths,
        "missing": missing,
        "state_index": state,
        "research_snapshot": snapshot,
        "original_user_authorization": "UNVERIFIED",
        "scientific_evidence": "UNVERIFIED_REQUIRE_RAW_ARTIFACTS",
        "next": "VERIFY_IDENTITY_AUTH_AND_RAW_EVIDENCE_BEFORE_RESTRICTED_ACTION",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    d = commands.add_parser("doctor", help="Read-only local workflow check")
    d.add_argument("--workflow-root", required=True)
    r = commands.add_parser("resume", help="Read-only mapped project snapshot")
    r.add_argument("--workflow-root", required=True)
    r.add_argument("--project-id", required=True)
    r.add_argument("--project-map", required=True)
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            result = doctor(args.workflow_root)
        else:
            result = resume(args.workflow_root, args.project_map, args.project_id)
        return emit(result, 2 if result["status"] == "ERROR" else 0)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        return emit({"status": "ERROR", "error_code": "INVALID_INPUT",
                     "detail": str(exc)}, 2)


if __name__ == "__main__":
    sys.exit(main())
