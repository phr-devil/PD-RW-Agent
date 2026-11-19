"""Synthetic scientific-autonomy regression tests (not scientific evidence)."""
import unittest

from pdrw_agent.science.lessons import compile_declared_lessons
from pdrw_agent.science.decision import assess_proposal
from pdrw_agent.schemas import AgentError


def observations():
    return {"observations": [
        {"run_id": "not-run", "outcome": "NOT_RUN", "evidence_refs": ["missing-data-log"]},
        {"run_id": "invalid", "outcome": "INVALID_EXPERIMENT",
         "evidence_refs": ["split-diagnostics"]},
        {"run_id": "inconclusive", "outcome": "INCONCLUSIVE",
         "evidence_refs": ["weak-pilot"]},
        {"run_id": "positive", "outcome": "VALID_POSITIVE",
         "tested_premise_id": "old-method-improves-stability",
         "scope": {"dataset": "dev-synthetic", "unit": "independent-participant"},
         "evidence_refs": ["group-run-p"]},
        {"run_id": "negative", "outcome": "VALID_NEGATIVE",
         "tested_premise_id": "new-net-beats-baseline",
         "scope": {"dataset": "dev-synthetic", "unit": "independent-participant"},
         "evidence_refs": ["group-run-n"]},
    ]}


def scientific_packet(positive_lessons):
    return {
        "question": "Is an ordinary-method improvement reproducible in this scope?",
        "claim_type": "CAPABILITY",
        "proposed_premise": {
            "premise_id": "old-method-improves-stability",
            "scope": {"dataset": "dev-synthetic", "unit": "independent-participant"},
        },
        "hypotheses": ["real-benefit", "measurement-artifact"],
        "probes": [{
            "id": "paired-group-control", "observable": "group-effect",
            "evaluation_unit": "independent-participant",
            "comparison_reference": "matched-baseline",
            "predictions": {"real-benefit": "INCREASE",
                            "measurement-artifact": "NO_CHANGE"},
            "cost_band": "LOW",
        }],
        "prior_positive_lessons": positive_lessons,
    }


class ScientificAutonomyRegressionTests(unittest.TestCase):
    def test_not_run_invalid_inconclusive_are_not_negative(self):
        out = compile_declared_lessons(observations())
        self.assertEqual([x["run_id"] for x in out["items"][:3]],
                         ["not-run", "invalid", "inconclusive"])
        self.assertTrue(all(x["negative_scientific_evidence"] is False
                            for x in out["items"][:3]))
        self.assertEqual(out["items"][0]["next"], "NOT_RUN_IS_NOT_SCIENTIFIC_EVIDENCE")
        self.assertEqual(len(out["candidate_prior_negative_lessons"]), 1)
        self.assertEqual(len(out["candidate_prior_positive_lessons"]), 1)
        self.assertFalse(out["automatic_project_stop"])

    def test_positive_is_scoped_and_does_not_authorize_go(self):
        pos = compile_declared_lessons(observations())["candidate_prior_positive_lessons"]
        result = assess_proposal(scientific_packet(pos))
        self.assertEqual(
            result["positive_premise_candidates"][0]["status"],
            "DECLARED_SAME_PREMISE_SCOPE_POSITIVE_CANDIDATE")
        self.assertFalse(result["positive_premise_candidates"][0]["scientific_equivalence_verified"])
        self.assertFalse(result["positive_premise_candidates"][0]["automatic_go"])
        self.assertFalse(result["automatic_go"])
        self.assertFalse(result["automatic_stop"])
        self.assertEqual(result["original_user_authorization"], "UNVERIFIED")

    def test_positive_different_group_is_not_automatically_transferred(self):
        pos = compile_declared_lessons(observations())["candidate_prior_positive_lessons"]
        pkt = scientific_packet(pos)
        pkt["proposed_premise"]["scope"]["unit"] = "new-independent-device"
        result = assess_proposal(pkt)
        self.assertEqual(result["positive_premise_candidates"][0]["status"],
                         "SCOPE_DIFFERS_REVIEW")
        self.assertFalse(result["automatic_go"])

    def test_unscoped_positive_kept_descriptive_not_transferred(self):
        obs = {"observations": [{
            "run_id": "positive-without-scope", "outcome": "VALID_POSITIVE",
            "evidence_refs": ["original-dev-run"]}]}
        out = compile_declared_lessons(obs)
        self.assertEqual(out["candidate_prior_positive_lessons"], [])
        self.assertEqual(out["items"][0]["next"], "POSITIVE_SCOPE_REQUIRED_FOR_TRANSFER")
        self.assertFalse(out["items"][0]["positive_scientific_evidence"])

    def test_invalid_declared_positive_does_not_count_as_success(self):
        pkt = scientific_packet([{
            "premise_id": "old-method-improves-stability",
            "scope": {"dataset": "dev-synthetic", "unit": "independent-participant"},
            "validity": "INVALID", "evidence_refs": ["source"],
        }])
        r = assess_proposal(pkt)
        self.assertEqual(r["positive_premise_candidates"][0]["status"],
                         "POSITIVE_EVIDENCE_INSUFFICIENT")
        self.assertFalse(r["automatic_go"])

    def test_no_evidence_ref_cannot_be_a_sourced_lesson(self):
        bad = {"observations": [{"run_id": "missing-source",
                                "outcome": "VALID_POSITIVE", "evidence_refs": []}]}
        with self.assertRaises(AgentError):
            compile_declared_lessons(bad)

    def test_old_negative_only_packets_remain_compatible(self):
        result = assess_proposal(scientific_packet([]))
        self.assertEqual(result["positive_premise_candidates"], [])
        self.assertEqual(result["status"], "ADVISORY_REVIEW_ONLY")


if __name__ == "__main__":
    unittest.main()
