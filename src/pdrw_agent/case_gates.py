"""Case-experience application gates: 3 mandatory checkpoints + 2 triggers.

Design contract (local increment on the existing 0.5.4 CASE_LIBRARY adapter):

* Reuse, do not reimplement: actual retrieval, ranking, source verification,
  8-dimension applicability review and decision experiences all come from
  ``case_learning.case_search`` -> CASE_LIBRARY/scripts/search_cases.py.
  This module only DECIDES WHEN to call it, CACHES the verified result, and
  VERIFIES that a real retrieval + applicability judgement happened.
* No second science-state database. The cache is a bounded in-process
  OrderedDict keyed by a deterministic fingerprint; it is not a project
  STATE/EVENTS/Run store and writes nothing to disk.
* Enforcement level is declared honestly: WorkBuddy exposes no trusted
  state-transition interceptor here. Checkpoints are Skill/tool-level
  advisory requests, NOT hard gates. A `CASE_CHECK: COMPLETED` string is
  explicitly rejected by ``verify_gate_record``.
* No GO/STOP, no authorization change, no writes to CASE_LIBRARY, PD-RW,
  STATE, Run, EVENTS, SEALED or any frozen A/B/C snapshot.
"""
from __future__ import annotations

import copy
import hashlib
import json
from collections import OrderedDict

from . import case_learning
from .schemas import AgentError

CASE_GATES_VERSION = "1.0"
GATE_CACHE_SIZE = 32
MAX_EVENT_FIELDS = 16
MAX_TEXT_CHARS = 1200
MAX_SIGNALS = 12
MAX_CASES = 5

# --- The five triggers -----------------------------------------------------
# Mandatory checkpoints are tied to PD-RW H stages + the decision milestone
# that is ABOUT to happen, not to a loose keyword guess.
CHECKPOINTS = {
    "G1": {
        "kind": "MANDATORY_CHECKPOINT", "priority": 1,
        "h_stages": ("H2", "H3"), "milestone": "QUESTION_SELECTION",
        "focus": ("高度重合的已有研究", "历史失败前提是否仍成立",
                  "成功案例的关键条件", "值得探索的新科学问题"),
        "output_key": "selection_impact",
    },
    "G2": {
        "kind": "MANDATORY_CHECKPOINT", "priority": 2,
        "h_stages": ("H6", "H7"), "milestone": "PROTOCOL_FREEZE",
        "focus": ("数据/标签/预测时合法输入与时间因果性", "分组独立性/评价指标/强简单基线",
                  "算法机制是否重复历史无效前提", "更有判别价值且成本更低的实验设计"),
        "output_key": "concrete_checks",
    },
    "G3": {
        "kind": "MANDATORY_CHECKPOINT", "priority": 3,
        "h_stages": ("H8", "H9", "H10"), "milestone": "CLAIM_OR_CLOSURE",
        "focus": ("正负结果是否已有类似解释", "证据是否支持算法创新/机制/规律主张",
                  "成功经验、失败边界与替代方向", "可进入候选区的新经验"),
        "output_key": "contribution_review",
    },
}
CONDITIONAL = {
    "T1": {
        "kind": "CONDITIONAL_TRIGGER", "priority": 4,
        "focus": ("先区分工程错误/无效实验/证据不足/有效科研负结果",
                  "再建议下一项决定性行动"),
        "output_key": "anomaly_triage",
    },
    "T2": {
        "kind": "CONDITIONAL_TRIGGER", "priority": 5,
        "focus": ("可能改变资源投入、核心算法、数据范围或科学问题决策的经验",),
        "output_key": "decision_change_review",
    },
}
TRIGGER_PRIORITY = ("G1", "G2", "G3", "T1", "T2")

T1_SIGNALS = frozenset({
    "UNEXPECTED_RESULT", "CORE_MECHANISM_UNSUPPORTED",
    "SEVERE_EVALUATION_PROBLEM", "REPEATED_INEFFECTIVE_ATTEMPTS",
    "VALID_NEGATIVE_RESULT", "CONSECUTIVE_NEGATIVE_RESULTS",
})
T2_SIGNALS = frozenset({
    "RESOURCE_INCREASE", "CORE_ALGORITHM_CHANGE", "DATA_SCOPE_CHANGE",
    "SCIENTIFIC_QUESTION_CHANGE", "EVALUATION_CRITERION_CHANGE",
})
# Ordinary DEV work must never cause a repeated case retrieval.
DEV_SIGNALS = frozenset({
    "CODE_CHANGE", "HYPERPARAMETER_TUNING", "TEST_ONLY", "PLOTTING",
    "SAME_SCOPE_DEV", "BUG_FIX", "DOCUMENTATION", "REFACTOR",
})
KNOWN_SIGNALS = T1_SIGNALS | T2_SIGNALS | DEV_SIGNALS
MILESTONES = frozenset({"QUESTION_SELECTION", "PROTOCOL_FREEZE",
                        "CLAIM_OR_CLOSURE", "NONE", ""})
