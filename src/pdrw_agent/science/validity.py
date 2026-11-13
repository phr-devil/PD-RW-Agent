"""Source-bound scientific evaluation checks for registered DEV/VAL Runs.

Recompute metrics from hash-checked predictions, test declared split groups
and baseline comparability. This is NOT an independent truth, causal, legal
inputs, or original user authorization attestation. Never reads SEALED files.
"""
from __future__ import annotations

import csv
import math
import hashlib
import re
from collections import defaultdict
from pathlib import Path

from ..config import Settings, read_json, under_root
from ..evidence import _events
from ..schemas import AgentError
from .run_integrity import verify_run_evidence
from .lineage import audit_python_code, audit_content_fingerprints

MAX_CSV_BYTES = 8 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 24
MAX_VALUE_LEN = 512
METRICS = {"MAE", "RMSE", "accuracy", "macro_f1"}
REQUIRED_PRED = {"sample_id", "group_id", "y_true", "y_pred"}
REQUIRED_TRAIN = {"sample_id", "group_id"}
COMPARABLE = ("task_id", "protocol_id", "dataset_version",
              "evaluator_version", "split", "group_split", "sample_ids_hash",
              "level_id", "k_unit", "support_query_policy",
              "label_definition", "evaluation_unit", "metric_direction")
TOL_ABS = 1e-7
TOL_REL = 1e-6


def _check(status: str, detail: str, **extra) -> dict:
    return {"status": status, "detail": detail, **extra}


def _csv_rows(root: Path, relative: str, required: set[str]) -> list[dict[str, str]]:
    path = under_root(root, relative, must_exist=True)
    if path.stat().st_size > MAX_CSV_BYTES:
        raise AgentError("EVALUATION_CSV_OVERSIZE", "Source exceeds bounded audit size")
    result: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8-sig") as fp:
        reader = csv.DictReader(fp)
        fields = reader.fieldnames
        if (not fields or len(fields) > MAX_COLUMNS or len(set(fields)) != len(fields)
                or not required.issubset(fields)):
            raise AgentError("EVALUATION_SCHEMA_INVALID", "Missing/duplicate evaluation columns")
        seen: set[str] = set()
        for row in reader:
            if len(result) >= MAX_ROWS:
                raise AgentError("EVALUATION_ROWS_EXCEEDED", "Rows exceed bounded audit size")
            if (None in row or any(not isinstance(v, str) or len(v) > MAX_VALUE_LEN
                                   for v in row.values())):
                raise AgentError("EVALUATION_ROW_INVALID", "Malformed or oversized CSV cell")
            sample_id = row["sample_id"].strip()
            group_id = row["group_id"].strip()
            if not sample_id or not group_id or sample_id in seen:
                raise AgentError("EVALUATION_KEYS_INVALID",
                                 "Missing/duplicate sample or group identifier")
            if any(not row[k].strip() for k in required):
                raise AgentError("EVALUATION_ROW_INVALID", "Required cell is empty")
            seen.add(sample_id)
            result.append(row)
    if not result:
        raise AgentError("EVALUATION_ROWS_MISSING", "No evaluation rows")
    return result


