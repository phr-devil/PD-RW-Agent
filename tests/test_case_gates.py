"""Acceptance tests for the five case-application gates.

Covers: real retrieval at 3 checkpoints; 2 conditional triggers; DEV-noise
suppression; fingerprint cache hit/invalidation; both polarities; historical
failure not negating a new direction; UNKNOWN marking; MCP/legacy
compatibility; honest (non-hard-gate) enforcement level.

Tool behaviour only. Scientific decision quality is NOT measured here; see
evals/case_gate_eval.py for the engineering differential and NOT_MEASURED.
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

from pdrw_agent import case_gates, case_learning  # noqa: E402
from pdrw_agent.config import Settings  # noqa: E402

# Reuse the already-verified CASE_LIBRARY fixture instead of building a second
# synthetic library. Loaded by path so it works both under unittest discover
# and when this module is imported as tests.test_case_gates.
_spec = importlib.util.spec_from_file_location(
    "pdrw_case_learning_fixture", ROOT / "tests" / "test_case_learning.py")
_fixture_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture_module)
_Fixture = _fixture_module._Fixture
_case = _fixture_module._case
REAL_LIBRARY = _fixture_module.REAL_LIBRARY
HAS_RETRIEVER = _fixture_module.HAS_RETRIEVER

PROFILE = {
    "decision": "滑窗 HAR 分类拟采用随机 k-fold",
    "mechanisms": "GROUP_INDEPENDENCE DATA_LEAKAGE",
    "legal_inputs": "预测时刻可得的 IMU 窗口",
    "labels": "受试者活动标注",
    "grouping": "随机 k-fold 窗口级划分",
    "evaluation_unit": "窗口级 accuracy",
    "baseline": "未配对简单线性基线",
    "boundaries": "仅限本数据集随机划分",
    "counterexamples": "若按受试者分组且窗口不重叠则泄漏前提不成立",
}


def gate_event(**overrides) -> dict:
    event = {
        "project_id": "19", "task_id": "T-HAR-01",
        "decision": "确定 HAR 滑窗分类的核心科学问题与协议",
        "hypothesis": "随机划分下窗口级准确率可代表泛化性能",
        "protocol": {"split": "random-kfold", "unit": "window"},
        "task_profile": dict(PROFILE),
        "query": "分组 泄漏 标签 基线",
        "filters": {},
        "h_stage": "DEV", "milestone": "NONE", "signals": [],
    }
    event.update(overrides)
    return event


@unittest.skipUnless(HAS_RETRIEVER, "CASE_LIBRARY/scripts/search_cases.py not present")
class CaseGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        case_learning._RESULT_CACHE.clear()
        case_learning._RETRIEVER_CACHE.clear()
        case_gates._GATE_CACHE.clear()
        self.base = Path(self.temp.name)
        self.cases = [
            _case("T-F1", "FAILURE", ["ORIGINAL_VERIFIED"],
                  ["GROUP_INDEPENDENCE", "DATA_LEAKAGE"]),
            _case("T-S1", "SUCCESS", ["PARTIAL_TEXT_VERIFIED"],
                  ["SENSOR_CALIBRATION"],
                  boundaries=["仅适用于可施加已知物理激励的电容式阵列"],
                  counterexamples=["光学视触觉在凝胶互换后完全无法迁移"],
                  role="THIRD_PARTY_REPLICATION"),
            _case("T-V1", "FAILURE", ["ORIGINAL_VERIFIED"], ["EXTERNAL_VALIDATION"],
                  boundaries=["本卡结论只适用于 Epic Sepsis Model v1；不得泛化到 v2 或后续版本"],
                  counterexamples=["v2 多中心前瞻验证 AUROC 0.82–0.92"]),
            _case("T-ABS", "FAILURE", ["ABSTRACT_VERIFIED"], ["LABEL_ERROR"]),
            _case("T-SEC", "FAILURE", ["SECONDARY_ONLY"], ["LABEL_ERROR"]),
            _case("T-INT", "FAILURE", ["INTERNAL_REPORT"], ["LABEL_ERROR"],
                  origin="INTERNAL", role="AUTHOR_REPORT"),
        ]
        self.fx = _Fixture(self.base, self.cases)
        self.env = patch.dict(os.environ, {"PDRW_CASE_LIBRARY_ROOT": str(self.fx.root)})
        self.env.start()
        self.addCleanup(self.env.stop)

    # -- 1. Three mandatory checkpoints actually retrieve ------------------
    def test_three_mandatory_checkpoints_actually_retrieve(self):
        for trigger, stage, milestone, output_key in (
            ("G1", "H3", "QUESTION_SELECTION", "selection_impact"),
            ("G2", "H7", "PROTOCOL_FREEZE", "concrete_checks"),
            ("G3", "H8", "CLAIM_OR_CLOSURE", "contribution_review"),
        ):
            with self.subTest(trigger=trigger):
                r = self.fx.service.call("case_gate_check",
                                         event=gate_event(h_stage=stage,
                                                          milestone=milestone))
                self.assertEqual(r["trigger"], trigger)
                self.assertEqual(r["trigger_kind"], "MANDATORY_CHECKPOINT")
                self.assertEqual(r["status"], "CHECKPOINT_RETRIEVAL_VERIFIED")
                self.assertTrue(r["retrieval_executed"])
                self.assertTrue(r["retrieval_executed_this_call"])
                self.assertEqual(r["verification"]["status"],
                                 "RETRIEVAL_AND_APPLICABILITY_VERIFIED")
                record = r["retrieval_record"]
                self.assertEqual(record["retrieval_tool"], "case_learning.case_search")
                self.assertTrue(record["retrieved_case_ids"])
                self.assertTrue(record["applicability_judgments"])
                self.assertIn("query", record["retrieval_scope"])
                self.assertIn("case_library_index_sha256", record["retrieval_scope"])
                self.assertIn(output_key, r)
                self.assertFalse(r["automatic_go_stop"])
        # G3 must not weaken PD-RW H8 author strategy / writing permission.
        g3 = self.fx.service.call("case_gate_check",
                                  event=gate_event(h_stage="H8",
                                                   milestone="CLAIM_OR_CLOSURE"))
        self.assertTrue(g3["contribution_review"]["author_strategy_required"])

    # -- 2. Two conditional triggers --------------------------------------
    def test_conditional_triggers_detect_material_changes(self):
        t1 = self.fx.service.call("case_gate_check", event=gate_event(
            signals=["UNEXPECTED_RESULT", "SEVERE_EVALUATION_PROBLEM"],
            outcome_class="VALID_SCIENTIFIC_NEGATIVE",
            evidence_refs=["runs/r1.json"]))
        self.assertEqual(t1["trigger"], "T1")
        self.assertEqual(t1["status"], "TRIGGER_RETRIEVAL_VERIFIED")
        self.assertIn("anomaly_triage", t1)
        self.assertEqual(t1["anomaly_triage"]["category"],
                         "VALID_SCIENTIFIC_NEGATIVE")
        self.assertFalse(t1["anomaly_triage"]["automatic_go_stop"])

        t2 = self.fx.service.call("case_gate_check", event=gate_event(
            task_id="T-CHANGE", signals=["RESOURCE_INCREASE",
                                         "CORE_ALGORITHM_CHANGE"]))
        self.assertEqual(t2["trigger"], "T2")
        self.assertIn("decision_change_review", t2)
        self.assertEqual(t2["decision_change_review"]["declared_material_changes"],
                         ["CORE_ALGORITHM_CHANGE", "RESOURCE_INCREASE"])

        # Priority: a checkpoint outranks a conditional trigger; the other
        # trigger is still reported but does NOT cause a second retrieval.
        both = self.fx.service.call("case_gate_check", event=gate_event(
            task_id="T-BOTH", h_stage="H3", milestone="QUESTION_SELECTION",
            signals=["UNEXPECTED_RESULT"]))
        self.assertEqual(both["trigger"], "G1")
        self.assertIn("T1", both["other_matched_triggers"])

    def test_unknown_declared_signal_is_not_invented(self):
        r = self.fx.service.call("case_gate_check", event=gate_event(
            signals=["QUANTUM_MIRACLE"]))
        self.assertEqual(r["status"], "NO_CASE_RETRIEVAL_REQUIRED")
        self.assertEqual(r["unknown_declared_signals"], ["QUANTUM_MIRACLE"])
        self.assertTrue(any("UNKNOWN_DECLARED_SIGNALS" in x
                            for x in r["unknown_reasons"]))

    # -- 3. Ordinary DEV does not repeat retrieval ------------------------
    def test_ordinary_dev_iteration_does_not_repeat_retrieval(self):
        dev_signals = ["CODE_CHANGE", "HYPERPARAMETER_TUNING", "TEST_ONLY",
                       "PLOTTING", "SAME_SCOPE_DEV", "BUG_FIX", "REFACTOR"]
        before = len(case_gates._GATE_CACHE)
        for i in range(6):
            r = self.fx.service.call("case_gate_check", event=gate_event(
                task_id=f"DEV-{i}", h_stage="H7",
                signals=dev_signals[:2] + [dev_signals[i % len(dev_signals)]]))
            self.assertEqual(r["status"], "NO_CASE_RETRIEVAL_REQUIRED")
            self.assertEqual(r["suppressed_reason"],
                             "ORDINARY_DEV_ITERATION_NO_CASE_RETRIEVAL")
            self.assertFalse(r["retrieval_executed"])
        self.assertEqual(len(case_gates._GATE_CACHE), before)
        # A same-scope H7 DEV step with no freeze milestone also does not fire
        # even though G2 covers H7 (the milestone is what matters).
        r = self.fx.service.call("case_gate_check", event=gate_event(
            h_stage="H7", milestone="NONE", signals=["SAME_SCOPE_DEV"]))
        self.assertEqual(r["trigger"], "NO_TRIGGER")

    # -- 4. Cache hit + invalidation --------------------------------------
    def test_cache_hit_and_key_condition_invalidation(self):
        ev = gate_event(h_stage="H3", milestone="QUESTION_SELECTION")
        a = self.fx.service.call("case_gate_check", event=ev)
        b = self.fx.service.call("case_gate_check", event=ev)
        self.assertFalse(a["cache_hit"])
        self.assertTrue(b["cache_hit"])
        self.assertTrue(b["reused_verified_record"])
        self.assertFalse(b["retrieval_executed_this_call"])
        self.assertEqual(b["token_budget"]["new_retrieval_calls"], 0)
        self.assertEqual(a["gate_fingerprint"], b["gate_fingerprint"])
        self.assertEqual(b["verification"]["status"],
                         "RETRIEVAL_AND_APPLICABILITY_VERIFIED")
        self.assertEqual(b["gate_status"], a["gate_status"])

        for key, value in (
            ("hypothesis", "changed scientific hypothesis"),
            ("protocol", {"split": "subject-wise", "unit": "subject"}),
            ("h_stage", "H2"),
            ("task_id", "T-OTHER"),
            ("query", "标签 错误"),
            ("filters", {"mechanism": "LABEL_ERROR"}),
        ):
            with self.subTest(changed=key):
                changed = gate_event(h_stage="H3", milestone="QUESTION_SELECTION")
                changed[key] = value
                r = self.fx.service.call("case_gate_check", event=changed)
                self.assertFalse(r["cache_hit"])
                self.assertNotEqual(r["gate_fingerprint"], a["gate_fingerprint"])
        changed_profile = dict(PROFILE)
        changed_profile["legal_inputs"] = "完全不同的合法信息集与预测时刻字段"
        r = self.fx.service.call("case_gate_check", event=gate_event(
            h_stage="H3", milestone="QUESTION_SELECTION",
            task_profile=changed_profile))
        self.assertFalse(r["cache_hit"])

    def test_case_library_version_change_invalidates_fingerprint(self):
        ev = gate_event(h_stage="H3", milestone="QUESTION_SELECTION")
        a, _ = case_gates.gate_fingerprint(ev, "G1", "sha-old")
        b, parts = case_gates.gate_fingerprint(ev, "G1", "sha-new")
        self.assertNotEqual(a, b)
        self.assertEqual(parts["case_library_index_sha256"], "sha-new")
        self.assertIn("hypothesis", parts)
        self.assertIn("protocol", parts)
        self.assertIn("trigger", parts)

    # -- 5. Success and failure both influence advice ---------------------
    def test_success_and_failure_cases_both_influence_advice(self):
        # Free-text (non-taxonomy) mechanisms avoid a hard mechanism filter,
        # so both the failure and the success card remain in the candidate set.
        broad_profile = dict(PROFILE)
        broad_profile["mechanisms"] = "分组独立性不足、泄漏与传感器标定"
        r = self.fx.service.call("case_gate_check", event=gate_event(
            h_stage="H3", milestone="QUESTION_SELECTION",
            query="分组 泄漏 标定", task_profile=broad_profile))
        polarities = {e["polarity"] for e in r["decision_experiences"]}
        self.assertIn("NEGATIVE_WARNING", polarities)
        self.assertIn("SUCCESS_TRANSFER", polarities)
        self.assertIn("T-F1", r["case_admissibility"])
        self.assertIn("T-S1", r["case_admissibility"])
        self.assertLessEqual(len(r["case_candidates"]), 5)
        self.assertGreaterEqual(len(r["selection_impact"]["key_experiences"]), 2)

    # -- 6. Historical failure must not negate a different new direction --
    def test_historical_failure_does_not_negate_new_direction(self):
        v2_profile = dict(PROFILE)
        v2_profile.update({
            "decision": "评估 Epic Sepsis Model v2 在本院 EHR 的表现",
            "mechanisms": "EXTERNAL_VALIDATION",
            "boundaries": "v2 多中心前瞻验证",
            "counterexamples": "v1 结论不得泛化到 v2",
        })
        r = self.fx.service.call("case_gate_check", event=gate_event(
            h_stage="H8", milestone="CLAIM_OR_CLOSURE",
            query="ESM v1 v2", filters={"mechanism": "EXTERNAL_VALIDATION"},
            task_profile=v2_profile))
        self.assertTrue(r["new_direction_not_negated_by_historical_failure"])
        self.assertTrue(r["may_proceed"])
        self.assertFalse(r["blocks_work"])
        self.assertFalse(r["automatic_go_stop"])
        self.assertEqual(r["case_admissibility"].get("T-V1"),
                         "UNKNOWN_CONDITIONS_DIFFER")
        self.assertIn("T-V1", r["conditions_differ_not_transferred"])
        self.assertFalse(any(e["case_id"] == "T-V1"
                             for e in r["decision_experiences"]))
        text = json.dumps(r, ensure_ascii=False)
        self.assertNotIn('"STOP"', text)
        self.assertNotIn('"GO"', text)

    # -- 7. UNKNOWN marking ------------------------------------------------
    def test_unknown_for_no_match_source_insufficient_and_conflict(self):
        no_match = self.fx.service.call("case_gate_check", event=gate_event(
            h_stage="H3", milestone="QUESTION_SELECTION", task_id="NO-MATCH",
            filters={"mechanism": "NO_SUCH_MECHANISM"}))
        self.assertEqual(no_match["gate_status"], "UNKNOWN")
        self.assertTrue(no_match["retrieval_record"]["no_match"])
        self.assertTrue(any("NO_CASE_MATCH" in x
                            for x in no_match["unknown_reasons"]))
        self.assertTrue(no_match["may_proceed"])
        self.assertEqual(no_match["verification"]["status"],
                         "RETRIEVAL_AND_APPLICABILITY_VERIFIED")
        self.assertIn("filters", no_match["retrieval_record"]["retrieval_scope"])

        weak = self.fx.service.call("case_gate_check", event=gate_event(
            h_stage="H3", milestone="QUESTION_SELECTION", task_id="WEAK",
            filters={"mechanism": "LABEL_ERROR"}))
        self.assertEqual(weak["gate_status"], "UNKNOWN")
        self.assertTrue(any("UNKNOWN_SOURCE_INSUFFICIENT" in x
                            for x in weak["unknown_reasons"]))

        no_profile = self.fx.service.call("case_gate_check", event=gate_event(
            h_stage="H3", milestone="QUESTION_SELECTION", task_profile=None))
        self.assertEqual(no_profile["status"], "TASK_PROFILE_REQUIRED")
        self.assertEqual(no_profile["gate_status"], "UNKNOWN")
        self.assertFalse(no_profile["retrieval_executed"])

    def test_inaccessible_library_reports_reason_without_fake_or_block(self):
        with patch.dict(os.environ, {"PDRW_CASE_LIBRARY_ROOT": str(self.base / "missing")}):
            r = self.fx.service.call("case_gate_check", event=gate_event(
                h_stage="H3", milestone="QUESTION_SELECTION"))
        self.assertEqual(r["status"], "CASE_LIBRARY_UNAVAILABLE")
        self.assertEqual(r["gate_status"], "UNKNOWN")
        self.assertFalse(r["retrieval_executed"])
        self.assertTrue(r["unknown_reasons"])
        self.assertTrue(r["may_proceed"])
        self.assertFalse(r["blocks_work"])

    # -- 8. Compatibility + real MCP wire ---------------------------------
    def test_case_check_text_is_not_accepted_as_proof(self):
        v = case_gates.verify_gate_record({"CASE_CHECK": "COMPLETED"})
        self.assertEqual(v["status"], "UNKNOWN")
        self.assertTrue(v["unknown_reasons"])
        self.assertTrue(any("RETRIEVAL_RECORD_FIELDS_MISSING" in x
                            for x in v["unknown_reasons"]))

    def test_legacy_memory_shape_unchanged_and_enforcement_honest(self):
        legacy = self.fx.service.call("search_research_memory", query="HAR 分组")
        for key in ("status", "query", "matches", "truncated", "limitations"):
            self.assertIn(key, legacy)
        gate = self.fx.service.call("case_gate_check", event=gate_event(
            h_stage="H3", milestone="QUESTION_SELECTION", task_id="ENF"))
        enf = gate["enforcement_level"]
        self.assertEqual(enf["actual"], "ADVISORY_SKILL_AND_TOOL_LEVEL")
        self.assertFalse(enf["hard_gate"])
        self.assertFalse(enf["host_state_transition_interception"])
        self.assertFalse(enf["can_block_work"])
        self.assertTrue(gate["no_writes"])
        self.assertEqual(gate["decision_authority"],
                         "PD-RW_WORKFLOW_AND_AUTHOR_ONLY")

    @unittest.skipUnless(importlib.util.find_spec("mcp") is not None,
                         "Install optional MCP SDK for wire-level tests")
    def test_real_mcp_wire_call_returns_gate_record(self):
        from mcp import Client
        from pdrw_agent.integrations.mcp_server import create_server

        async def exercise():
            server = create_server(self.fx.settings)
            async with Client(server) as client:
                names = {t.name for t in (await client.list_tools()).tools}
                self.assertIn("case_gate_check", names)
                self.assertNotIn("write_case_to_library", names)
                for existing in ("search_research_memory", "review_case_transfer",
                                 "extract_case_candidates", "get_project_context"):
                    self.assertIn(existing, names)
                resp = await client.call_tool("case_gate_check", {
                    "event": gate_event(h_stage="H3",
                                        milestone="QUESTION_SELECTION",
                                        task_id="MCP-WIRE")})
                self.assertFalse(resp.is_error)
                text = str(resp.structured_content or resp.content)
                for marker in ("CHECKPOINT_RETRIEVAL_VERIFIED",
                               "RETRIEVAL_AND_APPLICABILITY_VERIFIED",
                               "selection_impact", "automatic_go_stop",
                               "ADVISORY_SKILL_AND_TOOL_LEVEL"):
                    self.assertIn(marker, text)

        asyncio.run(exercise())


@unittest.skipUnless(HAS_RETRIEVER and (REAL_LIBRARY / "index.json").is_file(),
                     "Real CASE_LIBRARY not available")
class RealLibraryGateTests(unittest.TestCase):
    def setUp(self):
        case_learning._RESULT_CACHE.clear()
        case_gates._GATE_CACHE.clear()
        self.settings = Settings.load(
            str(ROOT / "project-map.local.json"),
            str(ROOT.parent / "Problem-Data-Research-Workflow"))
        self.env = patch.dict(os.environ, {"PDRW_CASE_LIBRARY_ROOT": str(REAL_LIBRARY)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_real_har_grouping_checkpoint_produces_verified_negative_advice(self):
        from pdrw_agent.service import ResearchService
        from case_learning_ablation import SCENARIOS
        sc = SCENARIOS[0]
        event = {
            "project_id": "37", "task_id": "REAL-G1",
            "h_stage": "H3", "milestone": "QUESTION_SELECTION",
            "decision": sc["profile"]["decision"],
            "hypothesis": "随机 k-fold 窗口级准确率可代表泛化",
            "protocol": {"split": "random-kfold", "unit": "window"},
            "task_profile": sc["profile"], "query": sc["query"],
            "filters": sc["filters"], "signals": [],
        }
        r = ResearchService(self.settings).call("case_gate_check", event=event)
        self.assertEqual(r["status"], "CHECKPOINT_RETRIEVAL_VERIFIED")
        self.assertEqual(r["verification"]["status"],
                         "RETRIEVAL_AND_APPLICABILITY_VERIFIED")
        self.assertGreater(r["retrieval_record"]["retrieval_scope"]["cases_in_index"], 60)
        self.assertTrue(any(e["polarity"] == "NEGATIVE_WARNING"
                            for e in r["decision_experiences"]))
        self.assertTrue(r["retrieval_record"]["retrieved_case_ids"])

    def test_real_v1_v2_conflict_is_unknown_not_a_stop(self):
        from pdrw_agent.service import ResearchService
        event = {
            "project_id": "37", "task_id": "REAL-V2",
            "h_stage": "H8", "milestone": "CLAIM_OR_CLOSURE",
            "decision": "评估 Epic Sepsis Model v2 在本院 EHR 的部署表现",
            "hypothesis": "v2 外部验证结论可直接沿用 v1 口径",
            "protocol": {"version": "v2"},
            "task_profile": {
                "decision": "评估 ESM v2", "mechanisms": "EXTERNAL_VALIDATION",
                "legal_inputs": "院内 EHR 预测时刻可得字段",
                "labels": "复合脓毒症标签", "grouping": "独立住院次",
                "evaluation_unit": "encounter AUROC", "baseline": "厂商报告 AUC",
                "boundaries": "v2 多中心前瞻",
                "counterexamples": "v1 不得泛化到 v2"},
            "query": "ESM v1 v2",
            "filters": {"mechanism": "EXTERNAL_VALIDATION", "keyword": "Epic"},
        }
        r = ResearchService(self.settings).call("case_gate_check", event=event)
        self.assertTrue(r["new_direction_not_negated_by_historical_failure"])
        self.assertFalse(r["automatic_go_stop"])
        self.assertIn("EXT-X6B", r["case_admissibility"])
        self.assertEqual(r["case_admissibility"]["EXT-X6B"],
                         "UNKNOWN_CONDITIONS_DIFFER")
        self.assertTrue(any("UNKNOWN_CONDITIONS_DIFFER" in x
                            for x in r["unknown_reasons"]))


if __name__ == "__main__":
    unittest.main()
