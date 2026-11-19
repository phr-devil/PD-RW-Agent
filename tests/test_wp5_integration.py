"""v0.8.2 integration tests: H3/H4/H6 bridge, export contract, cloud parity.

These are TOOL-BEHAVIOUR tests on a synthetic library. They prove the merged
interface keeps both sides' contracts; they are NOT evidence of research value.
"""
from __future__ import annotations

import copy
import json
import tempfile
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_case_learning import HAS_RETRIEVER, _Fixture, _case  # noqa: E402

from pdrw_agent import case_bridge, case_export, case_gates, case_learning
from pdrw_agent.schemas import AgentError
from pdrw_agent.science import lessons

HASH_A = "a" * 64


def early_plan(**overrides) -> dict:
    plan = {
        "schema_version": "pdrw-early-plan-v1", "stage": "H3",
        "research_line_ref": "P37", "scope_ref": "ws-imu",
        "hard_constraints_sha256": HASH_A,
        "upstream_choices": {
            "H1": {"plan_sha256": HASH_A, "original_user_message_ref": "m1", "choice": "HAR"},
            "H2": {"plan_sha256": HASH_A, "original_user_message_ref": "m2", "choice": "Q2+"},
        },
        "options": [{
            "id": "Q1",
            "question_or_evidence_path": "滑窗 HAR 随机 k-fold 是否造成受试者泄漏",
            "paper_value": "可复用的评价协议修正",
            "nearest_prior": "受试者分组交叉验证已成惯例",
            "truth_and_independence": "需要真实受试者标识",
            "discriminating_probe": "随机与 subject-wise 成对比较",
            "cost_and_risk": "仅需重跑评估，不需要新数据",
        }],
        "recommended_option_id": "Q1",
        "recommendation_rationale": "低成本、高判别力",
    }
    plan.update(overrides)
    return plan


def h6_card() -> dict:
    return {
        "schema_version": "pdrw-h6-plan-v3", "scope_ref": "ws-imu",
        "research_line_ref": "P37",
        "hard_constraints_sha256": HASH_A,
        "upstream_choices": {
            "H3": {"plan_sha256": HASH_A, "original_user_message_ref": "m3", "choice": "Q1"},
            "H4": {"plan_sha256": HASH_A, "original_user_message_ref": "m4", "choice": "E1"},
        },
        "options": [{
            "id": "T1",
            "scientific_question": "分组独立时滑窗分类增益是否仍然成立",
            "core_task": "成对评估随机/分组划分差值",
            "dataset_or_proof_path": "本数据集受试者标注",
            "nearest_work_or_unknown": "受试者独立评估",
            "truth_and_independence": "受试者级划分",
            "competing_explanation": "增益来自同受试者窗口重叠而非模型能力",
            "decisive_probe": "同一模型两种划分的配对差值",
            "cost_and_risk": "单卡数小时",
            "science_fit": "SUPPORTED_BY_METADATA", "primary_type": "C02",
            "route": "R1", "p_orientation": "P1",
            "adaptive_pivot_envelope": "仅在差值显著时扩展",
        }],
        "recommended_option_id": "T1",
        "recommendation_rationale": "直接检验泄漏解释",
        "choice": {
            "schema_version": "pdrw-h6-choice-v1", "plan_sha256": HASH_A,
            "kind": "USER_SELECTED", "original_user_message_ref": "msg-h6",
            "selected_option_id": "T1", "allowed_option_ids": [],
            "delegated_scope": None,
        },
    }


