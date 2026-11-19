"""Synthetic checks of read-only science feedback; not real scientific validation."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.schemas import AgentError
from pdrw_agent.science.feedback import proposal_sha256, review_probe_feedback


def proposal():
    return {
        "question": "Does a calibrated sensor gain survive independent groups?",
        "claim_type": "MECHANISM",
        "hypotheses": ["real-increment", "group-leakage"],
        "proposed_premise": {
            "premise_id": "sensor-increment",
            "scope": {"dataset": "synthetic-dev", "group_unit": "person"},
        },
        "probes": [{
            "id": "heldout-check",
            "observable": "macro-f1-delta",
            "evaluation_unit": "held-out-person",
            "comparison_reference": "matched-simple-baseline",
            "predictions": {"real-increment": "INCREASE", "group-leakage": "NO_CHANGE"},
            "prediction_evidence_refs": ["frozen-protocol"],
            "cost_band": "LOW",
        }],
    }


def packet():
    p = proposal()
    digest = proposal_sha256(p)
    return {
        "schema_version": "pdrw-probe-feedback-v1",
        "prior_decision_ref": "frozen/decision-before-result.json",
        "prior_proposal_sha256": digest,
        "prior_proposal": p,
        "observation": {
            "run_ref": "DEV/run-001",
            "probe_id": "heldout-check",
            "prior_proposal_sha256": digest,
            "observable": "macro-f1-delta",
            "evaluation_unit": "held-out-person",
            "comparison_reference": "matched-simple-baseline",
            "validity": "VALID",
            "outcome": "NO_CHANGE",
            "evidence_refs": ["DEV/run-001/evaluation.json"],
        },
        "consulted_case_ids": ["EXT-X3"],
    }


class ProbeFeedbackTests(unittest.TestCase):
    def assert_error(self, packet_value, code):
        with self.assertRaises(AgentError) as ctx:
            review_probe_feedback(packet_value)
        self.assertEqual(ctx.exception.code, code)

    def test_same_snapshot_digest_is_stable(self):
        original = proposal()
        shuffled = dict(reversed(list(original.items())))
        self.assertEqual(proposal_sha256(original), proposal_sha256(shuffled))
        edited = copy.deepcopy(original)
        edited["probes"][0]["predictions"]["real-increment"] = "NO_CHANGE"
        self.assertNotEqual(proposal_sha256(original), proposal_sha256(edited))

    def test_valid_observation_compares_declared_predictions_only(self):
        result = review_probe_feedback(packet())
        self.assertEqual(result["status"], "ADVISORY_FEEDBACK_ONLY")
        self.assertEqual(result["declared_prediction_review"], "DECLARED_PREDICTION_CONTRAST")
        self.assertEqual(result["compatible_predictions"], ["group-leakage"])
        self.assertEqual(result["contradicted_predictions"], ["real-increment"])
        self.assertFalse(result["original_run_verified"])
        self.assertFalse(result["historical_order_verified"])
        self.assertFalse(result["permission_to_execute"])
        self.assertFalse(result["automatic_stop"])
        self.assertEqual(result["consulted_case_ids"], ["EXT-X3"])

    def test_invalid_or_not_run_do_not_become_scientific_negatives(self):
        for state in ("INVALID", "NOT_RUN", "INCONCLUSIVE"):
            p = packet()
            p["observation"]["validity"] = state
            p["observation"]["outcome"] = "UNKNOWN"
            result = review_probe_feedback(p)
            self.assertEqual(result["declared_prediction_review"], "NO_VALID_SCIENTIFIC_INFERENCE")
            self.assertEqual(result["compatible_predictions"], [])
            self.assertEqual(result["contradicted_predictions"], [])

    def test_changed_measurement_axis_rejected(self):
        for axis in ("observable", "evaluation_unit", "comparison_reference"):
            p = packet()
            p["observation"][axis] = "changed-after-seeing-result"
            self.assert_error(p, "FEEDBACK_NOT_COMPARABLE")

    def test_tampered_prior_snapshot_rejected(self):
        p = packet()
        p["prior_proposal"]["question"] = "Rewritten after observing result"
        self.assert_error(p, "FEEDBACK_SNAPSHOT_MISMATCH")
        p = packet()
        p["observation"]["prior_proposal_sha256"] = "0" * 64
        self.assert_error(p, "FEEDBACK_SNAPSHOT_MISMATCH")

    def test_unknown_probe_and_missing_evidence_rejected(self):
        p = packet()
        p["observation"]["probe_id"] = "different-probe"
        self.assert_error(p, "FEEDBACK_PROBE_UNKNOWN")
        p = packet()
        p["observation"]["evidence_refs"] = []
        self.assert_error(p, "FEEDBACK_EVIDENCE_MISSING")

    def test_invalid_run_with_pretended_science_rejected(self):
        p = packet()
        p["observation"]["validity"] = "INVALID"
        self.assert_error(p, "FEEDBACK_INVALID_OUTCOME")

    def test_no_contrast_does_not_select_winner(self):
        p = packet()
        p["prior_proposal"]["probes"][0]["predictions"] = {
            "real-increment": "NO_CHANGE", "group-leakage": "NO_CHANGE"
        }
        new_hash = proposal_sha256(p["prior_proposal"])
        p["prior_proposal_sha256"] = new_hash
        p["observation"]["prior_proposal_sha256"] = new_hash
        result = review_probe_feedback(p)
        self.assertEqual(result["declared_prediction_review"], "NO_DISCRIMINATING_CONTRAST")
        self.assertEqual(result["contradicted_predictions"], [])

    def test_cli_synthetic_packet_is_advisory(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "feedback.json"
            path.write_text(json.dumps(packet()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "pdrw_agent.science.feedback",
                 "--packet", str(path)],
                capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            parsed = json.loads(result.stdout)
            self.assertFalse(parsed["scientific_inference_verified"])
            self.assertFalse(parsed["writes_performed"])


if __name__ == "__main__":
    unittest.main()
