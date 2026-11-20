"""SCIENCE-03B: an experiment that already ran is not a next action.

The packets come from `RCT-CONTACT-26`: the DEV-only slope diagnosis was run and
closed by user decision (`R1_BRANCH = CLOSED_BY_USER_DECISION`,
`NO_USEFUL_NEXT_PROBE = TRUE`), it costs less than every live probe, and it
separates the same hypothesis pair -- so a cost-only frontier kept naming it.

What the fix must and must not do:

* a completed-and-valid probe stays as recorded evidence and is not rerun;
* an INVALID run asks for a repair of its named defect, not a repeat;
* an INCONCLUSIVE run continues only when new information can change the call;
* a probe that needs an authorization remains a candidate, not a next action;
* a closure declared without a Run reference is a claim to check, not a closure;
* nothing is deleted, nothing stops, and old packets without the field behave
  exactly as before.
"""
import unittest

from pdrw_agent.schemas import AgentError
from pdrw_agent.science.decision import assess_proposal

PREDICTS = {"H_material": "INCREASE", "H_sensor_trajectory": "NO_CHANGE"}


def probe(ident, cost="LOW", prior=None, reference="same-material repeat press replicates",
          unit="FRAME"):
    entry = {"id": ident, "observable": "per-material force-Z slope",
             "evaluation_unit": unit, "comparison_reference": reference,
             "predictions": dict(PREDICTS), "cost_band": cost}
    if prior is not None:
        entry["prior_execution"] = prior
    return entry


def packet(probes):
    return {
        "claim_type": "MECHANISM/CAUSAL",
        "question": "Does the contact response identify the material or the sensor?",
        "hypotheses": ["H_material", "H_sensor_trajectory"],
        "proposed_premise": {"premise_id": "CONTACT", "scope": {"rig": "DIGIT"}},
        "prechecks": {"group_independence": {"status": "UNKNOWN"}},
        "probes": probes,
    }


CLOSED = {"status": "COMPLETED_VALID", "run_ref": "EXP-006", "premise_id": "CONTACT"}
PRESS = {"id": "PRESS", "observable": "slope vs external modulus",
         "evaluation_unit": "MATERIAL", "comparison_reference": "external modulus",
         "predictions": dict(PREDICTS), "cost_band": "HIGH"}
SWAP = {"id": "SWAP", "observable": "slope difference between sensors",
        "evaluation_unit": "SEQUENCE",
        "comparison_reference": "other sensor instance", "predictions": dict(PREDICTS),
        "cost_band": "MEDIUM"}


def eff(result):
    return result["declared_probe_efficiency"]


def app(result, ident):
    return next(s for s in result["probe_comparisons"] if s["id"] == ident)["applicability"]


class ClosedProbeTests(unittest.TestCase):
    def test_a_closed_probe_is_history_not_the_next_experiment(self):
        result = assess_proposal(packet([probe("SLOPE", prior=CLOSED), PRESS, SWAP]))
        self.assertEqual(["SWAP"], eff(result)["frontier_candidate_ids_as_declared"])
        self.assertEqual(["SLOPE"], eff(result)["historical_evidence_ids"])
        self.assertEqual("HISTORICAL_EVIDENCE_ONLY", app(result, "SLOPE"))

    def test_a_closed_probe_cannot_dominate_a_live_one(self):
        result = assess_proposal(packet([probe("SLOPE", prior=CLOSED), PRESS, SWAP]))
        self.assertEqual(["PRESS"], [d["id"] for d in eff(result)["dominated_candidates_as_declared"]])
        self.assertNotIn("SLOPE", [d["id"] for d in eff(result)["dominated_candidates_as_declared"]])

    def test_a_closed_probe_keeps_its_next_action_label(self):
        result = assess_proposal(packet([probe("SLOPE", prior=CLOSED), PRESS]))
        entry = next(s for s in result["probe_comparisons"] if s["id"] == "SLOPE")
        self.assertEqual("KEEP_AS_RECORDED_EVIDENCE_DO_NOT_RERUN", entry["next_action"])
        self.assertTrue(entry["prior_execution"]["status_verified"])


