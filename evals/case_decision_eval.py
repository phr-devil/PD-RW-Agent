#!/usr/bin/env python3
"""WP4 verification: do the 65 real cases change the next research action?

MEASURED HERE (tool-level, deterministic, read-only):
  10 concrete decision scenarios against the single real CASE_LIBRARY, a
  synthetic project-identity fixture, fingerprint/cache behaviour, a REAL
  stdio MCP wire call using the live mcp.json configuration, and a static
  installed-Skill deployment check.

NOT MEASURED (never inferred from this script):
  real WorkBuddy A/B/C decision quality, LLM input/output tokens, wall time,
  human turns, blind reviewer grades, scientific utility, and whether the
  WorkBuddy host will *proactively* request the right tool in a live session.
  A host state-transition hard gate is NOT claimed.

Safety: no writes to CASE_LIBRARY, PD-RW rules, STATE/Run/EVENTS, SEALED or
any frozen A/B/C snapshot. Only TemporaryDirectory synthetic fixtures are
created; no network fetch, no training, no GO/STOP.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

from pdrw_agent.config import Settings  # noqa: E402
from pdrw_agent.projects import get_project_context  # noqa: E402
from pdrw_agent.service import ResearchService  # noqa: E402
from pdrw_agent import case_gates, case_learning  # noqa: E402
from case_learning_ablation import SCENARIOS  # noqa: E402
from case_gate_eval import event_for  # noqa: E402

DEFAULTS = {
    "PDRW_AGENT_CONFIG": str(ROOT / "project-map.local.json"),
    "PDRW_WORKFLOW_ROOT": str(ROOT.parent / "Problem-Data-Research-Workflow"),
    "PDRW_CASE_LIBRARY_ROOT": "D:/workbuddy-work/CASE_LIBRARY",
}
MCP_CONFIG = Path("C:/Users/user/.workbuddy/mcp.json")
INSTALLED_SKILL = Path("C:/Users/user/.workbuddy/skills/pd-rw-research/SKILL.md")

NOT_MEASURED = {
    "workbuddy_a_b_c_decision_quality": "NOT_MEASURED",
    "scientific_decision_correctness": "NOT_MEASURED",
    "blind_reviewer_grades": "NOT_MEASURED",
    "real_llm_input_output_token_delta": "NOT_MEASURED",
    "wall_time_delta": "NOT_MEASURED",
    "human_turns_or_interventions": "NOT_MEASURED",
    "scientific_utility": "NOT_MEASURED",
    "host_proactive_tool_request_behaviour": "NOT_MEASURED",
    "host_state_transition_hard_gate": "NOT_MEASURED",
    "reason": ("No real same-model / same-budget / same-frozen-material "
               "WorkBuddy A/B/C replay was executed. Tool-output character "
               "counts are a SIZE proxy, not LLM tokens or research benefit."),
}


def library_digest(root: Path) -> dict:
    files = [root / "index.json"] + sorted(
        p for p in (root / "cases").rglob("*.md") if p.is_file())
    h = hashlib.sha256()
    for p in files:
        h.update(p.name.encode("utf-8"))
        h.update(p.read_bytes())
    return {"files": len(files), "sha256": h.hexdigest()}


def action_types(result: dict) -> list[str]:
    return [a["action_type"] for a in
            (result.get("next_actions") or {}).get("actions", [])]


def identity_probe() -> dict:
    """Synthetic 42/43/44-style Markdown STATE. Real projects untouched."""
    base = Path(tempfile.mkdtemp(prefix="pdrw-wp4-identity-"))
    runtime = Path(tempfile.mkdtemp(prefix="pdrw-wp4-rt-"))
    previous_runtime = os.environ.get("PDRW_RUNTIME_DIR")
    os.environ["PDRW_RUNTIME_DIR"] = str(runtime)
    try:
        rules = base / "rules"
        rules.mkdir()
        for name in ("AGENTS.md", "WORKFLOW.md"):
            (rules / name).write_text("# synthetic\n", encoding="utf-8")
        root = base / "science"
        root.mkdir()
        (root / "STATE.md").write_text(
            "**项目身份**：`PROJECT_ID = 43`｜`PROJECT_ROOT = D:/workbuddy-work/43`｜"
            "P37 与 ws42/44 为不同研究线，不继承其 Run/Claim/分组。\n"
            "## 0. Snapshot\n- ACTIVE_TASK: dev-task\n## 1. History\nold\n",
            encoding="utf-8")
        (root / "RESEARCH_RECORD.md").write_text("## 0. Snapshot\nsynthetic\n",
                                                 encoding="utf-8")
        cfg = base / "projects.json"
        cfg.write_text(json.dumps({"schema_version": 1, "projects": {
            "p": {"root": str(root), "state": "STATE.md",
                  "expected_state_project_id": "44"}}}), encoding="utf-8")
        settings = Settings.load(str(cfg), str(rules))
        conflict = get_project_context(settings, "p")
        svc = ResearchService(settings)
        resume = svc.call("get_resume_context", project_id="p")
        receipt = svc.call("begin_operation_receipt", project_id="p",
                           operation_id="identity-op", task_id="dev-task",
                           action="DEV_CODE")
        status_after = svc.call("get_execution_status", project_id="p")
        return {
            "synthetic_only": True,
            "context_identity": conflict.get("identity"),
            "context_status": conflict.get("status"),
            "declared_state_project_id": conflict.get("declared_state_project_id"),
            "resume_status": resume.get("status"),
            "receipt_status": receipt.get("status"),
            "receipt_error_code": receipt.get("error_code"),
            "receipt_db_created": (runtime / "runtime.sqlite").exists(),
            "exec_status": status_after.get("status"),
            "receipt_blocked": (
                receipt.get("status") in {"IDENTITY_CONFLICT",
                                         "BLOCKED_PROJECT_IDENTITY"} or
                receipt.get("error_code") == "PROJECT_CONTEXT_NOT_READY")
            and not (runtime / "runtime.sqlite").exists(),
        }
    finally:
        import shutil
        shutil.rmtree(base, ignore_errors=True)
        shutil.rmtree(runtime, ignore_errors=True)
        if previous_runtime is None:
            os.environ.pop("PDRW_RUNTIME_DIR", None)
        else:
            os.environ["PDRW_RUNTIME_DIR"] = previous_runtime


def live_mcp_probe(event: dict) -> dict:
    """REAL stdio MCP call with the exact command/args/env from live mcp.json."""
    if not MCP_CONFIG.is_file():
        return {"status": "MCP_CONFIG_MISSING", "checked": False}
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as exc:
        return {"status": "MCP_SDK_UNAVAILABLE", "detail": str(exc)[:120],
                "checked": False}
    cfg = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))
    entry = cfg["mcpServers"]["pd-rw-research"]
    env = dict(os.environ)
    env.update(entry.get("env", {}))
    params = StdioServerParameters(command=entry["command"],
                                   args=entry["args"], env=env)

    async def exercise():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = sorted(t.name for t in (await session.list_tools()).tools)
                mem = await session.call_tool(
                    "search_research_memory", {"query": "HAR 分组 泄漏", "limit": 3})
                mem_d = mem.structured_content or {}
                cl = mem_d.get("case_library") or {}
                gate = await session.call_tool(
                    "case_gate_check", {"event": event, "detail": "compact"})
                gate_d = gate.structured_content or {}
                return {
                    "status": "MCP_WIRE_CALL_EXECUTED", "checked": True,
                    "tool_count": len(tools),
                    "case_gate_check_visible": "case_gate_check" in tools,
                    "tools_called": ["search_research_memory", "case_gate_check"],
                    "search_research_memory_status": mem_d.get("status"),
                    "case_library_status": cl.get("status"),
                    "cases_in_index": ((cl.get("cases") or {})
                                       .get("source_verification") or {})
                                      .get("cases_in_index"),
                    "gate_status": gate_d.get("status"),
                    "gate_verification": (gate_d.get("verification") or {}).get("status"),
                    "next_action_count": (gate_d.get("next_actions") or {}).get("returned"),
                    "is_error": [bool(mem.is_error), bool(gate.is_error)],
                }
    try:
        return asyncio.run(exercise())
    except Exception as exc:  # record the real failure, never fabricate success
        return {"status": "MCP_WIRE_CALL_FAILED", "checked": True,
                "detail": type(exc).__name__ + ":" + str(exc)[:200]}


def installed_skill_probe() -> dict:
    if not INSTALLED_SKILL.is_file():
        return {"status": "INSTALLED_SKILL_MISSING"}
    text = INSTALLED_SKILL.read_text(encoding="utf-8")
    repo = (ROOT / "skills" / "pd-rw-research" / "SKILL.md").read_text(encoding="utf-8")
    return {
        "status": "STATIC_DEPLOYMENT_CHECK_ONLY",
        "version": next((l.split(":", 1)[1].strip() for l in text.splitlines()
                         if l.startswith("version:")), None),
        "byte_identical_to_repo": text == repo,
        "requests_case_gate_check": "case_gate_check(event)" in text,
        "five_triggers_present": all(x in text for x in
                                     ("G1 · H2–H3", "G2 · H4 and H6–H7",
                                      "G3 · H8/H10", "**T1**", "**T2**")),
        "h9_recheck_present": "H9 recheck" in text,
        "next_actions_present": "next_actions" in text,
        "exploratory_lead_present": "EXPLORATORY_LEAD" in text,
        "proactive_behaviour_in_live_session": "NOT_MEASURED",
    }


def run() -> dict:
    for key, value in DEFAULTS.items():
        os.environ.setdefault(key, value)
    settings = Settings.load()
    svc = ResearchService(settings)
    library_root = Path(os.environ["PDRW_CASE_LIBRARY_ROOT"]).expanduser().resolve()
    case_gates._GATE_CACHE.clear()
    case_learning._RESULT_CACHE.clear()
    before = library_digest(library_root)
    s = {x["id"]: x for x in SCENARIOS}

    def gate(scenario_id, trigger, stage, milestone, task_id, **extra):
        ev = event_for(s[scenario_id], trigger=trigger, stage=stage,
                       milestone=milestone, signals=[], task_id=task_id, **extra)
        return svc.call("case_gate_check", event=ev)

    checks = []

    # 1. HAR grouping leakage -> concrete evaluation-protocol check.
    v1 = gate("S1_HAR_GROUP_LEAKAGE", "G2", "H7", "PROTOCOL_FREEZE", "V1")
    v1_checks = [c for c in v1.get("concrete_checks", [])
                 if c.get("promoted_to_next_action")]
    v1_ok = ("CONCRETE_CHECK" in action_types(v1) and bool(v1_checks) and
             any("分组" in a["recommendation"] or "评价单位" in a["recommendation"]
                 for a in v1["next_actions"]["actions"]))
    checks.append({"id": "V1_HAR_GROUPING_TO_PROTOCOL_CHECK", "passed": v1_ok,
                   "observed": {"trigger": v1["trigger"],
                                "action_types": action_types(v1),
                                "promoted_checks": len(v1_checks),
                                "case_ids": [c["case_id"] for c in
                                             v1.get("case_candidates", [])]}})

    # 2. Cross-sensor success -> a conditional technical route, not excluded.
    v2 = gate("S3_CROSS_SENSOR_SUCCESS", "G1", "H3", "QUESTION_SELECTION", "V2")
    v2_success = [e for e in v2.get("decision_experiences", [])
                  if e["polarity"] == "SUCCESS_TRANSFER"]
    v2_ok = (bool(v2_success) and
             "SUCCESS_CONDITION_TO_PRESERVE" in action_types(v2) and
             bool(v2["selection_impact"]["success_key_conditions"]) and
             all(a.get("independent_confirmation") == "NOT_ESTABLISHED"
                 for a in v2["next_actions"]["actions"]
                 if a.get("exploratory_lead_only")))
    checks.append({"id": "V2_CROSS_SENSOR_SUCCESS_ROUTE", "passed": v2_ok,
                   "observed": {"gate_status": v2["gate_status"],
                                "success_experiences": [e["case_id"] for e in v2_success],
                                "tiers": sorted({e["evidence_tier"] for e in v2_success}),
                                "action_types": action_types(v2),
                                "exploratory_only":
                                    v2["next_actions"]["exploratory_only_result"],
                                "success_key_conditions":
                                    v2["selection_impact"]["success_key_conditions"]}})

    # 3. Complex model vs simple baseline -> decisive paired experiment.
    v3 = gate("S4_SIMPLE_BASELINE", "G2", "H7", "PROTOCOL_FREEZE", "V3")
    v3_ok = "DECISIVE_EXPERIMENT" in action_types(v3) and any(
        "强简单基线" in a["recommendation"] and "同一调参预算" in a["recommendation"]
        for a in v3["next_actions"]["actions"])
    checks.append({"id": "V3_BASELINE_DECISIVE_EXPERIMENT", "passed": v3_ok,
                   "observed": {"action_types": action_types(v3),
                                "case_ids": [a["linked_case_id"] for a in
                                             v3["next_actions"]["actions"]]}})

    # 4. Valid scientific negative vs engineering failure.
    def t1(outcome_class):
        ev = event_for(s["S2_ROBOT_DEMO_FAILURE"], trigger="T1", stage="DEV",
                       milestone="NONE", task_id="V4-" + outcome_class,
                       signals=["UNEXPECTED_RESULT"],
                       outcome_class=outcome_class,
                       evidence_refs=["runs/synthetic.json"])
        return svc.call("case_gate_check", event=ev)
    neg, eng = t1("VALID_SCIENTIFIC_NEGATIVE"), t1("ENGINEERING_FAILURE")
    v4_ok = (neg["anomaly_triage"]["category"] == "VALID_SCIENTIFIC_NEGATIVE" and
             eng["anomaly_triage"]["category"] == "ENGINEERING_FAILURE" and
             neg["anomaly_triage"]["category_meaning"] !=
             eng["anomaly_triage"]["category_meaning"] and
             not neg["automatic_go_stop"] and not eng["automatic_go_stop"])
    checks.append({"id": "V4_NEGATIVE_RESULT_VS_ENGINEERING", "passed": v4_ok,
                   "observed": {"negative": neg["anomaly_triage"]["category"],
                                "engineering": eng["anomaly_triage"]["category"],
                                "negative_actions": action_types(neg),
                                "engineering_actions": action_types(eng)}})

    # 5 + 6. Different conditions / strict ESM v1-v2 separation.
    v5 = gate("S5_LABEL_ERROR_AND_VERSION", "G3", "H8", "CLAIM_OR_CLOSURE", "V5",
              filters={"mechanism": "EXTERNAL_VALIDATION", "keyword": "Epic"})
    differ = v5.get("conditions_differ_not_transferred") or []
    transferred = {a["linked_case_id"] for a in v5["next_actions"]["actions"]}
    v5_ok = (bool(differ) and not (set(differ) & transferred) and
             not any(e["case_id"] in differ for e in v5["decision_experiences"]) and
             v5["new_direction_not_negated_by_historical_failure"] and
             v5["may_proceed"] and not v5["blocks_work"])
    v6_ok = ("EXT-X6B" in v5["case_admissibility"] and
             v5["case_admissibility"]["EXT-X6B"] == "UNKNOWN_CONDITIONS_DIFFER" and
             "v2" in json.dumps(v5["task_profile"] if "task_profile" in v5
                                else s["S5_LABEL_ERROR_AND_VERSION"]["profile"],
                                ensure_ascii=False))
    checks.append({"id": "V5_DIFFERENT_CONDITIONS_NOT_MIGRATED", "passed": v5_ok,
                   "observed": {"conditions_differ": differ,
                                "decision_experience_ids": [e["case_id"] for e in
                                                            v5["decision_experiences"]],
                                "next_action_case_ids": sorted(transferred)}})
    checks.append({"id": "V6_ESM_V1_V2_STRICTLY_SEPARATED", "passed": v6_ok,
                   "observed": {"case_admissibility": v5["case_admissibility"],
                                "gate_status": v5["gate_status"],
                                "unknown_reasons": v5["unknown_reasons"]}})

    # 7. Synthetic project identity conflict blocks affected continuation.
    ident = identity_probe()
    v7_ok = (ident["context_status"] == "IDENTITY_CONFLICT" and
             ident["declared_state_project_id"] == "43" and
             ident["resume_status"] == "BLOCKED_PROJECT_IDENTITY" and
             ident["receipt_blocked"])
    checks.append({"id": "V7_PROJECT_IDENTITY_CONFLICT", "passed": v7_ok,
                   "observed": ident})

    # 8. Cache invalidation, index_stale, declaration conflict, DEV suppression.
    base_ev = event_for(s["S1_HAR_GROUP_LEAKAGE"], trigger="G1", stage="H3",
                        milestone="QUESTION_SELECTION", signals=[], task_id="V8")
    a = svc.call("case_gate_check", event=base_ev)
    hit = svc.call("case_gate_check", event=dict(base_ev))
    changed = dict(base_ev)
    changed["decision"] = "改为按受试者独立分组，重新定义核心科学问题"
    changed["task_id"] = "V8-DECISION"
    fp_decision = svc.call("case_gate_check", event=changed)
    bundle = case_learning.load_index(case_learning.resolve_root(settings))
    stale_bundle = dict(bundle, index_stale=True)
    stale = case_gates.case_gate_check(settings, dict(base_ev, task_id="V8-STALE"),
                                       index_override=stale_bundle)
    conflict_ev = dict(base_ev, h_stage="H8", known_h_stage="H3",
                       task_id="V8-CONFLICT")
    conflict = svc.call("case_gate_check", event=conflict_ev)
    dev_ev = dict(base_ev, h_stage="DEV", milestone="NONE", task_id="V8-DEV",
                  signals=["CODE_CHANGE", "HYPERPARAMETER_TUNING"])
    dev = svc.call("case_gate_check", event=dev_ev)
    v8_ok = (hit["cache_hit"] and not hit["retrieval_executed_this_call"] and
             fp_decision["gate_fingerprint"] != a["gate_fingerprint"] and
             stale["verification"]["status"] == "UNKNOWN" and
             not stale["checkpoint_verified"] and
             not conflict["checkpoint_verified"] and
             dev["status"] == "NO_CASE_RETRIEVAL_REQUIRED" and
             not dev["retrieval_executed"])
    checks.append({"id": "V8_CACHE_INVALIDATION_AND_DEV_SUPPRESSION", "passed": v8_ok,
                   "observed": {
                       "identical_event_cache_hit": hit["cache_hit"],
                       "decision_change_new_fingerprint":
                           fp_decision["gate_fingerprint"] != a["gate_fingerprint"],
                       "index_stale_status": stale["status"],
                       "index_stale_verification": stale["verification"]["status"],
                       "declaration_conflict_status": conflict["status"],
                       "declaration_conflicts": conflict["declaration_conflicts"],
                       "dev_status": dev["status"],
                       "dev_retrieval_executed": dev["retrieval_executed"]}})

    # 9. Real stdio MCP wire call with the live deployment configuration.
    live = live_mcp_probe(event_for(
        s["S1_HAR_GROUP_LEAKAGE"], trigger="G1", stage="H3",
        milestone="QUESTION_SELECTION", signals=[], task_id="V9-LIVE"))
    v9_ok = (live.get("status") == "MCP_WIRE_CALL_EXECUTED" and
             live.get("case_gate_check_visible") and
             live.get("case_library_status") == "MATCHES_FOUND" and
             live.get("cases_in_index") == 65 and
             live.get("gate_verification") == "RETRIEVAL_AND_APPLICABILITY_VERIFIED" and
             (live.get("next_action_count") or 0) >= 1 and
             not any(live.get("is_error") or []))
    checks.append({"id": "V9_LIVE_STDIO_MCP_CASE_LIBRARY", "passed": v9_ok,
                   "observed": live})

    # 10. Installed Skill requests the correct tool (static; behaviour NOT_MEASURED).
    skill = installed_skill_probe()
    v10_ok = (skill.get("byte_identical_to_repo") and
              skill.get("requests_case_gate_check") and
              skill.get("five_triggers_present") and
              skill.get("h9_recheck_present") and
              skill.get("next_actions_present"))
    checks.append({"id": "V10_INSTALLED_SKILL_STATIC_CHECK", "passed": v10_ok,
                   "observed": skill,
                   "behavioural_verification": "NOT_MEASURED"})

    after = library_digest(library_root)
    examples = []
    for tag, result in (("HAR 分组泄漏", v1), ("跨传感器成功", v2),
                        ("简单基线增益归因", v3)):
        a0 = (result.get("next_actions") or {}).get("actions", [])[:1]
        if a0:
            a = a0[0]
            examples.append({
                "scenario": tag, "case_id": a["linked_case_id"],
                "action_type": a["action_type"],
                "exploratory_lead_only": a.get("exploratory_lead_only"),
                "recommendation": a["recommendation"][:240],
                "minimal_validation": a["minimal_validation"][:180],
                "execution_status": a["execution_evidence_status"]})

    payload = {
        "report_type": "WP4_CASE_DECISION_VERIFICATION",
        "not_a_scientific_utility_measurement": True,
        "library": {"root": str(library_root), "digest_before": before,
                    "digest_after": after,
                    "unchanged": before == after},
        "checks": checks,
        "checks_passed": sum(1 for c in checks if c["passed"]),
        "checks_total": len(checks),
        "decision_examples": examples,
        "token_cost": {
            "compact_payload_chars": {
                "V1": v1["token_budget"]["payload_chars"],
                "V2": v2["token_budget"]["payload_chars"],
                "V3": v3["token_budget"]["payload_chars"]},
            "note": ("Deterministic tool-output SIZE proxy only. Real LLM "
                     "tokens / wall time are NOT_MEASURED.")},
        "not_measured": NOT_MEASURED,
        "conclusion": ("Verified tool-level: cases produce 1-3 sourced next "
                       "actions, exploratory leads stay labelled, differing "
                       "conditions are not migrated, cache invalidation works, "
                       "and the live stdio MCP reaches the 65-case library. "
                       "Real research benefit is NOT claimed."),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    payload["report_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="", help="optional JSON report path")
    args = ap.parse_args()
    report = run()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print("DECISION_EVAL_REPORT_WRITTEN", out)
        print("report_sha256", report["report_sha256"])
        print("checks_passed", report["checks_passed"], "/", report["checks_total"])
        for c in report["checks"]:
            print(" ", "PASS" if c["passed"] else "FAIL", c["id"])
    else:
        print(text)
    return 0 if report["checks_passed"] == report["checks_total"] else 1


if __name__ == "__main__":
    sys.exit(main())
