"""Bounded read-only project audit: project sources remain authoritative.

This module checks source presence and byte integrity, never scientific truth,
historical authorization, provenance authenticity or permission to execute.
No project files, runtime database or memoized scientific state are written.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from ..config import Settings, under_root
from ..evidence import sha256_file
from ..projects import get_project_context
from ..schemas import AgentError
from .history import reconstruct_project_history

MAX_DIRS = 128
MAX_MANIFESTS = 16
MAX_MANIFEST_BYTES = 256 * 1024
MAX_ENTRIES = 512
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
EXAMPLES = 12
HEX_LINE = re.compile(r"^\s*([0-9a-fA-F]{64})\s+[* ]?(.+?)\s*$")
VERSION = re.compile(r"\bPD-RW\s+v(\d+\.\d+)\b", re.IGNORECASE)
EXCLUDE_NAMES = {"data", ".git", ".venv", "__pycache__"}
PROTECTED_TERMS = ("sealed", "holdout", "confirmation")


def _protected(name: str) -> bool:
    name = name.casefold()
    return any(term in name for term in PROTECTED_TERMS)


def _manifest_paths(root: Path) -> tuple[list[Path], bool]:
    """Bound traversal; do not descend into data, protected or symlink dirs."""
    found: list[Path] = []
    directories = 0
    limited = False
    for current, dirs, files in os.walk(root, followlinks=False):
        directories += 1
        if directories > MAX_DIRS:
            limited = True
            break
        dirs[:] = sorted(d for d in dirs if d.casefold() not in EXCLUDE_NAMES
                         and not _protected(d) and not (Path(current) / d).is_symlink())
        for name in sorted(files):
            if not name.lower().endswith(".sha256"):
                continue
            path = Path(current) / name
            if path.is_symlink():
                continue
            if len(found) == MAX_MANIFESTS:
                limited = True
                break
            found.append(path)
        if limited:
            break
    return found, limited


def audit_frozen_manifests(root: Path) -> dict:
    """Inspect only small SHA-256 manifests and bounded, unprotected files.

    GNU sha256sum lines are interpreted relative to the containing manifest.
    Ambiguous/invalid lines remain counted as invalid, never as verified.
    """
    manifests, truncated = _manifest_paths(root)
    counts = {"declared": 0, "matched": 0, "missing": 0, "mismatched": 0,
              "unsafe": 0, "not_checked": 0, "invalid_lines": 0}
    examples: dict[str, list[str]] = {k: [] for k in
                                       ("missing", "mismatched", "unsafe", "not_checked", "invalid_lines")}
    inventory: list[dict] = []
    for manifest in manifests:
        rel_manifest = manifest.relative_to(root).as_posix()
        report = {"manifest": rel_manifest, "declared": 0, "matched": 0,
                  "missing": 0, "mismatched": 0, "unsafe": 0,
                  "not_checked": 0, "invalid_lines": 0}
        if manifest.stat().st_size > MAX_MANIFEST_BYTES:
            report["status"] = "MANIFEST_OVERSIZE"
            counts["not_checked"] += 1
            truncated = True
            inventory.append(report)
            continue
        for line_no, raw in enumerate(manifest.read_text(encoding="utf-8-sig").splitlines(), 1):
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            if counts["declared"] >= MAX_ENTRIES:
                truncated = True
                break
            match = HEX_LINE.fullmatch(raw)
            if not match:
                key = "invalid_lines"
                tag = f"{rel_manifest}:{line_no}"
            else:
                counts["declared"] += 1
                report["declared"] += 1
                digest, raw_ref = match.groups()
                name = raw_ref.strip().replace("\\", "/")
                tag = f"{rel_manifest}:{line_no}:{name[:100]}"
                try:
                    # Manifest paths are untrusted input. Resolve only inside the
                    # project root and use the existing protected-path gate.
                    candidate = (manifest.parent / name).resolve()
                    rel = candidate.relative_to(root).as_posix()
                    if not name or _protected(name) or any(_protected(p) for p in Path(rel).parts):
                        raise AgentError("PROTECTED_PROJECT_PATH", "Protected path")
                    candidate = under_root(root, rel)
                    if not candidate.is_file():
                        key = "missing"
                    elif candidate.stat().st_size > MAX_ARTIFACT_BYTES:
                        key = "not_checked"
                    elif sha256_file(candidate).casefold() == digest.casefold():
                        key = "matched"
                    else:
                        key = "mismatched"
                except (AgentError, ValueError, OSError):
                    key = "unsafe"
            counts[key] += 1
            report[key] += 1
            if key in examples and len(examples[key]) < EXAMPLES:
                examples[key].append(tag)
        inventory.append(report)
        if counts["declared"] >= MAX_ENTRIES:
            break
    status = ("NO_MANIFESTS" if not manifests else
              "AUDIT_INCOMPLETE" if truncated or counts["not_checked"] or counts["unsafe"]
              or counts["invalid_lines"] else
              "EVIDENCE_GAPS" if counts["missing"] or counts["mismatched"]
              else "BYTE_INTEGRITY_MATCHED_ONLY")
    return {"status": status, "counts": counts, "manifests": inventory,
            "examples": examples, "truncated": truncated,
            "scope": "BYTE_PRESENCE_AND_HASH_ONLY_NOT_SCIENCE_OR_AUTHORIZATION"}


def _declared_version(path: Path) -> str | None:
    if not path.is_file():
        return None
    with path.open(encoding="utf-8-sig", errors="replace") as handle:
        match = VERSION.search(handle.read(12_000))
    return match.group(1) if match else None


def audit_project_state(settings: Settings, project_id: str) -> dict:
    """One bounded project-level view; no attempt to reconstruct missing truth."""
    context = get_project_context(settings, project_id)
    root, _, paths = settings.project_paths(project_id)
    events = under_root(root, "EVENTS.jsonl")
    availability = {name: path.is_file() for name, path in paths.items()}
    availability["events"] = events.is_file()
    manifest = audit_frozen_manifests(root)
    history = reconstruct_project_history(settings, project_id)
    recorded = _declared_version(paths["research_record"])
    authority = _declared_version(settings.workflow_root / "WORKFLOW.md")
    version_discrepancy = bool(recorded and authority and recorded != authority)
    blockers = []
    advisories = []
    if context["status"] == "IDENTITY_CONFLICT":
        blockers.append("PROJECT_IDENTITY_CONFLICT")
    if not availability["state"]:
        blockers.append("STATE_MISSING")
    if not availability["events"]:
        blockers.append("EVENTS_MISSING")
    if not availability["research_record"]:
        blockers.append("RESEARCH_RECORD_MISSING")
    if version_discrepancy:
        blockers.append("DECLARED_RULE_VERSION_DIFFERS")
    if history["status"] not in {"METADATA_CHAIN_MATCHED_ONLY",
                                 "HISTORY_SOURCES_MISSING"}:
        blockers.append("STATE_EVENTS_METADATA_CONFLICT")
    if manifest["status"] == "NO_MANIFESTS":
        # The original PD-RW ledger already has event hashes. A separate
        # .sha256 manifest is optional and never a universal hard gate.
        advisories.append("OPTIONAL_STANDALONE_MANIFEST_NOT_PRESENT")
    elif manifest["status"] in {"EVIDENCE_GAPS", "AUDIT_INCOMPLETE"}:
        blockers.append("EVIDENCE_COVERAGE_INCOMPLETE")
    return {
        "status": "PARTIAL_RECOVERY" if blockers else "SOURCE_REVIEW_REQUIRED",
        "project_id": project_id, "project_root": str(root),
        "project_context_status": context["status"],
        "state_index": context["state_index"],
        "snapshot_excerpt": context["snapshot_excerpt"],
        "source_exists": availability,
        "manifest_audit": manifest,
        "history_diagnostic": {
            "status": history["status"],
            "state_matches_events": history.get("state_matches_events", False),
            "event_chain_valid": history.get("event_chain_valid", False),
            "differing_state_fields": history.get("differing_state_fields", []),
        },
        "rule_versions": {"record_declared": recorded,
                          "local_authority_declared": authority,
                          "local_authority_commit": context["workflow_commit_local_only"],
                          "remote_freshness": "NOT_CHECKED",
                          "declared_mismatch": version_discrepancy},
        "blockers": blockers,
        "advisories": advisories,
        "standalone_manifest_required_for_execution": False,
        "original_run_hashes_still_require_verification": True,
        "scientific_claims_verified": False,
        "original_authorization_verified": False,
        "event_chain_verified": history.get("event_chain_valid", False),
        "state_events_metadata_consistent":
            history.get("state_matches_events", False),
        "process_liveness_verified": False,
        "sealed_access": "NOT_ATTEMPTED",
        "execution_authorized": False,
        "next": "REVIEW_ORIGINAL_SOURCES_AND_RESOLVE_BLOCKERS_NO_AUTO_EXECUTION",
    }