H_STAGES = frozenset({"H1", "H2", "H3", "H4", "H5", "H6", "H7",
                      "H8", "H9", "H10", "DEV", ""})
OUTCOME_CLASSES = {
    "ENGINEERING_FAILURE": "工程错误：先核对实现/环境/日志，不计入科研负结果",
    "INVALID_EVALUATION": "无效实验：先核对评价协议、泄漏与非法输入",
    "INSUFFICIENT_EVIDENCE": "证据不足：补齐最小判别证据，暂不形成结论",
    "VALID_SCIENTIFIC_NEGATIVE": "有效科研负结果：登记前提与边界，检索失败/修复案例",
    "UNKNOWN": "UNKNOWN：证据不足以区分上述四类，不得自行归类",
}

ENFORCEMENT = {
    "actual": "ADVISORY_SKILL_AND_TOOL_LEVEL",
    "host_state_transition_interception": False,
    "hard_gate": False,
    "can_block_work": False,
    "note": ("WorkBuddy exposes no trusted state-transition hook in this local "
             "checkout. The three checkpoints are requested by the Skill and "
             "executed only when case_gate_check is actually called; a "
             "CASE_CHECK text is not proof and verify_gate_record rejects it. "
             "This is NOT a hard gate. PD-RW H6/H8 author strategy decisions "
             "and paper-writing permissions are unchanged."),
}

_GATE_CACHE: "OrderedDict[str, dict]" = OrderedDict()


# --- Small helpers ---------------------------------------------------------
def _text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"))
    if isinstance(value, (list, tuple)):
        return " ".join(str(x) for x in value)
    return "" if value is None else str(value)


def _clip(value, n: int = 240) -> str:
    s = str(value).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _canonical_event(event) -> dict:
    if not isinstance(event, dict) or not event:
        raise AgentError("GATE_EVENT_REQUIRED", "A nonempty gate event object is required")
    if len(event) > MAX_EVENT_FIELDS:
        raise AgentError("GATE_EVENT_TOO_LARGE", "Gate event has too many fields")
    out = {}
    for key, value in event.items():
        if not isinstance(key, str) or len(key) > 48:
            raise AgentError("GATE_EVENT_INVALID", "Event keys must be bounded strings")
        if len(_text(value)) > MAX_TEXT_CHARS:
            raise AgentError("GATE_EVENT_INVALID", f"Event field {key} is too long")
        out[key] = value
    signals = out.get("signals") or []
    if not isinstance(signals, (list, tuple)) or len(signals) > MAX_SIGNALS:
        raise AgentError("GATE_EVENT_INVALID", "signals must be a bounded list")
    if any(not isinstance(s, str) for s in signals):
        raise AgentError("GATE_EVENT_INVALID", "signals must be strings")
    return out


