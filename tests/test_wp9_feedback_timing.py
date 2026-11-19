"""WP9-A: pre/post-Run case timing and prediction provenance.

Synthetic fixtures only. No scientific effect is measured here; the point is
that a post-Run retrieval cannot become a pre-decision citation and that a
self-declared timestamp cannot promote provenance.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.science import feedback_link
from pdrw_agent.science.feedback import proposal_sha256
from tests.test_science_feedback_link import _Project, _sha, _proposal


class TimingAndProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = _Project(Path(self.temp.name))

    def review(self, link=None, **kwargs):
        return feedback_link.review_linked_feedback(
            link or self.project.link(), project_root=self.project.root, **kwargs)

    # -- A1: pre-decision vs post-Run cases ---------------------------------
    def test_declared_pre_decision_cases_without_receipt_stay_unknown(self):
        link = self.project.link()
        link["cases"] = {"query": "受试者分组 泄漏", "limit": 2,
                         "pre_decision": {"case_ids": ["EXT-C04"]}}
        result = self.review(link)
        timing = result["case_timing"]
        self.assertEqual(timing["usage_status"], "UNKNOWN_NO_RECEIPT")
        self.assertEqual(timing["pre_decision_case_ids"], [])
        self.assertEqual(timing["declared_pre_decision_case_ids"], ["EXT-C04"])
        self.assertEqual(timing["case_influence_verified"], "UNKNOWN_NO_RECEIPT")
        self.assertEqual(result["feedback"]["consulted_case_ids"], [])

    def test_receipt_after_the_decision_is_not_pre_decision_use(self):
        link = self.project.link()
        receipt = self.project.root / "protocol" / "CASE-RECEIPT.json"
        receipt.write_text(json.dumps({
            "schema_version": "pdrw-case-usage-receipt-v1",
            "retrieved_at": "2026-01-05T00:00:00+00:00",
            "query": "受试者分组",
            "case_ids": ["EXT-C04"],
        }), encoding="utf-8")
        link["cases"] = {"pre_decision": {
            "case_ids": ["EXT-C04"], "receipt_ref": "protocol/CASE-RECEIPT.json",
            "receipt_sha256": _sha(receipt)}}
        result = self.review(link)
        timing = result["case_timing"]
        self.assertEqual(timing["usage_status"], "RECEIPT_AFTER_DECISION")
        self.assertEqual(timing["pre_decision_case_ids"], [])
        self.assertFalse(timing["checks"]["retrieved_before_decision"])

    def test_legal_receipt_is_retrieval_only_unless_frozen_record_cites_it(self):
        receipt = self.project.root / "protocol" / "CASE-RECEIPT.json"
        receipt.write_text(json.dumps({
            "schema_version": "pdrw-case-usage-receipt-v1",
            "retrieved_at": "2025-12-20T00:00:00+00:00",
            "query": "受试者分组",
            "case_ids": ["EXT-C04", "EXT-C05"],
        }), encoding="utf-8")
        link = self.project.link()
        link["cases"] = {"pre_decision": {
            "case_ids": ["EXT-C04"], "receipt_ref": "protocol/CASE-RECEIPT.json",
            "receipt_sha256": _sha(receipt)}}
        result = self.review(link)
        timing = result["case_timing"]
        self.assertEqual(timing["usage_status"], "VERIFIED")
        self.assertEqual(timing["pre_decision_case_ids"], ["EXT-C04"])
        self.assertEqual(timing["case_influence_verified"],
                         feedback_link.CASE_INFLUENCE_RETRIEVAL)
        self.assertEqual(result["feedback"]["consulted_case_ids"], ["EXT-C04"])

        # The same IDs cited by the frozen record itself raise the claim from
        # "retrieved" to "declared in the pre-result record".
        record = json.loads(self.project.prereg_path.read_text(encoding="utf-8"))
        record["consulted_case_ids"] = ["EXT-C04"]
        self.project.prereg_path.write_text(json.dumps(record, ensure_ascii=False),
                                            encoding="utf-8")
        link = self.project.link()
        link["prereg"]["sha256"] = _sha(self.project.prereg_path)
        link["cases"] = {"pre_decision": {
            "case_ids": ["EXT-C04"], "receipt_ref": "protocol/CASE-RECEIPT.json",
            "receipt_sha256": _sha(receipt)}}
        result = self.review(link)
        self.assertEqual(result["case_timing"]["case_influence_verified"],
                         feedback_link.CASE_INFLUENCE_VERIFIED)

    def test_post_run_retrieval_never_enters_pre_decision_fields(self):
        result = self.review()
        self.assertEqual(result["case_timing"]["pre_decision_case_ids"], [])
        self.assertEqual(result["case_timing"]["post_run_related_case_ids"], [])
        self.assertEqual(result["feedback"]["consulted_case_ids"], [])
        self.assertEqual(result["feedback"]["consulted_case_ids_semantics"],
                         "PRE_DECISION_VERIFIED_ONLY_NEVER_POST_RUN")

    # -- A2: prediction provenance ------------------------------------------
    def test_legal_binding_is_provenance_verified(self):
        result = self.review()
        self.assertEqual(result["provenance"]["pre_result_provenance"],
                         feedback_link.PROVENANCE_VERIFIED)
        self.assertEqual(result["provenance"]["prediction_comparison"],
                         feedback_link.COMPARISON_PERFORMED)
        self.assertTrue(result["prediction_verification_performed"])
        self.assertFalse(result["scientific_inference_verified"])
        self.assertFalse(result["automatic_go"])

    def test_proposal_replaced_after_freeze_is_not_compared(self):
        changed = _proposal()
        changed["probes"][0]["predictions"] = {"real-gain": "DECREASE",
                                               "leakage-explains-gain": "INCREASE"}
        self.project.proposal_path.write_text(
            json.dumps(changed, ensure_ascii=False), encoding="utf-8")
        result = self.review()
        self.assertEqual(result["status"], "PRE_RESULT_RECORD_UNVERIFIED")
        self.assertEqual(result["reason"], "PROPOSAL_CHANGED_SINCE_FREEZE")
        self.assertIsNone(result["feedback"])
        self.assertFalse(result["prediction_verification_performed"])
        self.assertEqual(result["observation_preserved"]["declared_outcome"], "INCREASE")

    def test_self_declared_earlier_time_does_not_promote_provenance(self):
        # The frozen record really is dated after the Run; the link claims an
        # earlier time. The conservative effective time wins and the conflict
        # keeps provenance unverified.
        record = json.loads(self.project.prereg_path.read_text(encoding="utf-8"))
        record["frozen_at"] = "2026-01-05T09:00:00+00:00"
        self.project.prereg_path.write_text(json.dumps(record, ensure_ascii=False),
                                            encoding="utf-8")
        link = self.project.link()
        link["prereg"]["sha256"] = _sha(self.project.prereg_path)
        link["prereg"]["declared_at"] = "2025-12-01T09:00:00+00:00"
        result = self.review(link)
        self.assertEqual(result["order_check"], "DECLARED_AFTER_RUN")
        self.assertTrue(result["prereg"]["declared_at_conflict"])
        self.assertEqual(result["provenance"]["pre_result_provenance"],
                         feedback_link.PROVENANCE_UNVERIFIED)
        self.assertFalse(result["prediction_verification_performed"])

    def test_inline_proposal_object_is_never_file_bound(self):
        link = self.project.link()
        link["prereg"].pop("proposal_ref")
        link["prereg"]["proposal"] = _proposal()
        result = self.review(link)
        self.assertEqual(result["prereg"]["proposal_binding"], "INLINE_LINK_OBJECT")
        self.assertEqual(result["provenance"]["pre_result_provenance"],
                         feedback_link.PROVENANCE_UNVERIFIED)
        self.assertFalse(result["prediction_verification_performed"])
        # The comparison may still run as advisory, but it cannot certify.
        self.assertEqual(result["provenance"]["prediction_comparison"],
                         feedback_link.COMPARISON_PERFORMED)

    def test_prereg_with_hypotheses_but_no_feedback_schema(self):
        record = {"declaration_id": "PRIOR-002",
                  "frozen_at": "2026-01-01T09:00:00+00:00",
                  "scientific_hypotheses": {"h1": "declared"},
                  "ex_ante_decision_rules": {"POS": "delta>0"}}
        self.project.prereg_path.write_text(json.dumps(record), encoding="utf-8")
        link = self.project.link()
        link["prereg"] = {"ref": "protocol/PRIOR-DECLARATION.json",
                          "sha256": _sha(self.project.prereg_path)}
        result = self.review(link)
        self.assertEqual(result["reason"], "PREREG_WITHOUT_FEEDBACK_PROPOSAL")
        self.assertEqual(result["provenance"]["pre_result_provenance"],
                         feedback_link.PROVENANCE_UNVERIFIED)
        self.assertFalse(result["prediction_verification_performed"])
        self.assertIn("ex_ante_decision_rules",
                      result["prereg"]["declared_prediction_fields"])

    def test_changed_run_evidence_is_reported_not_verified(self):
        self.project.metrics.write_text(json.dumps({"delta": 0.9}), encoding="utf-8")
        link = self.project.link()
        link["run"]["observation"] = self.project.observation(
            evidence_sha256={"DEV/runs/RUN-001/metrics.json": "0" * 64})
        result = self.review(link)
        self.assertEqual(result["status"], "RUN_EVIDENCE_UNVERIFIED")
        self.assertEqual(result["provenance"]["pre_result_provenance"],
                         feedback_link.PROVENANCE_UNVERIFIED)
        self.assertFalse(result["prediction_verification_performed"])
        self.assertEqual(result["run"]["evidence_problems"][0]["problem"], "HASH_CHANGED")

    # -- INVALID / INCONCLUSIVE / NOT_RUN ----------------------------------
    def test_inconclusive_run_is_not_a_scientific_negative(self):
        self.project.record_path.write_text(json.dumps(
            {"run_id": "RUN-001", "status": "VALID"}), encoding="utf-8")
        link = self.project.link()
        link["run"]["observation"] = self.project.observation(
            validity="INCONCLUSIVE", outcome="UNKNOWN")
        result = self.review(link)
        self.assertIsNone(result["reason"])
        self.assertEqual(result["feedback"]["declared_prediction_review"],
                         "NO_VALID_SCIENTIFIC_INFERENCE")
        self.assertEqual(result["feedback"]["contradicted_predictions"], [])
        self.assertEqual(result["provenance"]["prediction_comparison"],
                         "NO_VALID_SCIENTIFIC_INFERENCE")
        self.assertFalse(result["prediction_verification_performed"])

    def test_not_run_keeps_the_observation_without_inference(self):
        self.project.record_path.write_text(json.dumps(
            {"run_id": "RUN-001", "status": "NOT_RUN"}), encoding="utf-8")
        link = self.project.link()
        link["run"]["observation"] = self.project.observation(
            validity="NOT_RUN", outcome="UNKNOWN")
        result = self.review(link)
        self.assertEqual(result["status"], "ADVISORY_FEEDBACK_ONLY")
        self.assertEqual(result["feedback"]["compatible_predictions"], [])
        self.assertEqual(result["feedback"]["contradicted_predictions"], [])
        self.assertFalse(result["automatic_stop"])
        self.assertFalse(result["scientific_inference_verified"])

    # -- compatibility ------------------------------------------------------
    def test_legacy_fields_keep_their_names_and_types(self):
        result = self.review()
        for key in ("status", "reason", "project_id", "prereg", "run", "order_check",
                    "feedback", "case_context", "observation_preserved",
                    "prediction_verification_performed"):
            self.assertIn(key, result)
        self.assertIsInstance(result["feedback"]["consulted_case_ids"], list)
        self.assertIn("declared_prediction_review", result["feedback"])
        self.assertIn("historical_order_verified", result)
        self.assertFalse(result["historical_order_verified"])
        self.assertFalse(result["writes_performed"])


if __name__ == "__main__":
    unittest.main()
