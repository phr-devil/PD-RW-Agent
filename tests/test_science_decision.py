"""Qualitative research advice; synthetic cases, not evidence of scientific gains."""
import copy
import unittest
from pdrw_agent.science.decision import assess_proposal
from pdrw_agent.schemas import AgentError


def proposal():
    return {
        "question": "Does the claimed mechanism survive a group-level control?",
        "claim_type": "MECHANISM",
        "claim_evidence_refs": [],
        "proposed_premise": {
            "premise_id": "signal-causal-association",
            "scope": {"dataset": "synthetic-dev", "split": "group-held-out"},
        },
        "hypotheses": ["causal", "confounded", "no-effect"],
        "probes": [
            {
                "id": "negative-control",
                "observable": "subject-level DEV signed effect",
                "evaluation_unit": "held-out-subject",
                "comparison_reference": "fixed-simple-baseline",
                "predictions": {
                    "causal": "DECREASE",
                    "confounded": "INCREASE",
                    "no-effect": "NO_CHANGE",
                },
                "cost_band": "LOW",
                "prediction_evidence_refs": ["synthetic-protocol-p1"],
            },
            {
                "id": "metric-only",
                "observable": "subject-level DEV signed effect",
                "evaluation_unit": "held-out-subject",
                "comparison_reference": "fixed-simple-baseline",
                "predictions": {
                    "causal": "INCREASE",
                    "confounded": "INCREASE",
                    "no-effect": "UNKNOWN",
                },
                "cost_band": "HIGH",
            },
        ],
        "prechecks": {"group_independence": {"status": "PASS", "evidence_refs": []}},
        "prior_negative_lessons": [{
            "premise_id": "signal-causal-association",
            "scope": {"dataset": "synthetic-dev", "split": "group-held-out"},
            "validity": "VALID_NEGATIVE", "evidence_refs": ["synthetic-run-a"],
        }],
    }


class ScienceDecisionTests(unittest.TestCase):
    def test_discriminability_is_descriptive_not_automatic_rank(self):
        result = assess_proposal(proposal())
        self.assertEqual(result["status"], "ADVISORY_REVIEW_ONLY")
        self.assertEqual(result["claim_type"], "MECHANISM/CAUSAL")
        self.assertEqual(result["probe_comparisons"][0]["observable"],
                         "subject-level DEV signed effect")
        self.assertEqual(result["probe_comparisons"][0]["pair_count"], 3)
        self.assertEqual(result["probe_comparisons"][1]["pair_count"], 0)
        self.assertFalse(result["probe_comparisons"][0]["prediction_source_verified"])
        self.assertFalse(result["automatic_stop"])
        self.assertEqual(result["original_user_authorization"], "UNVERIFIED")

    def test_same_failed_premise_is_only_candidate(self):
        r = assess_proposal(proposal())
        x = r["premise_candidates"][0]
        self.assertEqual(x["status"], "DECLARED_SAME_PREMISE_SCOPE_CANDIDATE")
        self.assertFalse(x["scientific_equivalence_verified"])
        self.assertFalse(x["automatic_stop"])

    def test_changed_scope_does_not_false_block(self):
        p = proposal()
        p["proposed_premise"]["scope"]["split"] = "different-group"
        r = assess_proposal(p)
        self.assertEqual(r["premise_candidates"][0]["status"], "SCOPE_DIFFERS_REVIEW")
        self.assertFalse(r["automatic_stop"])

    def test_invalid_past_run_not_negative_evidence(self):
        p = proposal()
        p["prior_negative_lessons"][0]["validity"] = "INVALID"
        r = assess_proposal(p)
        self.assertEqual(r["premise_candidates"][0]["status"], "NEGATIVE_EVIDENCE_INSUFFICIENT")

    def test_no_source_for_pass_is_not_verified(self):
        r = assess_proposal(proposal())
        self.assertEqual(r["prechecks"]["group_independence"]["review"], "SOURCE_REQUIRED")
        self.assertFalse(r["prechecks"]["group_independence"]["independently_verified"])
        self.assertEqual(r["prechecks"]["label_provenance"]["declared_status"], "NOT_CHECKED")

    def test_missing_hypothesis_predictions_are_unknown(self):
        p = proposal()
        p["probes"][0]["predictions"] = {"causal": "INCREASE"}
        r = assess_proposal(p)
        self.assertEqual(r["probe_comparisons"][0]["pair_count"], 0)
        self.assertEqual(set(r["probe_comparisons"][0]["missing_hypothesis_predictions"]),
                         {"confounded", "no-effect"})

    def test_missing_measurement_axis_cannot_be_counted(self):
        p = proposal()
        p["probes"][0].pop("evaluation_unit")
        with self.assertRaises(AgentError):
            assess_proposal(p)

    def test_reject_fabricated_numeric_prediction_probabilities(self):
        p = proposal()
        p["probes"][0]["predictions"]["causal"] = 0.85
        with self.assertRaises(AgentError):
            assess_proposal(p)

    def test_reject_unknown_hypothesis_and_duplicate_probe(self):
        p = proposal()
        p["probes"][0]["predictions"]["future-hypothesis"] = "INCREASE"
        with self.assertRaises(AgentError):
            assess_proposal(p)
        p = proposal()
        p["probes"][1]["id"] = p["probes"][0]["id"]
        with self.assertRaises(AgentError):
            assess_proposal(p)

    def test_reject_invalid_claim_precheck_and_large_payload(self):
        p = proposal()
        p["claim_type"] = "Q1_GUARANTEED"
        with self.assertRaises(AgentError):
            assess_proposal(p)
        p = proposal()
        p["prechecks"]["group_independence"]["status"] = True
        with self.assertRaises(AgentError):
            assess_proposal(p)
        p = proposal()
        p["probes"] = p["probes"] * 4
        with self.assertRaises(AgentError):
            assess_proposal(p)


if __name__ == "__main__":
    unittest.main()
