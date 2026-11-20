"""SCIENCE-02: a legal non-experimental direction must stay reviewable.

PD-RW allows theory and simulation evidence paths. If the card schema can only
express an experimental truth and an experimental unit, those directions are
removed by a *form* check, which is exactly what the task forbids.
"""
import json
import unittest
from pathlib import Path

from pdrw_agent.schemas import AgentError
from pdrw_agent.science.candidate_review import review_candidate, review_candidates

ROOT = Path(__file__).resolve().parents[1]
CARDS_DIR = ROOT / "evals" / "science_value"


def load(name):
    return json.loads((CARDS_DIR / name).read_text(encoding="utf-8"))


def theory_card():
    return load("non_experimental_cards.json")["cards"][0]


def simulation_card():
    return load("non_experimental_cards.json")["cards"][1]


class NonExperimentalPathTests(unittest.TestCase):
    def test_a_theory_card_is_reviewable(self):
        result = review_candidate(theory_card())
        self.assertEqual(result["status"], "CANDIDATE_REVIEW_ADVISORY")
        self.assertNotIn("TRUTH_NOT_INDEPENDENT", result["flags"])
        self.assertNotIn("UNIT_NOT_INDEPENDENT", result["flags"])
        self.assertFalse(result["scientific_truth_verified"])

    def test_a_simulation_card_is_reviewable(self):
        result = review_candidate(simulation_card())
        self.assertNotIn("UNIT_NOT_INDEPENDENT", result["flags"])
        self.assertNotIn("UNIT_COUNT_CONFLATION", result["flags"])

    def test_an_unverified_neighbour_is_still_reported_for_a_theory(self):
        # Being representable is not being waved through: an ABSTRACT_ONLY
        # neighbour is still flagged, it simply is not treated as a rejection.
        self.assertIn("NEIGHBOR_UNVERIFIED", review_candidate(theory_card())["flags"])

    def test_the_unit_vocabulary_is_extended_not_opened(self):
        card = simulation_card()
        card["evaluation_unit"] = "PROOF"
        with self.assertRaises(AgentError) as ctx:
            review_candidate(card)
        self.assertEqual(ctx.exception.code, "CANDIDATE_CARD_INVALID")

    def test_a_proxy_truth_is_still_self_referential(self):
        card = simulation_card()
        card["truth_kind"] = "PROXY_FROM_INPUT"
        card["truth_independent_of_input"] = True
        self.assertIn("TRUTH_NOT_INDEPENDENT", review_candidate(card)["flags"])

    def test_both_paths_can_be_compared_in_one_bundle(self):
        result = review_candidates([theory_card(), simulation_card()])
        self.assertEqual(len(result["candidates"]), 2)
        self.assertEqual(result["cross_candidate"]["distinct_failure_premises"], 2)
        self.assertFalse(result["score_provided"])


class HoldoutTests(unittest.TestCase):
    """Labels come from the case library, not from the checker."""

    @classmethod
    def setUpClass(cls):
        cls.cards = load("holdout_cards.json")["cards"]
        cls.labels = load("holdout_expectations.json")["cases"]

    def test_each_documented_defect_is_surfaced(self):
        hits = []
        for card in self.cards:
            label = self.labels[card["candidate_id"]]
            if not label["primary"]:
                continue
            flags = set(review_candidate(card)["flags"])
            hits.append((card["candidate_id"], bool(flags & set(label["primary"]))))
        self.assertEqual(3, len(hits), "holdout labels are incomplete")
        for candidate_id, hit in hits:
            self.assertTrue(hit, f"{candidate_id} was not flagged")

    def test_historically_successful_directions_stay_clean(self):
        for card in self.cards:
            if self.labels[card["candidate_id"]]["primary"]:
                continue
            self.assertEqual([], review_candidate(card)["flags"], card["candidate_id"])


if __name__ == "__main__":
    unittest.main()
