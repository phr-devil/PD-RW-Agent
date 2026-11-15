"""Bounded optional fold-by-arm coverage check of an original hash-linked DEV/VAL Run.

Both files must be linked in the Run and hash-checked by verify_run_evidence.
The plan is *declared*, not independently shown to predate results. A complete
matrix is NOT proof of legitimate skips, correct labels or scientific validity.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from ..config import read_json, under_root
from ..schemas import AgentError

MAX_CELLS = 10_000
MAX_FILE_BYTES = 512 * 1024
MAX_ITEMS = 120
ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
STATUSES = {"COMPLETED", "FAILED", "NOT_RUN", "INVALID", "INCONCLUSIVE", "SKIPPED"}


def _result(status: str, detail: str, **kwargs) -> dict:
    return {"status": status, "detail": detail,
            "original_plan_freeze_verified": False,
            "scientific_validity_verified": False,
            "sealed_access": "NOT_ATTEMPTED", **kwargs}


def _identifiers(items: object) -> bool:
    return (isinstance(items, list) and 1 <= len(items) <= MAX_ITEMS
            and len(set(items)) == len(items)
            and all(isinstance(x, str) and ID.fullmatch(x) for x in items))


def _read_matrix(root: Path, relative: str) -> list[dict]:
    path = under_root(root, relative, must_exist=True)
    if path.stat().st_size > MAX_FILE_BYTES:
        raise AgentError("MATRIX_OVERSIZE", "Matrix exceeds read limit")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if (reader.fieldnames is None or
                set(reader.fieldnames) != {"fold_id", "arm_id", "status"}
                or len(reader.fieldnames) != 3):
            raise ValueError("INVALID_MATRIX_COLUMNS")
        rows = []
        for row in reader:
            if len(rows) >= MAX_CELLS:
                raise ValueError("MATRIX_ROWS_EXCEEDED")
            if (None in row or set(row) != {"fold_id", "arm_id", "status"}
                    or any(not isinstance(v, str) for v in row.values())
                    or not ID.fullmatch(row["fold_id"])
                    or not ID.fullmatch(row["arm_id"])
                    or row["status"] not in STATUSES):
                raise ValueError("INVALID_MATRIX_ROW")
            rows.append(row)
    return rows


def audit_matrix_coverage(root: Path, run_id: str, refs: dict) -> dict:
    """Read optional plan and observation sources bound to an already checked Run."""
    plan_ref, observed_ref = refs.get("evaluation_plan"), refs.get("evaluation_results")
    if not plan_ref and not observed_ref:
        return _result("UNKNOWN", "No Run-linked matrix plan or observations")
    if not isinstance(plan_ref, str) or not isinstance(observed_ref, str):
        return _result("UNKNOWN", "Plan/observation pair is not fully Run-linked")
    try:
        plan = read_json(under_root(root, plan_ref, must_exist=True),
                         limit=MAX_FILE_BYTES)
        rows = _read_matrix(root, observed_ref)
    except (AgentError, OSError, UnicodeError) as exc:
        return _result("UNKNOWN", "Cannot inspect bounded Run-linked matrix sources",
                       reason=getattr(exc, "code", "SOURCE_UNAVAILABLE"))
    except ValueError as exc:
        return _result("FAIL", "Malformed matrix observation source",
                       reason=str(exc))

    folds, arms = plan.get("fold_ids"), plan.get("arm_ids")
    if (plan.get("schema_version") != "pdrw-evaluation-matrix-v1"
            or plan.get("run_id") != run_id
            or not _identifiers(folds) or not _identifiers(arms)
            or len(folds) * len(arms) > MAX_CELLS):
        return _result("FAIL", "Invalid or inconsistent declared matrix plan")
    skips = plan.get("declared_skips", [])
    if not isinstance(skips, list) or len(skips) > MAX_CELLS:
        return _result("FAIL", "Invalid declared skip list")
    declared_skips = set()
    for item in skips:
        if (not isinstance(item, dict) or
                set(item) != {"fold_id", "arm_id", "reason"} or
                not isinstance(item["reason"], str) or
                not 1 <= len(item["reason"].strip()) <= 240 or
                item["fold_id"] not in folds or item["arm_id"] not in arms):
            return _result("FAIL", "Malformed declared skip")
        key = (item["fold_id"], item["arm_id"])
        if key in declared_skips:
            return _result("FAIL", "Duplicate declared skip")
        declared_skips.add(key)

    expected = {(fold, arm) for fold in folds for arm in arms}
    observed = {}
    duplicates = set()
    for row in rows:
        key = (row["fold_id"], row["arm_id"])
        if key in observed:
            duplicates.add(key)
        observed[key] = row["status"]
    missing = expected - observed.keys()
    unexpected = observed.keys() - expected
    unplanned_skips = {key for key, status in observed.items()
                       if status == "SKIPPED" and key not in declared_skips}
    unresolved = {key for key, status in observed.items()
                  if status in {"FAILED", "NOT_RUN", "INVALID", "INCONCLUSIVE"}}
    declared_skip_mismatch = {key for key in declared_skips
                              if observed.get(key) != "SKIPPED"}
    severe = bool(duplicates or unexpected or unplanned_skips)
    requires_review = bool(missing or unresolved or declared_skips or declared_skip_mismatch)
    status = "FAIL" if severe else "REVIEW" if requires_review else "PASS"

    def short(keys):
        return [{"fold_id": a, "arm_id": b} for a, b in sorted(keys)[:20]]

    return _result(
        status, ("Observed cell keys conflict with the declared plan" if severe else
                 "Missing, incomplete or declared-skipped cells require review"
                 if requires_review else "All declared cells have COMPLETED records"),
        expected_cells=len(expected), observation_rows=len(rows),
        unique_observed_cells=len(observed),
        missing_count=len(missing), missing_cells=short(missing),
        unexpected_count=len(unexpected), unexpected_cells=short(unexpected),
        duplicate_count=len(duplicates), duplicate_cells=short(duplicates),
        unplanned_skip_count=len(unplanned_skips),
        declared_skip_count=len(declared_skips),
        declared_skip_mismatch_count=len(declared_skip_mismatch),
        incomplete_count=len(unresolved),
        complete_count=sum(1 for k, v in observed.items()
                           if k in expected and v == "COMPLETED"),
        cell_lists_truncated=any(len(keys) > 20 for keys in
                                 (missing, unexpected, duplicates)),
        note="Source bytes match original Run links, but plan preregistration, "
             "skip legitimacy and per-cell metrics are not certified.")
