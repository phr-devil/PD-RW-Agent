"""Associate a declared negative lesson with a hash-bound original DEV/VAL Run.

The original Run, its linked lesson context, baseline and science audit are
inspected under the explicit project registry. A negative *metric observation*
does not prove that a scientific premise is false or license an automatic STOP.
"""
from __future__ import annotations

import math

from ..config import Settings, read_json, under_root
from ..evidence import _events
from ..schemas import AgentError
from .applicability import CRITICAL, review_lesson_applicability
from .run_integrity import verify_run_evidence
from .validity import audit_scientific_experiment

MAX_CONTEXT_BYTES = 128 * 1024


def review_evidenced_lesson(settings: Settings, project_id: str, run_id: str,
                           proposal: dict) -> dict:
    if not isinstance(proposal, dict):
        raise AgentError("LESSON_REVIEW_INVALID", "A structured proposed premise is required")
    base = {
        "project_id": project_id, "source_run_id": run_id,
        "original_run_verified_as_valid_science": False,
        "original_user_authorization_verified": False,
        "proposal_scope_verified": False,
        "pre_registration_verified": False,
        "scientific_equivalence_verified": False,
        "automatic_stop": False, "execution_authorized": False,
        "sealed_access": "NOT_ATTEMPTED",
    }
    result = verify_run_evidence(settings, project_id, run_id)
    if result["status"] != "RUN_BYTES_MATCHED_ONLY":
        return {**base, "status": "LESSON_RUN_NOT_ATTESTABLE",
                "run_evidence_status": result["status"]}
    root, _ = settings.project(project_id)
    event = next((e for e in _events(root)
                  if e.get("kind") == "run" and e.get("artifact_id") == run_id), None)
    if event is None or event.get("split") not in {"dev", "validation"}:
        return {**base, "status": "LESSON_RUN_NOT_ATTESTABLE"}
    run = read_json(under_root(root, event["artifact_path"], must_exist=True),
                    limit=2 * 1024 * 1024)
    if run.get("status") != "VALID":
        return {**base, "status": "LESSON_RUN_NOT_VALID",
                "run_status_declared": run.get("status")}
    context_ref = run.get("artifact_refs", {}).get("lesson_context")
    if not isinstance(context_ref, str):
        return {**base, "status": "LESSON_CONTEXT_UNBOUND"}
    try:
        context = read_json(under_root(root, context_ref, must_exist=True),
                            limit=MAX_CONTEXT_BYTES)
    except (AgentError, OSError, ValueError) as exc:
        return {**base, "status": "LESSON_CONTEXT_INVALID",
                "reason": getattr(exc, "code", "SOURCE_UNAVAILABLE")}
    if (context.get("schema_version") != "pdrw-run-lesson-v1"
            or context.get("run_id") != run_id
            or context.get("outcome") != "DECLARED_NEGATIVE"
            or not isinstance(context.get("premise_id"), str)
            or not context["premise_id"].strip()
            or not isinstance(context.get("scope"), dict)):
        return {**base, "status": "LESSON_CONTEXT_INVALID"}
    threshold = context.get("minimum_important_improvement")
    if (isinstance(threshold, bool) or not isinstance(threshold, (int, float))
            or not math.isfinite(threshold) or not 0 <= threshold <= 1e6):
        return {**base, "status": "LESSON_THRESHOLD_INVALID"}
    science = audit_scientific_experiment(settings, project_id, run_id)
    checks = science.get("checks", {})
    gates = ("split_leakage", "evaluation_unit", "split_policy_alignment",
             "metric_recomputation", "baseline_fairness")
    failed = [k for k in gates if checks.get(k, {}).get("status") != "PASS"]
    risks = [k for k, v in checks.items() if v["status"] in {"FAIL", "REVIEW"}]
    if failed or risks:
        return {**base, "status": "LESSON_SCIENCE_EVIDENCE_BLOCKED",
                "science_status": science["status"],
                "missing_or_failed_gates": failed,
                "scientific_review_or_conflict_checks": risks}
    audit_event = run.get("artifact_refs", {}).get("science_audit")
    if not isinstance(audit_event, str):
        return {**base, "status": "LESSON_SCIENCE_EVIDENCE_BLOCKED"}
    config = read_json(under_root(root, audit_event, must_exist=True),
                       limit=MAX_CONTEXT_BYTES)
    baseline_id = config.get("baseline_run_id")
    metric = config.get("metric")
    direction = run.get("metric_direction")
    if not isinstance(baseline_id, str) or not baseline_id or direction not in {"min", "max"}:
        return {**base, "status": "LESSON_METRIC_DIRECTION_UNKNOWN"}
    expected = {
        "dataset_version": run.get("dataset_version"),
        "label_definition": run.get("label_definition"),
        "evaluation_unit": run.get("evaluation_unit"),
        "group_split": run.get("group_split"),
        "legal_inputs": ",".join(sorted(run.get("legal_inputs", []))),
        "metric": metric,
        "comparison_reference": baseline_id,
    }
    source_scope = context["scope"]
    if (set(source_scope) != set(CRITICAL)
            or any(not isinstance(expected.get(key), str) or not expected[key]
                   or source_scope.get(key) != expected[key] for key in CRITICAL)):
        return {**base, "status": "LESSON_RUN_SCOPE_NOT_ANCHORED",
                "unanchored_or_mismatched_keys": sorted(
                    set(source_scope).symmetric_difference(CRITICAL)
                    | {k for k in CRITICAL if source_scope.get(k) != expected[k]})}
    observed = checks["metric_recomputation"]["computed"]
    baseline = checks["baseline_fairness"]["baseline_metric_recomputed"]
    improvement = (baseline - observed if direction == "min"
                   else observed - baseline)
    negative = improvement <= threshold
    scoped = review_lesson_applicability(
        proposal, [{
            "premise_id": context["premise_id"], "scope": source_scope,
            "validity": "VALID_NEGATIVE" if negative else "INCONCLUSIVE",
            "evidence_refs": [f"{project_id}:{run_id}"],
        }])
    matched = scoped["reviews"][0]["classification"] == "EXACT_DECLARED_SCOPE_CANDIDATE"
    return {**base,
            "status": ("RUN_LINKED_NEGATIVE_METRIC_CANDIDATE" if negative and matched
                       else "NEGATIVE_METRIC_NOT_OBSERVED" if not negative
                       else "LESSON_PREMISE_SCOPE_NOT_MATCHED"),
            "original_run_hash_bound": True,
            "original_run_structural_contract_checked": True,
            "metric_recomputed_from_original_predictions": True,
            "run_scoped_checks_passed": list(gates),
            "metric": metric, "direction_declared": direction,
            "challenger_metric_recomputed": observed,
            "baseline_metric_recomputed": baseline,
            "improvement_over_baseline": improvement,
            "minimum_important_improvement_declared": threshold,
            "negative_metric_observation": negative,
            "lesson_scope_comparison": scoped["reviews"][0],
            "unverified_science_dimensions": [
                "ORIGINAL_LABEL_TRUTH", "CODE_EXECUTION_PROVENANCE",
                "PREDICTION_TIME_AVAILABILITY", "DECLARED_THRESHOLD_PREREGISTRATION",
                "INDEPENDENT_CONFIRMATION", "GENERALIZABILITY"
            ],
            "note": ("This is an observed, recorded DEV/VAL metric delta under "
                     "declared scope, not a proved negative scientific conclusion."),
            }
