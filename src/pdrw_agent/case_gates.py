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
import sqlite3
from collections import OrderedDict

from . import case_learning
from .schemas import AgentError

CASE_GATES_VERSION = "1.3"
GATE_CACHE_SIZE = 32
MAX_EVENT_FIELDS = 20
MAX_TEXT_CHARS = 1200
MAX_SIGNALS = 12
MAX_CASES = 5
MAX_NEXT_ACTIONS = 3
MAX_EXECUTION_REFS = 6

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
        "h_stages": ("H4", "H6", "H7"), "milestone": "PROTOCOL_FREEZE",
        "focus": ("数据/标签/预测时合法输入与时间因果性", "分组独立性/评价指标/强简单基线",
                  "算法机制是否重复历史无效前提", "更有判别价值且成本更低的实验设计"),
        "output_key": "concrete_checks",
    },
    "G3": {
        "kind": "MANDATORY_CHECKPOINT", "priority": 3,
        "h_stages": ("H8", "H10"), "milestone": "CLAIM_OR_CLOSURE",
        "focus": ("正负结果是否已有类似解释", "证据是否支持算法创新/机制/规律主张",
                  "成功经验、失败边界与替代方向", "可进入候选区的新经验"),
        "output_key": "contribution_review",
    },
}
# PD-RW stage/milestone cross-validation. H9 is NOT a claim checkpoint: a
# substantive change to the formal confirmation protocol re-opens G2 instead.
# H4 belongs to PROTOCOL_FREEZE because G2's window starts at the data/truth
# path (H4): a protocol frozen without checking grouping, labels and the legal
# input window is exactly the failure the case library documents most often.
EXPECTED_STAGES = {
    "QUESTION_SELECTION": frozenset({"H2", "H3"}),
    "PROTOCOL_FREEZE": frozenset({"H4", "H6", "H7"}),
    "PROTOCOL_RECHECK": frozenset({"H9"}),
    "CLAIM_OR_CLOSURE": frozenset({"H8", "H10"}),
}
H9_RECHECK_SIGNALS = frozenset({
    "CONFIRMATION_PROTOCOL_CHANGED", "PROTOCOL_SUBSTANTIVE_CHANGE",
    "HOLDOUT_PROTOCOL_CHANGED", "EVALUATION_CRITERION_CHANGE",
})
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
KNOWN_SIGNALS = T1_SIGNALS | T2_SIGNALS | DEV_SIGNALS | H9_RECHECK_SIGNALS
MILESTONES = frozenset({"QUESTION_SELECTION", "PROTOCOL_FREEZE",
                        "PROTOCOL_RECHECK", "CLAIM_OR_CLOSURE", "NONE", ""})
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


def _returned_chars(obj: dict) -> int:
    """Size of the ACTUAL returned payload, not the private cached copy."""
    return len(json.dumps(
        {k: v for k, v in obj.items()
         if k not in {"_full_payload", "token_budget"}},
        ensure_ascii=False))


# --- 1. Trigger determination (Python, deterministic) ---------------------
def _declared_project_stage(event: dict) -> str:
    """A caller may declare the project's known stage for cross-checking."""
    raw = event.get("known_h_stage") or event.get("known_project_state") or ""
    if isinstance(raw, dict):
        raw = raw.get("h_stage") or raw.get("stage") or ""
    return str(raw).strip().upper()


