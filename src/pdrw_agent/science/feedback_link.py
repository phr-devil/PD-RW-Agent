"""Bind an existing pre-result declaration to a real Run observation, read-only.

This is the optional bridge between ``science.feedback`` (which only compares a
declared proposal with a declared observation) and the actual project tree. It
checks that the cited files exist inside the project, that the declared hashes
match, and that the declaration is dated before the Run. Byte identity and
declared timestamps are *not* proof of historical order, so this module keeps
``historical_order_verified`` false and reports what it actually checked.

No writes, no ledger, no MCP tool, no authorization, no automatic GO/STOP.
Ordinary code changes and routine DEV must not call it: only a Run that really
judges a scientific hypothesis has anything to compare.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from ..schemas import AgentError
from .feedback import proposal_sha256, review_probe_feedback

LINK_SCHEMA = "pdrw-probe-feedback-link-v1"
MAX_LINK_BYTES = 128 * 1024
MAX_EVIDENCE_REFS = 12
MAX_QUERY = 400
PROTECTED_PARTS = {"sealed", "holdout", "confirmation"}
# Run records use a coarser vocabulary than the feedback contract. PARTIAL and
# CRASH are execution defects, never scientific negatives, so they map to the
# non-inferential INVALID state.
RUN_RECORD_STATUS = {
    "VALID": {"VALID"},
    "INVALID": {"INVALID"},
    "PARTIAL": {"INVALID"},
    "CRASH": {"INVALID"},
    "NOT_RUN": {"NOT_RUN", "INVALID"},
}
RULE_KEYS = ("prediction", "hypoth", "decision_rule", "ex_ante", "expected", "mechanism_probe")


def _bounded(value, field: str, limit: int = 240) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise AgentError("FEEDBACK_LINK_INVALID", f"{field} must be a bounded nonempty string")
    return value


def _iso(value, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise AgentError("FEEDBACK_LINK_INVALID", f"{field} requires an ISO timestamp with timezone")
    if parsed.tzinfo is None:
        raise AgentError("FEEDBACK_LINK_INVALID", f"{field} requires an explicit timezone")
    return parsed


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve(root: Path, ref, *, base: Path | None = None, directory: bool = False) -> Path:
    """Resolve a project-relative reference; never leave the project or read SEALED."""
    if not isinstance(ref, str) or not ref.strip() or len(ref) > 300:
        raise AgentError("FEEDBACK_LINK_INVALID", "Every reference must be a bounded relative path")
    raw = Path(ref)
    if raw.is_absolute() or ".." in raw.parts or raw.drive:
        raise AgentError("FEEDBACK_LINK_PATH_REJECTED", "References must stay inside the project")
    root = root.resolve()
    target = ((base or root) / raw).resolve()
    if target != root and root not in target.parents:
        raise AgentError("FEEDBACK_LINK_PATH_REJECTED", "Reference escapes the project root")
    if any(part.casefold() in PROTECTED_PARTS for part in target.relative_to(root).parts):
        raise AgentError("FEEDBACK_LINK_PATH_REJECTED",
                         "No SEALED/holdout/confirmation path may be read for feedback")
    if directory and not target.is_dir():
        raise AgentError("FEEDBACK_LINK_REF_MISSING", f"Referenced directory is absent: {ref}")
    if not directory and not target.is_file():
        raise AgentError("FEEDBACK_LINK_REF_MISSING", f"Referenced file is absent: {ref}")
    return target


def _resolve_artifact(root: Path, run_dir: Path, ref: str) -> Path:
    """Run artifacts are normally project-relative; run-dir-relative is also accepted."""
    try:
        return _resolve(root, ref)
    except AgentError as exc:
        if exc.code != "FEEDBACK_LINK_REF_MISSING":
            raise
        return _resolve(root, ref, base=run_dir)


def _read_json(path: Path, limit: int = MAX_LINK_BYTES) -> dict:
    if path.stat().st_size > limit:
        raise AgentError("FEEDBACK_LINK_TOO_LARGE", "Linked JSON file exceeds the bounded size")
    try:
        parsed = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeError, ValueError) as exc:
        raise AgentError("FEEDBACK_LINK_INVALID", "Linked JSON cannot be parsed") from exc
    if not isinstance(parsed, dict):
        raise AgentError("FEEDBACK_LINK_INVALID", "Linked JSON must be an object")
    return parsed


def _prereg(root: Path, block: dict) -> dict:
    if not isinstance(block, dict):
        raise AgentError("FEEDBACK_LINK_INVALID", "prereg must be an object")
    ref = _bounded(block.get("ref"), "prereg.ref")
    path = _resolve(root, ref)
    actual = _sha256(path)
    declared = block.get("sha256")
    if declared is not None and _bounded(declared, "prereg.sha256", 64) != actual:
        return {"ref": ref, "sha256": actual, "reason": "PREREG_HASH_MISMATCH",
                "proposal": None, "declared_prediction_fields": []}
    record = _read_json(path)
    proposal = block.get("proposal")
    if isinstance(block.get("proposal_ref"), str):
        proposal = _read_json(_resolve(root, _bounded(block["proposal_ref"], "prereg.proposal_ref")))
    base = {
        "ref": ref,
        "sha256": actual,
        "declared_at": block.get("declared_at") or record.get("frozen_at"),
        "record_keys": sorted(str(key) for key in record)[:40],
        "declared_prediction_fields": sorted(
            str(key) for key in record
            if any(marker in str(key).casefold() for marker in RULE_KEYS))[:8],
    }
    if not isinstance(proposal, dict):
        # The declaration exists but was never written in the feedback schema.
        # Guessing which prose sentence was the prediction would be fabrication.
        return {**base, "reason": "PREREG_WITHOUT_FEEDBACK_PROPOSAL", "proposal": None}
    try:
        digest = proposal_sha256(proposal)
    except AgentError:
        return {**base, "reason": "DECLARED_PROPOSAL_NOT_ASSESSABLE", "proposal": None}
    return {**base, "reason": "PREREG_RECORD_PRESENT", "proposal": proposal,
            "proposal_sha256": digest}


def _run(root: Path, block: dict) -> dict:
    if not isinstance(block, dict):
        raise AgentError("FEEDBACK_LINK_INVALID", "run must be an object")
    ref = _bounded(block.get("ref"), "run.ref")
    run_dir = _resolve(root, ref, directory=True)
    record = {}
    record_path = None
    if block.get("run_record_ref") is not None:
        record_path = _resolve_artifact(
            root, run_dir, _bounded(block["run_record_ref"], "run.run_record_ref"))
        record = _read_json(record_path)
    observation = block.get("observation")
    if not isinstance(observation, dict):
        raise AgentError("FEEDBACK_LINK_INVALID", "run.observation must be an object")
    refs = observation.get("evidence_refs", [])
    if not isinstance(refs, list) or len(refs) > MAX_EVIDENCE_REFS:
        raise AgentError("FEEDBACK_LINK_INVALID", "At most 12 original evidence refs")
    declared = observation.get("evidence_sha256") or {}
    if not isinstance(declared, dict):
        raise AgentError("FEEDBACK_LINK_INVALID", "observation.evidence_sha256 must be a mapping")
    checked, problems = [], []
    for item in refs:
        try:
            target = _resolve_artifact(root, run_dir, _bounded(item, "evidence ref"))
        except AgentError as exc:
            if exc.code != "FEEDBACK_LINK_REF_MISSING":
                raise
            problems.append({"ref": item, "problem": "MISSING"})
            continue
        digest = _sha256(target)
        if isinstance(declared.get(item), str) and declared[item] != digest:
            problems.append({"ref": item, "problem": "HASH_CHANGED"})
        checked.append({"ref": item, "sha256": digest})
    return {
        "ref": ref,
        "resolved_dir": str(run_dir.relative_to(root.resolve())).replace("\\", "/"),
        "run_record": record or None,
        "run_record_ref": str(record_path.relative_to(root.resolve())).replace("\\", "/")
                          if record_path else None,
        "observed_files": checked,
        "evidence_problems": problems,
        "observation": observation,
        "started_at": block.get("started_at"),
    }


def _run_classification(run_record: dict) -> str | None:
    """Preserve a declared ex-ante classification if the Run record carries one.

    Descriptive only: it is never compared with the protocol by this module.
    """
    for holder in (run_record, run_record.get("metrics") or {}):
        if isinstance(holder, dict):
            value = holder.get("ex_ante_classification")
            if isinstance(value, str) and value.strip():
                return value.strip()[:120]
    return None


def _status_conflict(run_record: dict, observation: dict) -> str | None:
    status = str(run_record.get("status") or "").upper()
    validity = str(observation.get("validity") or "").upper()
    if not status or status not in RUN_RECORD_STATUS:
        return None
    if validity not in RUN_RECORD_STATUS[status]:
        return f"RUN_RECORD_{status}_VS_OBSERVATION_{validity}"
    return None


def case_context(case_root, query, filters=None, limit: int = 3,
                 profile: dict | None = None, mirror_manifest=None) -> dict:
    """Read-only case candidates with grades, source independence and scope.

    A keyword match is a candidate, never premise equivalence or a GO/STOP.
    """
    if case_root is None:
        return {"status": "NOT_REQUESTED", "cases_do_not_certify_current_run": True,
                "automatic_go_stop": False}
    from .. import case_learning  # local import keeps the science package light

    root = Path(case_root)
    if not root.is_dir():
        raise AgentError("CASE_LIBRARY_UNAVAILABLE",
                         "The declared case library path is not a directory")
    query = _bounded(query, "cases.query", MAX_QUERY)
    index = case_learning.load_index(root)
    result = case_learning.search(index, filters or {}, query, limit=min(limit, 5), profile=profile)
    brief = case_learning.decision_brief(result, None, max_experiences=min(limit, 5),
                                         task_profile=profile)
    independence = result.get("source_independence") or {}
    groups: dict[str, list[str]] = {}
    for a, b, _ in independence.get("same_source_pairs", []):
        groups.setdefault(a, [])
        groups.setdefault(b, [])
        if b not in groups[a]:
            groups[a].append(b)
        if a not in groups[b]:
            groups[b].append(a)
    checks = {r["case_id"]: (r.get("next_minimal_check") or [])[:1]
              for r in result.get("results", [])}
    experiences = [{
        "case_id": item["case_id"],
        "polarity": item["polarity"],
        "verdict": item["verdict"],
        "evidence_grade": item["evidence_grade"],
        "evidence_tier": item["evidence_tier"],
        "exploratory_lead_only": item["exploratory_lead_only"],
        "independent_confirmation": item["independent_confirmation"],
        "same_source_with": groups.get(item["case_id"], []),
        "counterexample": item.get("risk_if_ignored"),
        "concrete_impact": item.get("concrete_impact"),
        "next_minimal_check": checks.get(item["case_id"], []),
        "evidence_paths": item.get("evidence_paths", [])[:2],
    } for item in brief.get("experiences", [])]
    mirror = None
    if mirror_manifest is not None:
        manifest = _read_json(Path(mirror_manifest), limit=2 * 1024 * 1024)
        scope = manifest.get("scope") if isinstance(manifest.get("scope"), dict) else {}
        mirror = {
            "manifest_ref": str(mirror_manifest),
            "mirror_version": manifest.get("mirror_version"),
            "content_sha256": manifest.get("content_sha256"),
            "publish_state": manifest.get("publish_state"),
            "scope_mode": scope.get("mode"),
            # Scope describes the BUILD, not what was pushed. A private cloud
            # repo may hold a smaller first batch, so this is never called
            # "published_cases".
            "manifest_scope_cases": scope.get("included"),
            "library_total": scope.get("library_total"),
            "publication_note": ("manifest.scope 只描述本次本地构建范围；"
                                 "云端仓库实际推送子集须以远端提交内容为准。"),
        }
    return {
        "status": result.get("status"),
        "query": query,
        "index_sha256": index.get("sha256"),
        "index_stale": index.get("index_stale"),
        "cases_in_index": index.get("card_count"),
        "independent_units": independence.get("independent_units"),
        "same_source_pairs": independence.get("same_source_pairs", []),
        "experiences": experiences,
        "candidates_only": brief.get("candidates_only_not_admitted", []),
        "mirror": mirror,
        "coverage_note": ("本地案例库是源；云端 Markdown 镜像可能只含已授权子集，"
                          "未命中表示 NOT_FOUND_WITHIN_SCOPE，不等于没有历史证据。"),
        "retrieval_is_candidate_only": True,
        "cases_do_not_certify_current_run": True,
        "automatic_go_stop": False,
    }


def review_linked_feedback(link: dict, *, project_root, case_root=None,
                           mirror_manifest=None) -> dict:
    """One bounded pass: verify declaration/Run bytes, compare, attach cases."""
    if not isinstance(link, dict) or link.get("schema_version") != LINK_SCHEMA:
        raise AgentError("FEEDBACK_LINK_INVALID", f"Expected schema_version={LINK_SCHEMA}")
    if project_root is None:
        raise AgentError("FEEDBACK_LINK_INVALID", "A project root is required")
    root = Path(project_root)
    if not root.is_dir():
        raise AgentError("FEEDBACK_LINK_INVALID", "Project root is not a directory")
    project_id = link.get("project_id")
    if project_id is not None:
        project_id = _bounded(project_id, "project_id", 80)

    prereg = _prereg(root, link.get("prereg"))
    run = _run(root, link.get("run"))
    observation = run["observation"]

    order = "NOT_EVALUATED"
    if prereg.get("proposal") is not None and prereg.get("declared_at") and run.get("started_at"):
        declared_at = _iso(prereg["declared_at"], "prereg.declared_at")
        started_at = _iso(run["started_at"], "run.started_at")
        order = "DECLARED_BEFORE_RUN" if declared_at < started_at else "DECLARED_AFTER_RUN"

    conflict = _status_conflict(run["run_record"] or {}, observation)
    feedback = None
    reason = None
    status = "PRE_RESULT_RECORD_UNVERIFIED"
    if conflict:
        status, reason = "RUN_STATUS_CONFLICT", conflict
    elif run["evidence_problems"]:
        status, reason = "RUN_EVIDENCE_UNVERIFIED", "EVIDENCE_REF_MISSING_OR_HASH_CHANGED"
    elif prereg.get("proposal") is None:
        reason = prereg.get("reason", "PREREG_WITHOUT_FEEDBACK_PROPOSAL")
    elif order == "DECLARED_AFTER_RUN":
        reason = "PREREG_DECLARED_AFTER_RUN"
    else:
        packet = {
            "schema_version": "pdrw-probe-feedback-v1",
            "prior_decision_ref": prereg["ref"],
            "prior_proposal_sha256": prereg["proposal_sha256"],
            "prior_proposal": prereg["proposal"],
            "observation": observation,
            "consulted_case_ids": [],
        }
        try:
            feedback = review_probe_feedback(packet)
            if order == "DECLARED_BEFORE_RUN":
                status, reason = "ADVISORY_FEEDBACK_ONLY", None
            else:
                status, reason = "PRE_RESULT_RECORD_UNVERIFIED", "ORDER_NOT_DECLARED"
        except AgentError as exc:
            if exc.code == "FEEDBACK_NOT_COMPARABLE":
                status, reason = "NOT_COMPARABLE", "MEASUREMENT_AXIS_CHANGED_SINCE_PREREG"
            elif exc.code == "FEEDBACK_SNAPSHOT_MISMATCH":
                status, reason = "PRE_RESULT_RECORD_UNVERIFIED", "PROPOSAL_SNAPSHOT_MISMATCH"
            elif exc.code in {"FEEDBACK_EVIDENCE_MISSING", "FEEDBACK_INVALID_OUTCOME",
                              "FEEDBACK_PACKET_INVALID", "FEEDBACK_PROBE_UNKNOWN"}:
                status, reason = "RUN_EVIDENCE_UNVERIFIED", exc.code
            else:
                raise

    cases_block = link.get("cases") if isinstance(link.get("cases"), dict) else {}
    cases = case_context(case_root, cases_block.get("query", ""),
                         filters=cases_block.get("filters"),
                         limit=cases_block.get("limit", 3),
                         profile=cases_block.get("profile"),
                         mirror_manifest=mirror_manifest)
    if feedback is not None and cases.get("experiences"):
        feedback["consulted_case_ids"] = [x["case_id"] for x in cases["experiences"]][:8]

    return {
        "schema_version": LINK_SCHEMA,
        "status": status,
        "reason": reason,
        "project_id": project_id,
        "prereg": {
            "ref": prereg.get("ref"),
            "sha256": prereg.get("sha256"),
            "declared_at": prereg.get("declared_at"),
            "proposal_bound": prereg.get("proposal") is not None,
            "proposal_sha256": prereg.get("proposal_sha256"),
            "declared_prediction_fields": prereg.get("declared_prediction_fields", []),
        },
        "run": {
            "ref": run["ref"],
            "run_record_ref": run["run_record_ref"],
            "declared_record_status": (run["run_record"] or {}).get("status"),
            "declared_run_classification": _run_classification(run["run_record"] or {}),
            "evidence_files_checked": len(run["observed_files"]),
            "evidence_problems": run["evidence_problems"],
        },
        "order_check": order,
        "feedback": feedback,
        "case_context": cases,
        "observation_preserved": {
            "run_ref": observation.get("run_ref"),
            "probe_id": observation.get("probe_id"),
            "declared_validity": observation.get("validity"),
            "declared_outcome": observation.get("outcome"),
            "evidence_refs": observation.get("evidence_refs", []),
        },
        "prediction_verification_performed": bool(
            feedback and status == "ADVISORY_FEEDBACK_ONLY" and order == "DECLARED_BEFORE_RUN"),
        "historical_order_verified": False,
        "original_run_verified": False,
        "scientific_inference_verified": False,
        "permission_to_execute": False,
        "automatic_go": False,
        "automatic_stop": False,
        "writes_performed": False,
        "note": ("Declared timestamps and byte equality are consistency checks, not proof that the "
                 "prediction existed before the result. Verify the original frozen record, the exact "
                 "Run and prediction-time inputs. A missing case is NOT_FOUND_WITHIN_SCOPE, not proof "
                 "that no prior evidence exists."),
    }
