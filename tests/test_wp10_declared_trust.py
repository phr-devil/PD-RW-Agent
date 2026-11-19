"""WP10: a public tool input can never authenticate itself.

These are adversarial tests. They reproduce the defect found after PR #19 —
`provenance=PRE_RESULT_PROVENANCE_VERIFIED` plus a caller-typed `link_status`
survived as "verified" credibility — and pin the honest behaviour that
replaces it: the gate reports what it did **not** check, and a declared
negative is not called a valid negative.

They are engineering contract tests, not evidence of scientific benefit.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pdrw_agent import case_gates, case_learning
from pdrw_agent.schemas import AgentError
from pdrw_agent.science import feedback_link
from pdrw_agent.science.feedback_link import to_run_feedback

from tests.test_case_gates import gate_event
from tests.test_case_learning import HAS_RETRIEVER, _Fixture, _case
from tests.test_science_feedback_link import _Project, _sha
from tests.test_wp9_next_action import PROFILE, feedback

VERIFIED = "PRE_RESULT_PROVENANCE_VERIFIED"
UNVERIFIED = "PRE_RESULT_RECORD_UNVERIFIED"
DIGEST = "a" * 64
EXECUTION = {"status": "NO_EXECUTION_EVIDENCE_DECLARED"}


def declared(**overrides):
    raw = {
        "run_ref": "DEV/runs/RUN-002",
        "validity": "VALID",
        "outcome": "INCREASE",
        "prediction_review": "DECLARED_PREDICTION_CONTRAST",
        "provenance": VERIFIED,
        "compatible": ["real-gain"],
        "contradicted": [],
        "evidence_refs": ["DEV/runs/RUN-002/metrics.json"],
    }
    raw.update(overrides)
    return case_gates._declared_run_feedback({"run_feedback": raw})


class ForgedCredentialTests(unittest.TestCase):
    """Every attack below used to be able to keep an "effective verified" label."""

    def test_typed_provenance_and_status_never_upgrade(self):
        for status in ("ADVISORY_FEEDBACK_ONLY", "NOT_COMPARABLE",
                       "PRE_RESULT_RECORD_UNVERIFIED", "UNKNOWN",
                       "RUN_EVIDENCE_UNVERIFIED", "RUN_STATUS_CONFLICT", ""):
            for digest in ("", DIGEST):
                with self.subTest(status=status, digest=bool(digest)):
                    feedback = declared(link_status=status,
                                        proposal_sha256=digest)
                    self.assertEqual(feedback["provenance_effective"], UNVERIFIED)
                    self.assertEqual(
                        feedback["provenance_basis"],
                        "DECLARED_INPUT_ONLY_GATE_PERFORMS_NO_BINDING")
                    self.assertTrue(feedback["declared_only"])
                    self.assertFalse(feedback["scientific_inference_verified"])

    def test_a_forged_binder_object_does_not_launder_through_the_projection(self):
        # A caller can fabricate a whole link result: the projection cannot tell
        # it from a real one, because it only reshapes a dict.
        forged = {
            "schema_version": feedback_link.LINK_SCHEMA,
            "status": "ADVISORY_FEEDBACK_ONLY",
            "provenance": {"pre_result_provenance": VERIFIED,
                           "prediction_comparison": "DECLARED_PREDICTION_COMPARED"},
            "observation_preserved": {"run_ref": "DEV/runs/RUN-002",
                                      "declared_validity": "VALID",
                                      "declared_outcome": "INCREASE",
                                      "evidence_refs": ["x"]},
            "feedback": {"compatible_predictions": ["real-gain"],
                         "contradicted_predictions": []},
            "prereg": {"proposal_sha256": DIGEST},
            "run": {"ref": "DEV/runs/RUN-002"},
        }
        projected = to_run_feedback(forged)
        self.assertEqual(projected["provenance"], VERIFIED)  # shape only
        feedback = case_gates._declared_run_feedback({"run_feedback": projected})
        self.assertEqual(feedback["provenance_effective"], UNVERIFIED)
        self.assertEqual(feedback["provenance_basis"],
                         "DECLARED_INPUT_ONLY_GATE_PERFORMS_NO_BINDING")

    def test_the_gate_lists_the_four_checks_it_did_not_perform(self):
        feedback = declared(link_status="ADVISORY_FEEDBACK_ONLY")
        self.assertEqual(set(feedback["checks_by_gate"]),
                         {"file_binding", "historical_order", "run_validity",
                          "scientific_truth"})
        self.assertEqual(set(feedback["checks_by_gate"].values()),
                         {"NOT_PERFORMED_BY_GATE"})

    def test_an_unknown_status_or_a_non_digest_still_fails_closed(self):
        with self.assertRaises(AgentError):
            declared(link_status="TRUSTED_BY_BINDER")
        with self.assertRaises(AgentError):
            declared(proposal_sha256="verified")


class DeclaredResultNamingTests(unittest.TestCase):
    def test_positive_stays_scoped_to_the_declared_hypothesis(self):
        situation = case_gates._run_situation(declared(), EXECUTION)
        self.assertEqual(situation, "SUPPORTS_DECLARED_HYPOTHESIS")

    def test_negative_is_not_promoted_to_a_valid_negative(self):
        feedback = declared(outcome="NO_CHANGE", compatible=[],
                            contradicted=["real-gain"])
        situation = case_gates._run_situation(feedback, EXECUTION)
        self.assertEqual(situation, "DECLARED_NEGATIVE_RESULT_UNVERIFIED")
        action = case_gates._situation_action(situation, feedback, EXECUTION)
        self.assertEqual(action["action_type"],
                         "REASSESS_FAILED_PREMISE_AND_ALTERNATIVES")
        # The advice is kept; only the claim is withdrawn.
        self.assertFalse(action["author_decision_required"])
        self.assertFalse(action["automatic_go_stop"])
        self.assertIn("未核验", action["recommendation"])
        self.assertIn("先由 Run 记录", action["minimal_validation"])

    def test_no_declared_combination_can_produce_a_valid_negative(self):
        for validity in ("VALID", "INVALID", "INCONCLUSIVE", "NOT_RUN"):
            for review in ("DECLARED_PREDICTION_CONTRAST", "",
                           "NO_DISCRIMINATING_CONTRAST",
                           "NO_VALID_SCIENTIFIC_INFERENCE"):
                for compatible, contradicted in (([], ["x"]), (["x"], []),
                                                 (["x"], ["y"]), ([], [])):
                    with self.subTest(validity=validity, review=review,
                                      compatible=compatible,
                                      contradicted=contradicted):
                        feedback = declared(validity=validity,
                                            prediction_review=review,
                                            compatible=compatible,
                                            contradicted=contradicted)
                        situation = case_gates._run_situation(feedback, EXECUTION)
                        self.assertNotEqual(situation, "VALID_NEGATIVE_RESULT")
                        self.assertIn(situation, case_gates._SITUATION_TEXT)

    def test_a_record_problem_outranks_any_result_reading(self):
        expected = {
            "RUN_STATUS_CONFLICT": "RUN_RECORD_CONFLICT",
            "RUN_EVIDENCE_UNVERIFIED": "RUN_EVIDENCE_MISSING",
            "NOT_COMPARABLE": "MEASUREMENT_AXES_CHANGED",
        }
        for status, situation in expected.items():
            with self.subTest(status=status):
                feedback = declared(link_status=status,
                                    contradicted=["real-gain"])
                self.assertEqual(case_gates._run_situation(feedback, EXECUTION),
                                 situation)
                action = case_gates._situation_action(situation, feedback, EXECUTION)
                self.assertNotIn(action["action_type"],
                                 {"REASSESS_FAILED_PREMISE_AND_ALTERNATIVES",
                                  "KEEP_CHAMPION_AND_FILL_EVIDENCE_GAP"})
                self.assertFalse(action["author_decision_required"])

    def test_the_situation_block_declares_its_scope(self):
        cl = {"cases": {"results": [], "source_verification": {"index_sha256": "f" * 64}},
              "case_review": {"comparisons": []},
              "decision_experiences": {"experiences": []}}
        advisory = {"case_admissibility": {}, "conditions_differ_not_transferred": [],
                    "unknown_reasons": [], "evidence_tiers": {}, "experiences": [],
                    "compact_cases": []}
        result = case_gates.build_next_actions(
            "G2", {"query": "q", "task_id": "T", "h_stage": "H7",
                   "milestone": "PROTOCOL_FREEZE"}, cl, advisory, EXECUTION,
            run_feedback=declared(link_status="ADVISORY_FEEDBACK_ONLY"))
        situation = result["situation"]
        self.assertEqual(situation["kind_scope"], "DECLARED_ONLY")
        self.assertEqual(situation["verification"], "NOT_VERIFIABLE_AT_GATE")
        self.assertFalse(situation["prediction_verification_performed"])
        self.assertTrue(situation["run_feedback_declared_only"])
        self.assertNotIn("prediction_verification_reported_by_binder", situation)
        self.assertTrue(result["not_a_scientific_conclusion"])
        self.assertFalse(result["automatic_go_stop"])


class RealBinderSeparationTests(unittest.TestCase):
    """The binder really reads files, so it may report what it checked."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = _Project(Path(self.temp.name))
        self.result = feedback_link.review_linked_feedback(
            self.project.link(), project_root=self.project.root)

    def test_the_binder_states_each_axis_separately(self):
        axes = self.result["verification_axes"]
        self.assertEqual(axes["file_binding"], "CHECKED_FILES_AND_DECLARED_DIGESTS")
        self.assertEqual(axes["historical_order"],
                         "DECLARED_TIMESTAMPS_ONLY_NOT_INDEPENDENTLY_VERIFIED")
        self.assertEqual(axes["run_validity"], "RUN_RECORD_READ_NO_EVIDENCE_PROBLEM")
        self.assertEqual(axes["scientific_truth"], "NOT_ASSESSED_BY_TOOL")

    def test_the_binder_never_claims_order_run_truth_or_permission(self):
        self.assertFalse(self.result["historical_order_verified"])
        self.assertFalse(self.result["original_run_verified"])
        self.assertFalse(self.result["scientific_inference_verified"])
        self.assertFalse(self.result["permission_to_execute"])
        self.assertTrue(all(self.result["provenance"]["checks"].values()))

    def test_a_post_run_retrieval_is_never_reported_as_pre_decision(self):
        self.assertEqual(self.result["case_timing"]["pre_decision_case_ids"], [])
        self.assertIn(self.result["case_timing"]["case_influence_verified"],
                      {"NOT_CLAIMED", "UNKNOWN_NO_RECEIPT"})


