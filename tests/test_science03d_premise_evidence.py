"""SCIENCE-03D: two equal premise labels are not a bound premise.

`prior_execution.premise_id` and `proposed_premise.premise_id` are both written
by the caller. Until 0.9.12 their equality was treated as proof that the cited
Run tested this premise, so a real, status-consistent Run that executed a
*different* frozen plan still closed the probe: `HISTORICAL_EVIDENCE_ONLY`, out
of the frontier, `no_executable_next_probe` true -- and the experiment nobody
ran was never run.

What this file pins, one axis at a time:

* the Run's own record, or the premise of the plan it names, can contradict the
  packet -- and then the probe is a new experiment, not recorded evidence;
* a directory holding another Run's record is an identity conflict, not a
  closure and not a free rerun;
* a file with numbers but no identity is reported as such (`METRICS_ONLY`);
* a plan the record names but that cannot be read keeps the closure unverified
  instead of trusted;
* plan bytes that differ from the declared hash are a conflict;
* when nothing on disk speaks to the premise, the attribution is labelled
  `CALLER_DECLARATION` instead of being presented as evidence;
* old packets, old binders and packets without `prior_execution` are unchanged.
"""
import json
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.schemas import AgentError
from pdrw_agent.science.decision import assess_proposal
from pdrw_agent.science.feedback_link import bind_run_reference

PREDICTS = {"H_drift": "DECREASE", "H_compliance": "NO_CHANGE"}
SENSOR = "SENSOR_DRIFT_MECHANISM"
BEAM = "BEAM_STIFFNESS_MECHANISM"
LIVE = {"id": "LIVE", "observable": "subject-level MAE", "evaluation_unit": "SUBJECT",
        "comparison_reference": "same folds, load-cell-only arm",
        "predictions": dict(PREDICTS), "cost_band": "HIGH"}


def probe(ident, prior=None, cost="LOW"):
    entry = {"id": ident, "observable": "subject-level MAE", "evaluation_unit": "SUBJECT",
             "comparison_reference": "same folds, load-cell-only arm",
             "predictions": dict(PREDICTS), "cost_band": cost}
    if prior is not None:
        entry["prior_execution"] = prior
    return entry


def packet(probes, premise=SENSOR):
    return {"claim_type": "MECHANISM/CAUSAL",
            "question": "Is the residual drift, or beam compliance?",
            "hypotheses": ["H_drift", "H_compliance"],
            "proposed_premise": {"premise_id": premise,
                                 "scope": {"dataset": "PRESS DEV 26"}},
            "prechecks": {"group_independence": {"status": "PASS"}},
            "probes": probes}


def entry_of(result, ident):
    return next(s for s in result["probe_comparisons"] if s["id"] == ident)


def eff(result):
    return result["declared_probe_efficiency"]