def _metric(rows: list[dict[str, str]], metric: str, unit: str,
            class_labels: list[str]) -> tuple[float, int]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["group_id"]].append(row)
    if metric in {"MAE", "RMSE"}:
        try:
            sq = [(float(x["y_true"]) - float(x["y_pred"])) ** 2 for x in rows]
            diffs = [abs(float(x["y_true"]) - float(x["y_pred"])) for x in rows]
        except (ValueError, OverflowError) as exc:
            raise AgentError("EVALUATION_NUMERIC_INVALID", "Regression requires numeric labels") from exc
        if not all(math.isfinite(x) for x in sq + diffs):
            raise AgentError("EVALUATION_NUMERIC_INVALID", "Metrics require finite values")
        if unit == "sample":
            score = (sum(diffs) / len(diffs) if metric == "MAE"
                     else math.sqrt(sum(sq) / len(sq)))
        else:
            # An explicit group-macro convention. For RMSE: mean(group RMSE),
            # not sqrt(mean(group MSE)). No implicit unit conversion.
            group_scores = []
            for subset in groups.values():
                ds = [abs(float(x["y_true"]) - float(x["y_pred"])) for x in subset]
                v = (sum(ds) / len(ds) if metric == "MAE"
                     else math.sqrt(sum(d*d for d in ds) / len(ds)))
                group_scores.append(v)
            score = sum(group_scores) / len(group_scores)
        return score, len(groups)
    if unit == "group":
        raise AgentError("GROUP_CLASSIFICATION_UNSUPPORTED",
                         "No implicit majority-vote or grouped F1 definition")
    if metric == "accuracy":
        return sum(x["y_true"] == x["y_pred"] for x in rows) / len(rows), len(groups)
    # Every class must be declared in advance; never silently exclude a rare
    # class or change the denominator based on which labels appeared.
    if (not class_labels or len(class_labels) > 100
            or any(not isinstance(x, str) or not x.strip() for x in class_labels)
            or len(set(class_labels)) != len(class_labels)):
        raise AgentError("CLASS_UNIVERSE_REQUIRED",
                         "Macro-F1 needs a fixed nonempty class list")
    observed = {v for x in rows for v in (x["y_true"], x["y_pred"])}
    if not observed.issubset(class_labels):
        raise AgentError("CLASS_UNIVERSE_MISMATCH", "Unknown label in prediction data")
    f1s = []
    for cls in class_labels:
        tp = sum(x["y_true"] == cls and x["y_pred"] == cls for x in rows)
        fp = sum(x["y_true"] != cls and x["y_pred"] == cls for x in rows)
        fn = sum(x["y_true"] == cls and x["y_pred"] != cls for x in rows)
        den = 2 * tp + fp + fn
        f1s.append(2 * tp / den if den else 0.0)
    return sum(f1s) / len(f1s), len(groups)


def _membership(rows: list[dict[str, str]]) -> dict[str, str]:
    return {row["sample_id"]: row["group_id"] for row in rows}


def _sorted_id_digest(rows: list[dict[str, str]]) -> str:
    # Defined canonicalization: UTF-8 sorted exact IDs, each with final LF.
    h = hashlib.sha256()
    for sid in sorted(row["sample_id"] for row in rows):
        h.update(sid.encode("utf-8") + b"\n")
    return h.hexdigest()


def _pred_identity(rows: list[dict[str, str]]) -> dict[str, tuple[str, str]]:
    return {row["sample_id"]: (row["group_id"], row["y_true"]) for row in rows}


