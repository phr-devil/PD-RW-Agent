"""SCIENCE-03: what may be called the decisive experiment.

Two boundary cases, both taken from real cards rather than invented:

* CASE-08 — a cheap probe that separates nothing was still listed next to the
  probe that does separate the hypotheses;
* CASE-02 / CASE-12 — a probe whose reference is test-time truth was cheap,
  separated the same pairs, and therefore *dominated* the legal probe.

The fix must not turn either into a stop: a blind probe can still be a pilot,
an oracle-referenced probe is still a legitimate upper bound, and a
window-level metric only asks for an independent-unit count.
"""
import unittest

from pdrw_agent.science.decision import assess_proposal


def packet(probes, **overrides):
    base = {
        "claim_type": "MECHANISM/CAUSAL",
        "question": "Does the geometric mechanism or the budget explain the collapse?",
        "claim_evidence_refs": ["DEV/runs/RUN-011/metrics.json"],
        "hypotheses": ["H_mechanism", "H_budget"],
        "proposed_premise": {"premise_id": "MECHANISM",
                             "scope": {"material": "unseen", "evaluator": "ridge"}},
        "prechecks": {"group_independence": {"status": "PASS",
                                            "evidence_refs": ["DEV/protocol.md"]}},
        "probes": probes,
    }
    base.update(overrides)
    return base


def probe(ident, predictions, cost="LOW", reference="VT_plain", unit="SPECIMEN"):
    return {"id": ident, "observable": "boundary error", "evaluation_unit": unit,
            "comparison_reference": reference, "predictions": predictions,
            "cost_band": cost}


DECIDES = {"H_mechanism": "DECREASE", "H_budget": "NO_CHANGE"}


def frontier(result):
    return result["declared_probe_efficiency"]


class BlindProbeTests(unittest.TestCase):
    def test_a_cheap_blind_probe_does_not_join_the_frontier(self):
        result = assess_proposal(packet([
            probe("CHEAP-BUT-BLIND", {}, "LOW"),
            probe("MEDIUM-BUT-DECIDES", DECIDES, "MEDIUM"),
        ]))
        self.assertEqual(["MEDIUM-BUT-DECIDES"],
                         frontier(result)["frontier_candidate_ids_as_declared"])
        self.assertEqual(["CHEAP-BUT-BLIND"], frontier(result)["exploratory_probe_ids"])

    def test_a_blind_probe_cannot_dominate_a_decisive_one(self):
        result = assess_proposal(packet([
            probe("CHEAP-BUT-BLIND", {"H_mechanism": "UNKNOWN"}, "LOW"),
            probe("EXPENSIVE-BUT-DECIDES", DECIDES, "HIGH"),
        ]))
        self.assertEqual(["EXPENSIVE-BUT-DECIDES"],
                         frontier(result)["frontier_candidate_ids_as_declared"])
        self.assertEqual([], frontier(result)["dominated_candidates_as_declared"])

    def test_a_pilot_is_still_available_but_not_called_decisive(self):
        result = assess_proposal(packet([
            probe("PILOT", {}, "LOW"),
            probe("DECIDES", DECIDES, "MEDIUM"),
        ]))
        self.assertIn("PILOT", frontier(result)["exploratory_probe_ids"])
        self.assertNotIn("PILOT", frontier(result)["frontier_candidate_ids_as_declared"])
        self.assertFalse(result["automatic_stop"])


class IllegalReferenceTests(unittest.TestCase):
    def test_an_oracle_referenced_probe_is_not_the_decisive_experiment(self):
        result = assess_proposal(packet([
            probe("ORACLE-UPPER-BOUND", DECIDES, "LOW",
                  reference="ORACLE_OFFSET_REMOVAL_DEV_VAL_LABELS"),
            probe("LEGAL-SPECIMEN-PROBE", DECIDES, "MEDIUM"),
        ]))
        self.assertEqual(["LEGAL-SPECIMEN-PROBE"],
                         frontier(result)["frontier_candidate_ids_as_declared"])
        self.assertEqual(["ORACLE-UPPER-BOUND"], frontier(result)["diagnostic_upper_bound_ids"])
        # The cheap illegal probe no longer eliminates the lawful one.
        self.assertEqual([], frontier(result)["dominated_candidates_as_declared"])

    def test_the_finding_says_what_the_probe_is_still_good_for(self):
        result = assess_proposal(packet([
            probe("ORACLE", DECIDES, reference="test-time labels"),
        ]))
        finding = result["probe_findings"][0]
        self.assertEqual(["DIAGNOSTIC_UPPER_BOUND_ONLY"], finding["usage"])
        self.assertTrue(finding["blocks_decisive_frontier"])

    def test_only_illegal_references_leave_no_legal_probe(self):
        result = assess_proposal(packet([
            probe("ORACLE", DECIDES, reference="ORACLE_OFFSET_REMOVAL_DEV_VAL_LABELS"),
        ]))
        self.assertEqual([], frontier(result)["frontier_candidate_ids_as_declared"])
        self.assertTrue(result["no_legal_decisive_probe"])
        self.assertFalse(result["no_decisive_probe"])
        self.assertIn("available at prediction time", result["no_legal_decisive_probe_question"])

    def test_no_question_when_a_legal_probe_exists(self):
        result = assess_proposal(packet([probe("LEGAL", DECIDES)]))
        self.assertFalse(result["no_legal_decisive_probe"])
        self.assertIsNone(result["no_legal_decisive_probe_question"])


class UnitVerificationTests(unittest.TestCase):
    def test_a_window_metric_asks_for_a_unit_count_not_a_ban(self):
        result = assess_proposal(packet([probe("WINDOW-PROBE", DECIDES, unit="WINDOW")]))
        self.assertEqual(["WINDOW-PROBE"], frontier(result)["frontier_candidate_ids_as_declared"])
        self.assertEqual(["WINDOW-PROBE"], frontier(result)["needs_unit_verification_ids"])
        self.assertEqual("DECLARED_CONFLICT", result["prechecks"]["group_independence"]["review"])
        self.assertEqual(["VERIFY_INDEPENDENT_UNITS_FIRST"],
                         result["probe_findings"][0]["usage"])
        self.assertFalse(result["probe_findings"][0]["blocks_decisive_frontier"])
        self.assertFalse(result["automatic_stop"])

    def test_a_window_metric_without_a_pass_declaration_is_not_flagged(self):
        pkt = packet([probe("WINDOW-PROBE", DECIDES, unit="WINDOW")],
                     prechecks={"group_independence": {"status": "NOT_CHECKED",
                                                      "evidence_refs": []}})
        result = assess_proposal(pkt)
        self.assertEqual([], frontier(result)["needs_unit_verification_ids"])
        self.assertEqual(["WINDOW-PROBE"], frontier(result)["frontier_candidate_ids_as_declared"])


class SafetyTests(unittest.TestCase):
    def test_the_frontier_still_authorizes_nothing(self):
        result = assess_proposal(packet([
            probe("ORACLE", DECIDES, reference="oracle"),
            probe("WINDOW", DECIDES, unit="WINDOW"),
            probe("BLIND", {}, "LOW"),
        ]))
        eff = frontier(result)
        self.assertFalse(eff["automatically_selected"])
        self.assertFalse(eff["scientifically_ranked"])
        self.assertFalse(eff["source_predictions_verified"])
        self.assertFalse(result["automatic_go"])
        self.assertFalse(result["automatic_stop"])
        self.assertEqual("UNVERIFIED", result["original_user_authorization"])


if __name__ == "__main__":
    unittest.main()
