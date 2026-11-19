"""Synthetic checks for declared scientific probe/cost hints, not research gains."""
import unittest

from pdrw_agent.science.decision import assess_proposal
from pdrw_agent.science.probe_frontier import summarize_declared_probe_frontier


def probe(name, pairs, cost):
    return {
        "id": name,
        "distinguishable_hypothesis_pairs_as_declared": pairs,
        "declared_cost_band": cost,
    }


class ProbeFrontierTests(unittest.TestCase):
    def test_cost_and_exact_pair_coverage(self):
        report = summarize_declared_probe_frontier([
            probe("cheap", [["a", "b"], ["a", "c"]], "LOW"),
            probe("expensive", [["a", "b"]], "HIGH"),
            probe("different", [["b", "c"]], "MEDIUM"),
        ])
        self.assertEqual(report["frontier_candidate_ids_as_declared"],
                         ["cheap", "different"])
        self.assertEqual(report["dominated_candidates_as_declared"],
                         [{"id": "expensive", "dominated_by": ["cheap"]}])
        self.assertFalse(report["automatically_selected"])
        self.assertFalse(report["scientifically_ranked"])
        self.assertFalse(report["source_predictions_verified"])

    def test_unknown_cost_not_dominated(self):
        report = summarize_declared_probe_frontier([
            probe("known", [["a", "b"]], "LOW"),
            probe("unknown", [], "UNKNOWN"),
        ])
        self.assertEqual(report["unknown_cost_ids"], ["unknown"])
        self.assertEqual(report["frontier_candidate_ids_as_declared"], ["known"])
        self.assertEqual(report["dominated_candidates_as_declared"], [])

    def test_equal_cost_and_coverage_remain_on_frontier(self):
        report = summarize_declared_probe_frontier([
            probe("a", [["a", "b"]], "LOW"),
            probe("b", [["a", "b"]], "LOW"),
        ])
        self.assertEqual(report["frontier_candidate_ids_as_declared"], ["a", "b"])

    def test_distinct_pairs_not_mistaken_for_subset(self):
        report = summarize_declared_probe_frontier([
            probe("a", [["a", "b"], ["a", "c"]], "LOW"),
            probe("b", [["b", "c"]], "HIGH"),
        ])
        self.assertEqual(report["frontier_candidate_ids_as_declared"], ["a", "b"])

    def test_assessment_includes_advisory_frontier_and_preserves_safety(self):
        packet = {
            "question": "Does a new lawful signal explain the residual?",
            "claim_type": "MECHANISM",
            "proposed_premise": {
                "premise_id": "lawful-signal",
                "scope": {"dataset": "synthetic-development"},
            },
            "hypotheses": ["mechanism", "shortcut", "null"],
            "probes": [
                {"id": "cheap-control", "observable": "group error",
                 "evaluation_unit": "subject",
                 "comparison_reference": "simple-model",
                 "predictions": {"mechanism": "INCREASE",
                                 "shortcut": "DECREASE", "null": "NO_CHANGE"},
                 "cost_band": "LOW"},
                {"id": "expensive-repeat", "observable": "group error",
                 "evaluation_unit": "subject",
                 "comparison_reference": "simple-model",
                 "predictions": {"mechanism": "INCREASE",
                                 "shortcut": "DECREASE", "null": "NO_CHANGE"},
                 "cost_band": "HIGH"},
            ],
        }
        result = assess_proposal(packet)
        frontier = result["declared_probe_efficiency"]
        self.assertEqual(frontier["frontier_candidate_ids_as_declared"], ["cheap-control"])
        self.assertEqual(frontier["dominated_candidates_as_declared"],
                         [{"id": "expensive-repeat", "dominated_by": ["cheap-control"]}])
        self.assertEqual(result["status"], "ADVISORY_REVIEW_ONLY")
        self.assertEqual(result["original_user_authorization"], "UNVERIFIED")
        self.assertFalse(result["automatic_stop"])
        self.assertFalse(frontier["automatically_selected"])


if __name__ == "__main__":
    unittest.main()