class RepairAndRevisitTests(unittest.TestCase):
    def test_an_invalid_run_asks_for_repair_not_a_repeat(self):
        result = assess_proposal(packet([
            probe("TRANSFORM", prior={"status": "COMPLETED_INVALID",
                                      "run_ref": "EXP-005", "premise_id": "CONTACT"}),
            PRESS]))
        self.assertEqual(["TRANSFORM"], eff(result)["repair_required_ids"])
        self.assertEqual(["PRESS"], eff(result)["frontier_candidate_ids_as_declared"])
        self.assertEqual("REPAIR_NAMED_DEFECT_FIRST",
                         next(s for s in result["probe_comparisons"]
                              if s["id"] == "TRANSFORM")["next_action"])

    def test_inconclusive_without_new_information_waits(self):
        result = assess_proposal(packet([
            probe("PARTIAL", prior={"status": "INCONCLUSIVE", "run_ref": "RUN-002",
                                    "premise_id": "CONTACT"}), PRESS]))
        self.assertEqual(["PARTIAL"], eff(result)["awaiting_new_information_ids"])
        self.assertEqual(["PRESS"], eff(result)["frontier_candidate_ids_as_declared"])

    def test_inconclusive_with_new_information_is_a_revisit_not_a_frontier_winner(self):
        result = assess_proposal(packet([
            probe("PARTIAL", prior={"status": "INCONCLUSIVE", "run_ref": "RUN-002",
                                    "premise_id": "CONTACT",
                                    "new_information": "unit now counted per sequence"}),
            PRESS]))
        self.assertEqual(["PARTIAL"], eff(result)["revisit_on_new_information_ids"])
        self.assertEqual(["PRESS"], eff(result)["frontier_candidate_ids_as_declared"])
        self.assertEqual("REVISIT_ONLY_IF_NEW_INFORMATION_CHANGES_JUDGMENT",
                         next(s for s in result["probe_comparisons"]
                              if s["id"] == "PARTIAL")["next_action"])

    def test_an_unauthorized_probe_is_a_candidate_not_a_next_action(self):
        result = assess_proposal(packet([
            probe("PRESS-NEW-TRUTH", "HIGH",
                  {"status": "NOT_EXECUTED", "requires_new_authorization": True},
                  reference="external modulus of the same material")]))
        self.assertEqual(["PRESS-NEW-TRUTH"], eff(result)["needs_authorization_ids"])
        self.assertEqual([], eff(result)["frontier_candidate_ids_as_declared"])
        self.assertTrue(result["no_executable_next_probe"])
        self.assertIsNotNone(result["no_executable_next_probe_question"])
        self.assertFalse(result["no_legal_decisive_probe"])


class UnverifiedClaimTests(unittest.TestCase):
    def test_a_closure_without_a_run_reference_is_not_a_closure(self):
        result = assess_proposal(packet([
            probe("CLAIMED", prior={"status": "COMPLETED_VALID", "premise_id": "CONTACT"}),
            PRESS]))
        self.assertEqual(["CLAIMED"], eff(result)["unverified_closure_ids"])
        self.assertEqual([], eff(result)["historical_evidence_ids"])
        self.assertEqual("CLOSURE_DECLARED_NOT_VERIFIED", app(result, "CLAIMED"))
        self.assertFalse(next(s for s in result["probe_comparisons"]
                              if s["id"] == "CLAIMED")["prior_execution"]["status_verified"])
        codes = [c for f in result["probe_findings"] for c in f["codes"]]
        self.assertIn("EXECUTION_DECLARED_NOT_VERIFIED", codes)

    def test_history_under_another_premise_does_not_close_this_one(self):
        result = assess_proposal(packet([
            probe("OTHER", prior={"status": "COMPLETED_VALID", "run_ref": "EXP-002",
                                  "premise_id": "DIFFERENT_PREMISE"}),
            PRESS]))
        self.assertEqual([], eff(result)["historical_evidence_ids"])
        self.assertEqual("NOT_YET_RUN", app(result, "OTHER"))
        self.assertFalse(next(s for s in result["probe_comparisons"]
                             if s["id"] == "OTHER")["prior_execution"]["history_applicable"])
        self.assertIn("OTHER", eff(result)["frontier_candidate_ids_as_declared"])


class BackwardCompatibilityTests(unittest.TestCase):
    def test_a_packet_without_execution_fields_behaves_as_before(self):
        result = assess_proposal(packet([probe("SLOPE"), PRESS]))
        self.assertEqual(["SLOPE"], eff(result)["frontier_candidate_ids_as_declared"])
        self.assertEqual("NOT_YET_RUN", app(result, "SLOPE"))
        self.assertNotIn("prior_execution",
                         next(s for s in result["probe_comparisons"] if s["id"] == "SLOPE"))
        self.assertFalse(result["no_executable_next_probe"])

    def test_all_probes_closed_is_not_a_legality_failure(self):
        result = assess_proposal(packet([probe("SLOPE", prior=CLOSED)]))
        self.assertEqual([], eff(result)["frontier_candidate_ids_as_declared"])
        self.assertFalse(eff(result)["no_legal_decisive_probe"])
        self.assertTrue(eff(result)["no_executable_next_probe"])

    def test_invalid_status_and_unknown_fields_are_rejected(self):
        with self.assertRaises(AgentError):
            assess_proposal(packet([probe("X", prior={"status": "MAYBE_DONE"})]))
        with self.assertRaises(AgentError):
            assess_proposal(packet([probe("X", prior={"status": "COMPLETED_VALID",
                                                      "trust_me": "yes"})]))
