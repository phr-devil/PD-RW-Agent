"""WP3 regressions: cases must change the next action, not just be listed.

All fixtures are synthetic TemporaryDirectory CASE_LIBRARY copies; no real
project STATE/Run/SEALED or frozen A/B/C artifact is read or written.
"""
from __future__ import annotations

import copy
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

from pdrw_agent import case_gates, case_learning, memory  # noqa: E402
from pdrw_agent.config import Settings  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "pdrw_wp3_fixture", ROOT / "tests" / "test_case_learning.py")
_fixture_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture_module)
_Fixture = _fixture_module._Fixture
_case = _fixture_module._case
HAS_RETRIEVER = _fixture_module.HAS_RETRIEVER

PROFILE = {
    "decision": "滑窗 HAR 分类采用随机 k-fold，拟直接报告窗口级准确率",
    "mechanisms": "分组独立性不足与数据泄漏",
    "legal_inputs": "预测时刻可得的 IMU 窗口", "labels": "受试者活动标注",
    "grouping": "随机 k-fold 窗口级划分", "evaluation_unit": "窗口级 accuracy",
    "baseline": "未配对简单线性基线", "boundaries": "仅本数据集随机划分",
    "counterexamples": "若按受试者分组且窗口不重叠，泄漏前提不成立",
}


def event(**overrides) -> dict:
    e = {
        "project_id": "19", "task_id": "WP3-01",
        "decision": PROFILE["decision"],
        "hypothesis": "随机划分下窗口级准确率可代表泛化性能",
        "protocol": {"split": "random-kfold", "unit": "window"},
        "h_stage": "H3", "milestone": "QUESTION_SELECTION", "signals": [],
        "task_profile": dict(PROFILE), "query": "分组 泄漏 标定",
        "filters": {},
    }
    e.update(overrides)
    return e