class V114BoundaryTests(unittest.TestCase):
    """v1.14 keeps in-scope algorithm work autonomous; only scope changes reopen."""

    def test_an_algorithm_swap_alone_does_not_reopen_the_author_decision(self):
        scope = case_gates._strategy_scope_change
        self.assertIsNone(scope({}, "T2", {"T2": ["CORE_ALGORITHM_CHANGE"]}))
        self.assertIsNone(scope({}, "T2", {"T2": ["CORE_ALGORITHM_CHANGE",
                                                  "RESOURCE_INCREASE"]}))

    def test_legal_scope_and_question_changes_still_do(self):
        scope = case_gates._strategy_scope_change
        self.assertEqual(scope({}, "T2", {"T2": ["DATA_SCOPE_CHANGE"]}),
                         "T2_MATERIAL_CHANGE_SIGNAL")
        self.assertEqual(scope({}, "T2", {"T2": ["SCIENTIFIC_QUESTION_CHANGE"]}),
                         "T2_MATERIAL_CHANGE_SIGNAL")
        self.assertEqual(scope({"strategy_scope": "main_claim"}, "G2", {}),
                         "DECLARED_MAIN_CLAIM")

    def test_the_author_option_names_the_upstream_question_node(self):
        cl = {"cases": {"results": [], "source_verification": {"index_sha256": "f" * 64}},
              "case_review": {"comparisons": []},
              "decision_experiences": {"experiences": []}}
        advisory = {"case_admissibility": {}, "conditions_differ_not_transferred": [],
                    "unknown_reasons": [], "evidence_tiers": {}, "experiences": [],
                    "compact_cases": []}
        event = {"query": "q", "task_id": "T", "h_stage": "H8",
                 "milestone": "CLAIM_OR_CLOSURE", "strategy_scope": "SCIENTIFIC_QUESTION"}
        # No cases at all: the option is driven by the declaration, not retrieval.
        result = case_gates.build_next_actions(
            "G3", event, cl, advisory, EXECUTION)
        self.assertIsNone(result["decision_basis"]["selected"])