def determine_trigger(event) -> dict:
    """Decide which trigger fires; cross-validate stage, milestone and state.

    Mandatory checkpoints outrank conditional triggers. Ordinary DEV signals
    are suppressed. H9 with a substantive confirmation-protocol change re-opens
    G2 instead of pretending to be a claim checkpoint. Contradictory caller
    declarations are reported explicitly so the caller can never be told the
    checkpoint was "verified" on the strength of a conflicting declaration.
    """
    e = _canonical_event(event)
    stage = str(e.get("h_stage") or "").strip().upper()
    milestone = str(e.get("milestone") or "").strip().upper()
    known_stage = _declared_project_stage(e)
    signals = [str(s).strip().upper() for s in (e.get("signals") or [])]
    unknown_signals = sorted(set(signals) - KNOWN_SIGNALS)
    t1 = sorted(set(signals) & T1_SIGNALS)
    t2 = sorted(set(signals) & T2_SIGNALS)
    dev = sorted(set(signals) & DEV_SIGNALS)
    h9 = sorted(set(signals) & H9_RECHECK_SIGNALS)

    matched = []
    for gid, spec in CHECKPOINTS.items():
        if milestone == spec["milestone"]:
            matched.append((spec["priority"], gid))
    # H9 recheck is a G2-class event: the protocol/checks must be re-derived.
    recheck = bool(h9 and stage == "H9") or milestone == "PROTOCOL_RECHECK"
    if recheck and not any(g == "G2" for _, g in matched):
        matched.append((CHECKPOINTS["G2"]["priority"], "G2"))
    if t1:
        matched.append((CONDITIONAL["T1"]["priority"], "T1"))
    if t2:
        matched.append((CONDITIONAL["T2"]["priority"], "T2"))
    matched.sort()

    reasons: list[str] = []
    conflicts: list[str] = []
    if stage not in H_STAGES:
        reasons.append("UNKNOWN_H_STAGE:" + _clip(stage, 40))
        conflicts.append("DECLARED_H_STAGE_NOT_IN_PD_RW_RANGE")
    if milestone not in MILESTONES:
        reasons.append("UNKNOWN_MILESTONE:" + _clip(milestone, 40))
        conflicts.append("DECLARED_MILESTONE_NOT_IN_CONTROLLED_SET")
    if unknown_signals:
        reasons.append("UNKNOWN_DECLARED_SIGNALS:" + ",".join(unknown_signals))
    expected = EXPECTED_STAGES.get(milestone)
    if expected and stage not in expected:
        conflicts.append("H_STAGE_MILESTONE_MISMATCH:" + stage + "/" + milestone)
    if known_stage and known_stage not in H_STAGES:
        conflicts.append("KNOWN_PROJECT_STAGE_UNRECOGNISED:" + _clip(known_stage, 40))
    elif known_stage and stage and known_stage != stage:
        conflicts.append("DECLARED_STAGE_DISAGREES_WITH_KNOWN_PROJECT_STATE:"
                         + stage + "/" + known_stage)
    # A claimed checkpoint must not be "verified" when the caller declares a
    # materially different project stage from an independent field.
    conflicts = list(dict.fromkeys(conflicts))

    base = {
        "evaluated_priority_order": list(TRIGGER_PRIORITY),
        "declared_h_stage": stage, "declared_milestone": milestone,
        "known_project_stage_declared": known_stage or None,
        "matched_signals": {"T1": t1, "T2": t2, "DEV": dev, "H9_RECHECK": h9},
        "suppressed_dev_signals": dev,
        "unknown_declared_signals": unknown_signals,
        "other_matched_triggers": [g for _, g in matched[1:]],
        "reasons": reasons,
        "declaration_conflicts": conflicts,
        "protocol_recheck": ("H9_CONFIRMATION_PROTOCOL_CHANGED_REOPENS_G2"
                             if recheck else None),
        "decision": _clip(str(e.get("decision", "")), 240),
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


# Only this class asserts a scientific conclusion; the other three are already
# self-limiting. So only it can be contradicted by the same call's Run state.
SCIENTIFIC_CONCLUSION_CLASSES = frozenset({"VALID_SCIENTIFIC_NEGATIVE"})
_CATEGORY_COMPATIBLE_SITUATIONS = frozenset({"DECLARED_NEGATIVE_RESULT_UNVERIFIED"})


def _declared_category_conflict(e: dict, category: str) -> dict | None:
    """A T1 declaration cannot outlive its own call's contradictory Run state.

    Pure declaration cross-check: no file is read, so this is a consistency
    rule, not a new gate and not an approval step.
    """
    if category not in SCIENTIFIC_CONCLUSION_CLASSES:
        return None
    if not isinstance(e.get("run_feedback"), dict) or not e["run_feedback"]:
        return None
    feedback = _declared_run_feedback(e)
    situation = _run_situation(feedback, {})
    if situation in _CATEGORY_COMPATIBLE_SITUATIONS:
        return None
    return {
        "reason": "DECLARED_OUTCOME_CLASS_CONTRADICTED_BY_DECLARED_RUN",
        "declared_situation": situation,
        "declared_validity": feedback["validity"],
        "declared_link_status": feedback["link_status_declared"],
        "meaning": ("同一调用声明为科学负结果，但随附的 Run 声明不支持该结论："
                    "保留声明供审计，有效分类降为 UNKNOWN。"),
    }


def triage_anomaly(event) -> dict:
    """T1: distinguish four outcome classes BEFORE suggesting a next action.

    All categories are DECLARED only; an unverified outcome stays UNKNOWN.
    `category` echoes the caller's declaration unchanged. When that declaration
    asserts a scientific conclusion while the SAME call declares a Run state
    that cannot support one (invalid, unexecuted, conflicting or not
    comparable), the declared category is kept for audit but the effective
    category is downgraded to UNKNOWN: the tool must not restate the caller's
    optimistic class as its own triage.
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
    conflict = _declared_category_conflict(e, category)
    effective = "UNKNOWN" if conflict else category
    if conflict:
        status = "UNKNOWN"
        reasons.append(conflict["reason"] + ":" + conflict["declared_situation"])
    return {
        "status": status, "category": category,
        "category_declared": category,
        "category_effective": effective,
        "category_scope": "DECLARED_ONLY",
        "category_meaning": OUTCOME_CLASSES[category],
        "declaration_conflict": conflict,
        "evidence_refs_declared": has_refs,
        "verification": "DECLARED_ONLY_NOT_INDEPENDENTLY_VERIFIED",
        "next_decisive_action": (
            "先核实 Run 记录与原始日志：本次声明的分类与同一 Run 的声明状态矛盾，"
            "核实前不得当作有效科研负结果；确认后按原 Run/日志区分上述类别，再从"
            "适用案例的 next_minimal_check 选一项最小判别检查"
            if conflict else
            "先按原 Run/日志区分上述类别，再从适用案例的 next_minimal_check "
            "选一项最小判别检查；不得把工程错误或证据不足升级为科研负结果"),
        "unknown_reasons": reasons,
        "automatic_go_stop": False,
        "decision_authority": "PD-RW_WORKFLOW_AND_AUTHOR_ONLY",
    }


# --- 2. Fingerprint + retrieval-record verification ------------------------
# Display-only bounds for the returned basis. These are NOT the hash bounds:
# `_canonical_event` already caps every legal field at MAX_TEXT_CHARS, so
# clipping a field before hashing would let two materially different
# declarations share one cache key and reuse the wrong advisory.
FINGERPRINT_DISPLAY_CLIP = {
    "decision": 400, "hypothesis": 600, "protocol": 600, "query": 300,
    "run_feedback": 900, "evidence_declaration": 500,
}


def _json_safe(value):
    """Keep list/scalar structure, stringify exotic leaves, stay JSON-safe."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)


def _fingerprint_inputs(e: dict, trigger: str, index_sha256: str,
                        index_stale: bool) -> dict:
    """Every input a legal event can carry, bounded only by the event limits."""
    return {
        "tool": "case_gate_check",
        "gate_version": CASE_GATES_VERSION,
        "trigger": trigger,
        "project_id": str(e.get("project_id") or ""),
        "task_id": str(e.get("task_id") or ""),
        "decision": _text(e.get("decision")),
        "hypothesis": _text(e.get("hypothesis")),
        "protocol": _text(e.get("protocol")),
        "case_library_version": str(e.get("case_library_version") or ""),
        "case_library_index_sha256": index_sha256,
        "case_library_index_stale": bool(index_stale),
        "h_stage": str(e.get("h_stage") or "").upper(),
        "milestone": str(e.get("milestone") or "").upper(),
        "known_project_stage": _declared_project_stage(e),
        "query": str(e.get("query") or ""),
        "filters": _json_safe(e.get("filters") or {}),
        "task_profile": _json_safe(e.get("task_profile") or {}),
        # The next-action block depends on the judged Run. Without this the gate
        # would answer a second call from the first call's cache and silently
        # ignore a changed (or contradictory) feedback object.
        "run_feedback": _json_safe(e.get("run_feedback") or {}),
        "evidence_declaration": {
            "outcome_class": _json_safe(e.get("outcome_class")),
            "evidence_refs": _json_safe(e.get("evidence_refs")),
            "execution_evidence_refs": _json_safe(e.get("execution_evidence_refs")),
            "signals": _json_safe(e.get("signals")),
            "known_project_state": _json_safe(e.get("known_project_state")),
        },
    }


def _fingerprint_display(parts: dict) -> dict:
    """The returned basis: human-auditable, and therefore clipped."""
    shown = dict(parts)
    for field, limit in FINGERPRINT_DISPLAY_CLIP.items():
        shown[field] = _clip(_text(parts[field]), limit)
    return shown


def gate_fingerprint(event, trigger: str, index_sha256: str,
                     *, index_stale: bool = False) -> tuple[str, dict]:
    """Same Task + decision + hypothesis + protocol + library version + stage.

    A material change to the decision, declared evidence, project stage,
    confirmation-protocol recheck, or a STALE case index must invalidate the
    cached "verified" advisory. No duplicate second fingerprint is emitted.

    The digest is computed over the *complete* bounded input (at most
    MAX_EVENT_FIELDS x MAX_TEXT_CHARS). The second return value is a clipped,
    display-only projection for audit; it is never hashed.
    """
    e = _canonical_event(event)
    full = _fingerprint_inputs(e, trigger, index_sha256, index_stale)
    return _digest(full), _fingerprint_display(full)


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
    """Grade evidence, compare premises, then build a compact advisory.

    Evidence is tiered with ``case_learning.evidence_tier`` so a success case
    with preprint / internal-report / abstract-only provenance is retained as
    an EXPLICITLY LABELLED exploratory lead instead of being silently dropped.
    A case whose declared scope excludes the current task is never transferred
    as an active negative warning against a different new direction.
    """
    cases = cl.get("cases") or {}
    results = cases.get("results") or []
    per_case = (cases.get("source_verification") or {}).get("per_case") or {}
    judgements = {c["case_id"]: c
                  for c in ((cl.get("case_review") or {}).get("comparisons") or [])}
    experiences = (cl.get("decision_experiences") or {}).get("experiences") or []
    polarity = {e["case_id"]: e["polarity"] for e in experiences}

    admissibility: dict[str, str] = {}
    evidence_tiers: dict[str, str] = {}
    unknown_reasons: list[str] = []
    compact_cases = []
    concrete_checks = []
    for r in results:
        cid = r["case_id"]
        info = per_case.get(cid, {})
        grade = info.get("evidence_grade", "UNVERIFIED")
        tier, _ = case_learning.evidence_tier(info)
        review = judgements.get(cid) or {}
        judgement = review.get("classification", "NOT_REVIEWED")
        if judgement == "CONDITIONS_DIFFER":
            state = "UNKNOWN_CONDITIONS_DIFFER"
        elif tier == "CANDIDATE_ONLY":
            state = "UNKNOWN_SOURCE_INSUFFICIENT"
        elif judgement == "EVIDENCE_INSUFFICIENT":
            state = "UNKNOWN_EVIDENCE_INSUFFICIENT"
        elif tier == "EXPLORATORY_LEAD":
            state = "EXPLORATORY_LEAD_ONLY"
        elif judgement == "APPLICABILITY_RISK":
            state = "ADMISSIBLE_WITH_RISK"
        else:
            state = "ADMISSIBLE_ADVISORY"
        admissibility[cid] = state
        evidence_tiers[cid] = tier
        if not state.startswith("ADMISSIBLE"):
            unknown_reasons.append(f"{cid}:{state}")
        compact_cases.append({
            "case_id": cid, "verdict": r["verdict"],
            "evidence_class": r["evidence_class"], "evidence_grade": grade,
            "evidence_tier": tier,
            "applicability": judgement, "admissibility": state,
            "polarity": polarity.get(cid, "NOT_ADMITTED"),
            "mechanisms": list(r.get("all_mechanisms") or [])[:3],
            "one_line_impact": _clip(
                r.get("transferable_lesson") or
                (r.get("premises") or [""])[0] or "未声明可迁移经验", 180),
            "evidence_paths": list(r.get("evidence_paths") or [])[:2],
            "dimension_status": dict(review.get("dimension_status") or {}),
        })
        if state.startswith("ADMISSIBLE"):
            for check in (r.get("next_minimal_check") or [])[:1]:
                concrete_checks.append({"case_id": cid, "check": _clip(check, 180),
                                        "evidence_tier": tier})

    no_match = cases.get("status") == "NO_CASE_MATCH" or not results
    if no_match:
        unknown_reasons.append("NO_CASE_MATCH_WITH_RECORDED_SCOPE")
    admissible = [c for c in compact_cases if c["admissibility"].startswith("ADMISSIBLE")]
    gate_status = "ADVISORY_AVAILABLE" if admissible else "UNKNOWN"
    if gate_status == "UNKNOWN" and not unknown_reasons:
        unknown_reasons.append("NO_ADMISSIBLE_DECISION_GRADE_CASE")
    # Two admissible cards from the same paper or the same Run are one
    # experience. Counting them as two would inflate the apparent independent
    # support without adding a second observation.
    admissible_ids = {c["case_id"] for c in admissible}
    pairs = [p for p in ((cases.get("source_independence") or {}).get("same_source_pairs") or [])
             if isinstance(p, (list, tuple)) and len(p) >= 2
             and p[0] in admissible_ids and p[1] in admissible_ids]
    groups = case_learning._source_groups(pairs)
    units = len({groups.get(cid, cid) for cid in admissible_ids})
    evidence_independence = {
        "admissible_cases": len(admissible_ids),
        "independent_source_units": units,
        "same_source_pairs": [list(p[:3]) for p in pairs[:2]],
        "strength": ("NO_ADMISSIBLE_CASE" if not admissible_ids
                     else "SINGLE_INDEPENDENT_SOURCE" if units <= 1
                     else "MULTIPLE_INDEPENDENT_SOURCES"),
        "note": "同源案例只算一份独立经验",
    }
    conditions_differ = [cid for cid, state in admissibility.items()
                         if state == "UNKNOWN_CONDITIONS_DIFFER"]
    excluded = set(conditions_differ)
    active_experiences = []
    for e in experiences:
        if e["case_id"] in excluded:
            continue
        item = {
            "case_id": e["case_id"], "polarity": e["polarity"],
            "concrete_impact": _clip(e.get("concrete_impact", ""), 220),
            "transfer_classification": e.get("transfer_classification"),
            "evidence_tier": e.get("evidence_tier", "UNVERIFIED"),
            "exploratory_lead_only": bool(e.get("exploratory_lead_only")),
            "evidence_paths": list(e.get("evidence_paths") or [])[:2],
        }
        if e.get("success_transfer"):
            item["success_transfer"] = e["success_transfer"]
        active_experiences.append(item)
    return {
        "gate_status": gate_status,
        "unknown_reasons": unknown_reasons[:6],
        "case_admissibility": admissibility,
        "evidence_tiers": evidence_tiers,
        "evidence_independence": evidence_independence,
        "conditions_differ_not_transferred": conditions_differ,
        "compact_cases": compact_cases[:MAX_CASES],
        "concrete_checks": concrete_checks[:MAX_CASES],
        "experiences": active_experiences[:MAX_CASES],
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


# --- 3b. Decision pipeline: case -> next action -> execution evidence ----
DECISION_PIPELINE = ("RETRIEVE", "GRADE_EVIDENCE", "COMPARE_PREMISES",
                     "EXTRACT_RISK_OR_SUCCESS_CONDITIONS", "PROPOSE_NEXT_ACTION",
                     "EXECUTION_EVIDENCE_RECHECK")
PREMISE_KEYS = ("decision", "mechanisms", "legal_inputs", "labels", "grouping",
                "evaluation_unit", "baseline", "boundaries", "counterexamples")
CORE_PREMISE_KEYS = ("legal_inputs", "labels", "grouping",
                     "evaluation_unit", "baseline")


def verify_execution_evidence(settings, event: dict) -> dict:
    """Read-only recheck of DECLARED Task/Run/receipt references.

    Producing a recommendation is never execution. Only a reference actually
    found in the EXISTING EVENTS.jsonl / private receipt store can be reported;
    even then this is a tool-level record check, not scientific validation.
    No new state, database, Run or receipt is created here.
    """
    raw = event.get("execution_evidence_refs") or []
    if not isinstance(raw, (list, tuple)):
        raw = []
    refs = [str(x).strip()[:120] for x in raw[:MAX_EXECUTION_REFS]
            if isinstance(x, str) and x.strip()]
    if not refs:
        return {"status": "NO_EXECUTION_EVIDENCE_DECLARED",
                "checked_refs": [], "records_checked": [], "matched": [],
                "no_writes": True,
                "note": "建议生成不等于行动完成；执行后请在 event 中声明 run_id / operation_id 再回查。"}
    project_id = str(event.get("project_id") or "")
    matched: list[dict] = []
    checked: list[str] = []
    if project_id:
        try:
            from .evidence import find_experiment_evidence
            ev = find_experiment_evidence(settings, project_id=project_id, limit=10)
            checked.append("find_experiment_evidence:" + str(ev.get("status")))
            for m in ev.get("matches", []):
                rid, tid = str(m.get("run_id") or ""), str(m.get("task_id") or "")
                if any(r in rid or r in tid or rid in r or tid in r for r in refs):
                    matched.append({"record": "INDEXED_RUN", "run_id": rid,
                                    "task_id": tid})
        except (AgentError, OSError, ValueError, TypeError) as exc:
            checked.append("find_experiment_evidence:UNAVAILABLE:" +
                           getattr(exc, "code", type(exc).__name__))
        try:
            from .runtime.receipts import execution_status
            st = execution_status(settings, project_id, limit=10)
            checked.append("execution_status:" + str(st.get("status")))
            for op in st.get("operations", []):
                oid = str(op.get("operation_id") or "")
                aref = str(op.get("artifact_ref") or "")
                if any(r in oid or r in aref or oid in r for r in refs):
                    matched.append({"record": "OPERATION_RECEIPT",
                                    "operation_id": oid, "artifact_ref": aref})
        except (AgentError, OSError, ValueError, TypeError, sqlite3.Error) as exc:
            checked.append("execution_status:UNAVAILABLE:" +
                           getattr(exc, "code", type(exc).__name__))
    else:
        checked.append("PROJECT_ID_NOT_DECLARED_NO_RECORD_LOOKUP")
    return {
        "status": ("EXECUTION_REF_FOUND_IN_EXISTING_RECORD" if matched else
                   "DECLARED_REFS_NOT_FOUND_IN_EXISTING_RECORDS"),
        "checked_refs": refs, "records_checked": checked,
        "matched": matched[:4], "no_writes": True,
        "verification": "TOOL_LEVEL_RECORD_CHECK_NOT_SCIENTIFIC_VALIDATION",
        "note": "仅回查既有 Task/Run/receipt 引用；不建立第二套科研状态库，不把建议视为已完成行动。",
    }


def _declared_premises(event: dict) -> dict:
    p = event.get("task_profile") or {}
    if not isinstance(p, dict):
        return {}
    return {k: _clip(str(p.get(k, "")), 110) for k in PREMISE_KEYS if p.get(k)}


def _applicability_basis(cid: str, exp: dict, case: dict, reviews: dict) -> dict:
    review = reviews.get(cid) or {}
    dims = review.get("dimension_status") or {}
    app = case.get("applicability") or {}
    return {
        "transfer_classification": exp.get("transfer_classification"),
        "classification_reasons": [_clip(x, 90) for x in
                                   list(review.get("reasons") or [])[:2]],
        "core_dimension_status": {k: dims[k] for k in CORE_PREMISE_KEYS if k in dims},
        "case_conditions": [_clip(x, 90) for x in
                            list(app.get("conditions") or [])[:2]],
        "case_boundaries": [_clip(x, 90) for x in
                            list(app.get("boundaries") or [])[:2]],
        "method": "DECLARED_TEXT_TRIAGE_NOT_EQUIVALENCE_VERIFIED",
        "scientific_equivalence_verified": False,
    }


def _action_type(exp: dict, case: dict, premises: dict) -> str:
    """Choose the action from the case MECHANISM, not incidental keywords."""
    if exp.get("polarity") == "SUCCESS_TRANSFER":
        return "SUCCESS_CONDITION_TO_PRESERVE"
    mechanisms = {str(m).upper() for m in (case.get("all_mechanisms") or [])}
    # Only a task that is actually claiming a gain over a baseline needs the
    # paired decisive experiment; a grouping/leakage checkpoint needs the
    # concrete protocol check instead.
    decision_text = (_text(premises.get("decision")) + " " +
                     _text(premises.get("mechanisms"))).casefold()
    gain_attribution = any(w in decision_text for w in
                           ("基线", "baseline", "增益", "创新", "调参", "等预算"))
    if "COMPLEX_VS_SIMPLE_BASELINE" in mechanisms and gain_attribution:
        return "DECISIVE_EXPERIMENT"
    return "CONCRETE_CHECK"


def _action_text(kind: str, cid: str, case: dict, exp: dict,
                 premises: dict) -> tuple[str, str, str]:
    check = (case.get("next_minimal_check") or ["核对案例适用条件与当前任务前提"])[0]
    mechs = ",".join(list(case.get("matched_mechanisms") or
                          case.get("all_mechanisms") or [])[:2]) or "未标注机制"
    lesson = _clip(case.get("transferable_lesson") or
                   (case.get("premises") or [""])[0], 150)
    grouping = premises.get("grouping", "当前任务未声明分组")
    unit = premises.get("evaluation_unit", "当前任务未声明评价单位")
    if kind == "SUCCESS_CONDITION_TO_PRESERVE":
        st = exp.get("success_transfer") or {}
        conds = "；".join(st.get("success_key_conditions") or []) or "案例卡未声明成功条件"
        minimal = st.get("minimal_validation_experiment") or check
        rec = (f"保留「{mechs}」这条有条件成立的有效路线，但先核对成功关键条件"
               f"「{_clip(conds, 150)}」在本任务是否成立，再决定是否沿用；"
               f"最小验证：{_clip(str(minimal), 170)}。")
    elif kind == "DECISIVE_EXPERIMENT":
        rec = (f"在同一数据划分（{_clip(grouping, 80)}）、同一评价单位（{_clip(unit, 80)}）"
               f"与同一调参预算下，成对运行强简单基线与拟用复杂模型；"
               f"先复现案例 {cid} 的检查「{_clip(str(check), 120)}」，再判断差值"
               f"是否越过其失败边界，而不是直接宣称算法创新。")
        minimal = (f"固定分组与评价单位后，做一次配对基线对照实验并保留原始 Run；"
                   f"检查「{_clip(str(check), 120)}」。")
    else:
        rec = (f"在冻结协议前执行「{_clip(str(check), 140)}」；把当前任务的分组"
               f"（{_clip(grouping, 70)}）与评价单位（{_clip(unit, 70)}）"
               f"同案例 {cid} 的前提逐项对照，记录一致与不同条件后再决定是否改动。")
        minimal = _clip(str(check), 170)
    why = (f"案例 {cid}（{case.get('verdict')}，"
           f"{exp.get('evidence_tier', 'UNVERIFIED')}）在前提「{_clip(lesson, 130)}」"
           f"下得到该经验；适用性 {exp.get('transfer_classification')}；"
           f"仅为声明文本比对，未验证科学等价性。")
    return _clip(rec, 330), _clip(why, 260), _clip(minimal, 220)


RUN_FEEDBACK_VALIDITY = {"VALID", "INVALID", "INCONCLUSIVE", "NOT_RUN"}
RUN_FEEDBACK_OUTCOMES = {"INCREASE", "DECREASE", "NO_CHANGE", "UNKNOWN"}
RUN_FEEDBACK_REVIEWS = {"DECLARED_PREDICTION_CONTRAST", "NO_DISCRIMINATING_CONTRAST",
                        "NO_VALID_SCIENTIFIC_INFERENCE"}
RUN_FEEDBACK_PROVENANCE = {"PRE_RESULT_PROVENANCE_VERIFIED", "PRE_RESULT_RECORD_UNVERIFIED"}
# Vocabulary of ``science.feedback_link``. A status is only echoed so the
# situation can tell a record conflict from a measured negative; the gate never
# re-reads the Run and never upgrades a provenance on its own.
RUN_FEEDBACK_LINK_STATUSES = {"ADVISORY_FEEDBACK_ONLY", "PRE_RESULT_RECORD_UNVERIFIED",
                              "NOT_COMPARABLE", "RUN_EVIDENCE_UNVERIFIED",
                              "RUN_STATUS_CONFLICT", "UNKNOWN"}
# Nothing in the event can authenticate a binding: ``case_gate_check`` is a
# public tool, so a "verified" provenance, a link status and a digest are all
# caller-typed text. The gate is therefore *never* allowed to report a verified
# provenance; only ``science.feedback_link``, which re-reads project files, can
# say which binding check passed.
PROVENANCE_UNVERIFIED_BY_GATE = "PRE_RESULT_RECORD_UNVERIFIED"
PROVENANCE_BASIS_DECLARED = "DECLARED_INPUT_ONLY_GATE_PERFORMS_NO_BINDING"
GATE_CHECK_AXES = ("file_binding", "historical_order", "run_validity",
                   "scientific_truth")
GATE_CHECK_STATUS = "NOT_PERFORMED_BY_GATE"
STRATEGY_SCOPES = {"CORE_TASK", "MAIN_CLAIM", "H6_STRATEGY", "SCIENTIFIC_QUESTION"}
# v1.14 keeps "routine method changes, original-vs-simple algorithm selection
# and in-scope DEV" autonomous, so an algorithm swap alone is not a reason to
# reopen the author's H6/H8 decision. A data-scope change (legal information)
# and a changed core research question still are.
T2_STRATEGY_SIGNALS = {"DATA_SCOPE_CHANGE", "SCIENTIFIC_QUESTION_CHANGE"}


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _declared_run_feedback(event: dict) -> dict | None:
    """Bounded declared feedback from ``science.feedback_link``, if supplied.

    Every field here is caller-supplied: ``case_gate_check`` is a public tool,
    so a ``link_status``, a digest or a word like "verified" can simply be
    typed by whoever builds the event. None of them is a credential.

    The gate therefore never raises credibility. ``provenance`` echoes the
    declaration for audit, ``provenance_effective`` is pinned to unverified,
    and the four checks the gate did not perform are listed one by one. Only
    ``science.feedback_link`` may report that a concrete binding check passed,
    because only it re-reads the project's frozen record and Run evidence.

    Triage — which next action is proposed — still follows the declared
    validity, outcome and contrast. Those are decision hints, never scientific
    facts, and ``_run_situation`` names the result accordingly.
    """
    raw = event.get("run_feedback")
    if raw is None:
        return None
    if not isinstance(raw, dict) or len(raw) > 12:
        raise AgentError("GATE_EVENT_INVALID",
                         "run_feedback must be a small declared object")

    def bounded_list(key: str) -> list[str]:
        value = raw.get(key) or []
        if not isinstance(value, (list, tuple)):
            return []
        return [_clip(str(x), 80) for x in value[:6] if str(x).strip()]

    validity = str(raw.get("validity") or "UNKNOWN").strip().upper()
    if validity not in RUN_FEEDBACK_VALIDITY:
        raise AgentError("GATE_EVENT_INVALID", "run_feedback.validity is not a declared validity")
    outcome = str(raw.get("outcome") or "UNKNOWN").strip().upper()
    if outcome not in RUN_FEEDBACK_OUTCOMES:
        raise AgentError("GATE_EVENT_INVALID", "run_feedback.outcome is not a declared outcome")
    review = str(raw.get("prediction_review") or "").strip().upper()
    if review and review not in RUN_FEEDBACK_REVIEWS:
        raise AgentError("GATE_EVENT_INVALID", "run_feedback.prediction_review is unknown")
    provenance = str(raw.get("provenance") or "").strip().upper()
    if provenance and provenance not in RUN_FEEDBACK_PROVENANCE:
        raise AgentError("GATE_EVENT_INVALID", "run_feedback.provenance is unknown")
    link_status = str(raw.get("link_status") or "").strip().upper()
    if link_status and link_status not in RUN_FEEDBACK_LINK_STATUSES:
        raise AgentError("GATE_EVENT_INVALID", "run_feedback.link_status is unknown")
    digest = str(raw.get("proposal_sha256") or "").strip().lower()
    if digest and not _is_sha256(digest):
        raise AgentError("GATE_EVENT_INVALID", "run_feedback.proposal_sha256 is not a digest")
    return {
        "run_ref": _clip(str(raw.get("run_ref") or ""), 120),
        "validity": validity,
        "outcome": outcome,
        "prediction_review": review,
        # Echoed declaration, kept only so an audit can compare claim against
        # what the gate actually used. It is never a credential.
        "provenance": provenance,
        "provenance_effective": PROVENANCE_UNVERIFIED_BY_GATE,
        "provenance_basis": PROVENANCE_BASIS_DECLARED,
        "link_status_declared": link_status,
        "proposal_sha256_declared": digest,
        "compatible": bounded_list("compatible"),
        "contradicted": bounded_list("contradicted"),
        "evidence_refs": bounded_list("evidence_refs"),
        # Requirement from WP10: file consistency, historical order, Run
        # validity and scientific truth are separate reports. The gate did
        # none of them, so each axis says so instead of defaulting to "ok".
        "checks_by_gate": {axis: GATE_CHECK_STATUS for axis in GATE_CHECK_AXES},
        "declared_only": True,
        "scientific_inference_verified": False,
    }


def _run_situation(feedback: dict | None, execution_evidence: dict) -> str:
    if feedback is None:
        return "NO_RUN_FEEDBACK_DECLARED"
    # A conflicting or unreadable record precedes every other reading: the
    # declared validity itself is what is in doubt, so no scientific inference
    # may be drawn from it yet. These statuses are declarations too, but they
    # only ever move the answer towards "go and check", never towards a result.
    declared_status = feedback.get("link_status_declared")
    if declared_status == "RUN_STATUS_CONFLICT":
        return "RUN_RECORD_CONFLICT"
    if declared_status == "RUN_EVIDENCE_UNVERIFIED":
        return "RUN_EVIDENCE_MISSING"
    if declared_status == "NOT_COMPARABLE":
        return "MEASUREMENT_AXES_CHANGED"
    if feedback["validity"] == "INVALID":
        if execution_evidence.get("status") == "NO_EXECUTION_EVIDENCE_DECLARED":
            return "EXECUTION_UNVERIFIED"
        return "PROTOCOL_OR_EXECUTION_DEFECT"
    if feedback["validity"] == "NOT_RUN":
        return "RUN_NOT_EXECUTED"
    if feedback["validity"] == "INCONCLUSIVE":
        return "INCONCLUSIVE_MEASUREMENT"
    if feedback["prediction_review"] == "NO_VALID_SCIENTIFIC_INFERENCE":
        return "NO_VALID_INFERENCE"
    if feedback["prediction_review"] == "NO_DISCRIMINATING_CONTRAST":
        return "NO_DISCRIMINATING_CONTRAST"
    if feedback["prediction_review"] != "DECLARED_PREDICTION_CONTRAST":
        # No declared contrast means the compatible/contradicted lists prove
        # nothing, whatever they contain.
        return "NO_DISCRIMINATING_CONTRAST"
    compatible, contradicted = feedback["compatible"], feedback["contradicted"]
    if compatible and contradicted:
        return "COMPETING_EXPLANATIONS_SPLIT"
    if compatible:
        return "SUPPORTS_DECLARED_HYPOTHESIS"
    if contradicted:
        # The gate never verified the Run, so the result cannot be called a
        # valid negative. It stays a declared negative with the same advice.
        return "DECLARED_NEGATIVE_RESULT_UNVERIFIED"
    return "NO_DISCRIMINATING_CONTRAST"


_SITUATION_TEXT = {
    "RUN_RECORD_CONFLICT": (
        "RESOLVE_RUN_RECORD_CONFLICT_FIRST",
        "声明的 Run 有效性与项目自身 Run 记录冲突：先核对原始记录，此前的预测对照作废，"
        "不得登记为科学负结果。",
        "打开项目内 Run 记录与原始日志确认实际状态；修正声明或按原协议重跑，并保留原记录。",
        ["哪一份记录是权威", "冲突是否也影响此前的结论"]),
    "RUN_EVIDENCE_MISSING": (
        "LOCATE_OR_REMEASURE_RUN_EVIDENCE_FIRST",
        "引用结果缺失或哈希已变：先找回或重测原始证据；在此之前不比较预测、不更新假设支持度。",
        "核对 evidence_refs 与原始文件哈希；无法复原时按原协议重跑同一探针。",
        ["文件是否被移动或覆盖", "是否必须重跑才能恢复比较"]),
    "MEASUREMENT_AXES_CHANGED": (
        "REPREREGISTER_CHANGED_AXES_BEFORE_COMPARING",
        "观测指标、评价单位或比较参照已偏离冻结提案：该跨度不能被当作被否假设。",
        "要么恢复原观测轴重跑，要么把新轴作为新探针重新声明预测后再比较。",
        ["偏离是有意改进还是实现漂移", "新轴下的最小可判别探针"]),
    "PROTOCOL_OR_EXECUTION_DEFECT": (
        "FIX_PROTOCOL_OR_EXECUTION_BEFORE_INTERPRETING",
        "先定位评价协议或执行缺陷（分组、泄漏、日志、资源），不要把该 Run 登记为科研负结果。",
        "复核 Run 日志与评价脚本，确认探针实际使用的数据划分、评价单位与比较参照。",
        ["该 Run 是否仍能回答原问题", "同一缺陷是否也影响此前的结论"]),
    "EXECUTION_UNVERIFIED": (
        "LOCATE_EXECUTION_RECORD_BEFORE_INTERPRETING",
        "声明为 INVALID 但没有执行证据：先找到真实 Run 记录，再判断是工程问题还是评价问题。",
        "回查 Run/operation 记录与原始日志；找不到时保持 UNKNOWN，不归入任何科学结论。",
        ["Run 是否真实执行过", "失败发生在哪一层"]),
    "RUN_NOT_EXECUTED": (
        "CONFIRM_BLOCKER_AND_RERUN_SAME_PROBE",
        "探针未执行：确认阻塞原因后重跑同一探针；未运行的结果不能改变科学结论。",
        "记录阻塞原因，按原协议重跑并保存原始 Run。",
        ["阻塞是资源、实现还是协议问题"]),
    "INCONCLUSIVE_MEASUREMENT": (
        "QUANTIFY_NOISE_BEFORE_MORE_DATA",
        "测量不确定：先量化噪声与评价单位的影响，再决定是否值得增加样本或换探针。",
        "用既有 Run 估计方差/置信区间，确认最小可检测差异后再决定是否追加数据。",
        ["当前设计能否分辨目标效应", "是否应先改评价单位"]),
    "NO_VALID_INFERENCE": (
        "REPAIR_EVIDENCE_BEFORE_SCIENTIFIC_UPDATE",
        "该 Run 的有效性不允许任何科学推断：保留观察，但不更新假设支持度。",
        "修复有效性缺陷或重跑；在此之前不比较预测与观测。",
        ["缺陷是否可修复", "是否需要重做协议"]),
    "NO_DISCRIMINATING_CONTRAST": (
        "DESIGN_DISCRIMINATING_PROBE",
        "该探针无法区分竞争解释（预测相同或未声明）：换一个能让它们给出不同预测的探针。",
        "列出每个假设的定性预测，只保留预测互不相同的观测；优先成本最低者。",
        ["哪些假设对仍未被区分", "新探针的最小成本"]),
    "COMPETING_EXPLANATIONS_SPLIT": (
        "VERIFY_RUN_THEN_DESIGN_DIFFERENTIATING_PROBE",
        "支持与反驳并存：先核验原始 Run，再用能分开幸存解释的最小探针推进。",
        "对每个幸存解释写出可观测预测，选一个成本最低且预测互斥的探针。",
        ["哪一个解释仍未被排除", "是否需要独立组复现"]),
    "SUPPORTS_DECLARED_HYPOTHESIS": (
        "KEEP_CHAMPION_AND_FILL_EVIDENCE_GAP",
        "保留当前 Champion，把下一步放在论文证据缺口（独立组复现、强简单基线、边界条件），"
        "而不是继续更换模型。",
        "先核对原始 Run 记录与证据（本工具未核验）；在同一评价单位下补一次独立组复现，"
        "并给出失效边界；不扩大模型搜索。",
        ["结论的外部效度", "最强简单基线是否已排除", "边界条件是否清楚"]),
    "DECLARED_NEGATIVE_RESULT_UNVERIFIED": (
        "REASSESS_FAILED_PREMISE_AND_ALTERNATIVES",
        "声明为负结果，但本工具未核验 Run、证据与协议，因此不称其为有效负结果；"
        "仅否定本探针实际测试的前提，检查失败边界与替代解释，不据此终止整个方向。",
        "先由 Run 记录、原始日志与评价脚本确认这次比较确实成立（无泄漏、分组与评价单位一致）；"
        "确认后写出被否定的前提、仍成立的相邻条件，以及一个能区分替代解释的最小实验。",
        ["失败是前提错还是范围错", "替代解释是否仍可检验", "该 Run 是否真的可比较"]),
}


def _situation_action(situation: str, feedback: dict | None,
                      execution_evidence: dict) -> dict | None:
    spec = _SITUATION_TEXT.get(situation)
    if spec is None:
        return None
    action_type, recommendation, minimal, open_questions = spec
    compatible = (feedback or {}).get("compatible") or []
    contradicted = (feedback or {}).get("contradicted") or []
    return {
        "action_type": action_type,
        "linked_case_id": None,
        "basis": {
            "run_ref": (feedback or {}).get("run_ref") or "",
            "declared_validity": (feedback or {}).get("validity"),
            "declared_outcome": (feedback or {}).get("outcome"),
            "prediction_review": (feedback or {}).get("prediction_review"),
            # Declared and effective are kept apart so a downstream summary
            # cannot quote a hand-written "verified" as if the gate had checked
            # it. Effective is always unverified here: no event field can
            # authenticate itself.
            "pre_result_provenance_declared": (feedback or {}).get("provenance"),
            "pre_result_provenance_effective": (feedback or {}).get("provenance_effective"),
            "provenance_basis": (feedback or {}).get("provenance_basis"),
            "link_status_declared": (feedback or {}).get("link_status_declared"),
            "proposal_sha256_declared":
                (feedback or {}).get("proposal_sha256_declared"),
            "evidence_refs": list((feedback or {}).get("evidence_refs") or []),
            "execution_evidence_status": execution_evidence.get("status"),
        },
        "differentiates": ([[a, b] for a in compatible[:2] for b in contradicted[:2]]
                           if situation == "COMPETING_EXPLANATIONS_SPLIT" else []),
        "recommendation": _clip(recommendation, 300),
        "why_this_case_applies": _clip(
            "依据本次 Run 的声明有效性与预测对照；案例只作为补充，不决定结论。", 180),
        "minimal_validation": _clip(minimal, 260),
        "open_questions": open_questions[:3],
        "applicability": "仅适用于本 Run 声明的探针、评价单位与比较参照",
        "exploratory_lead_only": False,
        "independent_confirmation": "NOT_A_SCIENTIFIC_PROOF",
        "status": "PROPOSED_NOT_EXECUTED",
        "execution_evidence_status": execution_evidence.get("status"),
        "author_decision_required": False,
        "decision_authority": "PD-RW_WORKFLOW_AND_AUTHOR_ONLY",
        "automatic_go_stop": False,
        "no_writes": True,
    }


def _strategy_scope_change(event: dict, trigger: str,
                           matched_signals: dict | None) -> str | None:
    """Only a claim/strategy-scope change justifies the author H6/H8 option.

    A keyword-similar case that merely carries applicability risk is not, by
    itself, a reason to ask the author to re-decide the core task.
    """
    scope = str(event.get("strategy_scope") or event.get("claim_scope") or "")
    scope = scope.strip().upper()
    if scope in STRATEGY_SCOPES:
        return "DECLARED_" + scope
    if event.get("main_claim_changed") is True or event.get("task_scope_changed") is True:
        return "DECLARED_SCOPE_FLAG"
    if trigger == "T2":
        signals = set((matched_signals or {}).get("T2") or [])
        if signals & T2_STRATEGY_SIGNALS:
            return "T2_MATERIAL_CHANGE_SIGNAL"
        return None
    # G3 is the H8/H10 claim-or-closure checkpoint: the claim decision itself.
    return "CLAIM_CHECKPOINT_G3" if trigger == "G3" else None


def build_next_actions(trigger: str, event: dict, cl: dict, advisory: dict,
                       execution_evidence: dict,
                       run_feedback: dict | None = None,
                       matched_signals: dict | None = None) -> dict:
    """检索 -> 证据分级 -> 前提比对 -> 风险/成功条件 -> 1–3 项下一行动.

    Every action cites a concrete case, the declared current-task premises and
    an applicability basis. Weak evidence is only a labelled exploratory lead.
    When nothing admissible exists the result is UNKNOWN, never a fabricated
    confident recommendation.
    """
    results = ((cl.get("cases") or {}).get("results") or [])
    by_id = {c["case_id"]: c for c in results}
    reviews = {c["case_id"]: c
               for c in ((cl.get("case_review") or {}).get("comparisons") or [])}
    per_case = (((cl.get("cases") or {}).get("source_verification") or {})
                .get("per_case") or {})
    experiences = (cl.get("decision_experiences") or {}).get("experiences") or []
    premises = _declared_premises(event)
    states = advisory["case_admissibility"]
    excluded = set(advisory["conditions_differ_not_transferred"])
    ranked = []
    for exp in experiences:
        cid = exp["case_id"]
        case = by_id.get(cid)
        if not case or cid in excluded:
            continue
        state = states.get(cid, "")
        if state.startswith("ADMISSIBLE"):
            rank = 0
        elif state == "EXPLORATORY_LEAD_ONLY":
            rank = 2
        else:
            continue
        ranked.append((rank, 0 if exp.get("polarity") == "NEGATIVE_WARNING" else 1,
                       exp, case))
    ranked.sort(key=lambda x: (x[0], x[1]))

    actions: list[dict] = []
    leads: list[dict] = []
    situation = _run_situation(run_feedback, execution_evidence)
    situation_action = _situation_action(situation, run_feedback, execution_evidence)
    if situation_action is not None:
        # The Run-level action comes first: a case hint cannot outrank the
        # question of whether this Run may be interpreted at all.
        actions.append({
            "action_id": "NA-1",
            **situation_action,
            "task_premises_ref": "next_actions.task_premises",
        })
    for rank, _, exp, case in ranked:
        cid = exp["case_id"]
        if len(actions) >= MAX_NEXT_ACTIONS:
            break
        exploratory_only = rank == 2
        if exploratory_only:
            # A preprint / internal / abstract-only SUCCESS case can still be
            # a useful technical route, but only as an explicitly labelled
            # lead with a minimal validation experiment -- never a confirmed
            # scientific conclusion and never an active negative warning.
            if exp.get("polarity") != "SUCCESS_TRANSFER" or actions:
                leads.append({"case_id": cid,
                              "reason": "EXPLORATORY_LEAD_ONLY_NOT_INDEPENDENTLY_CONFIRMED",
                              "note": "仅可作为明确标注的探索线索，不升级为独立确认的科学结论"})
                continue
        kind = _action_type(exp, case, premises)
        recommendation, why, minimal = _action_text(kind, cid, case, exp, premises)
        info = per_case.get(cid, {})
        actions.append({
            "action_id": f"NA-{len(actions) + 1}",
            "action_type": kind,
            "linked_case_id": cid,
            "case_source": {
                "evidence_paths": list(case.get("evidence_paths") or [])[:2],
                "evidence_grade": info.get("evidence_grade", "UNVERIFIED"),
                "evidence_tier": exp.get("evidence_tier", "UNVERIFIED"),
                "independent_confirmation": exp.get("independent_confirmation",
                                                    "NOT_ESTABLISHED"),
            },
            "task_premises_ref": "next_actions.task_premises",
            "applicability_basis": _applicability_basis(cid, exp, case, reviews),
            "recommendation": (("【探索线索·非独立确认结论】" + recommendation)
                               if exploratory_only else recommendation),
            "why_this_case_applies": why,
            "minimal_validation": minimal,
            "exploratory_lead_only": exploratory_only,
            "independent_confirmation": ("NOT_ESTABLISHED" if exploratory_only
                                         else "SOURCE_VERIFIED_NOT_SCIENTIFIC_PROOF"),
            "status": "PROPOSED_NOT_EXECUTED",
            "execution_evidence_status": (
                "NO_EXECUTION_EVIDENCE_DECLARED"
                if execution_evidence["status"] == "NO_EXECUTION_EVIDENCE_DECLARED"
                else execution_evidence["status"]),
            "author_decision_required": False,
            "decision_authority": "PD-RW_WORKFLOW_AND_AUTHOR_ONLY",
            "automatic_go_stop": False,
            "no_writes": True,
        })

    # At most one core strategy option is escalated to the author, and only
    # when the checkpoint is about claims/strategy AND a real risk exists.
    risk = [cid for cid, s in states.items()
            if s == "ADMISSIBLE_WITH_RISK" and cid not in excluded]
    strategy_basis = _strategy_scope_change(event, trigger, matched_signals)
    risk_noted: list[dict] = []
    if risk and not (trigger in {"G3", "T2"} and strategy_basis and actions
                     and len(actions) < MAX_NEXT_ACTIONS):
        # A similar case plus an applicability warning is not an approval node.
        risk_noted = [{
            "case_id": cid,
            "reason": "ADMISSIBLE_WITH_RISK",
            "author_decision_required": False,
            "note": ("案例适用风险仅作为上下文；未涉及核心 Task、主 Claim 或重大策略调整时，"
                     "不触发作者选择。"),
        } for cid in risk[:2]]
    if trigger in {"G3", "T2"} and risk and strategy_basis and actions \
            and len(actions) < MAX_NEXT_ACTIONS:
        cid = risk[0]
        case = by_id.get(cid) or {}
        actions.append({
            "action_id": f"NA-{len(actions) + 1}",
            "action_type": "AUTHOR_STRATEGY_OPTION",
            "linked_case_id": cid,
            "case_source": {"evidence_paths": list(case.get("evidence_paths") or [])[:2],
                            "evidence_tier": advisory["evidence_tiers"].get(cid)},
            "task_premises_ref": "next_actions.task_premises",
            "applicability_basis": _applicability_basis(
                cid, {"transfer_classification": "APPLICABILITY_RISK"},
                case, reviews),
            "strategy_scope_basis": strategy_basis,
            "recommendation": _clip(
                f"提交作者决定：案例 {cid} 的机制前提与当前声明存在适用风险，"
                f"是否调整 H3 问题、H6 核心策略或 H8 主 Claim 的表述范围？"
                f"本工具不选择策略、不升级结论。", 260),
            "why_this_case_applies": _clip(
                f"case_admissibility[{cid}] = ADMISSIBLE_WITH_RISK；"
                f"策略范围依据 {strategy_basis}；仍需原始 Run 与原文边界逐行核对。", 200),
            "minimal_validation": "由作者核对原始 Run/协议后再决定；不自动执行",
            "status": "PROPOSED_NOT_EXECUTED",
            "execution_evidence_status": "AUTHOR_DECISION_PENDING",
            "author_decision_required": True,
            "decision_authority": "PD-RW_WORKFLOW_AND_AUTHOR_ONLY",
            "automatic_go_stop": False,
            "no_writes": True,
        })

    case_ids = [x["case_id"] for x in experiences]
    evidence = {
        "run_ref": (run_feedback or {}).get("run_ref") or "",
        "run_evidence_refs": list((run_feedback or {}).get("evidence_refs") or []),
        "case_index_sha256": ((cl.get("cases") or {}).get("source_verification")
                              or {}).get("index_sha256"),
    }
    decision_basis = {
        "question": _clip(_text(event.get("query")), 180),
        "scope": {"task_id": _clip(_text(event.get("task_id")), 60),
                  "h_stage": _clip(_text(event.get("h_stage")), 8),
                  "milestone": _clip(_text(event.get("milestone")), 40)},
        "evidence": evidence,
    }
    if run_feedback is not None:
        # Additive only when a Run was actually judged, so a checkpoint without
        # Run feedback keeps its previous shape and size. Both evidence fields
        # say "declared" in their name: the gate read neither file nor digest.
        evidence["proposal_sha256_declared"] = (
            run_feedback.get("proposal_sha256_declared") or "")
        evidence["feedback_link_status_declared"] = (
            run_feedback.get("link_status_declared") or "")
        # Credibility is reported as declared-vs-effective, never summed up
        # into a single "verified" label. Effective stays unverified because no
        # public input can authenticate itself.
        decision_basis["credibility"] = {
            "run_feedback_declared_only": True,
            "pre_result_provenance_declared": run_feedback.get("provenance") or "",
            "pre_result_provenance_effective": run_feedback.get("provenance_effective") or "",
            "provenance_basis": run_feedback.get("provenance_basis") or "",
            "checks_by_gate": dict(run_feedback.get("checks_by_gate") or {}),
            "scientific_inference_verified": False,
        }
    decision_basis.update({
        # The gate cannot verify a decision-time receipt; claiming otherwise
        # would repeat the defect WP9-A fixes in feedback_link.
        "pre_decision_cases": ("NOT_VERIFIABLE_AT_GATE" if case_ids
                              else "NO_CASE_RETRIEVED"),
        "post_run_cases": case_ids[:5],
        "selected": None,
    })
    situation_block = {"kind": situation,
                       "run_feedback_declared": run_feedback is not None,
                       "scientific_inference_verified": False}
    if run_feedback is not None:
        situation_block.update({
            "run_feedback_declared_only": True,
            # The triage below reads declarations only. Saying so here stops a
            # downstream summary from quoting the kind as a measured fact.
            "kind_scope": "DECLARED_ONLY",
            "verification": "NOT_VERIFIABLE_AT_GATE",
            "prediction_verification_performed": False,
            "provenance_basis": run_feedback.get("provenance_basis") or "",
        })
    return {
        "status": ("ACTIONS_PROPOSED_NOT_EXECUTED" if actions else
                   "UNKNOWN_NO_ACTIONABLE_ADMISSIBLE_CASE"),
        "returned": len(actions), "max_actions": MAX_NEXT_ACTIONS,
        "exploratory_only_result": bool(actions) and all(
            a.get("exploratory_lead_only") for a in actions),
        "pipeline": list(DECISION_PIPELINE),
        "task_premises": premises,
        "execution_evidence": execution_evidence,
        "situation": situation_block,
        "decision_basis": decision_basis,
        "applicability_risk_noted": risk_noted,
        "actions": actions,
        "exploratory_leads_not_promoted": leads[:3],
        "unknown_reasons": ([] if actions else
                            ["NO_ADMISSIBLE_CASE_WITH_DECLARED_TASK_PREMISES"] +
                            advisory["unknown_reasons"][:3]),
        "automatic_go_stop": False, "no_writes": True,
        "not_a_scientific_conclusion": True,
    }


def _checkpoint_outputs(trigger: str, advisory: dict, event: dict,
                        cl: dict, triage: dict | None,
                        next_actions: dict | None = None) -> dict:
    out = {}
    actions = (next_actions or {}).get("actions") or []
    action_ids = [a["action_id"] for a in actions]
    task_premises = (next_actions or {}).get("task_premises") or {}
    exps = advisory["experiences"]
    # Compact projection: the full experience (incl. success_transfer detail)
    # already lives once in the top-level decision_experiences / next_actions.
    key_exps = [{"case_id": e["case_id"], "polarity": e["polarity"],
                 "evidence_tier": e["evidence_tier"],
                 "concrete_impact": e["concrete_impact"]}
                for e in exps]
    admitted = {c["case_id"]: c for c in advisory["compact_cases"]
                if c["admissibility"].startswith("ADMISSIBLE")}
    success_conditions = [
        {"case_id": e["case_id"],
         "key_conditions": (e.get("success_transfer") or {}).get(
             "success_key_conditions") or [],
         "minimal_validation": (e.get("success_transfer") or {}).get(
             "minimal_validation_experiment")}
        for e in exps if e["polarity"] == "SUCCESS_TRANSFER"][:3]

    if trigger == "G1":
        overlap = [
            {"case_id": cid, "mechanisms": c["mechanisms"],
             "basis": c["applicability"],
             "status": "SAME_DECLARED_PREMISE_CANDIDATE_VERIFY_ORIGINAL_TEXT"}
            for cid, c in admitted.items()
            if c["applicability"] in {"USEFUL_ANALOGY", "APPLICABILITY_RISK"}][:3]
        premise_check = []
        for cid, c in admitted.items():
            dims = c["dimension_status"]
            core = [dims.get(k) for k in CORE_PREMISE_KEYS if dims.get(k)]
            if core and all(x == "TEXT_OVERLAP_SIMILARITY_ONLY" for x in core):
                premise_check.append({"case_id": cid,
                                      "status": "ALL_DECLARED_CORE_PREMISES_TEXTUALLY_OVERLAP",
                                      "meaning": "历史失败前提可能仍成立，需逐行核对原文后确认"})
            elif core:
                premise_check.append({"case_id": cid,
                                      "status": "CORE_PREMISES_DECLARED_BUT_DIVERGENT_OR_UNDECLARED",
                                      "meaning": "信息条件可能不同，不得据此否定新方向"})
        questions = [
            {"case_id": a["linked_case_id"],
             "question": _clip(
                 f"在「{task_premises.get('legal_inputs', '当前合法输入')}」"
                 f"条件下，{a['action_type']} 是否能区分案例的历史前提与本任务？", 200)}
            for a in actions if a["action_type"] in
            {"DECISIVE_EXPERIMENT", "CONCRETE_CHECK"}][:2]
        out["selection_impact"] = {
            "key_experiences": key_exps[:MAX_CASES],
            "highly_overlapping_research": overlap or
                "UNKNOWN_NO_ADMISSIBLE_CASE_WITH_COMPARABLE_DECLARED_PREMISES",
            "historical_failure_premises_still_hold": premise_check or
                "UNKNOWN_NO_DECLARED_CORE_PREMISE_COMPARISON_AVAILABLE",
            "success_key_conditions": success_conditions or
                "UNKNOWN_NO_ADMISSIBLE_SUCCESS_CASE",
            "new_scientific_questions": questions or
                "UNKNOWN_NOT_INFERRED_WITHOUT_ADMISSIBLE_CASE",
            "next_action_ids": action_ids,
            "next_actions_ref": "top-level next_actions",
            "new_direction_not_negated_by_historical_failure": True,
            "verification": "DECLARED_TEXT_TRIAGE_NOT_EQUIVALENCE_VERIFIED",
            "note": "历史失败只提供风险与检查项，不得自动否定具有不同合法信息条件的新方向。",
        }
    elif trigger == "G2":
        checks = []
        by_action = {a["linked_case_id"]: a["action_id"] for a in actions}
        for c in advisory["concrete_checks"]:
            checks.append({**c, "next_action_id": by_action.get(c["case_id"]),
                           "promoted_to_next_action": c["case_id"] in by_action})
        out["concrete_checks"] = checks
        out["protocol_design_review"] = {
            "declared_8_dimensions": sorted((event.get("task_profile") or {}).keys()),
            "applicable_checks": checks[:MAX_CASES],
            "actionable_next_action_ids": [a["action_id"] for a in actions
                                           if a["action_type"] in
                                           {"CONCRETE_CHECK", "DECISIVE_EXPERIMENT"}],
            "design_improvement": ("ADVISORY_ONLY：ADMISSIBLE 案例的 next_minimal_check "
                                   "已转化为带案例来源与前提比对的 next_actions；"
                                   "不自动改动实验或授权"),
            "unknown_when_no_admissible_case": advisory["gate_status"] == "UNKNOWN",
        }
    elif trigger == "G3":
        claim_support = []
        for cid, c in admitted.items():
            dims = c["dimension_status"]
            weak = [k for k in CORE_PREMISE_KEYS
                    if dims.get(k) in {"NO_TEXT_OVERLAP", "NOT_IN_CASE", "UNDECLARED"}]
            claim_support.append({
                "case_id": cid,
                "status": ("ORIGINAL_RUN_REQUIRED_PREMISES_DIVERGENT_OR_UNDECLARED"
                           if weak else "DECLARED_PREMISES_TEXTUALLY_OVERLAP_ONLY"),
                "dimensions_requiring_verification": weak})
        out["contribution_review"] = {
            "similar_explanations": key_exps[:MAX_CASES],
            "evidence_supports_algorithm_innovation_or_mechanism_claim":
                claim_support or "UNKNOWN_VERIFY_ORIGINAL_RUN",
            "failure_boundaries_and_alternatives": [
                {"case_id": c["case_id"], "admissibility": c["admissibility"],
                 "evidence_tier": c["evidence_tier"]}
                for c in advisory["compact_cases"]][:MAX_CASES],
            "usable_success_conditions": success_conditions or
                "UNKNOWN_NO_ADMISSIBLE_SUCCESS_CASE",
            "next_action_ids": action_ids,
            "next_actions_ref": "top-level next_actions",
            "candidate_experiences_hint": {
                "tool": "extract_case_candidates",
                "status": "CANDIDATE_ONLY_NOT_FORMAL_CASE",
                "note": "仅从原始 Run 与既有科学审计提取候选，不写 STATE/Run/EVENTS/CASE_LIBRARY"},
            "author_strategy_required": True,
            "verification": "DECLARED_TEXT_TRIAGE_NOT_EQUIVALENCE_VERIFIED",
            "note": "H8 主 Claim 与重大升级仍由作者选择/明确委托；正式论文写作另行授权，本工具不改变 PD-RW 权限。",
        }
    elif trigger == "T1":
        out["anomaly_triage"] = triage
        out["failure_and_repair_experiences"] = key_exps[:MAX_CASES]
        out["next_action_ids"] = action_ids
    elif trigger == "T2":
        out["decision_change_review"] = {
            "declared_material_changes": (determine_trigger(event)["matched_signals"]["T2"]),
            "potentially_decision_changing_experiences": key_exps[:MAX_CASES],
            "next_action_ids": action_ids,
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
    stale = bool(bundle["index_stale"])
    conflicts = list(trig.get("declaration_conflicts") or [])
    key, _ = gate_fingerprint(e, trig["trigger"], sha, index_stale=stale)
    # A stale index or a contradictory caller declaration must never reuse a
    # previously "verified" conclusion. Both are also part of the fingerprint.
    use_cache = not stale and not conflicts
    if use_cache and key in _GATE_CACHE:
        _GATE_CACHE.move_to_end(key)
        cached = copy.deepcopy(_GATE_CACHE[key])
        if detail == "full" and cached.get("_full_payload") is not None:
            cached["full_case_payload"] = cached.pop("_full_payload")
        else:
            cached.pop("_full_payload", None)
        cached["cache_hit"] = True
        cached["reused_verified_record"] = True
        cached["retrieval_executed_this_call"] = False
        cached["verification"] = verify_gate_record(
            cached.get("retrieval_record"), sha)
        cached["token_budget"] = {
            "detail": detail, "cache_hit": True,
            "payload_chars": _returned_chars(cached),
            "new_retrieval_calls": 0,
        }
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
    execution_evidence = verify_execution_evidence(settings, e)
    next_actions = build_next_actions(trig["trigger"], e, cl, advisory,
                                      execution_evidence,
                                      run_feedback=_declared_run_feedback(e),
                                      matched_signals=trig.get("matched_signals"))
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
        # Audit trail for the WP6-A recall path: PRIMARY means the original
        # single-keyword AND search matched; TOKEN_UNION_FALLBACK means the
        # long question was widened to core concepts before ranking.
        "retrieval_mode": (cl.get("cases") or {}).get("retrieval_mode", "PRIMARY"),
        "recall_terms": (cl.get("cases") or {}).get("recall_terms") or [],
    }
    verification = verify_gate_record(record, sha)
    downgrade = []
    if conflicts:
        downgrade += ["DECLARATION_CONFLICT:" + c for c in conflicts]
    if stale:
        downgrade.append("INDEX_STALE_REBUILD_REQUIRED")
    if downgrade:
        # Still return the useful advisory, but NEVER call it "verified".
        verification = {"status": "UNKNOWN", "unknown_reasons": downgrade,
                        "verified_fields": verification.get("verified_fields", []),
                        "note": "声明矛盾或索引过期：检索仍可执行，但不得复用旧的已验证结论。"}
    if conflicts:
        status = ("CHECKPOINT_ADVISORY_DECLARATION_CONFLICT"
                  if trig["trigger_kind"] == "MANDATORY_CHECKPOINT"
                  else "TRIGGER_ADVISORY_DECLARATION_CONFLICT")
    elif stale:
        status = ("CHECKPOINT_ADVISORY_INDEX_STALE"
                  if trig["trigger_kind"] == "MANDATORY_CHECKPOINT"
                  else "TRIGGER_ADVISORY_INDEX_STALE")
    else:
        status = ("CHECKPOINT_RETRIEVAL_VERIFIED"
                  if trig["trigger_kind"] == "MANDATORY_CHECKPOINT"
                  else "TRIGGER_RETRIEVAL_VERIFIED")
    out = {
        "status": status,
        "checkpoint_verified": (verification["status"] ==
                                "RETRIEVAL_AND_APPLICABILITY_VERIFIED"),
        "gate_status": advisory["gate_status"],
        "checkpoint_focus": trig.get("focus"),
        "h_stage_declared": trig["declared_h_stage"],
        "milestone": trig["declared_milestone"],
        "stage_in_expected_range": trig.get("stage_in_expected_range"),
        "known_project_stage_declared": trig["known_project_stage_declared"],
        "declaration_conflicts": conflicts,
        "protocol_recheck": trig["protocol_recheck"],
        "index_stale": stale,
        "matched_signals": trig["matched_signals"],
        "unknown_declared_signals": trig["unknown_declared_signals"],
        "unknown_reasons": (advisory["unknown_reasons"] + trig["reasons"] +
                            downgrade)[:8],
        "retrieval_executed": True,
        "retrieval_executed_this_call": True,
        "cache_hit": False,
        "reused_verified_record": False,
        "gate_fingerprint": key,
        "retrieval_record": record,
        "verification": verification,
        "case_candidates": [
            {k: v for k, v in c.items() if k != "dimension_status"}
            for c in advisory["compact_cases"]],
        "case_admissibility": advisory["case_admissibility"],
        "evidence_tiers": advisory["evidence_tiers"],
        "evidence_independence": advisory["evidence_independence"],
        "conditions_differ_not_transferred": advisory["conditions_differ_not_transferred"],
        "concrete_checks": advisory["concrete_checks"],
        "decision_experiences": advisory["experiences"],
        "next_actions": next_actions,
        "full_evidence_at": {
            "tools": ["search_research_memory", "review_case_transfer"],
            "note": ("需要完整证据时复用这两个既有 MCP 工具或 detail='full'，"
                     "不新增重复检索工具"),
        },
        "new_direction_not_negated_by_historical_failure": True,
        "detail": detail,
        **common,
    }
    out.update(_checkpoint_outputs(trig["trigger"], advisory, e, cl, triage,
                                   next_actions))
    if detail == "full":
        out["full_case_payload"] = cl
    out["_full_payload"] = cl
    out["token_budget"] = {
        "detail": detail, "cache_hit": False,
        "max_cases": MAX_CASES,
        "returned_cases": len(advisory["compact_cases"]),
        "payload_chars": _returned_chars(out),
        "new_retrieval_calls": 0 if cl.get("cache_hit") else 1,
    }
    out["token_budget"]["payload_chars"] = _returned_chars(out)

    stored = {k: v for k, v in out.items()
              if k not in {"cache_hit", "retrieval_executed_this_call",
                           "verification", "full_case_payload", "token_budget"}}
    if use_cache:
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
