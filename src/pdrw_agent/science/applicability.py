"""Conservative scope compatibility of *declared* past negative lessons.

No embedding-based equivalence, automatic STOP, scientific approval, or
promotion of case-index prose into a validated experimental result.
"""
from __future__ import annotations

from ..schemas import AgentError

CRITICAL = ("dataset_version", "evaluation_unit", "group_split", "metric")
MAX_LESSONS = 20
MAX_SCOPE = 16


def _scope(obj: object) -> dict[str, str]:
    if (not isinstance(obj, dict) or not 1 <= len(obj) <= MAX_SCOPE
            or any(not isinstance(k, str) or not k or len(k) > 64
                   or not isinstance(v, str) or not v.strip() or len(v) > 200
                   for k, v in obj.items())):
        raise AgentError("LESSON_SCOPE_INVALID", "Nonempty bounded scope fields required")
    return obj


def review_lesson_applicability(proposal: dict, lessons: list[dict]) -> dict:
    """Compare literal premise ID and declared key/value conditions only."""
    if not isinstance(proposal, dict) or not isinstance(lessons, list) or len(lessons) > MAX_LESSONS:
        raise AgentError("LESSON_REVIEW_INVALID", "Proposal and at most 20 lessons required")
    pid = proposal.get("premise_id")
    if not isinstance(pid, str) or not 1 <= len(pid.strip()) <= 100:
        raise AgentError("LESSON_REVIEW_INVALID", "A premise ID is required")
    scope = _scope(proposal.get("scope"))
    missing_critical = [k for k in CRITICAL if k not in scope]
    reviews = []
    for index, item in enumerate(lessons):
        if not isinstance(item, dict):
            raise AgentError("LESSON_REVIEW_INVALID", "Lesson entries must be objects")
        identifier = item.get("premise_id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise AgentError("LESSON_REVIEW_INVALID", "Lesson premise ID required")
        prior = _scope(item.get("scope"))
        validity = item.get("validity", "UNKNOWN")
        if validity not in {"VALID_NEGATIVE", "INVALID", "UNKNOWN", "INCONCLUSIVE", "ENGINEERING_FAILURE"}:
            raise AgentError("LESSON_REVIEW_INVALID", "Unsupported declared validity")
        refs = item.get("evidence_refs", [])
        if not isinstance(refs, list) or len(refs) > 12 or any(not isinstance(x, str) or not x.strip() for x in refs):
            raise AgentError("LESSON_REVIEW_INVALID", "Evidence refs must be bounded strings")
        common = set(scope) & set(prior)
        conflicts = sorted(k for k in common if scope[k] != prior[k])
        only_current = sorted(set(scope) - set(prior))
        only_prior = sorted(set(prior) - set(scope))
        if identifier != pid:
            category = "DIFFERENT_PREMISE"
        elif validity != "VALID_NEGATIVE":
            category = "NOT_VALID_NEGATIVE"
        elif conflicts:
            category = "CONFLICTING_SCOPE"
        elif missing_critical or any(k not in prior for k in CRITICAL):
            category = "CRITICAL_SCOPE_UNKNOWN"
        elif only_current or only_prior:
            category = "PARTIAL_SCOPE_OVERLAP"
        elif not refs:
            category = "EVIDENCE_REFS_MISSING"
        else:
            category = "EXACT_DECLARED_SCOPE_CANDIDATE"
        reviews.append({
            "index": index, "premise_id": identifier,
            "classification": category,
            "conflicting_fields": conflicts,
            "only_in_current": only_current, "only_in_prior": only_prior,
            "declared_validity": validity,
            "evidence_refs": refs[:12],
            "original_run_verified": False,
            "scientific_equivalence_verified": False,
            "automatic_stop": False,
        })
    return {
        "status": "ADVISORY_SCOPE_COMPARISON_ONLY",
        "proposal_premise_id": pid,
        "missing_critical_scope_fields": missing_critical,
        "reviews": reviews,
        "exact_declared_candidates": sum(
            x["classification"] == "EXACT_DECLARED_SCOPE_CANDIDATE" for x in reviews),
        "original_evidence_verified": False,
        "scientific_equivalence_verified": False,
        "automatic_stop": False,
        "execution_authorized": False,
    }
