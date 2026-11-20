"""SCIENCE-03C: a non-empty `run_ref` is not a verified closure.

Before this round `status_verified` was `status != NOT_EXECUTED and bool(run_ref)`,
so a Run that does not exist, a Run belonging to another project and a Run whose
own record says INVALID all read as verified evidence that the premise was
already answered. A closure with no `premise_id` was also accepted, which let it
remove a live candidate from the frontier.

What this file pins, one axis at a time:

* reference present != file bound != status consistent != same premise !=
  trustworthy closure;
* a missing directory, an escaping path, a directory with no record and a
  contradicting record stay four different answers;
* a sealed/holdout path is never read to "verify" anything;
* an unbound premise neither closes the probe nor eliminates a live one;
* a declared authorization boolean is a caller statement, not a permit;
* packets without `prior_execution` behave exactly as before.
"""
import json
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.schemas import AgentError
from pdrw_agent.science.decision import assess_proposal
from pdrw_agent.science.feedback_link import bind_run_reference

PREDICTS = {"H_deployable": "DECREASE", "H_prior_only": "NO_CHANGE"}
PREMISE = "POPU_LOWER72"

LIVE = {"id": "LIVE", "observable": "cross-library ranking", "evaluation_unit": "SUBJECT",
        "comparison_reference": "same protocol, second library",
        "predictions": dict(PREDICTS), "cost_band": "HIGH"}


def probe(ident, prior=None, cost="HIGH"):
    entry = {"id": ident, "observable": "intensity MAE under the same folds",
             "evaluation_unit": "SUBJECT",
             "comparison_reference": "same protocol, same folds",
             "predictions": dict(PREDICTS), "cost_band": cost}
    if prior is not None:
        entry["prior_execution"] = prior
    return entry


def packet(probes):
    return {"claim_type": "MECHANISM/CAUSAL",
            "question": "Is there a deployable increment beyond the prior?",
            "hypotheses": ["H_deployable", "H_prior_only"],
            "proposed_premise": {"premise_id": PREMISE,
                                 "scope": {"dataset": "PoPu DEV 12", "input": "lower 72"}},
            "prechecks": {"group_independence": {"status": "PASS"}},
            "probes": probes}


def entry_of(result, ident):
    return next(s for s in result["probe_comparisons"] if s["id"] == ident)


def eff(result):
    return result["declared_probe_efficiency"]


