"""Bind an existing pre-result declaration to a real Run observation, read-only.

This is the optional bridge between ``science.feedback`` (which only compares a
declared proposal with a declared observation) and the actual project tree. It
checks that the cited files exist inside the project, that the declared hashes
match, and that the declaration is dated before the Run. Byte identity and
declared timestamps are *not* proof of historical order, so this module keeps
``historical_order_verified`` false and reports what it actually checked.

Three states are reported separately, never collapsed into one another:

``DECLARED_PREDICTION_COMPARED``
    A prediction/observation contrast was actually computed. Advisory only.
``PRE_RESULT_PROVENANCE_VERIFIED``
    The frozen record is a project file, names the proposal digest that the
    proposal file still matches, its own timestamp precedes the Run, and no
    declared timestamp contradicts it.
``PRE_RESULT_RECORD_UNVERIFIED``
    Anything less. The observation is preserved; no prediction verification is
    claimed. A link object written after the Run can always claim an earlier
    ``declared_at``, so a self-declared time is never promoted on its own.

Case timing is likewise explicit: a case retrieved now (after the Run) is
``post_run_related_case_ids``, never pre-decision evidence. Pre-decision use
requires a bounded usage receipt stored inside the project and dated before
the frozen decision.

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
from .feedback import HEX64, proposal_sha256, review_probe_feedback

LINK_SCHEMA = "pdrw-probe-feedback-link-v1"
CASE_RECEIPT_SCHEMA = "pdrw-case-usage-receipt-v1"
MAX_LINK_BYTES = 128 * 1024
MAX_EVIDENCE_REFS = 12
MAX_PRE_DECISION_CASES = 8
MAX_QUERY = 400
PROTECTED_PARTS = {"sealed", "holdout", "confirmation"}
# Run records use a coarser vocabulary than the feedback contract. PARTIAL and
# CRASH are execution defects, never scientific negatives, so they map to the
# non-inferential INVALID state.
RUN_RECORD_STATUS = {
    # A correctly executed Run may still be inconclusive: that is a valid
    # execution, not a defect and not a scientific negative.
    "VALID": {"VALID", "INCONCLUSIVE"},
    "INCONCLUSIVE": {"INCONCLUSIVE"},
    "INVALID": {"INVALID"},
    "PARTIAL": {"INVALID"},
    "CRASH": {"INVALID"},
    "NOT_RUN": {"NOT_RUN", "INVALID"},
}
RULE_KEYS = ("prediction", "hypoth", "decision_rule", "ex_ante", "expected", "mechanism_probe")
PROVENANCE_VERIFIED = "PRE_RESULT_PROVENANCE_VERIFIED"
PROVENANCE_UNVERIFIED = "PRE_RESULT_RECORD_UNVERIFIED"
COMPARISON_PERFORMED = "DECLARED_PREDICTION_COMPARED"
CASE_INFLUENCE_VERIFIED = "VERIFIED_IN_FROZEN_DECLARATION"
CASE_INFLUENCE_RETRIEVAL = "RECEIPT_VERIFIED_RETRIEVAL_ONLY"
CASE_INFLUENCE_UNKNOWN = "UNKNOWN_NO_RECEIPT"
CASE_INFLUENCE_DECLARED_ONLY = "NOT_CLAIMED"
# Vocabulary shared with ``case_gates``: the projection below speaks exactly the
# bounded ``run_feedback`` dialect so no caller has to invent a translation.
LINK_STATUSES = frozenset({
    "ADVISORY_FEEDBACK_ONLY", "PRE_RESULT_RECORD_UNVERIFIED", "NOT_COMPARABLE",
    "RUN_EVIDENCE_UNVERIFIED", "RUN_STATUS_CONFLICT",
})
GATE_VALIDITY = frozenset({"VALID", "INVALID", "INCONCLUSIVE", "NOT_RUN"})
GATE_OUTCOMES = frozenset({"INCREASE", "DECREASE", "NO_CHANGE", "UNKNOWN"})
GATE_REVIEWS = {
    # Only a real declared contrast may be reported as one; an incomparable or
    # absent comparison stays empty rather than being relabelled downstream.
    COMPARISON_PERFORMED: "DECLARED_PREDICTION_CONTRAST",
    "NO_VALID_SCIENTIFIC_INFERENCE": "NO_VALID_SCIENTIFIC_INFERENCE",
}
# These statuses mean the cited evidence or the declared status cannot be
# interpreted at all, so no prediction contrast may survive the projection.
UNINTERPRETABLE_STATUSES = frozenset({"RUN_EVIDENCE_UNVERIFIED", "RUN_STATUS_CONFLICT"})


def _bounded(value, field: str, limit: int = 240) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise AgentError("FEEDBACK_LINK_INVALID", f"{field} must be a bounded nonempty string")
    return value


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


def _parse_iso(value):
    """Lenient ISO parse used only for consistency checks, never as proof."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _record_case_ids(record: dict) -> list[str]:
    """Case IDs the FROZEN record itself cites, if any (bounded)."""
    for key in ("consulted_case_ids", "pre_decision_case_ids", "case_ids_used"):
        value = record.get(key)
        if isinstance(value, list) and len(value) <= MAX_PRE_DECISION_CASES:
            if all(isinstance(x, str) and 0 < len(x) <= 80 for x in value):
                return list(value)
    return []