class SealedBoundaryUnchangedTests(unittest.TestCase):
    def test_a_sealed_path_is_still_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            project = _Project(Path(temp))
            link = project.link()
            link["run"]["observation"]["evidence_refs"] = ["SEALED/answers.json"]
            with self.assertRaises(AgentError) as ctx:
                feedback_link.review_linked_feedback(
                    link, project_root=project.root)
            self.assertIn("SEALED", str(ctx.exception).upper())


class GateCacheKeyTests(unittest.TestCase):
    """A cached checkpoint must not answer for a different judged Run."""

    def test_the_fingerprint_includes_the_judged_run(self):
        kwargs = {"trigger": "G2", "index_sha256": "f" * 64}
        base = {"task_id": "T", "decision": "d", "protocol": "p"}
        first, _ = case_gates.gate_fingerprint(
            {**base, "run_feedback": {"validity": "VALID"}}, **kwargs)
        second, _ = case_gates.gate_fingerprint(
            {**base, "run_feedback": {"validity": "INVALID"}}, **kwargs)
        third, _ = case_gates.gate_fingerprint(base, **kwargs)
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, third)
        self.assertNotEqual(second, third)

    def test_caller_field_order_does_not_create_a_new_key(self):
        kwargs = {"trigger": "G2", "index_sha256": "f" * 64}
        a, _ = case_gates.gate_fingerprint(
            {"task_id": "T", "run_feedback": {"validity": "VALID", "outcome": "INCREASE"}},
            **kwargs)
        b, _ = case_gates.gate_fingerprint(
            {"run_feedback": {"outcome": "INCREASE", "validity": "VALID"}, "task_id": "T"},
            **kwargs)
        self.assertEqual(a, b)


