"""WP9-B: declared Run feedback actually changes the next-action proposal.

Tool-level tests on synthetic fixtures. They prove that a valid negative does
not stop the project, that an invalid Run is not read as a scientific failure,
and that case risk alone does not become an author approval node. They do NOT
measure scientific benefit.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from pdrw_agent import case_gates, case_learning  # noqa: E402
from tests.test_case_gates import gate_event  # noqa: E402
from tests.test_case_learning import HAS_RETRIEVER, _Fixture, _case  # noqa: E402

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


def feedback(**overrides):
    data = {
        "run_ref": "DEV/runs/RUN-001",
        "validity": "VALID",
        "outcome": "INCREASE",
        "prediction_review": "DECLARED_PREDICTION_CONTRAST",
        "provenance": "PRE_RESULT_PROVENANCE_VERIFIED",
        "compatible": ["real-gain"],
        "contradicted": [],
        "evidence_refs": ["DEV/runs/RUN-001/metrics.json"],
    }
    data.update(overrides)
    return data


@unittest.skipUnless(HAS_RETRIEVER, "CASE_LIBRARY/scripts/search_cases.py not present")
class RunFeedbackNextActionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        case_learning._RESULT_CACHE.clear()
        case_learning._RETRIEVER_CACHE.clear()
        case_gates._GATE_CACHE.clear()
        cases = [_case("T-F1", "FAILURE", ["ORIGINAL_VERIFIED"],
                       ["GROUP_INDEPENDENCE", "DATA_LEAKAGE"]),
                 _case("T-V1", "FAILURE", ["ORIGINAL_VERIFIED"], ["EXTERNAL_VALIDATION"],
                       boundaries=["本卡结论只适用于 Epic Sepsis Model v1；不得泛化到 v2"],
                       counterexamples=["v2 多中心前瞻验证 AUROC 0.82–0.92"])]
        self.fx = _Fixture(Path(self.temp.name), cases)
        self.env = patch.dict(os.environ, {"PDRW_CASE_LIBRARY_ROOT": str(self.fx.root)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def run_gate(self, **overrides):
        case_learning._RESULT_CACHE.clear()
        case_gates._GATE_CACHE.clear()
        event = gate_event(task_profile=dict(PROFILE), h_stage="H7",
                           milestone="PROTOCOL_FREEZE")
        event.update(overrides)
        return self.fx.service.call("case_gate_check", event=event)["next_actions"]

    def first(self, **overrides):
        actions = self.run_gate(**overrides)
        return actions, actions["actions"][0]

    def test_valid_positive_keeps_champion_and_names_the_evidence_gap(self):
        actions, first = self.first(run_feedback=feedback())
        self.assertEqual(actions["situation"]["kind"], "SUPPORTS_DECLARED_HYPOTHESIS")
        self.assertEqual(first["action_type"], "KEEP_CHAMPION_AND_FILL_EVIDENCE_GAP")
        self.assertFalse(first["author_decision_required"])
        self.assertIn("独立组", first["minimal_validation"])
        self.assertTrue(first["open_questions"])

    def test_valid_negative_challenges_only_the_tested_premise(self):
        actions, first = self.first(run_feedback=feedback(
            outcome="NO_CHANGE", compatible=[], contradicted=["real-gain"]))
        self.assertEqual(actions["situation"]["kind"], "VALID_NEGATIVE_RESULT")
        self.assertEqual(first["action_type"], "REASSESS_FAILED_PREMISE_AND_ALTERNATIVES")
        self.assertFalse(actions["automatic_go_stop"])
        self.assertIn("不据此终止整个方向", first["recommendation"])

    def test_invalid_run_is_an_execution_question_not_a_negative_result(self):
        actions, first = self.first(run_feedback=feedback(
            validity="INVALID", outcome="UNKNOWN", prediction_review="",
            compatible=[], contradicted=[]))
        self.assertEqual(actions["situation"]["kind"], "EXECUTION_UNVERIFIED")
        self.assertEqual(first["action_type"], "LOCATE_EXECUTION_RECORD_BEFORE_INTERPRETING")
        self.assertEqual(first["independent_confirmation"], "NOT_A_SCIENTIFIC_PROOF")

    def test_not_run_and_inconclusive_do_not_become_failures(self):
        actions, first = self.first(run_feedback=feedback(
            validity="NOT_RUN", outcome="UNKNOWN", compatible=[], contradicted=[]))
        self.assertEqual(actions["situation"]["kind"], "RUN_NOT_EXECUTED")
        self.assertEqual(first["action_type"], "CONFIRM_BLOCKER_AND_RERUN_SAME_PROBE")

        actions, first = self.first(run_feedback=feedback(
            validity="INCONCLUSIVE", outcome="UNKNOWN",
            prediction_review="NO_VALID_SCIENTIFIC_INFERENCE"))
        self.assertEqual(actions["situation"]["kind"], "INCONCLUSIVE_MEASUREMENT")
        self.assertEqual(first["action_type"], "QUANTIFY_NOISE_BEFORE_MORE_DATA")

    def test_no_discriminating_contrast_asks_for_a_better_probe(self):
        actions, first = self.first(run_feedback=feedback(
            prediction_review="NO_DISCRIMINATING_CONTRAST",
            compatible=[], contradicted=[]))
        self.assertEqual(first["action_type"], "DESIGN_DISCRIMINATING_PROBE")
        self.assertIn("预测互不相同", first["minimal_validation"])

    def test_split_explanations_name_the_pairs_to_separate(self):
        actions, first = self.first(run_feedback=feedback(
            compatible=["real-gain"], contradicted=["leakage-explains-gain"]))
        self.assertEqual(actions["situation"]["kind"], "COMPETING_EXPLANATIONS_SPLIT")
        self.assertEqual(first["action_type"], "VERIFY_RUN_THEN_DESIGN_DIFFERENTIATING_PROBE")
        self.assertEqual(first["differentiates"], [["real-gain", "leakage-explains-gain"]])

    def test_decisions_record_their_basis_without_a_new_ledger(self):
        actions, first = self.first(run_feedback=feedback())
        basis = actions["decision_basis"]
        self.assertEqual(basis["evidence"]["run_ref"], "DEV/runs/RUN-001")
        self.assertEqual(basis["evidence"]["run_evidence_refs"],
                         ["DEV/runs/RUN-001/metrics.json"])
        self.assertIsNone(basis["selected"])
        self.assertEqual(basis["pre_decision_cases"], "NOT_VERIFIABLE_AT_GATE")
        self.assertEqual(basis["scope"]["h_stage"], "H7")

    def test_no_feedback_keeps_the_old_case_path(self):
        actions = self.run_gate()
        self.assertEqual(actions["situation"]["kind"], "NO_RUN_FEEDBACK_DECLARED")
        self.assertEqual(actions["actions"][0]["action_type"], "CONCRETE_CHECK")

    def test_invalid_declared_feedback_is_rejected(self):
        case_learning._RESULT_CACHE.clear()
        case_gates._GATE_CACHE.clear()
        event = gate_event(task_profile=dict(PROFILE), h_stage="H7",
                           milestone="PROTOCOL_FREEZE")
        event["run_feedback"] = feedback(validity="PROBABLY_FINE")
        result = self.fx.service.call("case_gate_check", event=event)
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["error_code"], "GATE_EVENT_INVALID")

    # -- WP9-B3: case risk is not an approval node -------------------------
    def test_resource_increase_alone_does_not_escalate_to_the_author(self):
        actions = self.run_gate(h_stage="H6", signals=["RESOURCE_INCREASE"])
        kinds = [a["action_type"] for a in actions["actions"]]
        self.assertNotIn("AUTHOR_STRATEGY_OPTION", kinds)
        self.assertTrue(actions["applicability_risk_noted"])
        self.assertFalse(any(x["author_decision_required"]
                             for x in actions["applicability_risk_noted"]))

    def test_claim_checkpoint_still_offers_the_author_option(self):
        case_learning._RESULT_CACHE.clear()
        case_gates._GATE_CACHE.clear()
        event = gate_event(task_profile=dict(PROFILE), h_stage="H8",
                           milestone="CLAIM_OR_CLOSURE",
                           signals=["CORE_MECHANISM_UNSUPPORTED"])
        actions = self.fx.service.call("case_gate_check", event=event)["next_actions"]
        author = [a for a in actions["actions"]
                  if a["action_type"] == "AUTHOR_STRATEGY_OPTION"]
        self.assertTrue(author)
        self.assertEqual(author[0]["strategy_scope_basis"], "CLAIM_CHECKPOINT_G3")
        self.assertTrue(author[0]["author_decision_required"])


class StrategyScopeTests(unittest.TestCase):
    def test_declared_scope_and_material_signals(self):
        scope = case_gates._strategy_scope_change
        self.assertEqual(scope({"strategy_scope": "main_claim"}, "G2", {}),
                         "DECLARED_MAIN_CLAIM")
        self.assertEqual(scope({"main_claim_changed": True}, "G2", {}),
                         "DECLARED_SCOPE_FLAG")
        self.assertEqual(scope({}, "T2", {"T2": ["DATA_SCOPE_CHANGE"]}),
                         "T2_MATERIAL_CHANGE_SIGNAL")
        self.assertIsNone(scope({}, "T2", {"T2": ["RESOURCE_INCREASE"]}))
        self.assertIsNone(scope({}, "G2", {}))


if __name__ == "__main__":
    unittest.main()
