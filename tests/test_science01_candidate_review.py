"""SCIENCE-01: a candidate card must state the relations value depends on.

These tests reproduce four defect types documented by the case library
(CASE-10/11/14/21) on frozen cards reconstructed from those cases, and pin
that two historically successful directions raise nothing. They are
engineering contract tests: they do not show that a model would write a better
question, and they do not score science.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from pdrw_agent.schemas import AgentError
from pdrw_agent.science.candidate_review import review_candidate, review_candidates

ROOT = Path(__file__).resolve().parents[1]
CARDS = json.loads((ROOT / "evals" / "science_value" / "cards.json").read_text("utf-8"))["cards"]
EXPECTED = json.loads(
    (ROOT / "evals" / "science_value" / "expectations.json").read_text("utf-8"))["cases"]


def card(candidate_id: str) -> dict:
    return json.loads(json.dumps(next(c for c in CARDS if c["candidate_id"] == candidate_id)))


class HistoricalDefectTests(unittest.TestCase):
    def test_each_documented_defect_is_localised(self):
        for item in CARDS:
            with self.subTest(card=item["candidate_id"]):
                result = review_candidate(item)
                want = set(EXPECTED[item["candidate_id"]]["expected_flags"])
                self.assertTrue(want.issubset(set(result["flags"])), result["flags"])

    def test_replication_reframe_is_not_new_knowledge(self):
        result = review_candidate(card("SC-01-REDUNDANCY-BOUND"))
        self.assertIn("REPLICATION_ONLY", result["flags"])
        self.assertEqual("DECLARED_CONFLICT", result["checks"]["knowledge_gain"])

    def test_proxy_truth_that_declares_independence_is_a_conflict(self):
        result = review_candidate(card("SC-02-MU-FROM-SLIDE"))
        self.assertIn("TRUTH_NOT_INDEPENDENT", result["flags"])
        self.assertEqual("DECLARED_CONFLICT", result["checks"]["truth_provenance"])

    def test_rows_are_not_independent_units(self):
        for cid in ("SC-02-MU-FROM-SLIDE", "SC-03-FRAME-POWER"):
            with self.subTest(card=cid):
                result = review_candidate(card(cid))
                self.assertIn("UNIT_NOT_INDEPENDENT", result["flags"])
                self.assertIn("UNIT_COUNT_CONFLATION", result["flags"])

    def test_novelty_from_a_search_miss_is_rejected(self):
        for cid in ("SC-01-REDUNDANCY-BOUND", "SC-04-FIRST-MU"):
            with self.subTest(card=cid):
                self.assertIn("NOVELTY_FROM_ABSENCE", review_candidate(card(cid))["flags"])

    def test_two_explanations_with_one_predictions_are_not_discriminating(self):
        result = review_candidate(card("SC-01-REDUNDANCY-BOUND"))
        self.assertIn("NON_DISCRIMINATING", result["flags"])
        self.assertEqual("DECLARED_CONFLICT", result["checks"]["discrimination"])

    def test_a_missing_prediction_is_named_as_such(self):
        item = card("SC-05-K1-CALIBRATION")
        item["competing_explanations"][0]["predicted_observation"] = ""
        result = review_candidate(item)
        self.assertIn("PREDICTION_NOT_STATED", result["flags"])
        self.assertNotIn("FALSIFIER_NOT_STATED", result["flags"])

    def test_reusing_the_evaluation_set_as_confirmation_is_circular(self):
        self.assertIn("CONFIRMATION_CIRCULAR",
                      review_candidate(card("SC-01-REDUNDANCY-BOUND"))["flags"])


class CleanDirectionTests(unittest.TestCase):
    def test_successful_directions_raise_no_finding(self):
        for cid in ("SC-05-K1-CALIBRATION", "SC-06-SIMPLE-BASELINE"):
            with self.subTest(card=cid):
                result = review_candidate(card(cid))
                self.assertEqual([], result["flags"])
                self.assertEqual([], result["blocking_unknowns"])
                self.assertEqual([], result["findings"])
                self.assertIn("NONE_IDENTIFIED", result["next_cheapest_check"])

    def test_a_metric_only_gain_without_consequence_is_flagged(self):
        item = card("SC-05-K1-CALIBRATION")
        item["success_new_knowledge"] = "跨条件宏观 F1 提升 3 个百分点"
        self.assertIn("KNOWLEDGE_GAIN_IS_METRIC_ONLY", review_candidate(item)["flags"])

    def test_a_stated_consequence_clears_the_metric_flag(self):
        item = card("SC-05-K1-CALIBRATION")
        item["success_new_knowledge"] = "跨条件 F1 提升 3 个百分点，并给出失效边界"
        self.assertNotIn("KNOWLEDGE_GAIN_IS_METRIC_ONLY", review_candidate(item)["flags"])

    def test_small_repeated_unit_counts_are_not_called_conflation(self):
        item = card("SC-06-SIMPLE-BASELINE")
        item["evaluation_unit"] = "WINDOW"
        item["independent_units"] = 40
        item["reported_n"] = 60
        result = review_candidate(item)
        self.assertIn("UNIT_NOT_INDEPENDENT", result["flags"])
        self.assertNotIn("UNIT_COUNT_CONFLATION", result["flags"])


class OutputContractTests(unittest.TestCase):
    def test_review_is_advisory_and_scores_nothing(self):
        result = review_candidates(CARDS)
        self.assertEqual("CANDIDATE_REVIEW_ADVISORY", result["status"])
        self.assertFalse(result["score_provided"])
        self.assertFalse(result["scientific_truth_verified"])
        self.assertFalse(result["automatic_go"])
        self.assertFalse(result["automatic_stop"])
        self.assertFalse(result["model_invoked"])
        self.assertEqual("PD-RW_WORKFLOW_AND_AUTHOR_ONLY", result["decision_authority"])
        for item in result["candidates"]:
            self.assertFalse(item["scientific_truth_verified"])
            self.assertNotIn("recommended_option", item)
            self.assertNotIn("approval", item)

    def test_a_rewording_does_not_create_a_second_failure_premise(self):
        a, b = card("SC-05-K1-CALIBRATION"), card("SC-06-SIMPLE-BASELINE")
        b["failure_premise"] = f'  {a["failure_premise"]}  '
        result = review_candidates([a, b])
        self.assertEqual([[a["candidate_id"], b["candidate_id"]]],
                         result["cross_candidate"]["shared_failure_premise"])
        self.assertEqual(1, result["cross_candidate"]["distinct_failure_premises"])

    def test_distinct_premises_are_reported_as_a_real_comparison(self):
        result = review_candidates(CARDS)
        self.assertEqual([], result["cross_candidate"]["shared_failure_premise"])
        self.assertEqual(6, result["cross_candidate"]["distinct_failure_premises"])

    def test_unknowns_are_questions_with_a_cheapest_check(self):
        result = review_candidate(card("SC-01-REDUNDANCY-BOUND"))
        self.assertTrue(result["blocking_unknowns"])
        for unknown in result["blocking_unknowns"]:
            self.assertTrue(unknown["question"].endswith("?"))
            self.assertTrue(unknown["cheapest_check"].strip())
        self.assertEqual("nearest_prior", result["blocking_unknowns"][0]["unknown_id"].split(":")[1])


class SchemaTests(unittest.TestCase):
    def test_unexpected_field_is_rejected(self):
        item = card("SC-06-SIMPLE-BASELINE")
        item["expected_flags"] = []
        with self.assertRaises(AgentError):
            review_candidate(item)

    def test_unknown_unit_and_truth_kind_are_rejected(self):
        for field, value in (("evaluation_unit", "PATIENT"), ("truth_kind", "GROUND_TRUTH")):
            with self.subTest(field=field):
                item = card("SC-06-SIMPLE-BASELINE")
                item[field] = value
                with self.assertRaises(AgentError):
                    review_candidate(item)

    def test_bounded_card_count_and_unique_ids(self):
        with self.assertRaises(AgentError):
            review_candidates([])
        with self.assertRaises(AgentError):
            review_candidates([card("SC-05-K1-CALIBRATION")] * 7)
        with self.assertRaises(AgentError):
            review_candidates([card("SC-05-K1-CALIBRATION"), card("SC-05-K1-CALIBRATION")])

    def test_confounders_need_a_list_or_an_explicit_statement(self):
        item = card("SC-06-SIMPLE-BASELINE")
        item["confounders"] = []
        self.assertIn("CONFOUNDERS_NOT_STATED", review_candidate(item)["flags"])
        item["confounders"] = "NONE_AFTER_CHECK"
        self.assertNotIn("CONFOUNDERS_NOT_STATED", review_candidate(item)["flags"])

    def test_test_time_truth_is_an_illegal_input(self):
        item = card("SC-06-SIMPLE-BASELINE")
        item["prediction_time_inputs"] = "推理时窗口 + 测试集真值"
        self.assertIn("ILLEGAL_PREDICTION_INPUT", review_candidate(item)["flags"])


class CliTests(unittest.TestCase):
    def test_cli_reviews_a_bundle_and_never_signals_approval(self):
        proc = subprocess.run(
            [sys.executable, "-m", "pdrw_agent.science.cli", "candidate-review",
             "--cards", str(ROOT / "evals" / "science_value" / "cards.json")],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        )
        self.assertEqual(3, proc.returncode, proc.stderr)
        result = json.loads(proc.stdout)
        self.assertEqual(6, len(result["candidates"]))
        self.assertFalse(result["automatic_go"])

    def test_cli_rejects_a_bundle_without_cards(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"not_cards": []}', encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-m", "pdrw_agent.science.cli", "candidate-review",
                 "--cards", str(path)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            )
            self.assertEqual(2, proc.returncode)
            self.assertEqual("CANDIDATE_CARD_INVALID", json.loads(proc.stdout)["error_code"])


class RevisionLoopTests(unittest.TestCase):
    """Answering the questions must change the design, not the wording."""

    def test_answering_the_questions_clears_the_findings(self):
        original = review_candidate(card("SC-01-REDUNDANCY-BOUND"))
        revised = review_candidate(json.loads(
            (ROOT / "evals" / "science_value" / "revision_example.json").read_text("utf-8")))
        self.assertTrue(original["flags"])
        self.assertEqual([], revised["flags"])
        self.assertEqual("DECLARED", revised["checks"]["discrimination"])
        # Clearing a finding is not a scientific verdict.
        self.assertFalse(revised["scientific_truth_verified"])

    def test_the_revision_differs_in_the_relations_not_only_the_phrasing(self):
        original = card("SC-01-REDUNDANCY-BOUND")
        revised = json.loads(
            (ROOT / "evals" / "science_value" / "revision_example.json").read_text("utf-8"))
        self.assertEqual(2, len(revised["named_nearest"]))
        self.assertEqual("ACCESSED", revised["nearest_status"])
        before = [x["predicted_observation"] for x in original["competing_explanations"]]
        after = [x["predicted_observation"] for x in revised["competing_explanations"]]
        self.assertEqual(1, len(set(before)))
        self.assertEqual(2, len(set(after)))
        self.assertFalse(revised["confirmation_shares_evaluation_data"])


if __name__ == "__main__":
    unittest.main()