@unittest.skipUnless(HAS_RETRIEVER, "CASE_LIBRARY/scripts/search_cases.py not present")
class CaseDecisionTests(unittest.TestCase):
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
            _case("T-ABS", "SUCCESS", ["ABSTRACT_VERIFIED"],
                  ["SENSOR_CALIBRATION"], status="PREPRINT"),
        ]
        self.fx = _Fixture(self.base, self.cases)
        self.env = patch.dict(os.environ,
                              {"PDRW_CASE_LIBRARY_ROOT": str(self.fx.root)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def call(self, **kwargs):
        return self.fx.service.call("case_gate_check", **kwargs)

    # -- next actions ------------------------------------------------------
    def test_next_actions_are_sourced_bounded_and_not_executed(self):
        r = self.call(event=event())
        na = r["next_actions"]
        self.assertLessEqual(na["returned"], case_gates.MAX_NEXT_ACTIONS)
        self.assertGreaterEqual(na["returned"], 1)
        self.assertEqual(list(case_gates.DECISION_PIPELINE)[-1],
                         "EXECUTION_EVIDENCE_RECHECK")
        for a in na["actions"]:
            self.assertEqual(a["status"], "PROPOSED_NOT_EXECUTED")
            self.assertEqual(a["execution_evidence_status"],
                             "NO_EXECUTION_EVIDENCE_DECLARED")
            self.assertIn(a["linked_case_id"], r["case_admissibility"])
            self.assertTrue(a["case_source"]["evidence_grade"])
            self.assertTrue(a["applicability_basis"]["method"])
            self.assertEqual(a["task_premises_ref"], "next_actions.task_premises")
            self.assertFalse(a["automatic_go_stop"])
        self.assertTrue(na["task_premises"]["grouping"])
        self.assertEqual(r["selection_impact"]["next_action_ids"],
                         [a["action_id"] for a in na["actions"]])

    def test_g2_checks_are_promoted_into_next_actions(self):
        r = self.call(event=event(h_stage="H7", milestone="PROTOCOL_FREEZE",
                                  task_id="WP3-G2"))
        self.assertTrue(any(c.get("promoted_to_next_action")
                            for c in r["concrete_checks"]))
        self.assertTrue(r["protocol_design_review"]["actionable_next_action_ids"])

    def test_g1_and_g3_no_longer_have_fixed_placeholders(self):
        g1 = self.call(event=event())
        self.assertNotEqual(
            g1["selection_impact"]["highly_overlapping_research"],
            "UNKNOWN_REQUIRES_LINE_BY_LINE_PREMISE_COMPARISON")
        self.assertNotEqual(
            g1["selection_impact"]["historical_failure_premises_still_hold"],
            "UNKNOWN_REQUIRES_LINE_BY_LINE_PREMISE_COMPARISON")
        g3 = self.call(event=event(h_stage="H8", milestone="CLAIM_OR_CLOSURE",
                                   task_id="WP3-G3"))
        self.assertNotEqual(
            g3["contribution_review"]
              ["evidence_supports_algorithm_innovation_or_mechanism_claim"],
            "UNKNOWN_VERIFY_ORIGINAL_RUN")
        self.assertTrue(g3["contribution_review"]["author_strategy_required"])

    def test_one_line_impact_is_a_lesson_not_a_single_character(self):
        r = self.call(event=event())
        for c in r["case_candidates"]:
            self.assertGreater(len(c["one_line_impact"]), 3)

    def test_exploratory_success_lead_is_labelled_not_confirmed(self):
        r = self.call(event=event(query="标定", filters={"verdict": "SUCCESS"},
                                  task_id="WP3-LEAD",
                                  task_profile=dict(PROFILE, mechanisms="标定")))
        brief = case_learning.case_search(
            self.fx.settings, "标定", {"verdict": "SUCCESS"}, limit=5,
            task_profile=dict(PROFILE, mechanisms="标定"))
        tiers = {e["case_id"]: e["evidence_tier"]
                 for e in brief["decision_experiences"]["experiences"]}
        self.assertIn("EXPLORATORY_LEAD", tiers.values())
        for e in brief["decision_experiences"]["experiences"]:
            if e["exploratory_lead_only"] and e["polarity"] == "SUCCESS_TRANSFER":
                self.assertEqual(e["independent_confirmation"], "NOT_ESTABLISHED")
                self.assertIn("minimal_validation_experiment",
                              e["success_transfer"])
        for a in r["next_actions"]["actions"]:
            if a["exploratory_lead_only"]:
                self.assertEqual(a["independent_confirmation"], "NOT_ESTABLISHED")
                self.assertIn("探索线索", a["recommendation"])

    def test_conditions_differ_case_never_becomes_a_next_action(self):
        profile = dict(PROFILE, decision="评估 Epic Sepsis Model v2",
                       mechanisms="EXTERNAL_VALIDATION",
                       counterexamples="v1 不得泛化到 v2")
        r = self.call(event=event(h_stage="H8", milestone="CLAIM_OR_CLOSURE",
                                  task_id="WP3-V2", task_profile=profile,
                                  query="ESM v1 v2",
                                  filters={"mechanism": "EXTERNAL_VALIDATION"}))
        for cid in r["conditions_differ_not_transferred"]:
            self.assertNotIn(cid, [a["linked_case_id"]
                                   for a in r["next_actions"]["actions"]])
        self.assertTrue(r["new_direction_not_negated_by_historical_failure"])
        self.assertTrue(r["may_proceed"])

    # -- triggers, conflicts and cache -------------------------------------
    def test_h9_protocol_change_reopens_g2(self):
        r = self.call(event=event(h_stage="H9", milestone="PROTOCOL_RECHECK",
                                  task_id="WP3-H9",
                                  signals=["CONFIRMATION_PROTOCOL_CHANGED"]))
        self.assertEqual(r["trigger"], "G2")
        self.assertIn("concrete_checks", r)
        self.assertIn("H9", r["protocol_recheck"])

    def test_contradictory_declaration_is_never_verified_but_not_blocking(self):
        r = self.call(event=event(h_stage="H8", milestone="CLAIM_OR_CLOSURE",
                                  known_h_stage="H3", task_id="WP3-CONFLICT"))
        self.assertTrue(r["declaration_conflicts"])
        self.assertFalse(r["checkpoint_verified"])
        self.assertEqual(r["verification"]["status"], "UNKNOWN")
        self.assertTrue(r["may_proceed"])
        self.assertFalse(r["blocks_work"])
        self.assertTrue(r["retrieval_executed"])

    def test_index_stale_never_reuses_verified_conclusion(self):
        ev = event()
        first = self.call(event=ev)
        self.assertTrue(first["checkpoint_verified"])
        bundle = case_learning.load_index(self.fx.root)
        stale = case_gates.case_gate_check(
            self.fx.settings, ev, index_override=dict(bundle, index_stale=True))
        self.assertFalse(stale["cache_hit"])
        self.assertFalse(stale["checkpoint_verified"])
        self.assertEqual(stale["verification"]["status"], "UNKNOWN")

    def test_fingerprint_covers_decision_and_index_stale(self):
        e = event()
        a, parts = case_gates.gate_fingerprint(e, "G1", "sha")
        self.assertIn("decision", parts)
        self.assertIn("case_library_index_stale", parts)
        changed = dict(e, decision="改为按受试者独立分组")
        b, _ = case_gates.gate_fingerprint(changed, "G1", "sha")
        self.assertNotEqual(a, b)
        c, _ = case_gates.gate_fingerprint(e, "G1", "sha", index_stale=True)
        self.assertNotEqual(a, c)

    def test_payload_chars_matches_actual_returned_payload(self):
        r = self.call(event=event(task_id="WP3-PAYLOAD"))
        reported = r["token_budget"]["payload_chars"]
        actual = len(json.dumps(
            {k: v for k, v in r.items() if k != "token_budget"},
            ensure_ascii=False))
        self.assertLessEqual(abs(reported - actual), 2)
        again = self.call(event=event(task_id="WP3-PAYLOAD"))
        self.assertTrue(again["cache_hit"])
        self.assertLessEqual(
            abs(again["token_budget"]["payload_chars"] -
                len(json.dumps({k: v for k, v in again.items()
                                if k != "token_budget"}, ensure_ascii=False))), 2)

    # -- compact default and case_scope ------------------------------------
    def test_compact_search_removes_duplicated_nested_metadata(self):
        r = self.fx.service.call("search_research_memory", query="分组 泄漏",
                                 task_profile=dict(PROFILE))
        cl = r["case_library"]
        self.assertTrue(cl["compact_by_default"])
        for section in (cl["cases"], cl["case_review"], cl["decision_experiences"]):
            if isinstance(section, dict):
                self.assertNotIn("warning", section)
                self.assertNotIn("notice", section)
        for c in cl["case_review"]["comparisons"]:
            self.assertIn("dimension_status", c)
            self.assertNotIn("dimension_comparison", c)

    def test_unrelated_memory_lookup_skips_full_case_library(self):
        r = self.fx.service.call("search_research_memory", query="项目状态快照")
        self.assertEqual(r["case_library"]["status"],
                         "CASE_LIBRARY_RETRIEVAL_SKIPPED")
        self.assertFalse(r["case_learning_summary"]["case_retrieval_executed"])
        forced = self.fx.service.call("search_research_memory",
                                      query="项目状态快照", case_scope="force")
        self.assertNotEqual(forced["case_library"]["status"],
                            "CASE_LIBRARY_RETRIEVAL_SKIPPED")
        legacy_only = self.fx.service.call("search_research_memory",
                                           query="分组", include_cases=False)
        self.assertNotIn("case_library", legacy_only)

    def test_execution_evidence_is_not_claimed_without_real_refs(self):
        r = self.call(event=event(task_id="WP3-EXEC"))
        self.assertEqual(r["next_actions"]["execution_evidence"]["status"],
                         "NO_EXECUTION_EVIDENCE_DECLARED")
        declared = self.call(event=event(task_id="WP3-EXEC-REFS",
                                         execution_evidence_refs=["run-not-real"]))
        check = declared["next_actions"]["execution_evidence"]
        self.assertEqual(check["status"],
                         "DECLARED_REFS_NOT_FOUND_IN_EXISTING_RECORDS")
        self.assertTrue(check["no_writes"])


if __name__ == "__main__":
    unittest.main()