class ProjectRoot:
    """A throwaway project with four kinds of Run directory."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.write("runs/RUN-OK", {"run_id": "RUN-OK", "status": "COMPLETED",
                                   "verdict": "POS_INCREMENT", "anchor_pass": True})
        self.write("runs/RUN-BAD", {"run_id": "RUN-BAD",
                                    "status": "INVALID_HARNESS_TRAINING_SET",
                                    "anchor_pass": False})
        self.write("runs/RUN-INCON", {"run_id": "RUN-INCON", "status": "INCONCLUSIVE"})
        self.write("runs/DECLARED-VALID", {"run_id": "DECLARED-VALID",
                                           "status": "COMPLETED", "verdict": "NEG_X",
                                           "anchor_pass": True})
        (self.root / "runs" / "EMPTY").mkdir(parents=True)
        (self.root / "runs" / "sealed").mkdir(parents=True)
        self.write("runs/sealed/RUN-1", {"run_id": "RUN-1", "status": "COMPLETED"})

    def write(self, rel, obj):
        path = self.root / rel / "metrics.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj), encoding="utf-8")

    def close(self):
        self._tmp.cleanup()


class BindingAxisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = ProjectRoot()

    @classmethod
    def tearDownClass(cls):
        cls.project.close()

    def test_a_nonempty_reference_is_not_a_verified_run(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID", "run_ref": "runs/RUN-OK",
                          "premise_id": PREMISE}), LIVE]))
        prior = entry_of(result, "RAN")["prior_execution"]
        self.assertFalse(prior["status_verified"])
        self.assertFalse(prior["binding_checked"])
        self.assertEqual("NOT_CHECKED", prior["file_binding"])
        self.assertEqual("CLOSURE_DECLARED_NOT_VERIFIED", entry_of(result, "RAN")["applicability"])
        self.assertFalse(result["run_binding_checked"])
        self.assertEqual("NO_PROJECT_ROOT_SUPPLIED", result["run_binding_scope"])

    def test_a_missing_run_directory_stays_unresolved(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID", "run_ref": "runs/NOPE",
                          "premise_id": PREMISE}), LIVE]), project_root=self.project.root)
        prior = entry_of(result, "RAN")["prior_execution"]
        self.assertEqual("UNRESOLVED", prior["file_binding"])
        self.assertEqual("RUN_REF_MISSING", prior["run_binding"]["status"])
        self.assertFalse(prior["status_verified"])

    def test_a_reference_outside_the_project_is_not_bound(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID",
                          "run_ref": "../../MCS-HEMO-26/research",
                          "premise_id": PREMISE}), LIVE]), project_root=self.project.root)
        prior = entry_of(result, "RAN")["prior_execution"]
        self.assertEqual("UNRESOLVED", prior["file_binding"])
        self.assertEqual("RUN_REF_REJECTED", prior["run_binding"]["status"])
        self.assertFalse(prior["status_verified"])

    def test_a_sealed_reference_is_never_read(self):
        receipt = bind_run_reference(self.project.root, "runs/sealed/RUN-1")
        self.assertEqual("RUN_REF_REJECTED", receipt["status"])
        self.assertNotIn("record_sha256", receipt)

    def test_a_directory_without_a_run_record_is_not_a_closure(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID", "run_ref": "runs/EMPTY",
                          "premise_id": PREMISE}), LIVE]), project_root=self.project.root)
        prior = entry_of(result, "RAN")["prior_execution"]
        self.assertEqual("RUN_RECORD_ABSENT", prior["run_binding"]["status"])
        self.assertFalse(prior["status_verified"])
        self.assertEqual("CLOSURE_DECLARED_NOT_VERIFIED", entry_of(result, "RAN")["applicability"])

    def test_a_record_that_contradicts_the_declaration_is_a_conflict(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID", "run_ref": "runs/RUN-BAD",
                          "premise_id": PREMISE}), LIVE]), project_root=self.project.root)
        prior = entry_of(result, "RAN")["prior_execution"]
        self.assertEqual("BOUND", prior["file_binding"])
        self.assertEqual("CONFLICT", prior["status_consistency"])
        self.assertFalse(prior["status_verified"])
        self.assertEqual("STATUS_CONFLICT", entry_of(result, "RAN")["applicability"])
        self.assertIn("RAN", eff(result)["status_conflict_ids"])
        codes = [c for f in result["probe_findings"] for c in f["codes"]]
        self.assertIn("EXECUTION_STATUS_CONFLICT", codes)

    def test_an_invalid_run_declared_valid_does_not_become_history(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID", "run_ref": "runs/RUN-BAD",
                          "premise_id": PREMISE}), LIVE]), project_root=self.project.root)
        self.assertEqual([], eff(result)["historical_evidence_ids"])
        self.assertIn("LIVE", eff(result)["frontier_candidate_ids_as_declared"])

    def test_a_bound_consistent_run_under_this_premise_is_recorded_evidence(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID", "run_ref": "runs/RUN-OK",
                          "premise_id": PREMISE}), LIVE]), project_root=self.project.root)
        prior = entry_of(result, "RAN")["prior_execution"]
        # The record runs and says COMPLETED, and the caller's premise label
        # matches its own -- but no file states the premise, so this is execution
        # evidence with a declared premise link (0.9.13 draws that line).
        self.assertTrue(prior["execution_verified"])
        self.assertFalse(prior["premise_verified"])
        self.assertEqual("CALLER_DECLARATION", prior["premise_binding_basis"])
        self.assertEqual("BOUND", prior["file_binding"])
        self.assertEqual("CONSISTENT", prior["status_consistency"])
        self.assertEqual("MATCH", prior["premise_binding"])
        self.assertEqual("HISTORICAL_EVIDENCE_PREMISE_ASSUMED",
                         entry_of(result, "RAN")["applicability"])
        self.assertIn("RAN", eff(result)["historical_evidence_ids"])
        self.assertNotIn("RAN", eff(result)["frontier_candidate_ids_as_declared"])

    def test_an_invalid_declaration_matching_an_invalid_record_is_a_repair(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_INVALID", "run_ref": "runs/RUN-BAD",
                          "premise_id": PREMISE}), LIVE]), project_root=self.project.root)
        self.assertEqual("TARGETED_REPAIR", entry_of(result, "RAN")["applicability"])
        self.assertFalse(entry_of(result, "RAN")["prior_execution"]["status_verified"])

    def test_an_inconclusive_record_waits_for_new_information(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "INCONCLUSIVE", "run_ref": "runs/RUN-INCON",
                          "premise_id": PREMISE}), LIVE]), project_root=self.project.root)
        self.assertEqual("AWAIT_NEW_INFORMATION", entry_of(result, "RAN")["applicability"])
        self.assertIn("RAN", eff(result)["awaiting_new_information_ids"])


class PremiseBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = ProjectRoot()

    @classmethod
    def tearDownClass(cls):
        cls.project.close()

    def test_an_unbound_premise_does_not_close_anything(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID", "run_ref": "runs/RUN-OK"}),
            LIVE]), project_root=self.project.root)
        prior = entry_of(result, "RAN")["prior_execution"]
        self.assertEqual("UNBOUND", prior["premise_binding"])
        self.assertIsNone(prior["premise_match"])
        self.assertFalse(prior["history_applicable"])
        self.assertFalse(prior["status_verified"])
        self.assertEqual("CLOSURE_PREMISE_UNBOUND", entry_of(result, "RAN")["applicability"])
        self.assertEqual("BIND_PREMISE_ID_BEFORE_TREATING_AS_CLOSED",
                         entry_of(result, "RAN")["next_action"])
        self.assertEqual([], eff(result)["historical_evidence_ids"])
        self.assertIn("RAN", eff(result)["premise_unbound_ids"])
        self.assertNotIn("RAN", eff(result)["unverified_closure_ids"])

    def test_an_unbound_premise_cannot_eliminate_a_live_probe(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID", "run_ref": "runs/RUN-OK"}, cost="LOW"),
            LIVE]), project_root=self.project.root)
        self.assertEqual(["LIVE"], eff(result)["frontier_candidate_ids_as_declared"])
        self.assertNotIn("RAN", [d["id"] for d in eff(result)["dominated_candidates_as_declared"]])
        self.assertIn("CLOSURE_PREMISE_UNBOUND",
                      [c for f in result["probe_findings"] if f["probe_id"] == "RAN"
                       for c in f["codes"]])

    def test_history_under_another_premise_stays_a_live_candidate(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID", "run_ref": "runs/RUN-OK",
                          "premise_id": "SOMETHING_ELSE"}), LIVE]),
            project_root=self.project.root)
        self.assertEqual("NOT_YET_RUN", entry_of(result, "RAN")["applicability"])
        self.assertIn("RAN", eff(result)["frontier_candidate_ids_as_declared"])
        self.assertEqual([], eff(result)["historical_evidence_ids"])

    def test_a_premise_bound_but_unbound_run_is_not_history(self):
        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID", "run_ref": "runs/NOPE",
                          "premise_id": PREMISE}), LIVE]),
            project_root=self.project.root)
        self.assertEqual("CLOSURE_DECLARED_NOT_VERIFIED", entry_of(result, "RAN")["applicability"])
        self.assertEqual([], eff(result)["historical_evidence_ids"])


class AuthorizationAndCompatibilityTests(unittest.TestCase):
    def test_a_declared_authorization_is_not_a_permit(self):
        result = assess_proposal(packet([
            probe("FRESH", {"status": "NOT_EXECUTED", "requires_new_authorization": False})]))
        prior = entry_of(result, "FRESH")["prior_execution"]
        self.assertEqual("CALLER_DECLARED_ONLY", prior["authorization_basis"])
        self.assertEqual("CALLER_DECLARED_ONLY_NEVER_A_PERMIT", result["authorization_basis"])
        self.assertEqual("RUN_IF_LEGAL_AND_DISCRIMINATING", entry_of(result, "FRESH")["next_action"])
        # The packet cannot grant an execution permit, and this tool never claims one.
        self.assertFalse(result["automatic_go"])

    def test_packets_without_execution_fields_are_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "runs").mkdir()
            result = assess_proposal(packet([probe("A"), probe("B", cost="LOW")]), project_root=tmp)
        # Same pair set, so the cheaper one dominates exactly as in 0.9.10.
        self.assertEqual(["B"], eff(result)["frontier_candidate_ids_as_declared"])
        self.assertEqual(["A"], [d["id"] for d in eff(result)["dominated_candidates_as_declared"]])
        self.assertNotIn("prior_execution", entry_of(result, "A"))
        self.assertFalse(result["no_executable_next_probe"])

    def test_a_failing_binder_degrades_to_unknown_not_verified(self):
        def binder(_ref):
            raise AgentError("RUN_ID_INVALID", "boom")

        result = assess_proposal(packet([
            probe("RAN", {"status": "COMPLETED_VALID", "run_ref": "whatever",
                          "premise_id": PREMISE})]), run_binder=binder)
        prior = entry_of(result, "RAN")["prior_execution"]
        self.assertEqual("BINDING_ERROR", prior["run_binding"]["status"])
        self.assertFalse(prior["status_verified"])

    def test_an_unknown_execution_status_is_still_rejected(self):
        with self.assertRaises(AgentError):
            assess_proposal(packet([probe("X", {"status": "PROBABLY_DONE"})]))


if __name__ == "__main__":
    unittest.main()


class ReferenceWordingTests(unittest.TestCase):
    """A diagnostic arm named in the reference is not an illegal comparison.

    Found on a real replay: the reference "oracle upper bound and deployable
    arm, same folds" was flagged `REFERENCE_NOT_LEGAL`, and `no_legal_decisive_probe`
    became true for a probe whose deciding comparison is the deployable arm.
    """

    def _result(self, reference):
        return assess_proposal(packet([
            {"id": "P", "observable": "subject AUC of predicted error",
             "evaluation_unit": "SUBJECT", "comparison_reference": reference,
             "predictions": dict(PREDICTS), "cost_band": "MEDIUM"}]))

    def test_a_named_diagnostic_upper_bound_is_not_the_comparison(self):
        result = self._result("oracle upper bound and deployable arm, same folds")
        codes = [c for f in result["probe_findings"] for c in f["codes"]]
        self.assertNotIn("REFERENCE_NOT_LEGAL", codes)
        self.assertEqual([], eff(result)["diagnostic_upper_bound_ids"])
        self.assertFalse(result["no_legal_decisive_probe"])
        self.assertIn("P", eff(result)["frontier_candidate_ids_as_declared"])

    def test_an_oracle_used_as_the_reference_is_still_illegal(self):
        result = self._result("oracle labels at test time")
        self.assertEqual(["P"], eff(result)["diagnostic_upper_bound_ids"])
        self.assertTrue(result["no_legal_decisive_probe"])

    def test_test_time_truth_is_still_illegal(self):
        result = self._result("test-time truth from the sealed labels")
        self.assertEqual(["P"], eff(result)["diagnostic_upper_bound_ids"])