def _digest(obj) -> str:
    raw = json.dumps(obj, ensure_ascii=True, sort_keys=True,
                     separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# --- 1. Trigger determination (Python, deterministic) ---------------------
def determine_trigger(event) -> dict:
    """Decide which of the five triggers fires; never guess from prose.

    Mandatory checkpoints outrank conditional triggers. Ordinary DEV signals
    are explicitly suppressed. Unknown declared signals are reported as
    UNKNOWN instead of being silently dropped or invented.
    """
    e = _canonical_event(event)
    stage = str(e.get("h_stage") or "").strip().upper()
    milestone = str(e.get("milestone") or "").strip().upper()
    signals = [str(s).strip().upper() for s in (e.get("signals") or [])]
    unknown_signals = sorted(set(signals) - KNOWN_SIGNALS)
    t1 = sorted(set(signals) & T1_SIGNALS)
    t2 = sorted(set(signals) & T2_SIGNALS)
    dev = sorted(set(signals) & DEV_SIGNALS)

    matched = []
    for gid, spec in CHECKPOINTS.items():
        if milestone == spec["milestone"]:
            matched.append((spec["priority"], gid))
    if t1:
        matched.append((CONDITIONAL["T1"]["priority"], "T1"))
    if t2:
        matched.append((CONDITIONAL["T2"]["priority"], "T2"))
    matched.sort()

    reasons = []
    if stage not in H_STAGES:
        reasons.append("UNKNOWN_H_STAGE:" + _clip(stage, 40))
    if milestone not in MILESTONES:
        reasons.append("UNKNOWN_MILESTONE:" + _clip(milestone, 40))
    if unknown_signals:
        reasons.append("UNKNOWN_DECLARED_SIGNALS:" + ",".join(unknown_signals))

    base = {
        "evaluated_priority_order": list(TRIGGER_PRIORITY),
        "declared_h_stage": stage, "declared_milestone": milestone,
        "matched_signals": {"T1": t1, "T2": t2, "DEV": dev},
        "suppressed_dev_signals": dev,
        "unknown_declared_signals": unknown_signals,
        "other_matched_triggers": [g for _, g in matched[1:]],
        "reasons": reasons,
        "decision": _clip(e.get("decision", "")),
    }
    if not matched:
        return {"status": "NO_TRIGGER", "trigger": "NO_TRIGGER",
                "trigger_kind": "NONE", "priority": None,
                "suppressed_reason": ("ORDINARY_DEV_ITERATION_NO_CASE_RETRIEVAL"
                                      if dev else "NO_CHECKPOINT_OR_MATERIAL_CHANGE_DECLARED"),
                **base}
    primary = matched[0][1]
    spec = CHECKPOINTS.get(primary) or CONDITIONAL[primary]
    stage_ok = stage in spec.get("h_stages", H_STAGES)
    return {
        "status": "TRIGGER_REQUIRED", "trigger": primary,
        "trigger_kind": spec["kind"], "priority": spec["priority"],
        "h_stages": list(spec.get("h_stages", [])),
        "focus": list(spec["focus"]),
        "output_key": spec["output_key"],
        "stage_in_expected_range": bool(stage_ok),
        **base,
    }


def triage_anomaly(event) -> dict:
    """T1: distinguish four outcome classes BEFORE suggesting a next action.

    All categories are DECLARED only; an unverified outcome stays UNKNOWN.
    """
    e = _canonical_event(event)
    declared = str(e.get("outcome_class") or "UNKNOWN").strip().upper()
    valid = declared in OUTCOME_CLASSES
    category = declared if valid else "UNKNOWN"
    refs = e.get("evidence_refs") or []
    has_refs = isinstance(refs, (list, tuple)) and bool(refs)
    status = "TRIAGE_ADVISORY_ONLY" if valid and declared != "UNKNOWN" else "UNKNOWN"
    reasons = []
    if not valid:
        reasons.append("UNKNOWN_OUTCOME_CLASS_NOT_DECLARED_OR_UNRECOGNISED")
    if category == "UNKNOWN":
        reasons.append("OUTCOME_CLASS_UNKNOWN")
    if not has_refs:
        reasons.append("EVIDENCE_REFS_NOT_DECLARED_DO_NOT_TREAT_AS_VERIFIED_NEGATIVE")
    return {
        "status": status, "category": category,
        "category_meaning": OUTCOME_CLASSES[category],
        "evidence_refs_declared": has_refs,
        "verification": "DECLARED_ONLY_NOT_INDEPENDENTLY_VERIFIED",
        "next_decisive_action": (
            "先按原 Run/日志区分上述类别，再从适用案例的 next_minimal_check "
            "选一项最小判别检查；不得把工程错误或证据不足升级为科研负结果"),
        "unknown_reasons": reasons,
        "automatic_go_stop": False,
        "decision_authority": "PD-RW_WORKFLOW_AND_AUTHOR_ONLY",
    }


# --- 2. Fingerprint + retrieval-record verification ------------------------
def gate_fingerprint(event, trigger: str, index_sha256: str) -> tuple[str, dict]:
    """Same Task + hypothesis + protocol + library version + trigger stage.

    Key premises (task_profile), evidence declarations and query/filters are
    included so a material change invalidates the cache.
    """
    e = _canonical_event(event)
    parts = {
        "tool": "case_gate_check",
        "gate_version": CASE_GATES_VERSION,
        "trigger": trigger,
        "project_id": str(e.get("project_id") or ""),
        "task_id": str(e.get("task_id") or ""),
        "hypothesis": _clip(_text(e.get("hypothesis")), 600),
        "protocol": _clip(_text(e.get("protocol")), 600),
        "case_library_version": str(e.get("case_library_version") or ""),
        "case_library_index_sha256": index_sha256,
        "h_stage": str(e.get("h_stage") or "").upper(),
        "milestone": str(e.get("milestone") or "").upper(),
        "query": _clip(str(e.get("query") or ""), 300),
        "filters": e.get("filters") or {},
        "task_profile": e.get("task_profile") or {},
        "evidence_declaration": _clip(_text({
            "outcome_class": e.get("outcome_class"),
            "evidence_refs": e.get("evidence_refs"),
            "signals": e.get("signals")}), 400),
    }
    return _digest(parts), parts


REQUIRED_RECORD_FIELDS = (
    "retrieval_executed", "retrieval_tool", "query_fingerprint",
    "index_sha256", "retrieval_scope", "retrieved_case_ids",
    "applicability_judgments", "source_verification_present",
)


def verify_gate_record(record, expected_index_sha256: str | None = None) -> dict:
    """Reject a bare `CASE_CHECK: COMPLETED` text as proof of a checkpoint.

    A verifiable record must show the real retrieval tool, the exact case
    library version, the recorded search scope, the returned case IDs and a
    per-case applicability judgement (or an explicit no-match record).
    """
    if not isinstance(record, dict):
        return {"status": "UNKNOWN", "unknown_reasons": ["RETRIEVAL_RECORD_NOT_AN_OBJECT"]}
    missing = [k for k in REQUIRED_RECORD_FIELDS if k not in record]
    reasons = []
    if missing:
        reasons.append("RETRIEVAL_RECORD_FIELDS_MISSING:" + ",".join(missing))
    if not record.get("retrieval_executed"):
        reasons.append("NO_ACTUAL_RETRIEVAL_RECORDED")
    if record.get("retrieval_tool") != "case_learning.case_search":
        reasons.append("RETRIEVAL_TOOL_NOT_THE_EXISTING_CASE_SEARCH")
    if expected_index_sha256 and record.get("index_sha256") != expected_index_sha256:
        reasons.append("INDEX_SHA256_CHANGED_RE_RETRIEVE_REQUIRED")
    ids = record.get("retrieved_case_ids") or []
    judgements = record.get("applicability_judgments") or {}
    if ids and not judgements:
        reasons.append("APPLICABILITY_NOT_JUDGED")
    if ids and not all(cid in judgements for cid in ids):
        reasons.append("APPLICABILITY_JUDGEMENT_INCOMPLETE")
    if not ids and not record.get("no_match"):
        reasons.append("NO_CASES_AND_NO_EXPLICIT_NO_MATCH_SCOPE")
    if not record.get("source_verification_present"):
        reasons.append("SOURCE_VERIFICATION_MISSING")
    if reasons:
        return {"status": "UNKNOWN", "unknown_reasons": reasons,
                "verified_fields": [k for k in REQUIRED_RECORD_FIELDS if k not in missing]}
    return {"status": "RETRIEVAL_AND_APPLICABILITY_VERIFIED",
            "verified_fields": list(REQUIRED_RECORD_FIELDS),
            "unknown_reasons": [],
            "note": "Verified tool-level evidence, NOT verified scientific equivalence or a hard gate."}


# --- 3. Build the compact advisory from the EXISTING case_search result ----
def _advisory_from_case_search(cl: dict, index_sha256: str, trigger: str) -> dict:
    cases = cl.get("cases") or {}
    results = cases.get("results") or []
    per_case = (cases.get("source_verification") or {}).get("per_case") or {}
    judgements = {c["case_id"]: c["classification"]
                  for c in ((cl.get("case_review") or {}).get("comparisons") or [])}
    experiences = (cl.get("decision_experiences") or {}).get("experiences") or []
    polarity = {e["case_id"]: e["polarity"] for e in experiences}

    admissibility = {}
    unknown_reasons = []
    compact_cases = []
    concrete_checks = []
    for r in results:
        cid = r["case_id"]
        grade = per_case.get(cid, {}).get("evidence_grade", "UNVERIFIED")
        judgement = judgements.get(cid, "NOT_REVIEWED")
        if judgement == "CONDITIONS_DIFFER":
            state = "UNKNOWN_CONDITIONS_DIFFER"
        elif grade != "DECISION_GRADE":
            state = "UNKNOWN_SOURCE_INSUFFICIENT"
        elif judgement == "EVIDENCE_INSUFFICIENT":
            state = "UNKNOWN_EVIDENCE_INSUFFICIENT"
        elif judgement == "APPLICABILITY_RISK":
            state = "ADMISSIBLE_WITH_RISK"
        else:
            state = "ADMISSIBLE_ADVISORY"
        admissibility[cid] = state
        if state.startswith("UNKNOWN"):
            unknown_reasons.append(f"{cid}:{state}")
        compact_cases.append({
            "case_id": cid, "verdict": r["verdict"],
            "evidence_class": r["evidence_class"], "evidence_grade": grade,
            "applicability": judgement, "admissibility": state,
            "polarity": polarity.get(cid, "NOT_ADMITTED"),
            "mechanisms": list(r.get("all_mechanisms") or [])[:3],
            "one_line_impact": _clip(
                (r.get("transferable_lesson") or r.get("premises") or [""])[0], 180),
            "evidence_paths": list(r.get("evidence_paths") or [])[:2],
        })
        if state.startswith("ADMISSIBLE"):
            for check in (r.get("next_minimal_check") or [])[:1]:
                concrete_checks.append({"case_id": cid, "check": _clip(check, 180)})

    no_match = cases.get("status") == "NO_CASE_MATCH" or not results
    if no_match:
        unknown_reasons.append("NO_CASE_MATCH_WITH_RECORDED_SCOPE")
    admissible = [c for c in compact_cases if c["admissibility"].startswith("ADMISSIBLE")]
    gate_status = "ADVISORY_AVAILABLE" if admissible else "UNKNOWN"
    if gate_status == "UNKNOWN" and not unknown_reasons:
        unknown_reasons.append("NO_ADMISSIBLE_DECISION_GRADE_CASE")
    # A case whose declared scope EXCLUDES the current task must not reach the
    # active advisory as a negative warning: that would wrongly negate a new
    # direction with different legal information conditions.
    conditions_differ = [cid for cid, state in admissibility.items()
                         if state == "UNKNOWN_CONDITIONS_DIFFER"]
    active_experiences = [e for e in experiences
                          if e["case_id"] not in set(conditions_differ)]
    return {
        "gate_status": gate_status,
        "unknown_reasons": unknown_reasons[:6],
        "case_admissibility": admissibility,
        "conditions_differ_not_transferred": conditions_differ,
        "compact_cases": compact_cases[:MAX_CASES],
        "concrete_checks": concrete_checks[:MAX_CASES],
        "experiences": [
            {"case_id": e["case_id"], "polarity": e["polarity"],
             "concrete_impact": _clip(e.get("concrete_impact", ""), 220),
             "transfer_classification": e.get("transfer_classification")}
            for e in active_experiences[:MAX_CASES]],
        "no_match": bool(no_match),
        "retrieval_scope": {
            "query": cases.get("query"), "filters": cases.get("filters"),
            "limit": MAX_CASES, "total_matches": cases.get("total_matches"),
            "returned": cases.get("returned"),
            "case_library_index_sha256": index_sha256,
            "source_of_truth": (cases.get("source_verification") or {}).get("source_of_truth"),
            "cases_in_index": (cases.get("source_verification") or {}).get("cases_in_index"),
        },
    }


def _checkpoint_outputs(trigger: str, advisory: dict, event: dict,
                        cl: dict, triage: dict | None) -> dict:
    out = {}
    if trigger == "G1":
        out["selection_impact"] = {
            "key_experiences": advisory["experiences"][:MAX_CASES],
            "highly_overlapping_research": "UNKNOWN_REQUIRES_LINE_BY_LINE_PREMISE_COMPARISON",
            "historical_failure_premises_still_hold": "UNKNOWN_REQUIRES_LINE_BY_LINE_PREMISE_COMPARISON",
            "success_key_conditions": [
                _clip(c, 160) for r in advisory["compact_cases"]
                if r["verdict"] == "SUCCESS"
                for c in ([r["one_line_impact"]] if r["admissibility"].startswith("ADMISSIBLE") else [])][:3],
            "new_scientific_questions": "UNKNOWN_NOT_INFERRED_FROM_CASE_CARDS",
            "new_direction_not_negated_by_historical_failure": True,
            "note": "历史失败只提供风险与检查项，不得自动否定具有不同合法信息条件的新方向。",
        }
    elif trigger == "G2":
        out["concrete_checks"] = advisory["concrete_checks"]
        out["protocol_design_review"] = {
            "declared_8_dimensions": sorted((event.get("task_profile") or {}).keys()),
            "applicable_checks": advisory["concrete_checks"][:MAX_CASES],
            "design_improvement": "ADVISORY_ONLY：仅将 ADMISSIBLE 案例的 next_minimal_check 转为具体协议检查；不自动改动实验或授权",
            "unknown_when_no_admissible_case": advisory["gate_status"] == "UNKNOWN",
        }
    elif trigger == "G3":
        out["contribution_review"] = {
            "similar_explanations": advisory["experiences"][:MAX_CASES],
            "evidence_supports_algorithm_innovation_or_mechanism_claim": "UNKNOWN_VERIFY_ORIGINAL_RUN",
            "failure_boundaries_and_alternatives": [
                {"case_id": c["case_id"], "admissibility": c["admissibility"]}
                for c in advisory["compact_cases"]][:MAX_CASES],
            "candidate_experiences_hint": {
                "tool": "extract_case_candidates",
                "status": "CANDIDATE_ONLY_NOT_FORMAL_CASE",
                "note": "仅从原始 Run 与既有科学审计提取候选，不写 STATE/Run/EVENTS/CASE_LIBRARY"},
            "author_strategy_required": True,
            "note": "H8 主 Claim 与重大升级仍由作者选择/明确委托；正式论文写作另行授权，本工具不改变 PD-RW 权限。",
        }
    elif trigger == "T1":
        out["anomaly_triage"] = triage
        out["failure_and_repair_experiences"] = advisory["experiences"][:MAX_CASES]
    elif trigger == "T2":
        out["decision_change_review"] = {
            "declared_material_changes": (determine_trigger(event)["matched_signals"]["T2"]),
            "potentially_decision_changing_experiences": advisory["experiences"][:MAX_CASES],
            "fingerprint_invalidation": "TASK_OR_SCOPE_CHANGE_PRODUCES_NEW_GATE_FINGERPRINT",
            "note": "普通代码修改、调参、测试、绘图及同范围 DEV 不触发；重大变化才请求检索。",
        }
    return out


# --- 4. Service-level entry point -----------------------------------------
def case_gate_check(settings, event: dict, detail: str = "compact",
                    *, index_override: dict | None = None) -> dict:
    """Trigger decision -> bounded cache -> REAL retrieval -> record verification.

    Returns a compact (<=5 cases) advisory by default; detail="full" attaches
    the existing case_search payload. Full evidence is otherwise reachable via
    the EXISTING `search_research_memory` / `review_case_transfer` MCP tools.
    """
    if detail not in {"compact", "full"}:
        raise AgentError("DETAIL_INVALID", "detail must be 'compact' or 'full'")
    e = _canonical_event(event)
    trig = determine_trigger(e)
    common = {
        "case_gates_version": CASE_GATES_VERSION,
        "trigger": trig["trigger"],
        "trigger_kind": trig["trigger_kind"],
        "priority": trig["priority"],
        "evaluated_priority_order": trig["evaluated_priority_order"],
        "other_matched_triggers": trig["other_matched_triggers"],
        "enforcement_level": dict(ENFORCEMENT),
        "automatic_go_stop": False,
        "may_proceed": True,
        "blocks_work": False,
        "decision_authority": "PD-RW_WORKFLOW_AND_AUTHOR_ONLY",
        "no_writes": True,
        "warning": case_learning.WARNING,
        "notice": case_learning.NOTICE,
    }

    if trig["status"] == "NO_TRIGGER":
        return {
            "status": "NO_CASE_RETRIEVAL_REQUIRED", "gate_status": "NOT_APPLICABLE",
            "retrieval_executed": False, "cache_hit": False,
            "suppressed_reason": trig["suppressed_reason"],
            "suppressed_dev_signals": trig["suppressed_dev_signals"],
            "unknown_declared_signals": trig["unknown_declared_signals"],
            "unknown_reasons": trig["reasons"],
            "detail": detail, **common,
        }

    try:
        root = case_learning.resolve_root(settings)
    except (AgentError, OSError, ValueError) as exc:
        return {
            "status": "CASE_LIBRARY_UNAVAILABLE", "gate_status": "UNKNOWN",
            "retrieval_executed": False, "cache_hit": False,
            "unknown_reasons": ["CASE_LIBRARY_ROOT_INVALID:" +
                                getattr(exc, "code", "CASE_LIBRARY_ERROR")],
            "detail": _clip(str(exc), 200),
            "detail_note": "案例库不可访问：明确报告原因，不伪造已完成检查，不阻塞无关的合法工作。",
            "checkpoint_focus": trig.get("focus"), **common,
        }
    if root is None:
        return {
            "status": "CASE_LIBRARY_UNAVAILABLE", "gate_status": "UNKNOWN",
            "retrieval_executed": False, "cache_hit": False,
            "unknown_reasons": [
                "CASE_LIBRARY_NOT_CONFIGURED",
                "SET_PDRW_CASE_LIBRARY_ROOT_OR_case_library_root_IN_PRIVATE_PROJECT_MAP"],
            "detail": "案例库不可访问：明确报告原因，不伪造已完成检查，不阻塞无关的合法工作。",
            "checkpoint_focus": trig.get("focus"),
            **common,
        }

    try:
        bundle = index_override or case_learning.load_index(root)
    except (AgentError, OSError, UnicodeError, ValueError) as exc:
        return {
            "status": "CASE_LIBRARY_UNAVAILABLE", "gate_status": "UNKNOWN",
            "retrieval_executed": False, "cache_hit": False,
            "unknown_reasons": ["CASE_LIBRARY_READ_FAILED:" +
                                getattr(exc, "code", "CASE_LIBRARY_ERROR")],
            "detail": _clip(str(exc), 200),
            "checkpoint_focus": trig.get("focus"), **common,
        }

    sha = bundle["sha256"]
    key, parts = gate_fingerprint(e, trig["trigger"], sha)
    if key in _GATE_CACHE:
        _GATE_CACHE.move_to_end(key)
        cached = copy.deepcopy(_GATE_CACHE[key])
        cached["cache_hit"] = True
        cached["reused_verified_record"] = True
        cached["retrieval_executed_this_call"] = False
        cached["verification"] = verify_gate_record(
            cached.get("retrieval_record"), sha)
        cached["token_budget"] = {
            "detail": detail, "cache_hit": True,
            "payload_chars": len(json.dumps(cached, ensure_ascii=False)),
            "new_retrieval_calls": 0,
        }
        if detail == "full" and cached.get("_full_payload") is not None:
            cached["full_case_payload"] = cached.pop("_full_payload")
        else:
            cached.pop("_full_payload", None)
        return cached

    query = str(e.get("query") or "").strip() or _default_query(trig["trigger"])
    filters = e.get("filters") or {}
    if not isinstance(filters, dict):
        raise AgentError("FILTERS_INVALID", "filters must be an object")
    profile = e.get("task_profile")
    # A checkpoint must produce a REAL applicability judgement, not a text
    # flag. Without declared task dimensions there is nothing to compare, so
    # report UNKNOWN rather than fabricating a completed check.
    if not isinstance(profile, dict) or not profile:
        return {
            "status": "TASK_PROFILE_REQUIRED", "gate_status": "UNKNOWN",
            "retrieval_executed": False, "cache_hit": False,
            "unknown_reasons": ["TASK_PROFILE_REQUIRED_FOR_APPLICABILITY_REVIEW",
                                "NO_COMPLETED_CHECK_CLAIMED_WITHOUT_REAL_RETRIEVAL"],
            "detail": ("声明 task_profile 的 8 个维度后再执行本检查点；"
                       "缺失时标 UNKNOWN，不伪造检查完成，也不阻塞无关的合法工作。"),
            "checkpoint_focus": trig.get("focus"), **common,
        }

    try:
        cl = case_learning.case_search(
            settings, query, filters, limit=MAX_CASES,
            task_profile=profile, max_experiences=MAX_CASES,
            index_override=bundle)
    except (AgentError, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        return {
            "status": "CASE_LIBRARY_UNAVAILABLE", "gate_status": "UNKNOWN",
            "retrieval_executed": False, "cache_hit": False,
            "unknown_reasons": ["CASE_SEARCH_FAILED:" +
                                getattr(exc, "code", "CASE_LIBRARY_ERROR")],
            "detail": _clip(str(exc), 200),
            "retrieval_scope": {"query": query, "filters": filters,
                                "case_library_index_sha256": sha},
            "checkpoint_focus": trig.get("focus"), **common,
        }

    advisory = _advisory_from_case_search(cl, sha, trig["trigger"])
    triage = triage_anomaly(e) if trig["trigger"] == "T1" else None
    record = {
        "retrieval_executed": True,
        "retrieval_tool": "case_learning.case_search",
        "retriever": (cl.get("cases") or {}).get("retriever"),
        "query_fingerprint": cl.get("query_fingerprint"),
        "underlying_retrieval_cache_hit": bool(cl.get("cache_hit")),
        "index_sha256": sha,
        "case_library_version": cl.get("case_learning_version"),
        "retrieval_scope": advisory["retrieval_scope"],
        "retrieved_case_ids": [c["case_id"] for c in advisory["compact_cases"]],
        "applicability_judgments": advisory["case_admissibility"],
        "source_verification_present": bool(
            (cl.get("cases") or {}).get("source_verification")),
        "no_match": advisory["no_match"],
    }
    out = {
        "status": ("CHECKPOINT_RETRIEVAL_VERIFIED"
                   if trig["trigger_kind"] == "MANDATORY_CHECKPOINT"
                   else "TRIGGER_RETRIEVAL_VERIFIED"),
        "gate_status": advisory["gate_status"],
        "checkpoint_focus": trig.get("focus"),
        "h_stage_declared": trig["declared_h_stage"],
        "milestone": trig["declared_milestone"],
        "stage_in_expected_range": trig.get("stage_in_expected_range"),
        "matched_signals": trig["matched_signals"],
        "unknown_declared_signals": trig["unknown_declared_signals"],
        "unknown_reasons": advisory["unknown_reasons"] + trig["reasons"],
        "retrieval_executed": True,
        "retrieval_executed_this_call": True,
        "cache_hit": False,
        "gate_fingerprint": key,
        "fingerprint_inputs": sorted(parts.keys()),
        "invalidation_keys": ["task_id", "hypothesis", "protocol", "h_stage",
                              "milestone", "task_profile", "query", "filters",
                              "case_library_index_sha256"],
        "retrieval_record": record,
        "verification": verify_gate_record(record, sha),
        "case_candidates": advisory["compact_cases"],
        "case_admissibility": advisory["case_admissibility"],
        "conditions_differ_not_transferred": advisory["conditions_differ_not_transferred"],
        "concrete_checks": advisory["concrete_checks"],
        "decision_experiences": advisory["experiences"],
        "full_evidence_at": {
            "tools": ["search_research_memory", "review_case_transfer"],
            "note": ("需要完整证据时复用这两个既有 MCP 工具或 detail='full'，"
                     "不新增重复检索工具"),
        },
        "new_direction_not_negated_by_historical_failure": True,
        "detail": detail,
        **common,
    }
    out.update(_checkpoint_outputs(trig["trigger"], advisory, e, cl, triage))
    if detail == "full":
        out["full_case_payload"] = cl
    out["_full_payload"] = cl
    out["token_budget"] = {
        "detail": detail, "cache_hit": False,
        "max_cases": MAX_CASES,
        "returned_cases": len(advisory["compact_cases"]),
        "payload_chars": len(json.dumps(
            {k: v for k, v in out.items() if k not in {"_full_payload", "full_case_payload"}},
            ensure_ascii=False)),
        "new_retrieval_calls": 0 if cl.get("cache_hit") else 1,
    }

    stored = {k: v for k, v in out.items()
              if k not in {"cache_hit", "retrieval_executed_this_call",
                           "verification", "full_case_payload", "token_budget"}}
    _GATE_CACHE[key] = stored
    while len(_GATE_CACHE) > GATE_CACHE_SIZE:
        _GATE_CACHE.popitem(last=False)
    out.pop("_full_payload", None)
    return out


def _default_query(trigger: str) -> str:
    return {
        "G1": "选题 科学问题 失败前提 成功条件 反例",
        "G2": "实验协议 标签 合法输入 分组 评价单位 基线",
        "G3": "科研结论 创新 证据 贡献 替代方向",
        "T1": "异常 负结果 评价问题 失败 修复",
        "T2": "重大决策 资源 算法策略 数据范围 科学问题变化",
    }.get(trigger, "案例 迁移 审查")