def _prereg(root: Path, block: dict) -> dict:
    if not isinstance(block, dict):
        raise AgentError("FEEDBACK_LINK_INVALID", "prereg must be an object")
    ref = _bounded(block.get("ref"), "prereg.ref")
    path = _resolve(root, ref)
    actual = _sha256(path)
    declared = block.get("sha256")
    if declared is not None and _bounded(declared, "prereg.sha256", 64).lower() != actual:
        return {"ref": ref, "sha256": actual, "reason": "PREREG_HASH_MISMATCH",
                "proposal": None, "declared_prediction_fields": [],
                "declared_at": None, "declared_at_source": "NONE",
                "record_frozen_at": None, "link_declared_at": block.get("declared_at"),
                "declared_at_conflict": False, "proposal_binding": "NONE",
                "record_binds_proposal": False, "record_case_ids": []}
    record = _read_json(path)
    proposal = None
    binding = "NONE"
    if isinstance(block.get("proposal_ref"), str):
        proposal = _read_json(
            _resolve(root, _bounded(block["proposal_ref"], "prereg.proposal_ref")))
        binding = "PROJECT_FILE"
    elif isinstance(block.get("proposal"), dict):
        # The link is written after the Run: an inline object is not the frozen
        # artifact, so it can never support verified provenance.
        proposal = block["proposal"]
        binding = "INLINE_LINK_OBJECT"

    record_frozen = record.get("frozen_at")
    link_declared = block.get("declared_at")
    frozen_dt, link_dt = _parse_iso(record_frozen), _parse_iso(link_declared)
    conflict = bool(frozen_dt and link_dt and
                    abs((frozen_dt - link_dt).total_seconds()) > 60)
    stamps = [x for x in (frozen_dt, link_dt) if x]
    # Conservative: if either declared time is later, the earlier one is not
    # evidence that the prediction existed first.
    effective = max(stamps) if stamps else None
    source = ("RECORD_FROZEN_AT" if frozen_dt and effective is frozen_dt
              else "LINK_DECLARED_AT" if link_dt and effective is link_dt else "NONE")
    base = {
        "ref": ref,
        "sha256": actual,
        "declared_at": (effective.isoformat() if effective
                        else record_frozen or link_declared),
        "declared_at_source": source,
        "record_frozen_at": record_frozen,
        "link_declared_at": link_declared,
        "declared_at_conflict": conflict,
        "record_keys": sorted(str(key) for key in record)[:40],
        "declared_prediction_fields": sorted(
            str(key) for key in record
            if any(marker in str(key).casefold() for marker in RULE_KEYS))[:8],
        "record_case_ids": _record_case_ids(record),
    }
    if not isinstance(proposal, dict):
        # The declaration exists but was never written in the feedback schema.
        # Guessing which prose sentence was the prediction would be fabrication.
        return {**base, "reason": "PREREG_WITHOUT_FEEDBACK_PROPOSAL",
                "proposal": None, "proposal_binding": binding,
                "record_binds_proposal": False}
    try:
        digest = proposal_sha256(proposal)
    except AgentError:
        return {**base, "reason": "DECLARED_PROPOSAL_NOT_ASSESSABLE", "proposal": None,
                "proposal_binding": binding, "record_binds_proposal": False}
    record_digest = None
    for key in ("proposal_sha256", "prior_proposal_sha256", "proposal_digest",
                "proposal_ref_sha256"):
        value = record.get(key)
        if isinstance(value, str) and HEX64.fullmatch(value.strip().lower()):
            record_digest = value.strip().lower()
            break
    binds = bool(record_digest) and record_digest == digest
    if record_digest is not None and not binds:
        # The frozen record names a different proposal: the file was replaced
        # or the link points at another snapshot. Comparing predictions now
        # would verify nothing, so the proposal is dropped but the Run stays.
        return {**base, "reason": "PROPOSAL_CHANGED_SINCE_FREEZE", "proposal": None,
                "proposal_binding": binding, "record_binds_proposal": False,
                "record_proposal_sha256": record_digest,
                "computed_proposal_sha256": digest}
    return {**base, "reason": "PREREG_RECORD_PRESENT", "proposal": proposal,
            "proposal_sha256": digest, "proposal_binding": binding,
            "record_binds_proposal": binds,
            "record_proposal_sha256": record_digest}


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