@unittest.skipUnless(HAS_RETRIEVER, "CASE_LIBRARY/scripts/search_cases.py not present")
class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.fx = _Fixture(base, [
            _case("T-01", "FAILURE", levels=["ORIGINAL_VERIFIED"],
                  mechanisms=["DATA_LEAKAGE"]),
            _case("T-02", "SUCCESS", levels=["PARTIAL_TEXT_VERIFIED"],
                  mechanisms=["GROUP_INDEPENDENCE"]),
        ])
        case_gates._GATE_CACHE.clear()
        case_learning._RESULT_CACHE.clear()

    def test_h3_card_maps_to_g1_without_rewriting_or_inventing(self):
        card = early_plan()
        before = copy.deepcopy(card)
        r = self.fx.service.call("project_case_bridge", stage_card=card)
        self.assertEqual(card, before, "the bridge must not mutate the card")
        self.assertEqual(r["status"], "CARD_MAPPED_TO_ADVISORY_GATE")
        self.assertEqual((r["stage"], r["gate"]), ("H3", "G1"))
        self.assertTrue(r["early_stage_no_experiment_profile_required"])
        for flag in ("card_rewritten", "choice_altered", "plan_approved",
                     "execution_authorized", "authorization_verified"):
            self.assertFalse(r["authorization"][flag])
        self.assertTrue(r["no_writes"])
        # Only same-meaning fields become profile text; nothing is guessed.
        self.assertEqual(r["task_profile"]["decision"],
                         "滑窗 HAR 随机 k-fold 是否造成受试者泄漏")
        self.assertNotIn("UNKNOWN", r["task_profile"].values())
        for dim in ("labels", "grouping", "evaluation_unit", "baseline",
                    "legal_inputs", "boundaries"):
            self.assertIn(dim, r["unknown_dimensions"])
        self.assertEqual(r["gate_result"]["h_stage_declared"], "H3")
        self.assertTrue(r["gate_result"]["stage_in_expected_range"])

    def test_h6_card_keeps_choice_and_uses_pre_freeze_window(self):
        card = h6_card()
        before = copy.deepcopy(card)
        r = self.fx.service.call("project_case_bridge", stage_card=card)
        self.assertEqual(card, before)
        self.assertEqual((r["stage"], r["gate"]), ("H6", "G2"))
        self.assertEqual(r["selected_option_id"], "T1")
        self.assertEqual(r["selection_basis"],
                         "AUTHOR_SELECTED_DECLARED_UNAUTHENTICATED")
        self.assertEqual(r["choice_ref_declared"], "msg-h6")
        self.assertEqual(r["gate_result"]["h_stage_declared"], "H6")
        self.assertTrue(r["gate_result"]["stage_in_expected_range"])
        self.assertFalse(r["authorization"]["authorization_verified"])
        # The competing explanation is carried only as a counterexample.
        self.assertIn("窗口重叠", r["task_profile"]["counterexamples"])
        self.assertIn("baseline", r["unknown_dimensions"])

    def test_h4_maps_to_the_pre_freeze_window(self):
        card = early_plan(stage="H4")
        r = self.fx.service.call("project_case_bridge", stage_card=card)
        self.assertEqual((r["stage"], r["gate"]), ("H4", "G2"))
        self.assertTrue(r["gate_result"]["stage_in_expected_range"])

    def test_unsupported_stage_is_rejected_without_retrieval(self):
        with self.assertRaises(AgentError) as ctx:
            case_bridge.project_case_bridge(
                self.fx.settings, early_plan(stage="H5"))
        self.assertEqual(ctx.exception.code, "BRIDGE_STAGE_UNSUPPORTED")

    def test_unknown_dimensions_never_fabricate_a_conditions_differ(self):
        """A literal 'UNKNOWN' in the profile would compare as declared text."""
        card = early_plan()
        card["case_profile"] = {"grouping": "随机 k-fold 窗口级"}
        card["query"] = "泄漏 指标"
        r = self.fx.service.call("project_case_bridge", stage_card=card)
        self.assertEqual(r["task_profile"]["grouping"], "随机 k-fold 窗口级")
        self.assertNotIn("grouping", r["unknown_dimensions"])
        self.assertNotIn("UNKNOWN", r["task_profile"].values())
        gate = r["gate_result"]
        self.assertEqual(gate["gate_status"], "ADVISORY_AVAILABLE")
        # Undeclared core dimensions yield applicability RISK, never a
        # fabricated CONDITIONS_DIFFER or an automatic rejection.
        self.assertEqual(gate["case_candidates"][0]["applicability"],
                         "APPLICABILITY_RISK")
        self.assertEqual(gate["case_candidates"][0]["admissibility"],
                         "ADMISSIBLE_WITH_RISK")
        self.assertEqual(gate["next_actions"]["actions"][0]["action_type"],
                         "CONCRETE_CHECK")
        self.assertFalse(gate["automatic_go_stop"])
        self.assertFalse(gate["enforcement_level"]["hard_gate"])


