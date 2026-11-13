"""Bounded, non-executing Python AST review and declared input-hash collision checks.

This is a deliberately narrow reviewer: source bytes are already linked and
verified by the caller. It never imports/executes submitted code or returns
private rows. Dynamic pipelines and unexamined source remain UNKNOWN.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

from ..config import under_root
from ..schemas import AgentError

MAX_CODE_BYTES = 256 * 1024
MAX_AST_NODES = 25_000
MAX_LITERAL_COLUMNS = 128
_FEATURE_SINK = re.compile(
    r"^(?:x(?:_(?:train|val|valid|test|eval))?|features?|"
    r"feature_matrix|input_features|model_inputs)$", re.I)
_EVAL_NAMES = re.compile(r"(?:^|_)(?:test|eval|validation|val)(?:_|$)", re.I)


def _literal_strings(node: ast.AST, aliases: dict[str, list[str] | None]) -> list[str] | None:
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        if len(node.elts) > MAX_LITERAL_COLUMNS:
            return None
        out = []
        for item in node.elts:
            if not isinstance(item, ast.Constant) or not isinstance(item.value, str):
                return None
            out.append(item.value)
        return out
    if isinstance(node, ast.Name):
        return aliases.get(node.id)
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    return None


def _selected_columns(node: ast.AST, aliases: dict[str, list[str] | None]) -> list[str] | None:
    """Recognize only direct dataframe-like column selection expressions."""
    if not isinstance(node, ast.Subscript):
        return None
    if isinstance(node.value, ast.Attribute) and node.value.attr == "loc":
        sl = node.slice
        if not isinstance(sl, ast.Tuple) or len(sl.elts) != 2:
            return None
        return _literal_strings(sl.elts[1], aliases)
    if isinstance(node.value, (ast.Name, ast.Attribute, ast.Subscript)):
        return _literal_strings(node.slice, aliases)
    return None


def audit_python_code(root: Path, code_ref: str, legal_inputs: list[str]) -> dict:
    """Review limited AST patterns; never present absence of findings as PASS."""
    base = {"status": "UNKNOWN", "scope": "BOUNDED_PYTHON_AST_ONLY",
            "code_executed": False, "trained_code_proven": False,
            "runtime_feature_lineage_verified": False}
    if not code_ref.endswith(".py"):
        return {**base, "reason": "NON_PYTHON_OR_UNKNOWN_CODE_FORMAT"}
    try:
        source = under_root(root, code_ref, must_exist=True)
        if source.stat().st_size > MAX_CODE_BYTES:
            return {**base, "reason": "CODE_TOO_LARGE"}
        source_text = source.read_text(encoding="utf-8-sig")
        tree = ast.parse(source_text)
    except (AgentError, UnicodeError, SyntaxError, OSError) as exc:
        return {**base, "reason": getattr(exc, "code", "CODE_NOT_PARSEABLE")}
    nodes = list(ast.walk(tree))
    if len(nodes) > MAX_AST_NODES:
        return {**base, "reason": "AST_TOO_LARGE"}

    # A variable used as a literal column list is only resolvable when it has
    # exactly one static assignment. Reassignments/dynamic expressions are
    # intentionally not treated as determinate feature lineage.
    candidates: dict[str, list[list[str] | None]] = {}
    for node in nodes:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    value = getattr(node, "value", None)
                    if isinstance(value, (ast.List, ast.Tuple, ast.Set)):
                        parsed = _literal_strings(value, {})
                    else:
                        parsed = None
                    candidates.setdefault(target.id, []).append(parsed)
    aliases = {k: values[0] if len(values) == 1 else None
               for k, values in candidates.items()}

    out_of_scope = []
    reviewed_sinks = 0
    unresolved_sinks = 0
    suspicious_eval_fit = 0
    for node in nodes:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if not any(isinstance(t, ast.Name) and _FEATURE_SINK.fullmatch(t.id)
                       for t in targets):
                continue
            reviewed_sinks += 1
            names = _selected_columns(node.value, aliases)
            if names is None:
                unresolved_sinks += 1
                continue
            illegal = sorted(set(names) - set(legal_inputs))
            if illegal:
                out_of_scope.append({"line": node.lineno,
                                     "declared_forbidden_column_count": len(illegal)})
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and (
                node.func.attr in {"fit", "fit_transform", "partial_fit"}):
            if node.args and isinstance(node.args[0], ast.Name) and (
                    _EVAL_NAMES.search(node.args[0].id)):
                suspicious_eval_fit += 1
    risks = []
    if out_of_scope:
        risks.append("STATIC_FEATURE_ALLOWLIST_CONFLICT")
    if suspicious_eval_fit:
        risks.append("POSSIBLE_EVALUATION_FIT_OR_PREPROCESSING_LEAK")
    return {**base,
            "status": "REVIEW" if risks else "UNKNOWN",
            "reason": "STATIC_RISK_CANDIDATES" if risks else "LIMITED_STATIC_COVERAGE",
            "risk_types": risks[:3], "feature_sink_count": reviewed_sinks,
            "unresolved_feature_sinks": unresolved_sinks,
            "forbidden_feature_sink_occurrences": len(out_of_scope),
            "affected_code_lines": [n["line"] for n in out_of_scope[:10]],
            "suspicious_fit_calls": suspicious_eval_fit,
            "note": ("AST is not execution. A risk requires manual source/Run review; "
                     "no finding never certifies legal training inputs.")}


def audit_content_fingerprints(root: Path, refs: dict, predictions: list[dict],
                               training: list[dict] | None,
                               csv_reader, fingerprint_rule: str | None = None) -> dict:
    """Compare declared canonical *input content* hashes on bound sample IDs.

    A shared hash is an observable collision under the source's own declared
    hashing convention, not independent proof that raw samples are identical.
    """
    base = {"status": "UNKNOWN",
            "source_truth_verified": False,
            "near_duplicate_independence_verified": False}
    if fingerprint_rule != "sha256_canonical_input_v1":
        return {**base, "reason": "CANONICAL_INPUT_FINGERPRINT_RULE_NOT_DECLARED"}
    train_ref = refs.get("train_content_hashes")
    eval_ref = refs.get("eval_content_hashes")
    if not isinstance(train_ref, str) or not isinstance(eval_ref, str):
        return {**base, "reason": "HASHED_CONTENT_MEMBERSHIPS_MISSING"}
    if training is None:
        return {**base, "reason": "ORIGINAL_TRAIN_MEMBERSHIP_UNAVAILABLE"}
    required = {"sample_id", "group_id", "feature_sha256"}
    try:
        train_fp = csv_reader(root, train_ref, required)
        eval_fp = csv_reader(root, eval_ref, required)
    except (AgentError, OSError, ValueError, UnicodeError) as exc:
        return {**base, "reason": getattr(exc, "code", "CONTENT_FINGERPRINT_READ_FAILED")}
    def membership(rows):
        return {r["sample_id"]: r["group_id"] for r in rows}
    if (membership(train_fp) != membership(training)
            or membership(eval_fp) != membership(predictions)):
        return {**base, "status": "FAIL", "reason": "CONTENT_FINGERPRINT_MEMBERSHIP_CONFLICT"}
    valid_sha = re.compile(r"[a-fA-F0-9]{64}\Z")
    if any(not valid_sha.fullmatch(r["feature_sha256"]) for r in train_fp + eval_fp):
        return {**base, "status": "FAIL", "reason": "CONTENT_FINGERPRINT_FORMAT_INVALID"}
    intersection = ({r["feature_sha256"].lower() for r in train_fp}
                    & {r["feature_sha256"].lower() for r in eval_fp})
    return {**base,
            "status": "FAIL" if intersection else "UNKNOWN",
            "reason": ("DECLARED_IDENTICAL_FEATURE_CONTENT_CROSS_SPLIT" if intersection
                       else "NO_EXACT_CONTENT_HASH_OVERLAP_ONLY"),
            "cross_split_content_hash_matches": len(intersection),
            "train_fingerprint_rows": len(train_fp),
            "evaluation_fingerprint_rows": len(eval_fp)}
