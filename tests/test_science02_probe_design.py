"""SCIENCE-02: declaration-level contradictions in a probe packet.

Each check answers a real historical failure, not a hypothetical one:
an oracle reference (CASE-02/CASE-12), windows counted as independent units
(CASE-11/EXT-X3), and a packet where no probe can change the judgment
(CASE-08). None of them reads a file, ranks candidates or approves anything.
"""
import unittest

from pdrw_agent.science.decision import assess_proposal


def packet(**overrides):
    base = {
        "claim_type": "MECHANISM/CAUSAL",
        "question": "Does the geometric mechanism explain the collapse?",
        "claim_evidence_refs": ["DEV/runs/RUN-011/metrics.json"],
        "hypotheses": ["H_mechanism", "H_budget"],
        "proposed_premise": {"premise_id": "MECHANISM",
                             "scope": {"material": "unseen", "evaluator": "ridge"}},
        "prechecks": {
            "group_independence": {"status": "PASS", "evidence_refs": ["DEV/protocol.md"]},
        },
        "probes": [{
            "id": "P1",
            "observable": "boundary error",
            "evaluation_unit": "SPECIMEN",
            "comparison_reference": "VT_plain",
            "predictions": {"H_mechanism": "DECREASE", "H_budget": "NO_CHANGE"},
            "cost_band": "LOW",
        }],
    }
    base.update(overrides)
    return base


class ReferenceLegalityTests(unittest.TestCase):
    def test_an_oracle_reference_is_reported(self):
        pkt = packet()
        pkt["probes"][0]["comparison_reference"] = "ORACLE_OFFSET_REMOVAL_DEV_VAL_LABELS"
        result = assess_proposal(pkt)
        self.assertEqual(["REFERENCE_NOT_LEGAL"], result["probe_findings"][0]["codes"])

    def test_a_legal_reference_is_not_reported(self):
        self.assertEqual([], assess_proposal(packet())["probe_findings"])

    def test_a_supervised_simple_baseline_is_a_legal_reference(self):
        # A strong simple baseline trained on training labels is exactly what
        # PD-RW asks for; only test-time truth is illegal.
        pkt = packet()
        pkt["probes"][0]["comparison_reference"] = "human-label-trained linear baseline"
        self.assertEqual([], assess_proposal(pkt)["probe_findings"])

    def test_the_finding_cites_its_own_case(self):
        pkt = packet()
        pkt["probes"][0]["comparison_reference"] = "test-time labels"
        finding = assess_proposal(pkt)["probe_findings"][0]
        self.assertIn("CASE-02", finding["precedent"])
        self.assertFalse(finding["independently_verified"])


class ProbeUnitTests(unittest.TestCase):
    def test_a_repeated_unit_contradicts_declared_group_independence(self):
        pkt = packet()
        pkt["probes"][0]["evaluation_unit"] = "WINDOW"
        result = assess_proposal(pkt)
        self.assertEqual(["PROBE_UNIT_NOT_INDEPENDENT"], result["probe_findings"][0]["codes"])
        self.assertEqual("DECLARED_CONFLICT", result["prechecks"]["group_independence"]["review"])
        self.assertEqual(["P1"], result["prechecks"]["group_independence"]["conflict_with_probe_units"])

    def test_an_unknown_group_check_is_not_called_a_contradiction(self):
        pkt = packet()
        pkt["probes"][0]["evaluation_unit"] = "WINDOW"
        pkt["prechecks"] = {"group_independence": {"status": "NOT_CHECKED", "evidence_refs": []}}
        result = assess_proposal(pkt)
        self.assertEqual([], result["probe_findings"])
        self.assertNotEqual("DECLARED_CONFLICT", result["prechecks"]["group_independence"]["review"])

    def test_an_independent_unit_stays_clean(self):
        for unit in ("SUBJECT", "SESSION", "SPECIMEN"):
            pkt = packet()
            pkt["probes"][0]["evaluation_unit"] = unit
            self.assertEqual([], assess_proposal(pkt)["probe_findings"], unit)


class DecisivenessTests(unittest.TestCase):
    def test_a_packet_that_cannot_separate_anything_says_so(self):
        pkt = packet()
        pkt["probes"] = [
            {"id": "A", "observable": "R2", "evaluation_unit": "SPECIMEN",
             "comparison_reference": "VT_plain", "predictions": {}, "cost_band": "LOW"},
            {"id": "B", "observable": "MAE", "evaluation_unit": "SPECIMEN",
             "comparison_reference": "VT_plain",
             "predictions": {"H_mechanism": "UNKNOWN"}, "cost_band": "MEDIUM"},
        ]
        result = assess_proposal(pkt)
        self.assertTrue(result["no_decisive_probe"])
        self.assertEqual([], result["declared_probe_efficiency"]["frontier_candidate_ids_as_declared"])
        self.assertTrue(result["declared_probe_efficiency"]["no_discriminating_probe"])
        self.assertIn("cannot change the judgment", result["no_decisive_probe_question"])

    def test_one_separating_probe_is_enough_to_keep_the_frontier(self):
        result = assess_proposal(packet())
        self.assertFalse(result["no_decisive_probe"])
        self.assertEqual(["P1"],
                         result["declared_probe_efficiency"]["frontier_candidate_ids_as_declared"])

    def test_an_uninformative_probe_is_never_named_as_the_cheap_option(self):
        pkt = packet()
        pkt["probes"].append({
            "id": "EMPTY-BUT-CHEAP", "observable": "R2", "evaluation_unit": "SPECIMEN",
            "comparison_reference": "VT_plain", "predictions": {}, "cost_band": "LOW"})
        result = assess_proposal(pkt)
        frontier = result["declared_probe_efficiency"]["frontier_candidate_ids_as_declared"]
        self.assertEqual(["P1"], frontier)


class SafetyTests(unittest.TestCase):
    def test_new_fields_do_not_add_authority(self):
        pkt = packet()
        pkt["probes"][0]["comparison_reference"] = "ORACLE"
        result = assess_proposal(pkt)
        self.assertEqual("ADVISORY_REVIEW_ONLY", result["status"])
        self.assertFalse(result["automatic_stop"])
        self.assertFalse(result["automatic_go"])
        self.assertEqual("UNVERIFIED", result["original_user_authorization"])
        self.assertTrue(result["no_claim_of_novelty_or_scientific_validity"])


if __name__ == "__main__":
    unittest.main()
