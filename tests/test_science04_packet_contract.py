"""SCIENCE-04: the packet contract has to be usable from the error message.

Four independent sessions in SCIENCE-03D wrote four packets and all four were
rejected on shape. The rejections were the barrier: one defect per call, and a
message that named the wrong thing ("Unexpected precheck names" for a
`prechecks` *list*). This file pins the three repairs, and the one scientific
consequence they exposed:

* every violation is reported at once, with a path, the value found and what the
  field accepts;
* fields the decision path silently ignores are reported as ignored, so a packet
  cannot believe its execution history was read;
* normalization moves only shapes that are a bijection of the input -- never a
  prediction, a premise, an evidence reference or an authorization;
* `status_verified` can no longer be true while `premise_verified` is false: a
  Run that ran and a premise that is settled are two different claims.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pdrw_agent.science.cli import main as cli_main
from pdrw_agent.science.decision import assess_proposal
from pdrw_agent.science.packet_schema import (
    check_packet, normalize_packet, template,
)

PREDICTS = {"H_drift": "DECREASE", "H_compliance": "NO_CHANGE"}
SENSOR = "SENSOR_DRIFT_MECHANISM"


def probe(ident="P1", **overrides):
    entry = {"id": ident, "observable": "subject-level MAE", "evaluation_unit": "SUBJECT",
             "comparison_reference": "same folds, load-cell arm",
             "predictions": dict(PREDICTS), "cost_band": "LOW"}
    entry.update(overrides)
    return entry


def packet(probes=None, **overrides):
    body = {"claim_type": "MECHANISM/CAUSAL",
            "question": "Is the residual drift, or beam compliance?",
            "hypotheses": ["H_drift", "H_compliance"],
            "proposed_premise": {"premise_id": SENSOR,
                                 "scope": {"dataset": "PRESS DEV 26"}},
            "prechecks": {"group_independence": {"status": "PASS"}},
            "probes": probes or [probe()]}
    body.update(overrides)
    return body


def paths(result):
    return [item["path"] for item in result["violations"]]


class TemplateTests(unittest.TestCase):
    def test_the_template_is_accepted_by_the_shape_check(self):
        self.assertEqual("SHAPE_OK", check_packet(template())["status"])

    def test_the_template_is_accepted_by_the_decision_path(self):
        # A template that only passes its own checker would be a lie.
        result = assess_proposal(template())
        self.assertEqual("ADVISORY_REVIEW_ONLY", result["status"])

    def test_the_template_names_no_science(self):
        body = template()
        self.assertEqual(["H1_PRIMARY", "H2_COMPETING"], body["hypotheses"])
        self.assertEqual("PREMISE_ID", body["proposed_premise"]["premise_id"])
        # No evidence, no authorization, no run reference is pre-filled.
        self.assertNotIn("prior_execution", body["probes"][0])
        self.assertEqual([], body["prechecks"]["group_independence"]["evidence_refs"])


class AllViolationsAtOnceTests(unittest.TestCase):
    def test_a_list_shaped_prechecks_block_is_named_as_such(self):
        result = check_packet(packet(prechecks=[
            {"id": "group_independence", "status": "PASS"},
            {"id": "legal_inputs", "status": "UNKNOWN"}]))
        self.assertEqual("SHAPE_VIOLATIONS", result["status"])
        self.assertEqual(["prechecks"], paths(result))
        violation = result["violations"][0]
        self.assertIn("list", violation["problem"])
        # The hint has to be followable: it shows the mapping keyed by the ids
        # the caller already wrote.
        self.assertIn("group_independence", violation["hint"])

    def test_four_defects_come_back_in_one_call(self):
        result = check_packet(packet(
            probes=[probe("P1", cost_band="HIGHISH",
                          predictions={"H_drift": "DECREASES", "H_compliance": "NO_CHANGE"},
                          evaluation_unit="subject (12-fold LOSO)")],
            claim_type="DEPLOYABLE_INCREMENT"))
        self.assertEqual(3, len(result["violations"]))  # claim_type, cost_band, prediction
        self.assertEqual(["claim_type", "probes[0].cost_band", "probes[0].predictions.H_drift"],
                         paths(result))
        self.assertEqual(["probes[0].evaluation_unit"], [w["path"] for w in result["warnings"]])

    def test_every_violation_carries_a_path_and_an_accepted_shape(self):
        result = check_packet(packet(probes=[probe(predictions={"H_drift": "MAYBE"})],
                                     hypotheses=["H_drift"]))
        for item in result["violations"]:
            self.assertTrue(item["path"])
            self.assertTrue(item["accepted"])
        self.assertIn("hypotheses", paths(result))

    def test_a_misspelled_check_name_suggests_the_real_one(self):
        result = check_packet(packet(prechecks={"group_independance": {"status": "PASS"}}))
        violation = result["violations"][0]
        self.assertIn("group_independance", violation["problem"])
        self.assertIn("group_independence", violation["hint"])

    def test_an_invented_claim_type_says_what_the_field_is_for(self):
        result = check_packet(packet(claim_type="DEPLOYABLE_INCREMENT"))
        violation = result["violations"][0]
        self.assertEqual("claim_type", violation["path"])
        self.assertIn("type", violation["hint"])

    def test_a_scope_string_is_refused_with_the_keys_to_use(self):
        result = check_packet(packet(proposed_premise={"premise_id": SENSOR,
                                                       "scope": "PoPu DEV, 12 subjects, LOSO"}))
        violation = result["violations"][0]
        self.assertEqual("proposed_premise.scope", violation["path"])
        self.assertIn("mapping", violation["problem"])
        self.assertIn("dataset", violation["hint"])

    def test_a_long_scope_value_names_which_key(self):
        long_text = "x" * 200
        result = check_packet(packet(proposed_premise={
            "premise_id": SENSOR, "scope": {"dataset": long_text}}))
        self.assertEqual(["proposed_premise.scope.dataset"], paths(result))
        self.assertIn("200", result["violations"][0]["problem"])


class IgnoredFieldTests(unittest.TestCase):
    def test_an_unknown_probe_field_is_reported_as_ignored_not_rejected(self):
        result = check_packet(packet(probes=[probe(notes="see the report")]))
        self.assertEqual("SHAPE_OK", result["status"])
        self.assertEqual(["probes[0].notes"], [g["path"] for g in result["ignored_fields"]])

    def test_execution_fields_at_the_top_level_are_a_violation_not_a_note(self):
        result = check_packet(packet(status="COMPLETED_VALID", run_ref="DEV/runs/RUN-005"))
        self.assertEqual(["run_ref", "status"], paths(result))
        self.assertIn("inside probes[i].prior_execution",
                      result["violations"][0]["accepted"])

    def test_a_cli_envelope_is_named_instead_of_parsed(self):
        envelope = {"status": "TEMPLATE", "packet": packet(), "note": "..."}
        result = check_packet(envelope)
        self.assertIn("$", paths(result))
        self.assertIn("envelope", result["violations"][0]["problem"])
        # It does not unwrap it either: guessing which envelope keys are output
        # and which are declared is the kind of inference that produced four
        # silently mis-read packets. The envelope is judged as the packet.
        self.assertIn("hypotheses", paths(result))


class NormalizationTests(unittest.TestCase):
    def test_a_prechecks_list_becomes_a_mapping_and_keeps_its_notes(self):
        original = packet(prechecks=[
            {"id": "group_independence", "status": "PASS", "note": "12 folds on 12 subjects"},
            {"id": "legal_inputs", "status": "UNKNOWN"}])
        result = normalize_packet(original)
        self.assertEqual(["prechecks"], [c["path"] for c in result["changes"]])
        self.assertEqual({"group_independence": {"status": "PASS",
                                                 "note": "12 folds on 12 subjects"},
                          "legal_inputs": {"status": "UNKNOWN"}},
                         result["packet"]["prechecks"])
        # The input object is untouched: normalization never edits in place.
        self.assertIsInstance(original["prechecks"], list)
        self.assertEqual("SHAPE_OK", check_packet(result["packet"])["status"])

    def test_predictions_written_as_pairs_become_a_mapping(self):
        result = normalize_packet(packet(probes=[probe(predictions=[
            {"hypothesis": "H_drift", "outcome": "DECREASE"},
            {"hypothesis": "H_compliance", "outcome": "NO_CHANGE"}])]))
        self.assertEqual({"H_drift": "DECREASE", "H_compliance": "NO_CHANGE"},
                         result["packet"]["probes"][0]["predictions"])
        self.assertEqual("SHAPE_OK", check_packet(result["packet"])["status"])

    def test_a_prediction_with_an_unknown_direction_is_refused_not_guessed(self):
        result = normalize_packet(packet(probes=[probe(predictions=[
            {"hypothesis": "H_drift", "outcome": "GOES DOWN"}])]))
        self.assertEqual([], result["changes"])
        self.assertEqual("probes[0].predictions", result["refused"][0]["path"])
        self.assertIn("INCREASE", result["refused"][0]["hint"])

    def test_a_prose_scope_is_refused_because_splitting_it_is_a_choice(self):
        result = normalize_packet(packet(proposed_premise={
            "premise_id": SENSOR, "scope": "PoPu DEV, 12 subjects, LOSO, top-1% target"}))
        self.assertEqual("proposed_premise.scope", result["refused"][0]["path"])
        self.assertEqual("PoPu DEV, 12 subjects, LOSO, top-1% target",
                         result["packet"]["proposed_premise"]["scope"])

    def test_hoisted_execution_fields_are_refused_because_the_probe_is_ambiguous(self):
        original = packet(status="COMPLETED_VALID", run_ref="DEV/runs/RUN-005")
        result = normalize_packet(original)
        self.assertEqual("run_ref, status", result["refused"][0]["path"])
        self.assertEqual("COMPLETED_VALID", result["packet"]["status"])
        # The top-level value is not copied into a probe: which probe it belongs
        # to cannot be inferred, and inventing that would invent an experiment.
        self.assertNotIn("prior_execution", result["packet"]["probes"][0])

    def test_normalization_on_a_clean_packet_changes_nothing(self):
        result = normalize_packet(packet())
        self.assertEqual([], result["changes"])
        self.assertEqual([], result["refused"])
        self.assertEqual(packet(), result["packet"])


class UnitTokenTests(unittest.TestCase):
    def test_a_prose_unit_is_a_warning_and_the_independence_check_goes_quiet(self):
        prose = "subject（12 折 LOSO，每折留出 1 名受试者）"
        shape = check_packet(packet(probes=[probe(evaluation_unit=prose)]))
        self.assertEqual("SHAPE_OK", shape["status"])
        self.assertEqual("probes[0].evaluation_unit", shape["warnings"][0]["path"])
        # The consequence, stated as a fact rather than a style objection: with
        # group independence declared PASS and a window unit spelled as a
        # sentence, the CASE-11 conflict is not detected.
        as_token = assess_proposal(packet(probes=[probe(evaluation_unit="WINDOW")]))
        as_prose = assess_proposal(packet(probes=[probe(evaluation_unit=prose)]))
        self.assertEqual(["PROBE_UNIT_NOT_INDEPENDENT"],
                         [f["codes"][0] for f in as_token["probe_findings"]])
        self.assertEqual([], as_prose["probe_findings"])


class VerifiedMeansVerifiedTests(unittest.TestCase):
    """`status_verified` may not outrun `premise_verified` (the 0.9.13 line),
    and evidence may not outrun attribution (the 0.9.14 line)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        run = self.root / "DEV" / "runs" / "RUN-9"
        run.mkdir(parents=True)
        (run / "metrics.json").write_text(json.dumps(
            {"run_id": "RUN-9", "status": "COMPLETED", "verdict": "NEG",
             "anchor_pass": True, "protocol_id": "P-POPU"}), encoding="utf-8")
        plan = self.root / "protocol" / "P-POPU.json"
        plan.parent.mkdir(parents=True)
        plan.write_text(json.dumps({"protocol_id": "P-POPU",
                                    "frozen_before_fitting": True}), encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_a_run_that_ran_with_a_declared_premise_is_not_yet_evidence(self):
        body = packet(probes=[probe("BARE", prior_execution={
            "status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-9",
            "premise_id": SENSOR})])
        result = assess_proposal(body, project_root=self.root)
        prior = result["probe_comparisons"][0]["prior_execution"]
        self.assertTrue(prior["execution_verified"])
        self.assertFalse(prior["premise_verified"])
        self.assertFalse(prior["status_verified"])
        self.assertFalse(prior["attribution_verified"])
        self.assertEqual("CALLER_DECLARATION", prior["premise_binding_basis"])
        self.assertEqual("CLOSURE_ATTRIBUTION_UNCHECKED",
                         result["probe_comparisons"][0]["applicability"])
        self.assertNotIn("BARE",
                         result["declared_probe_efficiency"]["frontier_candidate_ids_as_declared"])
        self.assertEqual(["BARE"],
                         result["declared_probe_efficiency"]["attribution_unchecked_ids"])
        self.assertEqual([],
                         result["declared_probe_efficiency"]["historical_evidence_ids"])

    def test_naming_the_plan_the_run_executed_makes_it_citable_evidence(self):
        body = packet(probes=[probe("BARE", prior_execution={
            "status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-9",
            "premise_ref": "protocol/P-POPU.json", "premise_id": SENSOR})])
        result = assess_proposal(body, project_root=self.root)
        prior = result["probe_comparisons"][0]["prior_execution"]
        self.assertTrue(prior["attribution_verified"])
        self.assertEqual("CALLER_PREMISE_PLAN", prior["attribution_basis"])
        self.assertFalse(prior["premise_verified"])
        self.assertFalse(prior["closure_verified"])
        self.assertEqual("HISTORICAL_EVIDENCE_PREMISE_ATTRIBUTED",
                         result["probe_comparisons"][0]["applicability"])
        self.assertEqual(["BARE"],
                         result["declared_probe_efficiency"]["historical_evidence_ids"])

    def test_a_record_that_states_the_premise_is_a_verified_closure(self):
        run = self.root / "DEV" / "runs" / "RUN-9" / "metrics.json"
        run.write_text(json.dumps({"run_id": "RUN-9", "status": "COMPLETED",
                                   "verdict": "NEG", "anchor_pass": True,
                                   "premise_id": SENSOR}), encoding="utf-8")
        body = packet(probes=[probe("BARE", prior_execution={
            "status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-9",
            "premise_id": SENSOR})])
        prior = assess_proposal(body, project_root=self.root)["probe_comparisons"][0]["prior_execution"]
        self.assertTrue(prior["premise_verified"])
        self.assertTrue(prior["status_verified"])
        self.assertTrue(prior["closure_verified"])
        self.assertEqual("RUN_RECORD", prior["premise_binding_basis"])

    def test_the_two_flags_can_never_disagree_in_that_direction(self):
        cases = [
            {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-9", "premise_id": SENSOR},
            {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-9"},
            {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-404", "premise_id": SENSOR},
            {"status": "COMPLETED_INVALID", "run_ref": "DEV/runs/RUN-9", "premise_id": SENSOR},
            {"status": "INCONCLUSIVE", "run_ref": "DEV/runs/RUN-9", "premise_id": SENSOR},
        ]
        for prior in cases:
            result = assess_proposal(packet(probes=[probe(prior_execution=prior)]),
                                     project_root=self.root)
            flags = result["probe_comparisons"][0]["prior_execution"]
            if flags["status_verified"]:
                self.assertTrue(flags["premise_verified"], prior)


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        buffer = io.StringIO()
        with patch.object(sys, "argv", ["science-cli", *argv]), \
                contextlib.redirect_stdout(buffer):
            code = cli_main()
        return code, json.loads(buffer.getvalue())

    def test_a_rejected_packet_exits_three_and_lists_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "p.json")
            path.write_text(json.dumps(packet(prechecks=[{"id": "legal_inputs",
                                                          "status": "PASS"}])),
                            encoding="utf-8")
            code, out = self.run_cli(["packet-check", "--packet", str(path)])
        self.assertEqual(3, code)
        self.assertEqual("SHAPE_VIOLATIONS", out["status"])
        self.assertEqual(["prechecks"], paths(out))

    def test_an_accepted_packet_can_be_decided_in_the_same_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "p.json")
            path.write_text(json.dumps(packet()), encoding="utf-8")
            code, out = self.run_cli(["packet-check", "--packet", str(path)])
        self.assertEqual(0, code)
        self.assertEqual("SHAPE_OK", out["status"])

    def test_normalization_is_written_to_a_new_file_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "p.json")
            original = json.dumps(packet(prechecks=[{"id": "legal_inputs",
                                                     "status": "PASS"}]),
                                  ensure_ascii=False)
            path.write_text(original, encoding="utf-8")
            target = Path(tmp, "fixed.json")
            code, out = self.run_cli(["packet-check", "--packet", str(path),
                                      "--normalize-out", str(target)])
            # The file it was given is still invalid: normalization never
            # rewrites the caller's packet in place.
            self.assertEqual(original, path.read_text(encoding="utf-8"))
            written = json.loads(target.read_text(encoding="utf-8"))
            self.assertIsInstance(written["prechecks"], dict)
            self.assertEqual("PASS", written["prechecks"]["legal_inputs"]["status"])
        self.assertEqual(3, code)
        self.assertEqual(str(target), out["normalization"]["written_to"])


if __name__ == "__main__":
    unittest.main()
