"""Bounded per-service startup identity for detecting stale MCP processes.

This fingerprints package SOURCE FILES at construction, not loaded bytecode,
authorization, reproducibility or research provenance. Never use it to certify
scientific results or to infer that a host tool can execute a DEV operation.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

from . import __version__

MAX_FILES = 300
MAX_TOTAL_BYTES = 4 * 1024 * 1024


def capture_runtime_identity() -> dict:
    """Capture bounded, stable source evidence once for one service process."""
    base = {
        "reported_agent_version": __version__,
        "process_id": os.getpid(),
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "identity_scope": "SOURCE_FILES_AT_SERVICE_INITIALIZATION_ONLY",
        "loaded_bytecode_attested": False,
        "mcp_host_reloaded_attested": False,
    }
    try:
        base["installed_distribution_version"] = metadata.version("pdrw-agent")
    except metadata.PackageNotFoundError:
        base["installed_distribution_version"] = None
    base["version_consistent"] = (
        base["installed_distribution_version"] in (None, __version__)
    )
    try:
        root = Path(__file__).resolve().parent
        paths = sorted(root.rglob("*.py"))
        if not paths or len(paths) > MAX_FILES:
            raise ValueError("package source count outside bounded range")
        size = 0
        digest = hashlib.sha256()
        for path in paths:
            if not path.is_file():
                raise ValueError("source not a file")
            data = path.read_bytes()
            size += len(data)
            if size > MAX_TOTAL_BYTES:
                raise ValueError("package sources exceed bounded total")
            relative = path.relative_to(root).as_posix().encode("utf-8")
            digest.update(len(relative).to_bytes(4, "big"))
            digest.update(relative)
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
        base.update(
            source_snapshot_status="CAPTURED",
            source_snapshot_sha256=digest.hexdigest(),
            source_files_count=len(paths),
        )
    except (OSError, UnicodeError, ValueError):
        base.update(
            source_snapshot_status="UNAVAILABLE",
            source_snapshot_sha256=None,
            source_files_count=None,
        )
    return base