class Project:
    """A throwaway project with two frozen plans and five Run directories."""

    def __init__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.beam = self.plan("PROTO-PRESS-BEAM-26", BEAM)
        self.sensor = self.plan("PROTO-PRESS-SENSOR-26", SENSOR)
        self.run("RUN-101", {"run_id": "RUN-101", "protocol_id": "PROTO-PRESS-BEAM-26",
                             "protocol_sha256": self.sha(self.beam), "status": "COMPLETED",
                             "verdict": "NEG_BEAM_STIFFNESS", "anchor_pass": True})
        # A second file in the same directory: identity, no status claim.
        Project.write(self.root / "DEV" / "runs" / "RUN-101" / "verification.json",
                      {"run_id": "RUN-101", "checks": {"anchor": "PASS", "folds": 12}})
        # Names a plan file that is not in this project: nothing to compare with.
        self.run("RUN-104", {"run_id": "RUN-104", "protocol_id": "PROTO-MISSING-26",
                             "status": "COMPLETED", "verdict": "NEG_X", "anchor_pass": True})
        # Declares a hash that is not the plan's bytes.
        self.run("RUN-105", {"run_id": "RUN-105", "protocol_id": "PROTO-PRESS-BEAM-26",
                             "protocol_sha256": "0" * 64, "status": "COMPLETED",
                             "verdict": "NEG_BEAM_STIFFNESS", "anchor_pass": True})
        # The record itself says which premise it tested.
        self.run("RUN-106", {"run_id": "RUN-106", "premise_id": SENSOR,
                             "status": "COMPLETED", "verdict": "POS_DRIFT",
                             "anchor_pass": True})
        # A copy whose record still claims to be RUN-101.
        self.run("RUN-102", {"run_id": "RUN-101", "protocol_id": "PROTO-PRESS-BEAM-26",
                             "protocol_sha256": self.sha(self.beam), "status": "COMPLETED",
                             "verdict": "NEG_BEAM_STIFFNESS", "anchor_pass": True})
        (self.root / "DEV" / "runs" / "RUN-103").mkdir(parents=True)
        self.write(self.root / "DEV" / "runs" / "RUN-103" / "metrics.json",
                   {"aggregate": {"base_mae": 9.17}, "note": "scratch copy"})

    def plan(self, protocol_id, premise_id):
        path = self.root / "protocol" / f"{protocol_id}.json"
        self.write(path, {"protocol_id": protocol_id, "premise_id": premise_id,
                          "frozen_before_fitting": True,
                          "primary_outcome": "subject-level MAE"})
        return path

    def run(self, name, payload):
        self.write(self.root / "DEV" / "runs" / name / "metrics.json", payload)

    @staticmethod
    def write(path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    @staticmethod
    def sha(path):
        import hashlib
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def close(self):
        self._tmp.cleanup()


class ContradictedPremiseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = Project()

    @classmethod
    def tearDownClass(cls):
        cls.project.close()

    def test_a_run_that_executed_another_plan_does_not_close_this_premise(self):
        result = assess_proposal(packet([
            probe("SENSOR", {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-101",
                             "premise_id": SENSOR}), LIVE]),
            project_root=self.project.root)
        entry = entry_of(result, "SENSOR")
        prior = entry["prior_execution"]
        self.assertEqual("NOT_YET_RUN", entry["applicability"])
        # Runnable, but the instruction is to settle which experiment the Run
        # answered -- not to spend the compute again.
        self.assertEqual("CONFIRM_WHICH_EXPERIMENT_THE_RUN_ANSWERED", entry["next_action"])
        finding = next(f for f in result["probe_findings"] if f["probe_id"] == "SENSOR")
        self.assertEqual(["DO_NOT_TREAT_AS_CLOSED_OR_AS_NEW"], finding["usage"])
        self.assertFalse(prior["status_verified"])
        self.assertFalse(prior["premise_verified"])
        self.assertTrue(prior["premise_contradicted"])
        self.assertEqual("MISMATCH", prior["premise_binding"])
        self.assertEqual("FROZEN_PLAN", prior["premise_binding_basis"])
        self.assertIn("CLOSURE_PREMISE_CONTRADICTED", entry["findings"])
        self.assertEqual([], eff(result)["historical_evidence_ids"])
        self.assertIn("SENSOR", eff(result)["premise_contradicted_ids"])
        self.assertIn("SENSOR", eff(result)["frontier_candidate_ids_as_declared"])

    def test_the_unanswered_experiment_is_not_reported_as_none_to_run(self):
        # The failure mode this round fixes: one probe, cited against a Run that
        # executed another premise, and the tool said there was nothing to run.
        result = assess_proposal(packet([
            probe("SENSOR", {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-101",
                             "premise_id": SENSOR})]),
            project_root=self.project.root)
        self.assertEqual(["SENSOR"], eff(result)["frontier_candidate_ids_as_declared"])
        self.assertFalse(result["no_executable_next_probe"])
        self.assertFalse(result["automatic_go"])
        self.assertEqual("ADVISORY_REVIEW_ONLY", result["status"])

    def test_a_premise_reference_to_another_plan_is_a_contradiction(self):
        result = assess_proposal(packet([
            probe("SENSOR", {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-101",
                             "premise_id": SENSOR,
                             "premise_ref": "protocol/PROTO-PRESS-SENSOR-26.json"})]),
            project_root=self.project.root)
        prior = entry_of(result, "SENSOR")["prior_execution"]
        self.assertIs(False, prior["run_binding"]["premise_plan_match"])
        self.assertEqual("PREMISE_PLAN", prior["premise_binding_basis"])
        self.assertEqual("NOT_YET_RUN", entry_of(result, "SENSOR")["applicability"])

    def test_a_premise_reference_matching_the_run_plan_keeps_the_evidence(self):
        result = assess_proposal(packet([
            probe("BEAM", {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-101",
                           "premise_id": BEAM,
                           "premise_ref": "protocol/PROTO-PRESS-BEAM-26.json"})], premise=BEAM),
            project_root=self.project.root)
        prior = entry_of(result, "BEAM")["prior_execution"]
        self.assertIs(True, prior["run_binding"]["premise_plan_match"])
        self.assertTrue(prior["premise_verified"])
        self.assertTrue(prior["status_verified"])
        self.assertEqual("HISTORICAL_EVIDENCE_ONLY", entry_of(result, "BEAM")["applicability"])
        self.assertIn("BEAM", eff(result)["historical_evidence_ids"])

    def test_a_record_level_premise_that_agrees_is_verified_history(self):
        result = assess_proposal(packet([
            probe("DRIFT", {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-106",
                            "premise_id": SENSOR})]),
            project_root=self.project.root)
        prior = entry_of(result, "DRIFT")["prior_execution"]
        self.assertEqual("RUN_RECORD", prior["premise_binding_basis"])
        self.assertTrue(prior["premise_verified"])
        self.assertEqual("HISTORICAL_EVIDENCE_ONLY", entry_of(result, "DRIFT")["applicability"])

    def test_a_record_level_premise_that_disagrees_is_not_history(self):
        result = assess_proposal(packet([
            probe("DRIFT", {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-106",
                            "premise_id": BEAM})], premise=BEAM),
            project_root=self.project.root)
        prior = entry_of(result, "DRIFT")["prior_execution"]
        self.assertTrue(prior["premise_contradicted"])
        self.assertEqual("RUN_RECORD", prior["premise_binding_basis"])
        self.assertEqual("NOT_YET_RUN", entry_of(result, "DRIFT")["applicability"])
        self.assertEqual([], eff(result)["historical_evidence_ids"])


class IdentityAndStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = Project()

    @classmethod
    def tearDownClass(cls):
        cls.project.close()

    def test_a_directory_holding_another_runs_record_is_a_conflict(self):
        result = assess_proposal(packet([
            probe("COPIED", {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-102",
                             "premise_id": SENSOR})]),
            project_root=self.project.root)
        entry = entry_of(result, "COPIED")
        prior = entry["prior_execution"]
        self.assertEqual("MISMATCH", prior["run_binding"]["run_id_consistency"])
        self.assertEqual("CONFLICT", prior["status_consistency"])
        self.assertEqual("STATUS_CONFLICT", entry["applicability"])
        self.assertFalse(prior["status_verified"])
        self.assertEqual(["COPIED"], eff(result)["status_conflict_ids"])
        # A conflict is not a licence to rerun either.
        self.assertNotIn("COPIED", eff(result)["frontier_candidate_ids_as_declared"])

    def test_numbers_without_identity_are_reported_as_metrics_only(self):
        result = assess_proposal(packet([
            probe("SCRATCH", {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-103",
                              "premise_id": SENSOR})]),
            project_root=self.project.root)
        prior = entry_of(result, "SCRATCH")["prior_execution"]
        self.assertEqual("METRICS_ONLY", prior["run_binding"]["record_structure"])
        self.assertEqual("CLOSURE_DECLARED_NOT_VERIFIED", entry_of(result, "SCRATCH")["applicability"])
        self.assertFalse(prior["status_verified"])

    def test_a_plan_that_cannot_be_read_keeps_the_closure_unverified(self):
        result = assess_proposal(packet([
            probe("LOST", {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-104",
                           "premise_id": SENSOR})]),
            project_root=self.project.root)
        prior = entry_of(result, "LOST")["prior_execution"]
        self.assertEqual("UNRESOLVED", prior["run_binding"]["plan"]["plan_status"])
        self.assertTrue(prior["plan_unresolved"])
        self.assertFalse(prior["status_verified"])
        self.assertIn("CLOSURE_PLAN_UNRESOLVED", entry_of(result, "LOST")["findings"])
        self.assertEqual([], eff(result)["historical_evidence_ids"])

    def test_plan_bytes_that_differ_from_the_declared_hash_are_a_conflict(self):
        result = assess_proposal(packet([
            probe("HASHED", {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-105",
                             "premise_id": BEAM})], premise=BEAM),
            project_root=self.project.root)
        prior = entry_of(result, "HASHED")["prior_execution"]
        self.assertIs(False, prior["run_binding"]["plan"]["hash_match"])
        self.assertEqual("CONFLICT", prior["status_consistency"])
        self.assertEqual("STATUS_CONFLICT", entry_of(result, "HASHED")["applicability"])

    def test_record_ref_selects_the_record_file(self):
        # `record_ref` was accepted but never passed to the binder before 0.9.12.
        default = bind_run_reference(self.project.root, "DEV/runs/RUN-101")
        explicit = bind_run_reference(self.project.root, "DEV/runs/RUN-101",
                                      run_record_ref="verification.json")
        self.assertTrue(default["record_ref"].endswith("metrics.json"))
        self.assertTrue(explicit["record_ref"].endswith("verification.json"))
        self.assertEqual("RUN_RECORD", default["record_structure"])
        # The verification file states no execution status: reading it cannot
        # close anything, and saying RUN_RECORD here would be an overclaim.
        self.assertEqual("METRICS_ONLY", explicit["record_structure"])
        self.assertEqual("MATCH", default["run_id_consistency"])
        self.assertFalse(default["artifact_links_verified"])

    def test_a_sealed_plan_reference_is_never_read(self):
        (self.project.root / "protocol" / "sealed").mkdir(parents=True, exist_ok=True)
        Project.write(self.project.root / "protocol" / "sealed" / "P.json",
                      {"protocol_id": "P", "premise_id": SENSOR})
        receipt = bind_run_reference(self.project.root, "DEV/runs/RUN-101",
                                     premise_ref="protocol/sealed/P.json")
        self.assertNotEqual("BOUND", (receipt.get("premise_plan") or {}).get("plan_status"))


class DeclaredOnlyTests(unittest.TestCase):
    """Nothing on disk speaks to the premise: say so instead of dressing it up."""

    def test_two_equal_labels_are_reported_as_a_caller_declaration(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp, "DEV", "runs", "RUN-9")
            run.mkdir(parents=True)
            (run / "metrics.json").write_text(json.dumps(
                {"run_id": "RUN-9", "status": "COMPLETED", "verdict": "NEG",
                 "anchor_pass": True}), encoding="utf-8")
            result = assess_proposal(packet([
                probe("BARE", {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-9",
                               "premise_id": SENSOR})]), project_root=tmp)
        prior = entry_of(result, "BARE")["prior_execution"]
        self.assertEqual("CALLER_DECLARATION", prior["premise_binding_basis"])
        self.assertEqual("NONE", prior["premise_evidence"])
        self.assertFalse(prior["premise_verified"])
        # Unchanged recommendation: a bound, consistent Run is recorded evidence
        # even when only the caller names the premise -- but it is no longer
        # presentable as a verified premise match.
        self.assertEqual("HISTORICAL_EVIDENCE_ONLY", entry_of(result, "BARE")["applicability"])
        self.assertEqual([], eff(result)["premise_contradicted_ids"])


class CompatibilityTests(unittest.TestCase):
    def test_a_binder_with_the_old_signature_still_works(self):
        calls = []

        def binder(ref):
            calls.append(ref)
            return {"status": "RUN_RECORD_BOUND", "run_status_declared": "COMPLETED",
                    "anchor_pass_declared": True}

        result = assess_proposal(packet([
            probe("OLD", {"status": "COMPLETED_VALID", "run_ref": "x", "premise_id": SENSOR})]),
            run_binder=binder)
        self.assertEqual(["x"], calls)
        self.assertTrue(entry_of(result, "OLD")["prior_execution"]["status_verified"])

    def test_an_unknown_execution_field_is_still_rejected(self):
        with self.assertRaises(AgentError):
            assess_proposal(packet([
                probe("X", {"status": "COMPLETED_VALID", "run_ref": "x",
                            "premise_guess": "SENSOR"})]))

    def test_a_packet_without_execution_fields_is_unchanged(self):
        result = assess_proposal(packet([probe("A", cost="HIGH"), probe("B", cost="LOW")]))
        self.assertEqual(["B"], eff(result)["frontier_candidate_ids_as_declared"])
        self.assertNotIn("prior_execution", entry_of(result, "A"))
        self.assertEqual([], eff(result)["premise_contradicted_ids"])


if __name__ == "__main__":
    unittest.main()