RUN_RECORD_NAMES = ("metrics.json", "run.json", "RUN.json")
MAX_RUN_RECORD_BYTES = 128 * 1024


def bind_run_reference(project_root, run_ref, run_record_ref=None) -> dict:
    """Resolve one declared Run reference to bytes inside *this* project.

    Answers exactly one question: does the reference point at a readable Run
    record here, and what does that record say about itself? It does not judge
    scientific validity, does not read SEALED/holdout paths (``_resolve``
    refuses them), and does not grant permission. A missing directory, a path
    that escapes the project, and a directory with no run record stay three
    different answers -- collapsing them into "verified" was the defect.

    The declared ``status`` of a *claim* is compared with the Run's own
    ``status``/``verdict``/``anchor_pass`` upstream, never here.
    """
    if project_root is None:
        raise AgentError("FEEDBACK_LINK_INVALID", "A project root is required")
    root = Path(project_root)
    if not root.is_dir():
        raise AgentError("FEEDBACK_LINK_INVALID", "Project root is not a directory")
    ref = _bounded(run_ref, "run_ref", 300)
    base = {"run_ref": ref, "run_record_ref": run_record_ref,
            "scope": "DECLARED_REFERENCE_TO_PROJECT_BYTES_ONLY"}
    try:
        run_dir = _resolve(root, ref, directory=True)
        target_is_dir = True
    except AgentError as exc:
        if exc.code == "FEEDBACK_LINK_REF_MISSING":
            target_is_dir = False
        else:
            return {**base, "status": "RUN_REF_REJECTED", "reason": exc.code}
    if target_is_dir:
        if run_record_ref is not None:
            try:
                record_path = _resolve_artifact(
                    root, run_dir, _bounded(run_record_ref, "run_record_ref", 300))
            except AgentError as exc:
                if exc.code == "FEEDBACK_LINK_REF_MISSING":
                    return {**base, "status": "RUN_RECORD_ABSENT", "reason": exc.code}
                return {**base, "status": "RUN_REF_REJECTED", "reason": exc.code}
        else:
            record_path = next(
                (run_dir / name for name in RUN_RECORD_NAMES
                 if (run_dir / name).is_file()), None)
            if record_path is None:
                return {**base, "status": "RUN_RECORD_ABSENT",
                        "reason": "NO_RUN_RECORD_IN_REFERENCED_DIRECTORY"}
        try:
            runner = str(run_dir.relative_to(root.resolve())).replace("\\", "/")
        except ValueError:
            runner = None
    else:
        try:
            record_path = _resolve(root, ref)
        except AgentError as exc:
            return {**base, "status": "RUN_REF_MISSING", "reason": exc.code}
        runner = None
    if record_path.stat().st_size > MAX_RUN_RECORD_BYTES:
        return {**base, "status": "RUN_RECORD_TOO_LARGE",
                "run_dir": runner, "record_ref": str(record_path.name)}
    try:
        record = _read_json(record_path, limit=MAX_RUN_RECORD_BYTES)
    except AgentError as exc:
        return {**base, "status": "RUN_RECORD_UNREADABLE", "reason": exc.code,
                "run_dir": runner, "record_ref": str(record_path.name)}
    anchor = record.get("anchor_pass")
    return {
        **base,
        "status": "RUN_RECORD_BOUND",
        "run_dir": runner,
        "record_ref": str(record_path.relative_to(root.resolve())).replace("\\", "/"),
        "record_sha256": _sha256(record_path),
        "run_id_declared": _text(record.get("run_id")),
        "run_status_declared": _text(record.get("status")),
        "verdict_declared": _text(record.get("verdict")),
        "anchor_pass_declared": anchor if isinstance(anchor, bool) else None,
        "note": ("The record was read from this project. Its own status is compared "
                 "with the declared one upstream; bytes matching is not a scientific "
                 "conclusion and not a permission."),
    }


