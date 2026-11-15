#!/usr/bin/env python3
"""Local engineering evaluation of the five case-application gates.

MEASURED here (tool-level, deterministic, on the REAL CASE_LIBRARY):
  actual gate calls and real retrieval calls, cache hits, false triggers,
  missed triggers, UNKNOWN markings, compact/full payload characters, and
  retrieval-call savings versus a naive "retrieve every step" baseline.

NOT MEASURED (see evals/SCIENTIFIC_UTILITY_GATES.md):
  WorkBuddy task completion, scientific decision correctness, blind reviewer
  grades, real LLM input/output tokens, wall time, human turns, scientific
  utility and host-level hard-gate enforcement. Unit tests and this tool
  differential MUST NOT be reported as scientific benefit.

Safety: read-only; hashes CASE_LIBRARY/index.json + all case cards before/after;
no GO/STOP, no writes to CASE_LIBRARY, PD-RW, STATE, Run, EVENTS, SEALED or
any frozen A/B/C snapshot; no network fetch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

from pdrw_agent import case_gates, case_learning  # noqa: E402
from pdrw_agent.config import Settings  # noqa: E402
from pdrw_agent.service import ResearchService  # noqa: E402
from case_learning_ablation import SCENARIOS, library_digest  # noqa: E402

DEFAULTS = {
    "PDRW_AGENT_CONFIG": str(ROOT / "project-map.local.json"),
    "PDRW_WORKFLOW_ROOT": str(ROOT.parent / "Problem-Data-Research-Workflow"),
    "PDRW_CASE_LIBRARY_ROOT": str(Path("D:/workbuddy-work/CASE_LIBRARY")),
}

NOT_MEASURED = {
    "workbuddy_task_completion": "NOT_MEASURED",
    "scientific_decision_correctness": "NOT_MEASURED",
    "blind_reviewer_grades": "NOT_MEASURED",
    "real_llm_input_output_token_delta": "NOT_MEASURED",
    "wall_time_delta": "NOT_MEASURED",
    "human_turns_or_interventions": "NOT_MEASURED",
    "scientific_utility": "NOT_MEASURED",
    "host_state_transition_hard_gate": "NOT_MEASURED",
    "reason": ("No real WorkBuddy A/B/C replay and no trusted host "
               "state-transition hook were exercised. Payload characters are a "
               "tool-output SIZE proxy, not LLM tokens or research benefit."),
}


def event_for(scenario: dict, *, trigger: str, stage: str, milestone: str,
              signals: list[str], task_id: str, **extra) -> dict:
    event = {
        "project_id": "37", "task_id": task_id,
        "h_stage": stage, "milestone": milestone, "signals": signals,
        "decision": scenario["profile"]["decision"],
        "hypothesis": "沿用所选研究策略的既有前提与评价口径",
        "protocol": {"split": scenario["profile"].get("grouping", ""),
                     "unit": scenario["profile"].get("evaluation_unit", "")},
        "task_profile": scenario["profile"],
        "query": scenario["query"], "filters": dict(scenario["filters"]),
    }
    event.update(extra)
    return event


def scenarios() -> list[dict]:
    """Each row: expected trigger (or NO_TRIGGER) and the gate event."""
    s = {x["id"]: x for x in SCENARIOS}
    rows = [
        ("E01", "G1", event_for(
            s["S1_HAR_GROUP_LEAKAGE"], trigger="G1", stage="H3",
            milestone="QUESTION_SELECTION", signals=[], task_id="E01")),
        ("E02", "G2", event_for(
            s["S4_SIMPLE_BASELINE"], trigger="G2", stage="H7",
            milestone="PROTOCOL_FREEZE", signals=[], task_id="E02")),
        ("E03", "G3", event_for(
            s["S6_CROSS_EMBODIMENT_SUCCESS"], trigger="G3", stage="H8",
            milestone="CLAIM_OR_CLOSURE", signals=[], task_id="E03")),
        ("E04", "G3", event_for(
            s["S5_LABEL_ERROR_AND_VERSION"], trigger="G3", stage="H9",
            milestone="CLAIM_OR_CLOSURE", signals=[], task_id="E04",
            filters={"mechanism": "EXTERNAL_VALIDATION", "keyword": "Epic"})),
        ("E05", "T1", event_for(
            s["S2_ROBOT_DEMO_FAILURE"], trigger="T1", stage="DEV",
            milestone="NONE", signals=["UNEXPECTED_RESULT",
                                       "CORE_MECHANISM_UNSUPPORTED"],
            task_id="E05", outcome_class="VALID_SCIENTIFIC_NEGATIVE",
            evidence_refs=["runs/run-01.json"])),
        ("E06", "T2", event_for(
            s["S3_CROSS_SENSOR_SUCCESS"], trigger="T2", stage="DEV",
            milestone="NONE", signals=["RESOURCE_INCREASE", "DATA_SCOPE_CHANGE"],
            task_id="E06")),
        ("E07", "NO_TRIGGER", event_for(
            s["S1_HAR_GROUP_LEAKAGE"], trigger="DEV", stage="DEV",
            milestone="NONE", signals=["CODE_CHANGE", "TEST_ONLY"],
            task_id="E07")),
        ("E08", "NO_TRIGGER", event_for(
            s["S1_HAR_GROUP_LEAKAGE"], trigger="DEV", stage="H7",
            milestone="NONE", signals=["HYPERPARAMETER_TUNING", "SAME_SCOPE_DEV"],
            task_id="E08")),
        ("E09", "NO_TRIGGER", event_for(
            s["S1_HAR_GROUP_LEAKAGE"], trigger="DEV", stage="DEV",
            milestone="NONE", signals=["PLOTTING", "REFACTOR"],
            task_id="E09")),
    ]
    # Repeat E01 unchanged -> cache hit, zero new retrieval.
    rows.append(("E10", "G1_HIT", dict(rows[0][2])))
    # Material protocol change -> fingerprint invalidation.
    changed = dict(rows[0][2])
    changed["task_id"] = "E11"
    changed["protocol"] = {"split": "subject-wise", "unit": "subject"}
    changed["hypothesis"] = "按受试者独立分组后重新估计泛化性能"
    rows.append(("E11", "G1_MISS", changed))
    return [{"id": i, "expected": e, "event": v} for i, e, v in rows]


def run() -> dict:
    for key, value in DEFAULTS.items():
        os.environ.setdefault(key, value)
    settings = Settings.load()
    service = ResearchService(settings)
    library_root = Path(os.environ["PDRW_CASE_LIBRARY_ROOT"]).expanduser().resolve()
    case_learning._RESULT_CACHE.clear()
    case_gates._GATE_CACHE.clear()
    before = library_digest(library_root)

    rows = []
    for row in scenarios():
        event, expected = row["event"], row["expected"]
        out = service.call("case_gate_check", event=event)
        triggered = out.get("trigger", "NO_TRIGGER")
        false_trigger = expected == "NO_TRIGGER" and triggered != "NO_TRIGGER"
        missed = (expected in {"G1", "G2", "G3", "T1", "T2"}
                  and triggered != expected)
        rows.append({
            "scenario_id": row["id"], "expected": expected,
            "observed_trigger": triggered,
            "false_trigger": false_trigger, "missed_trigger": missed,
            "status": out.get("status"), "gate_status": out.get("gate_status"),
            "retrieval_executed": bool(out.get("retrieval_executed_this_call")),
            "cache_hit": bool(out.get("cache_hit")),
            "verification": (out.get("verification") or {}).get("status"),
            "returned_cases": len(out.get("case_candidates") or []),
            "negative_warnings": sum(1 for e in (out.get("decision_experiences") or [])
                                     if e["polarity"] == "NEGATIVE_WARNING"),
            "success_transfers": sum(1 for e in (out.get("decision_experiences") or [])
                                     if e["polarity"] == "SUCCESS_TRANSFER"),
            "unknown_reasons": out.get("unknown_reasons") or [],
            "conditions_differ_not_transferred": out.get(
                "conditions_differ_not_transferred") or [],
            "payload_chars": len(json.dumps(out, ensure_ascii=False)),
            "automatic_go_stop": bool(out.get("automatic_go_stop")),
            "hard_gate": bool((out.get("enforcement_level") or {}).get("hard_gate")),
        })

    # Full-detail path: complete evidence via the SAME gate tool, no new tool.
    full = service.call("case_gate_check",
                        event=event_for(SCENARIOS[0], trigger="G1", stage="H3",
                                        milestone="QUESTION_SELECTION",
                                        signals=[], task_id="FULL"),
                        detail="full")
    after = library_digest(library_root)

    gate_calls = len(rows)
    real_retrievals = sum(1 for r in rows if r["retrieval_executed"])
    cache_hits = sum(1 for r in rows if r["cache_hit"])
    compact_chars = sum(r["payload_chars"] for r in rows)
    naive_retrievals = gate_calls  # a naive loop retrieves on every gate call
    guardrails = {
        "no_writes_to_case_library": before == after,
        "no_false_triggers": not any(r["false_trigger"] for r in rows),
        "no_missed_triggers": not any(r["missed_trigger"] for r in rows),
        "all_triggered_checkpoints_verified": all(
            r["verification"] == "RETRIEVAL_AND_APPLICABILITY_VERIFIED"
            for r in rows if r["expected"] in {"G1", "G2", "G3", "T1", "T2"}
            and not r["cache_hit"]),
        "dev_iterations_caused_zero_retrieval": all(
            not r["retrieval_executed"] for r in rows
            if r["expected"] == "NO_TRIGGER"),
        "cache_hit_reused_verified_record": any(
            r["cache_hit"] and r["verification"] ==
            "RETRIEVAL_AND_APPLICABILITY_VERIFIED" for r in rows),
        "material_change_invalidated_cache": any(
            r["expected"] == "G1_MISS" and not r["cache_hit"] for r in rows),
        "unknown_marking_exercised": any(
            r["gate_status"] == "UNKNOWN" for r in rows),
        "conditions_differ_not_used_to_negate": any(
            r["conditions_differ_not_transferred"] for r in rows),
        "no_automatic_go_stop": not any(r["automatic_go_stop"] for r in rows),
        "no_hard_gate_claimed": not any(r["hard_gate"] for r in rows),
        "full_detail_reuses_same_tool": "full_case_payload" in full,
        "compact_default_returns_at_most_5": all(
            r["returned_cases"] <= 5 for r in rows),
    }
    payload = {
        "report_type": "CASE_GATE_ENGINEERING_DIFFERENTIAL",
        "not_a_scientific_utility_measurement": True,
        "library": {"root": str(library_root), "digest_before": before,
                    "digest_after": after},
        "trigger_priority": list(case_gates.TRIGGER_PRIORITY),
        "scenarios": rows,
        "measured": {
            "gate_calls": gate_calls,
            "real_retrieval_calls": real_retrievals,
            "cache_hits": cache_hits,
            "dev_no_trigger_calls": sum(1 for r in rows
                                        if r["expected"] == "NO_TRIGGER"),
            "false_triggers": sum(1 for r in rows if r["false_trigger"]),
            "missed_triggers": sum(1 for r in rows if r["missed_trigger"]),
            "verified_checkpoints": sum(
                1 for r in rows if r["verification"] ==
                "RETRIEVAL_AND_APPLICABILITY_VERIFIED"),
            "unknown_marked_scenarios": sum(1 for r in rows
                                            if r["gate_status"] == "UNKNOWN"),
            "naive_retrieve_every_call_baseline": naive_retrievals,
            "retrieval_calls_avoided": naive_retrievals - real_retrievals,
            "compact_payload_chars_total": compact_chars,
            "compact_payload_chars_mean": round(compact_chars / gate_calls, 1),
            "full_payload_chars": len(json.dumps(full, ensure_ascii=False)),
            "cache_hit_payload_chars": next(
                (r["payload_chars"] for r in rows if r["cache_hit"]), 0),
            "note": ("Payload characters are a deterministic tool-output SIZE "
                     "proxy. Real LLM token cost is NOT_MEASURED."),
        },
        "guardrails": guardrails,
        "not_measured": NOT_MEASURED,
        "interpretation": ("Gates actually retrieve and judge applicability at "
                           "the five triggers, suppress ordinary DEV, reuse a "
                           "verified record on unchanged conditions and mark "
                           "conflicts UNKNOWN. Whether this improves a real "
                           "research decision is NOT measured here."),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    payload["report_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="", help="optional path for the JSON report")
    args = ap.parse_args()
    report = run()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print("GATE_EVAL_REPORT_WRITTEN", out)
        print("report_sha256", report["report_sha256"])
        print("measured", json.dumps(report["measured"], ensure_ascii=False,
                                     sort_keys=True))
        print("guardrails", json.dumps(report["guardrails"], ensure_ascii=False,
                                      sort_keys=True))
    else:
        print(text)
    return 0 if all(report["guardrails"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