def audit_scientific_experiment(settings: Settings, project_id: str,
                                run_id: str, baseline_run_id: str = "") -> dict:
    """Return independently computed *selected* checks, never science PASS."""
    if not isinstance(run_id, str) or not 1 <= len(run_id) <= 100:
        raise AgentError("RUN_ID_INVALID", "Run ID must be bounded text")
    if not isinstance(baseline_run_id, str) or len(baseline_run_id) > 100:
        raise AgentError("RUN_ID_INVALID", "Invalid baseline ID")
    base = {
        "project_id": project_id, "run_id": run_id,
        "scientific_validity_verified": False, "original_authorization_verified": False,
        "sealed_access": "NOT_ATTEMPTED", "execution_authorized": False,
        "source_scope": "HASHED_DEV_VAL_RUN_AND_DECLARED_SCIENCE_AUDIT_ONLY",
    }
    root, _ = settings.project(project_id)
    # Verify original Run, linked hashes, machine state and PD-RW contract first.
    result = verify_run_evidence(settings, project_id, run_id)
    if result["status"] != "RUN_BYTES_MATCHED_ONLY":
        return {**base, "status": "AUDIT_PREREQUISITE_UNVERIFIED",
                "run_evidence_status": result["status"]}
    event = next((e for e in _events(root)
                  if e.get("kind") == "run" and e.get("artifact_id") == run_id), None)
    if not event or event.get("split") not in ("dev", "validation"):
        return {**base, "status": "AUDIT_PREREQUISITE_UNVERIFIED"}
    obj = read_json(under_root(root, event["artifact_path"], must_exist=True),
                    limit=2 * 1024 * 1024)
    refs = obj.get("artifact_refs", {})
    spec_ref = refs.get("science_audit")
    if not isinstance(spec_ref, str):
        return {**base, "status": "AUDIT_SPEC_NOT_BOUND_TO_RUN"}
    try:
        spec = read_json(under_root(root, spec_ref, must_exist=True), limit=128 * 1024)
    except (AgentError, OSError) as exc:
        return {**base, "status": "AUDIT_SPEC_INVALID",
                "reason": getattr(exc, "code", "READ_FAILED")}
    if (spec.get("schema_version") != "pdrw-science-audit-v1"
            or spec.get("run_id") != run_id
            or spec.get("metric") not in METRICS
            or spec.get("evaluation_unit") not in {"sample", "group"}
            or spec.get("independence_unit") not in {"sample", "group"}):
        return {**base, "status": "AUDIT_SPEC_INVALID"}
    metric = spec["metric"]
    unit = spec["evaluation_unit"]
    labels = spec.get("class_labels", [])
    if not isinstance(labels, list):
        return {**base, "status": "AUDIT_SPEC_INVALID"}
    checks = {}
    if obj.get("evaluation_unit") not in {"sample", "group"}:
        checks["evaluation_unit"] = _check(
            "UNKNOWN", "Original Run does not declare evaluation_unit")
    elif obj["evaluation_unit"] != unit:
        checks["evaluation_unit"] = _check(
            "FAIL", "Original Run and hashed audit specify different units")
    else:
        checks["evaluation_unit"] = _check(
            "PASS", "Declared unit is consistent; its scientific appropriateness is unverified",
            unit=unit)

    original_independence = obj.get("independence_unit")
    if original_independence not in {"sample", "group"}:
        checks["split_policy_alignment"] = _check(
            "UNKNOWN", "Run does not independently declare a split independence unit")
    elif original_independence != spec["independence_unit"]:
        checks["split_policy_alignment"] = _check(
            "FAIL", "Run and hashed audit declare different split independence units")
    else:
        checks["split_policy_alignment"] = _check(
            "PASS", "Run and audit independence declarations agree; underlying grouping remains unverified")

    declared_inputs = spec.get("used_inputs_declared")
    legal = obj.get("legal_inputs")
    if (not isinstance(declared_inputs, list) or not declared_inputs
            or any(not isinstance(s, str) or not s for s in declared_inputs)
            or not isinstance(legal, list)):
        checks["input_legality"] = _check("UNKNOWN", "Feature lineage not supplied")
    else:
        illegal = sorted(set(declared_inputs) - set(legal))
        checks["input_legality"] = _check(
            "FAIL" if illegal else "UNKNOWN",
            ("Declared illegal model inputs" if illegal else
             "Declared inputs within Run allowlist; actual code/dataflow not independently traced"),
            declared_out_of_scope=illegal, code_lineage_verified=False)

    if spec.get("independence_unit") == "group":
        split_policy = "GROUP_DISJOINT"
    else:
        split_policy = "SAMPLE_DISJOINT"

    try:
        pred = _csv_rows(root, refs["predictions"], REQUIRED_PRED)
    except (AgentError, KeyError, UnicodeError, ValueError, OSError) as exc:
        return {**base, "status": "EVALUATION_SOURCE_INVALID",
                "reason": getattr(exc, "code", "PREDICTIONS_NOT_AVAILABLE"),
                "checks": checks}
    checks["evaluation_rows"] = _check(
        "PASS", "Bounded predictions have unique sample IDs and nonempty group IDs",
        n_samples=len(pred), n_groups=len({x["group_id"] for x in pred}))
    checks["source_code_lineage"] = audit_python_code(
        root, refs.get("code", ""), obj.get("legal_inputs", []))
    # The legacy sample_ids_hash is not defined to use one universal encoding.
    # Only verify if a frozen audit explicitly selects our canonicalization.
    fingerprint_rule = spec.get("sample_ids_hash_rule")
    if fingerprint_rule is None:
        checks["sample_identity_fingerprint"] = _check(
            "UNKNOWN", "No original canonical sample-ID hash convention declared")
    elif fingerprint_rule != "sha256_sorted_ids_v1":
        checks["sample_identity_fingerprint"] = _check(
            "UNKNOWN", "Unrecognized declared sample-ID fingerprint convention")
    else:
        declared_digest = obj.get("sample_ids_hash")
        calculated_digest = _sorted_id_digest(pred)
        valid_digest = (isinstance(declared_digest, str) and
                        bool(re.fullmatch(r"[a-fA-F0-9]{64}", declared_digest)))
        checks["sample_identity_fingerprint"] = _check(
            "PASS" if valid_digest and calculated_digest.casefold() == declared_digest.casefold()
            else "FAIL" if valid_digest else "UNKNOWN",
            ("Canonical sorted evaluation IDs match Run declaration"
             if valid_digest and calculated_digest.casefold() == declared_digest.casefold()
             else "Canonical evaluation IDs disagree with Run declaration"
             if valid_digest else "Run uses no supported 64-hex sample fingerprint"),
            rule=fingerprint_rule)
    # Explicit input train_index must be a link registered with and hash-checked
    # by verify_run_evidence. No free-standing, unanchored train CSV.
    train_ref = refs.get("train_index")
    train_rows = None
    if train_ref is None:
        checks["split_leakage"] = _check(
            "UNKNOWN", "No Run-linked training membership manifest; leakage cannot be ruled out",
            declared_independence_unit=spec["independence_unit"])
    else:
        try:
            train = _csv_rows(root, train_ref, REQUIRED_TRAIN)
            train_rows = train
            train_ids = {x["sample_id"] for x in train}
            eval_ids = {x["sample_id"] for x in pred}
            train_groups = {x["group_id"] for x in train}
            eval_groups = {x["group_id"] for x in pred}
            shared_ids = len(train_ids & eval_ids)
            shared_groups = len(train_groups & eval_groups)
            leak = shared_ids > 0 or (split_policy == "GROUP_DISJOINT"
                                       and shared_groups > 0)
            checks["split_leakage"] = _check(
                "FAIL" if leak else "PASS",
                ("Direct reuse of identifiers across train/evaluation" if leak
                 else "No exact ID overlap under the declared independence policy; near-duplicates untested"),
                shared_sample_ids=shared_ids, shared_groups=shared_groups,
                declared_independence_unit=spec["independence_unit"],
                observed_groups=len(eval_groups))
        except (AgentError, UnicodeError, ValueError, OSError) as exc:
            code = getattr(exc, "code", "TRAIN_INDEX_READ_FAILED")
            invalid = code in {"EVALUATION_KEYS_INVALID", "EVALUATION_ROW_INVALID",
                               "EVALUATION_SCHEMA_INVALID", "EVALUATION_ROWS_MISSING"}
            checks["split_leakage"] = _check(
                "FAIL" if invalid else "UNKNOWN",
                "Training membership malformed" if invalid else
                "Training index unavailable or not fully inspected",
                reason=code)

    checks["cross_split_content_identity"] = audit_content_fingerprints(
        root, refs, pred, train_rows, _csv_rows,
        spec.get("content_fingerprint_rule"))

    try:
        recomputed, groups = _metric(pred, metric, unit, labels)
    except AgentError as exc:
        checks["metric_recomputation"] = _check(
            "UNKNOWN", "Metric cannot be recomputed under the declared convention",
            reason=exc.code)
    else:
        stored = obj.get("metrics", {}).get(metric)
        equal = (isinstance(stored, (int, float)) and not isinstance(stored, bool)
                 and math.isfinite(stored)
                 and math.isclose(recomputed, stored, rel_tol=TOL_REL, abs_tol=TOL_ABS))
        checks["metric_recomputation"] = _check(
            "PASS" if equal else "FAIL",
            ("Computed value matches registered Run metric" if equal
             else "Computed value differs from registered Run metric"),
            metric=metric, computed=recomputed, registered=stored,
            evaluation_unit=unit, n_groups=groups,
            formula=("equal_group_mean_of_per_group_metrics" if unit == "group"
                     else "sample_micro_metric"),
            tolerance={"relative": TOL_REL, "absolute": TOL_ABS})
    baseline_expected = spec.get("baseline_run_id", "")
    if (not isinstance(baseline_expected, str)
            or len(baseline_expected) > 100
            or (baseline_run_id and baseline_run_id != baseline_expected)):
        checks["baseline_fairness"] = _check(
            "FAIL", "Supplied baseline ID conflicts with registered audit specification")
    elif not baseline_expected:
        checks["baseline_fairness"] = _check(
            "UNKNOWN", "No frozen baseline reference")
    elif baseline_expected == run_id:
        checks["baseline_fairness"] = _check(
            "FAIL", "Baseline cannot be the same Run as the challenger")
    else:
        prior = verify_run_evidence(settings, project_id, baseline_expected)
        if prior["status"] != "RUN_BYTES_MATCHED_ONLY":
            checks["baseline_fairness"] = _check(
                "UNKNOWN", "Baseline original evidence is not independently hash-checked",
                baseline_evidence_status=prior["status"])
        else:
            baseline_event = next((e for e in _events(root)
                                   if e.get("kind") == "run" and
                                   e.get("artifact_id") == baseline_expected), None)
            assert baseline_event is not None
            past = read_json(
                under_root(root, baseline_event["artifact_path"], must_exist=True),
                limit=2 * 1024 * 1024)
            different = [k for k in COMPARABLE if obj.get(k) != past.get(k)]
            if sorted(obj.get("legal_inputs", [])) != sorted(past.get("legal_inputs", [])):
                different.append("legal_inputs")
            uncertain = []
            if not obj.get("budget_basis") or not past.get("budget_basis"):
                uncertain.append("budget_basis_not_declared")
            elif obj["budget_basis"] != past["budget_basis"]:
                different.append("budget_basis")
            if not obj.get("label_definition") or not past.get("label_definition"):
                uncertain.append("label_definition_not_declared")
            if not obj.get("metric_direction") or not past.get("metric_direction"):
                uncertain.append("metric_direction_not_declared")
            try:
                base_rows = _csv_rows(
                    root, past["artifact_refs"]["predictions"], REQUIRED_PRED)
                identity_agrees = _pred_identity(base_rows) == _pred_identity(pred)
                base_score, _ = _metric(base_rows, metric, unit, labels)
                stored = past.get("metrics", {}).get(metric)
                base_metric_agrees = (isinstance(stored, (int, float))
                                      and not isinstance(stored, bool)
                                      and math.isfinite(stored)
                                      and math.isclose(base_score, stored,
                                                       rel_tol=TOL_REL, abs_tol=TOL_ABS))
                if not identity_agrees:
                    different.append("prediction_identity_or_ground_truth")
                if not base_metric_agrees:
                    different.append("baseline_metric")
                if past.get("evaluation_unit") != unit:
                    different.append("baseline_evaluation_unit")
                prior_train_ref = past.get("artifact_refs", {}).get("train_index")
                if train_rows is None or not isinstance(prior_train_ref, str):
                    uncertain.append("training_membership_not_bound")
                else:
                    other_train = _csv_rows(root, prior_train_ref, REQUIRED_TRAIN)
                    if _membership(other_train) != _membership(train_rows):
                        different.append("training_membership")
                checks["baseline_fairness"] = _check(
                    "FAIL" if different else "UNKNOWN" if uncertain else "PASS",
                    ("Baseline not structurally comparable" if different else
                     "Training budget/lineage not fully declared" if uncertain else
                     "Matching train/eval memberships, metric and recorded protocol; tuning fairness unverified"),
                    differing_fields=sorted(set(different)),
                    unresolved_fields=sorted(set(uncertain)),
                    baseline_metric_recomputed=base_score,
                    equal_evaluation_rows=identity_agrees)
            except (AgentError, KeyError, UnicodeError, ValueError, OSError) as exc:
                checks["baseline_fairness"] = _check(
                    "UNKNOWN", "Cannot recompute baseline under the specified metric",
                    reason=getattr(exc, "code", "BASELINE_UNAVAILABLE"))

    failures = sorted(k for k, v in checks.items() if v["status"] == "FAIL")
    reviews = sorted(k for k, v in checks.items() if v["status"] == "REVIEW")
    unknown = sorted(k for k, v in checks.items() if v["status"] == "UNKNOWN")
    status = ("SCIENTIFIC_AUDIT_CONFLICT" if failures else
              "SCIENTIFIC_AUDIT_REVIEW_REQUIRED" if reviews else
              "SCIENTIFIC_AUDIT_INCOMPLETE" if unknown else
              "SCOPED_NUMERIC_CHECKS_MATCHED_ONLY")
    return {
        **base, "status": status, "metric": metric,
        "evaluation_unit_declared": unit,
        "independence_unit_declared": spec["independence_unit"],
        "checks": checks, "failed_checks": failures,
        "review_checks": reviews, "unknown_checks": unknown,
        "all_scientific_conditions_verified": False,
        "scientific_claims_verified": False,
        "original_code_inputs_traced": False,
        "dataset_label_semantics_verified": False,
        "near_duplicate_leakage_excluded": False,
        "confirmation_unlocked": False,
        "note": ("These checks are scoped to frozen, hashed DEV/VAL files. "
                 "A PASS never authenticates original labels, pipeline feature "
                 "availability, training code, independence, causality or generalization."),
    }
