"""Read-only source integrity check for an operator-installed runner catalog.

A matching file hash and manifest do NOT prove an OS account, user grant,
feature legality or script safety. This module never runs catalog entries.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

from ..config import Settings, read_json, under_root
from ..schemas import AgentError

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
SHA = re.compile(r"[0-9a-fA-F]{64}\Z")


def inspect_registered_runner(settings: Settings, project_id: str,
                              runner_id: str, registry_root: Path | None = None) -> dict:
    if not isinstance(runner_id, str) or not ID.fullmatch(runner_id):
        raise AgentError("HOST_RUNNER_ID_INVALID", "Invalid registered runner identifier")
    root_text = str(registry_root or os.environ.get("PDRW_HOST_REGISTRY_DIR") or "")
    if not root_text or not Path(root_text).is_absolute():
        return {"status": "HOST_RUNNER_REGISTRY_NOT_CONFIGURED",
                "execution_authorized": False}
    original = Path(root_text)
    if original.is_symlink() or not original.is_dir():
        return {"status": "HOST_RUNNER_REGISTRY_INVALID",
                "execution_authorized": False}
    root = original.resolve()
    project, _ = settings.project(project_id)
    for protected in (project, settings.workflow_root, settings.project_map.parent):
        p = protected.resolve()
        if root == p or root in p.parents or p in root.parents:
            return {"status": "HOST_REGISTRY_OVERLAPS_UNTRUSTED_SOURCES",
                    "execution_authorized": False}
    file = root / "registry.json"
    if file.is_symlink():
        return {"status": "HOST_RUNNER_REGISTRY_INVALID",
                "execution_authorized": False}
    doc = read_json(file, limit=64 * 1024)
    entries = doc.get("runners")
    if (doc.get("schema_version") != "pdrw-runner-catalog-v1"
            or not isinstance(entries, list) or len(entries) > 64):
        return {"status": "HOST_RUNNER_CATALOG_INVALID",
                "execution_authorized": False}
    candidates = [e for e in entries if isinstance(e, dict)
                  and e.get("runner_id") == runner_id]
    if len(candidates) != 1:
        return {"status": "HOST_RUNNER_NOT_UNIQUE_OR_MISSING",
                "execution_authorized": False}
    item = candidates[0]
    if (set(item) != {"runner_id", "entrypoint", "sha256", "cpu_only", "network"}
            or item["cpu_only"] is not True or item["network"] is not False
            or not isinstance(item["sha256"], str)
            or not SHA.fullmatch(item["sha256"])):
        return {"status": "HOST_RUNNER_CATALOG_INVALID",
                "execution_authorized": False}
    try:
        # Reject every lexical symlink component, not just the fully
        # resolved target. A trusted catalog must reference immutable files.
        rel = item["entrypoint"]
        if not isinstance(rel, str):
            raise AgentError("HOST_RUNNER_SOURCE_INVALID", "Runner path must be text")
        cursor = root
        for part in Path(rel).parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise AgentError("HOST_RUNNER_SOURCE_INVALID", "Symlinked source forbidden")
        source = under_root(root, rel, must_exist=True)
        if source.stat().st_size > 256 * 1024:
            return {"status": "HOST_RUNNER_SOURCE_INVALID", "execution_authorized": False}
        h = hashlib.sha256()
        with source.open("rb") as stream:
            for part in iter(lambda: stream.read(131072), b""):
                h.update(part)
        equal = h.hexdigest().lower() == item["sha256"].lower()
    except (AgentError, OSError, ValueError, TypeError):
        return {"status": "HOST_RUNNER_SOURCE_INVALID",
                "execution_authorized": False}
    return {"status": ("HOST_RUNNER_SOURCE_HASH_MATCHED_ONLY" if equal
                       else "HOST_RUNNER_SOURCE_HASH_MISMATCH"),
            "runner_id": runner_id, "source_sha256_matched": equal,
            "catalog_origin_authenticated": False,
            "actual_imports_and_dataflow_verified": False,
            "os_acl_verified": False, "execution_authorized": False,
            "runner_executed": False}