@unittest.skipUnless(HAS_RETRIEVER, "CASE_LIBRARY/scripts/search_cases.py not present")
class ExportContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fx = _Fixture(Path(self.temp.name), [_case("T-01", "FAILURE")])

    def test_markdown_card_is_deterministic_and_read_only(self):
        first = self.fx.service.call("export_case_markdown", case_id="T-01")
        second = self.fx.service.call("export_case_markdown", case_id="T-01")
        self.assertEqual(first["status"], "MARKDOWN_CARD_RENDERED_NOT_WRITTEN")
        self.assertEqual(first["markdown"], second["markdown"])
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertTrue(first["markdown"].startswith("---json\n"))
        self.assertIn("## 可迁移经验", first["markdown"])
        self.assertIn("## 最小验证", first["markdown"])
        self.assertTrue(first["no_writes"])
        self.assertFalse(first["sync_performed"])
        self.assertFalse(first["front_matter"]["authorization_granted"])
        self.assertFalse(first["front_matter"]["scientific_equivalence_verified"])
        self.assertEqual(first["source"]["library_index_sha256"],
                         second["source"]["library_index_sha256"])

    def test_unknown_case_and_missing_library_are_errors(self):
        missing = self.fx.service.call("export_case_markdown", case_id="NOPE")
        self.assertEqual(missing["error_code"], "CASE_NOT_FOUND")
        with self.assertRaises(AgentError):
            case_export.read_case(self.fx.settings, "")


class CloudCapabilityParityTests(unittest.TestCase):
    def test_declared_positive_lesson_stays_unverified(self):
        packet = {"observations": [{
            "run_id": "R-1", "outcome": "VALID_POSITIVE",
            "tested_premise_id": "P-1", "scope": {"dataset": "ws-imu"},
            "evidence_refs": ["run:r-1"],
        }]}
        out = lessons.compile_declared_lessons(packet)
        self.assertEqual(out["status"], "DECLARED_LESSONS_ONLY")
        self.assertEqual(len(out["candidate_prior_positive_lessons"]), 1)
        self.assertFalse(out["all_sources_verified"])
        self.assertFalse(out["semantic_equivalence_verified"])
        self.assertFalse(out["stop_or_go_authorized"])
        self.assertFalse(out["automatic_project_stop"])

    def test_unscoped_positive_is_not_promoted_to_a_lesson(self):
        packet = {"observations": [{
            "run_id": "R-2", "outcome": "VALID_POSITIVE",
            "evidence_refs": ["run:r-2"],
        }]}
        out = lessons.compile_declared_lessons(packet)
        self.assertEqual(out["candidate_prior_positive_lessons"], [])
        self.assertEqual(out["items"][0]["next"],
                         "POSITIVE_SCOPE_REQUIRED_FOR_TRANSFER")

    @unittest.skipUnless(HAS_RETRIEVER, "CASE_LIBRARY/scripts/search_cases.py not present")
    def test_legacy_memory_contract_still_holds(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            fx = _Fixture(base, [_case("T-01")])
            r = fx.service.call("search_research_memory", query="HAR 分组")
            for key in ("status", "query", "matches", "truncated", "limitations"):
                self.assertIn(key, r)
            self.assertIn("case_library", r)
            self.assertIn("case_learning_summary", r)
            skipped = fx.service.call("search_research_memory", query="HAR 分组",
                                      include_cases=False)
            for key in ("status", "query", "matches", "truncated", "limitations"):
                self.assertIn(key, skipped)
            self.assertNotIn("case_library", skipped)


if __name__ == "__main__":
    unittest.main()