def _text(value, limit: int = 120) -> str | None:
    return value.strip()[:limit] if isinstance(value, str) and value.strip() else None


def _case_usage(root: Path, block, *, decision_at, run_started,
                frozen_case_ids: list[str]) -> dict:
    """Split a case list into pre-decision use and post-Run relevance.

    A receipt proves *retrieval*, not influence. Without one, a declared
    pre-decision list stays UNKNOWN instead of being inferred from similarity.
    """
    pre = block.get("pre_decision") if isinstance(block, dict) else None
    if not isinstance(pre, dict):
        return {"status": "NOT_DECLARED", "pre_decision_case_ids": [],
                "declared_case_ids": [], "case_influence_verified": CASE_INFLUENCE_DECLARED_ONLY,
                "retrieved_at": None, "checks": {}, "receipt_ref": None}
    ids = pre.get("case_ids") or []
    if (not isinstance(ids, list) or len(ids) > MAX_PRE_DECISION_CASES
            or any(not isinstance(x, str) or not x.strip() or len(x) > 80 for x in ids)):
        raise AgentError("FEEDBACK_LINK_INVALID",
                         "pre_decision.case_ids must be at most 8 bounded case IDs")
    ids = [x.strip() for x in ids]
    if len(set(ids)) != len(ids):
        raise AgentError("FEEDBACK_LINK_INVALID", "Duplicate pre-decision case ID")
    ref = pre.get("receipt_ref")
    if not isinstance(ref, str) or not ref.strip():
        # Declaring "I consulted these" after the Run is exactly the claim that
        # cannot be checked. Keep the declaration visible, not the conclusion.
        return {"status": "UNKNOWN_NO_RECEIPT", "pre_decision_case_ids": [],
                "declared_case_ids": ids,
                "case_influence_verified": CASE_INFLUENCE_UNKNOWN,
                "retrieved_at": None, "receipt_ref": None,
                "checks": {"receipt_present": False},
                "note": "缺少检索收据：不得把声明的事前案例当作已使用证据。"}
    path = _resolve(root, _bounded(ref, "pre_decision.receipt_ref"))
    actual = _sha256(path)
    declared_sha = pre.get("receipt_sha256")
    if not isinstance(declared_sha, str) or declared_sha.strip().lower() != actual:
        return {"status": "RECEIPT_SHA_MISMATCH" if isinstance(declared_sha, str)
                else "RECEIPT_SHA_UNVERIFIED",
                "pre_decision_case_ids": [], "declared_case_ids": ids,
                "case_influence_verified": CASE_INFLUENCE_UNKNOWN,
                "retrieved_at": None, "receipt_ref": ref, "receipt_sha256": actual,
                "checks": {"receipt_present": True,
                           "receipt_sha256_matches": False}}
    receipt = _read_json(path)
    checks = {"receipt_present": True, "receipt_sha256_matches": True}
    if receipt.get("schema_version") != CASE_RECEIPT_SCHEMA:
        return {"status": "RECEIPT_SCHEMA_INVALID", "pre_decision_case_ids": [],
                "declared_case_ids": ids,
                "case_influence_verified": CASE_INFLUENCE_UNKNOWN,
                "retrieved_at": None, "receipt_ref": ref, "receipt_sha256": actual,
                "checks": checks}
    retrieved_dt = _parse_iso(receipt.get("retrieved_at"))
    checks["retrieved_at_has_timezone"] = retrieved_dt is not None
    if retrieved_dt is None:
        return {"status": "RECEIPT_TIME_UNVERIFIED", "pre_decision_case_ids": [],
                "declared_case_ids": ids,
                "case_influence_verified": CASE_INFLUENCE_UNKNOWN,
                "retrieved_at": receipt.get("retrieved_at"), "receipt_ref": ref,
                "receipt_sha256": actual, "checks": checks}
    boundary = decision_at or run_started
    checks["retrieved_before_decision"] = bool(boundary and retrieved_dt < boundary)
    checks["retrieved_before_run"] = bool(run_started and retrieved_dt < run_started)
    if boundary is not None and retrieved_dt >= boundary:
        return {"status": "RECEIPT_AFTER_DECISION", "pre_decision_case_ids": [],
                "declared_case_ids": ids,
                "case_influence_verified": CASE_INFLUENCE_UNKNOWN,
                "retrieved_at": receipt.get("retrieved_at"), "receipt_ref": ref,
                "receipt_sha256": actual, "checks": checks}
    returned = receipt.get("case_ids")
    returned_ids = [str(x) for x in returned] if isinstance(returned, list) else []
    checks["declared_ids_returned"] = set(ids) <= set(returned_ids)
    if not checks["declared_ids_returned"]:
        return {"status": "DECLARED_CASE_NOT_IN_RECEIPT", "pre_decision_case_ids": [],
                "declared_case_ids": ids,
                "case_influence_verified": CASE_INFLUENCE_UNKNOWN,
                "retrieved_at": receipt.get("retrieved_at"), "receipt_ref": ref,
                "receipt_sha256": actual, "checks": checks}
    in_frozen = bool(frozen_case_ids) and set(ids) <= set(frozen_case_ids)
    checks["cited_by_frozen_record"] = in_frozen
    return {"status": "VERIFIED", "pre_decision_case_ids": ids,
            "declared_case_ids": ids,
            # Retrieval is verified. Influence on the decision is not, unless
            # the frozen record itself cites the same IDs.
            "case_influence_verified": (CASE_INFLUENCE_VERIFIED if in_frozen
                                        else CASE_INFLUENCE_RETRIEVAL),
            "retrieved_at": receipt.get("retrieved_at"),
            "receipt_ref": ref, "receipt_sha256": actual,
            "receipt_index_sha256": receipt.get("index_sha256"),
            "checks": checks,
            "note": ("检索收据只证明在决策前检索过这些案例，不证明它们改变了决策；"
                     "只有冻结记录自身引用同一组案例时才可称事前使用。")}


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

    declared_dt = _parse_iso(prereg.get("declared_at"))
    started_dt = _parse_iso(run.get("started_at"))
    order = "NOT_EVALUATED"
    if declared_dt and started_dt:
        order = "DECLARED_BEFORE_RUN" if declared_dt < started_dt else "DECLARED_AFTER_RUN"

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

    # Provenance is judged separately from whether the comparison ran. Byte
    # equality proves the objects agree, never that the prediction came first.
    checks = {
        "prereg_record_readable": prereg.get("reason") != "PREREG_HASH_MISMATCH",
        "proposal_from_project_file": prereg.get("proposal_binding") == "PROJECT_FILE",
        "frozen_record_binds_proposal_digest": bool(prereg.get("record_binds_proposal")),
        "declaration_time_from_frozen_record":
            prereg.get("declared_at_source") == "RECORD_FROZEN_AT",
        "declared_time_matches_link": not prereg.get("declared_at_conflict", False),
        "declared_before_run": order == "DECLARED_BEFORE_RUN",
        "run_evidence_unchanged": not run["evidence_problems"],
    }
    provenance = (PROVENANCE_VERIFIED if all(checks.values())
                  else PROVENANCE_UNVERIFIED)
    if feedback is None:
        comparison = ("NOT_COMPARABLE" if status == "NOT_COMPARABLE" else "NOT_PERFORMED")
    elif feedback["declared_prediction_review"] == "NO_VALID_SCIENTIFIC_INFERENCE":
        comparison = "NO_VALID_SCIENTIFIC_INFERENCE"
    else:
        comparison = COMPARISON_PERFORMED

    cases_block = link.get("cases") if isinstance(link.get("cases"), dict) else {}
    usage = _case_usage(root, cases_block, decision_at=declared_dt,
                        run_started=started_dt,
                        frozen_case_ids=prereg.get("record_case_ids") or [])
    cases = case_context(case_root, cases_block.get("query", ""),
                         filters=cases_block.get("filters"),
                         limit=cases_block.get("limit", 3),
                         profile=cases_block.get("profile"),
                         mirror_manifest=mirror_manifest)
    post_run_ids = [x["case_id"] for x in cases.get("experiences", [])]
    if feedback is not None:
        # Compatibility: the field keeps its name and type, but it may now only
        # carry PRE-decision IDs. Filling it from a post-Run retrieval was the
        # defect this field previously caused.
        feedback["consulted_case_ids"] = list(usage["pre_decision_case_ids"])
        feedback["consulted_case_ids_semantics"] = (
            "PRE_DECISION_VERIFIED_ONLY_NEVER_POST_RUN")
        feedback["post_run_related_case_ids"] = post_run_ids
        feedback["case_influence_verified"] = usage["case_influence_verified"]

    return {
        "schema_version": LINK_SCHEMA,
        "status": status,
        "reason": reason,
        "project_id": project_id,
        "prereg": {
            "ref": prereg.get("ref"),
            "sha256": prereg.get("sha256"),
            "declared_at": prereg.get("declared_at"),
            "declared_at_source": prereg.get("declared_at_source"),
            "declared_at_conflict": prereg.get("declared_at_conflict", False),
            "record_frozen_at": prereg.get("record_frozen_at"),
            "proposal_bound": prereg.get("proposal") is not None,
            "proposal_binding": prereg.get("proposal_binding"),
            "record_binds_proposal": bool(prereg.get("record_binds_proposal")),
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
        "provenance": {
            "pre_result_provenance": provenance,
            "prediction_comparison": comparison,
            "checks": checks,
            "note": ("PRE_RESULT_PROVENANCE_VERIFIED 只表示冻结记录可读、由项目文件约束其提案摘要、"
                     "记录自身时间早于 Run 且无时间冲突；仍不等于科学结论成立。"),
        },
        "feedback": feedback,
        "case_context": cases,
        "case_timing": {
            "pre_decision_case_ids": list(usage["pre_decision_case_ids"]),
            "declared_pre_decision_case_ids": list(usage.get("declared_case_ids", [])),
            "post_run_related_case_ids": post_run_ids,
            "case_influence_verified": usage["case_influence_verified"],
            "usage_status": usage["status"],
            "retrieved_at": usage.get("retrieved_at"),
            "checks": usage.get("checks", {}),
            "note": ("本次检索发生在 Run 之后，只能作为结果解释。事前使用必须有决策前的检索收据；"
                     "相似性不能推断使用时间。"),
        },
        "observation_preserved": {
            "run_ref": observation.get("run_ref"),
            "probe_id": observation.get("probe_id"),
            "declared_validity": observation.get("validity"),
            "declared_outcome": observation.get("outcome"),
            "evidence_refs": observation.get("evidence_refs", []),
        },
        "prediction_verification_performed": bool(
            comparison == COMPARISON_PERFORMED and provenance == PROVENANCE_VERIFIED),
        # Four different questions, answered separately on purpose. "The file
        # was where it claimed to be" must never be read as "the prediction
        # came first", and neither is a statement about scientific truth.
        "verification_axes": {
            "file_binding": ("CHECKED_FILES_AND_DECLARED_DIGESTS"
                             if checks["prereg_record_readable"]
                             and checks["proposal_from_project_file"]
                             and checks["run_evidence_unchanged"]
                             else "NOT_ESTABLISHED"),
            "historical_order": "DECLARED_TIMESTAMPS_ONLY_NOT_INDEPENDENTLY_VERIFIED",
            "run_validity": ("RUN_RECORD_READ_NO_EVIDENCE_PROBLEM"
                             if not run["evidence_problems"] else "EVIDENCE_PROBLEM"),
            "scientific_truth": "NOT_ASSESSED_BY_TOOL",
        },
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


def _clip_refs(values, limit: int = 6) -> list[str]:
    out: list[str] = []
    for item in values or []:
        text = str(item).strip()
        if text and len(text) <= 240 and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def to_run_feedback(link_result: dict) -> dict:
    """Project a link result into the bounded ``run_feedback`` of ``case_gate_check``.

    The projection is **downgrade-only**. It can copy a verified provenance the
    binder reported, but it can never raise one: an unverified provenance stays
    unverified, and a Run whose status or evidence failed verification loses its
    prediction contrast entirely.

    It is a *shape* adapter, not a credential. The projected object crosses a
    public tool boundary as JSON, so ``case_gate_check`` re-labels everything in
    it as declared and never reports a verified provenance from it. Only this
    module — which re-reads the frozen record and the Run evidence — may state
    which binding check passed.
    """
    if not isinstance(link_result, dict) or link_result.get("schema_version") != LINK_SCHEMA:
        raise AgentError("FEEDBACK_LINK_INVALID", "Not a feedback-link result")
    status = str(link_result.get("status") or "").upper()
    if status not in LINK_STATUSES:
        raise AgentError("FEEDBACK_LINK_INVALID", "Link result carries no known status")

    observed = link_result.get("observation_preserved")
    observed = observed if isinstance(observed, dict) else {}
    provenance_block = link_result.get("provenance")
    provenance_block = provenance_block if isinstance(provenance_block, dict) else {}
    provenance = str(provenance_block.get("pre_result_provenance") or PROVENANCE_UNVERIFIED)
    if provenance not in {PROVENANCE_VERIFIED, PROVENANCE_UNVERIFIED}:
        provenance = PROVENANCE_UNVERIFIED
    comparison = str(provenance_block.get("prediction_comparison") or "NOT_PERFORMED")
    review = GATE_REVIEWS.get(comparison, "")

    validity = str(observed.get("declared_validity") or "UNKNOWN").upper()
    validity = validity if validity in GATE_VALIDITY else "UNKNOWN"
    outcome = str(observed.get("declared_outcome") or "UNKNOWN").upper()
    outcome = outcome if outcome in GATE_OUTCOMES else "UNKNOWN"

    feedback = link_result.get("feedback")
    feedback = feedback if isinstance(feedback, dict) else {}
    compatible = _clip_refs(feedback.get("compatible_predictions"))
    contradicted = _clip_refs(feedback.get("contradicted_predictions"))

    if status in UNINTERPRETABLE_STATUSES:
        # The cited result or the declared status cannot be read at all.
        provenance, review, outcome = PROVENANCE_UNVERIFIED, "", "UNKNOWN"
        compatible, contradicted = [], []
    elif status != "ADVISORY_FEEDBACK_ONLY" and status != "NOT_COMPARABLE":
        provenance = PROVENANCE_UNVERIFIED
    if review != "DECLARED_PREDICTION_CONTRAST":
        compatible, contradicted = [], []

    prereg = link_result.get("prereg")
    digest = str((prereg or {}).get("proposal_sha256") or "").lower()
    digest = digest if len(digest) == 64 and all(c in "0123456789abcdef" for c in digest) else ""

    run = link_result.get("run")
    run_ref = str((run or {}).get("ref") or observed.get("run_ref") or "").strip()[:120]
    return {
        "run_ref": run_ref,
        "validity": validity,
        "outcome": outcome,
        "prediction_review": review,
        "provenance": provenance,
        "compatible": compatible,
        "contradicted": contradicted,
        "evidence_refs": _clip_refs(observed.get("evidence_refs")),
        "link_status": status,
        "proposal_sha256": digest,
    }