@unittest.skipUnless(HAS_RETRIEVER, "CASE_LIBRARY/scripts/search_cases.py not present")
class GateCacheBehaviourTests(unittest.TestCase):
    def setUp(self):
        import os
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        case_learning._RESULT_CACHE.clear()
        case_gates._GATE_CACHE.clear()
        cases = [_case("T-F1", "FAILURE", ["ORIGINAL_VERIFIED"],
                       ["GROUP_INDEPENDENCE", "DATA_LEAKAGE"])]
        self.fx = _Fixture(Path(self.temp.name), cases)
        self.env = patch.dict(os.environ,
                              {"PDRW_CASE_LIBRARY_ROOT": str(self.fx.root)})
        self.env.start()
        self.addCleanup(self.env.stop)

    def call(self, judged):
        event = gate_event(task_profile=dict(PROFILE), h_stage="H7",
                           milestone="PROTOCOL_FREEZE")
        event["run_feedback"] = judged
        return self.fx.service.call("case_gate_check", event=event)

    def test_a_changed_run_replaces_the_cached_next_action(self):
        first = self.call(feedback())
        second = self.call(feedback(
            validity="INVALID", outcome="UNKNOWN", prediction_review="",
            compatible=[], contradicted=[]))
        self.assertEqual(first["next_actions"]["situation"]["kind"],
                         "SUPPORTS_DECLARED_HYPOTHESIS")
        self.assertEqual(second["next_actions"]["situation"]["kind"],
                         "EXECUTION_UNVERIFIED")
        self.assertFalse(second["cache_hit"])


if __name__ == "__main__":
    unittest.main()
