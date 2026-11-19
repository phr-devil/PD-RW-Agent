"""ARCH-CONVERGENCE: the feedback -> next-action seam and the documented boundary.

These tests pin the *preservation* properties of the convergence round:

* the projection from a feedback-link result into ``run_feedback`` is
  downgrade-only, so no source credibility can be raised on the way down;
* a conflicting or unreadable Run record cannot be read as a scientific
  negative or a supported hypothesis;
* a hand-written provenance without a binder status is capped;
* the MCP surface, tool profiles and the documented layer boundaries did not
  change.

They are engineering checks on adapter behavior, not scientific validation.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from pdrw_agent import __version__, case_gates  # noqa: E402
from pdrw_agent.schemas import AgentError  # noqa: E402
from pdrw_agent.science.feedback_link import (  # noqa: E402
    PROVENANCE_UNVERIFIED,
    PROVENANCE_VERIFIED,
    to_run_feedback,
)
from tests.test_science_feedback import packet  # noqa: E402
from pdrw_agent.science.feedback import review_probe_feedback  # noqa: E402

DIGEST = "a" * 64


def link_result(**overrides):
    base = {
        "schema_version": "pdrw-probe-feedback-link-v1",
        "status": "ADVISORY_FEEDBACK_ONLY",
        "prereg": {"proposal_sha256": DIGEST},
        "run": {"ref": "DEV/runs/RUN-002"},
        "provenance": {
            "pre_result_provenance": PROVENANCE_VERIFIED,
            "prediction_comparison": "DECLARED_PREDICTION_COMPARED",
        },
        "feedback": {
            "compatible_predictions": ["real-gain"],
            "contradicted_predictions": ["leakage-explains-gain"],
        },
        "observation_preserved": {
            "run_ref": "DEV/runs/RUN-002",
            "declared_validity": "VALID",
            "declared_outcome": "INCREASE",
            "evidence_refs": ["DEV/runs/RUN-002/metrics.json"],
        },
    }
    base.update(overrides)
    return base


class ProjectionIsDowngradeOnlyTests(unittest.TestCase):
    def test_verified_binding_survives_the_projection(self):
        out = to_run_feedback(link_result())
        self.assertEqual(out["provenance"], PROVENANCE_VERIFIED)
        self.assertEqual(out["prediction_review"], "DECLARED_PREDICTION_CONTRAST")
        self.assertEqual(out["compatible"], ["real-gain"])
        self.assertEqual(out["contradicted"], ["leakage-explains-gain"])
        self.assertEqual(out["link_status"], "ADVISORY_FEEDBACK_ONLY")
        self.assertEqual(out["proposal_sha256"], DIGEST)
        self.assertEqual(len(out), 10, "the gate accepts at most 12 bounded keys")

    def test_unverified_binding_cannot_be_reported_as_verified(self):
        out = to_run_feedback(link_result(
            status="PRE_RESULT_RECORD_UNVERIFIED",
            provenance={"pre_result_provenance": PROVENANCE_VERIFIED,
                        "prediction_comparison": "DECLARED_PREDICTION_COMPARED"}))
        self.assertEqual(out["provenance"], PROVENANCE_UNVERIFIED)
        # The advisory contrast may still be reported; only the provenance drops.
        self.assertEqual(out["prediction_review"], "DECLARED_PREDICTION_CONTRAST")

    def test_status_conflict_removes_the_contrast_entirely(self):
        out = to_run_feedback(link_result(status="RUN_STATUS_CONFLICT"))
        self.assertEqual(out["provenance"], PROVENANCE_UNVERIFIED)
        self.assertEqual(out["prediction_review"], "")
        self.assertEqual(out["outcome"], "UNKNOWN")
        self.assertEqual(out["compatible"], [])
        self.assertEqual(out["contradicted"], [])
        self.assertEqual(out["evidence_refs"], ["DEV/runs/RUN-002/metrics.json"])

    def test_missing_evidence_cannot_support_a_prediction_review(self):
        out = to_run_feedback(link_result(status="RUN_EVIDENCE_UNVERIFIED"))
        self.assertEqual(out["prediction_review"], "")
        self.assertEqual(out["provenance"], PROVENANCE_UNVERIFIED)

    def test_changed_axes_are_not_a_failed_hypothesis(self):
        out = to_run_feedback(link_result(
            status="NOT_COMPARABLE",
            provenance={"pre_result_provenance": PROVENANCE_VERIFIED,
                        "prediction_comparison": "NOT_COMPARABLE"}))
        self.assertEqual(out["prediction_review"], "")
        self.assertEqual(out["compatible"], [])
        self.assertEqual(out["link_status"], "NOT_COMPARABLE")

    def test_unknown_result_shapes_are_rejected_instead_of_guessed(self):
        for bad in ({}, {"schema_version": "pdrw-probe-feedback-link-v1"},
                    link_result(status="SOMETHING_NEW")):
            with self.assertRaises(AgentError):
                to_run_feedback(bad)


class GateCredibilityTests(unittest.TestCase):
    def declared(self, **overrides):
        raw = {
            "run_ref": "DEV/runs/RUN-002", "validity": "VALID",
            "outcome": "INCREASE",
            "prediction_review": "DECLARED_PREDICTION_CONTRAST",
            "provenance": PROVENANCE_VERIFIED,
            "compatible": ["real-gain"], "contradicted": [],
            "evidence_refs": ["DEV/runs/RUN-002/metrics.json"],
        }
        raw.update(overrides)
        return case_gates._declared_run_feedback({"run_feedback": raw})

    def test_hand_written_provenance_is_capped(self):
        feedback = self.declared()
        self.assertEqual(feedback["provenance"], PROVENANCE_VERIFIED)
        self.assertEqual(feedback["provenance_effective"], PROVENANCE_UNVERIFIED)
        self.assertEqual(feedback["provenance_basis"],
                         "DECLARED_INPUT_ONLY_GATE_PERFORMS_NO_BINDING")

    def test_a_hand_written_link_status_cannot_restore_verified(self):
        # The exact WP10 defect: provenance + any link status typed by the
        # caller used to survive as "verified". Both are just JSON.
        feedback = self.declared(link_status="ADVISORY_FEEDBACK_ONLY",
                                 proposal_sha256=DIGEST)
        self.assertEqual(feedback["provenance_effective"], PROVENANCE_UNVERIFIED)
        self.assertEqual(feedback["provenance_basis"],
                         "DECLARED_INPUT_ONLY_GATE_PERFORMS_NO_BINDING")
        self.assertEqual(feedback["link_status_declared"], "ADVISORY_FEEDBACK_ONLY")
        self.assertEqual(feedback["proposal_sha256_declared"], DIGEST)

    def test_the_gate_names_every_check_it_did_not_perform(self):
        feedback = self.declared(link_status="ADVISORY_FEEDBACK_ONLY")
        self.assertEqual(feedback["checks_by_gate"], {
            "file_binding": "NOT_PERFORMED_BY_GATE",
            "historical_order": "NOT_PERFORMED_BY_GATE",
            "run_validity": "NOT_PERFORMED_BY_GATE",
            "scientific_truth": "NOT_PERFORMED_BY_GATE",
        })
        self.assertFalse(feedback["scientific_inference_verified"])
        self.assertTrue(feedback["declared_only"])

    def test_no_status_can_upgrade_credibility(self):
        for status in ("ADVISORY_FEEDBACK_ONLY", "NOT_COMPARABLE",
                       "PRE_RESULT_RECORD_UNVERIFIED", ""):
            with self.subTest(status=status):
                feedback = self.declared(link_status=status)
                self.assertEqual(feedback["provenance_effective"],
                                 PROVENANCE_UNVERIFIED)

    def test_bad_link_status_or_digest_is_rejected(self):
        with self.assertRaises(AgentError):
            self.declared(link_status="APPROVED_BY_AUTHOR")
        with self.assertRaises(AgentError):
            self.declared(proposal_sha256="not-a-digest")

    def test_situation_for_uninterpretable_records(self):
        execution = {"status": "NO_EXECUTION_EVIDENCE_DECLARED"}
        cases = {
            "RUN_STATUS_CONFLICT": "RUN_RECORD_CONFLICT",
            "RUN_EVIDENCE_UNVERIFIED": "RUN_EVIDENCE_MISSING",
            "NOT_COMPARABLE": "MEASUREMENT_AXES_CHANGED",
        }
        for link_status, expected in cases.items():
            situation = case_gates._run_situation(
                self.declared(link_status=link_status), execution)
            self.assertEqual(situation, expected)

    def test_those_situations_never_ask_the_author_and_never_stop(self):
        execution = {"status": "NO_EXECUTION_EVIDENCE_DECLARED"}
        for link_status in ("RUN_STATUS_CONFLICT", "RUN_EVIDENCE_UNVERIFIED",
                            "NOT_COMPARABLE"):
            feedback = self.declared(link_status=link_status)
            situation = case_gates._run_situation(feedback, execution)
            action = case_gates._situation_action(situation, feedback, execution)
            self.assertFalse(action["author_decision_required"])
            self.assertFalse(action["automatic_go_stop"])
            self.assertEqual(action["status"], "PROPOSED_NOT_EXECUTED")
            self.assertEqual(action["decision_authority"],
                             "PD-RW_WORKFLOW_AND_AUTHOR_ONLY")

    def test_empty_review_proves_nothing_even_with_lists(self):
        # No declared contrast => the compatible/contradicted lists are noise.
        feedback = self.declared(prediction_review="", compatible=["real-gain"])
        self.assertEqual(case_gates._run_situation(
            feedback, {"status": "NO_EXECUTION_EVIDENCE_DECLARED"}),
            "NO_DISCRIMINATING_CONTRAST")

    def test_an_unverified_negative_is_not_called_a_valid_negative(self):
        feedback = self.declared(outcome="NO_CHANGE", compatible=[],
                                 contradicted=["real-gain"])
        situation = case_gates._run_situation(
            feedback, {"status": "NO_EXECUTION_EVIDENCE_DECLARED"})
        self.assertEqual(situation, "DECLARED_NEGATIVE_RESULT_UNVERIFIED")
        self.assertNotIn("VALID_NEGATIVE_RESULT", case_gates._SITUATION_TEXT)
        # The advice is preserved: reassess the premise, never stop the project.
        action = case_gates._situation_action(
            situation, feedback, {"status": "NO_EXECUTION_EVIDENCE_DECLARED"})
        self.assertEqual(action["action_type"],
                         "REASSESS_FAILED_PREMISE_AND_ALTERNATIVES")
        self.assertFalse(action["author_decision_required"])
        self.assertFalse(action["automatic_go_stop"])


class DecisionBasisTests(unittest.TestCase):
    def test_next_action_records_the_proposal_digest_and_credibility(self):
        cl = {"cases": {"results": [], "source_verification": {"index_sha256": "f" * 64}},
              "case_review": {"comparisons": []},
              "decision_experiences": {"experiences": []}}
        advisory = {"case_admissibility": {}, "conditions_differ_not_transferred": [],
                    "unknown_reasons": [], "evidence_tiers": {}, "experiences": [],
                    "compact_cases": []}
        feedback = case_gates._declared_run_feedback({"run_feedback": {
            "run_ref": "DEV/runs/RUN-002", "validity": "VALID", "outcome": "NO_CHANGE",
            "prediction_review": "DECLARED_PREDICTION_CONTRAST",
            "provenance": PROVENANCE_VERIFIED, "link_status": "ADVISORY_FEEDBACK_ONLY",
            "proposal_sha256": DIGEST, "compatible": [],
            "contradicted": ["real-gain"], "evidence_refs": ["DEV/runs/RUN-002/metrics.json"],
        }})
        result = case_gates.build_next_actions(
            "G2", {"query": "q", "task_id": "T", "h_stage": "H7",
                   "milestone": "PROTOCOL_FREEZE"},
            cl, advisory, {"status": "NO_EXECUTION_EVIDENCE_DECLARED"},
            run_feedback=feedback)
        basis = result["decision_basis"]
        self.assertEqual(basis["evidence"]["proposal_sha256_declared"], DIGEST)
        self.assertEqual(basis["evidence"]["feedback_link_status_declared"],
                         "ADVISORY_FEEDBACK_ONLY")
        self.assertEqual(basis["credibility"]["pre_result_provenance_declared"],
                         PROVENANCE_VERIFIED)
        self.assertEqual(basis["credibility"]["pre_result_provenance_effective"],
                         PROVENANCE_UNVERIFIED)
        self.assertEqual(basis["credibility"]["checks_by_gate"]["file_binding"],
                         "NOT_PERFORMED_BY_GATE")
        self.assertFalse(basis["credibility"]["scientific_inference_verified"])
        self.assertEqual(result["situation"]["kind"],
                         "DECLARED_NEGATIVE_RESULT_UNVERIFIED")
        self.assertEqual(result["situation"]["kind_scope"], "DECLARED_ONLY")
        self.assertFalse(result["situation"]["prediction_verification_performed"])
        self.assertEqual(result["actions"][0]["action_type"],
                         "REASSESS_FAILED_PREMISE_AND_ALTERNATIVES")
        self.assertEqual(result["actions"][0]["basis"]["proposal_sha256_declared"],
                         DIGEST)
        self.assertNotIn("proposal_sha256", result["actions"][0]["basis"])


class LegacyFeedbackSemanticsTests(unittest.TestCase):
    def test_declared_cases_are_not_reported_as_pre_decision(self):
        result = review_probe_feedback(packet())
        self.assertEqual(result["consulted_case_ids"], ["EXT-X3"])
        self.assertEqual(result["consulted_case_ids_semantics"],
                         "DECLARED_ONLY_TIMING_UNVERIFIED")
        self.assertEqual(result["case_timing"]["pre_decision_case_ids"], [])
        self.assertEqual(result["case_timing"]["declared_case_ids"], ["EXT-X3"])
        self.assertFalse(result["historical_order_verified"])


class McpSurfaceUnchangedTests(unittest.TestCase):
    def test_profiles_still_expose_11_21_24_tools(self):
        from pdrw_agent.integrations import mcp_server
        self.assertEqual(len(mcp_server.tools_for_profile("minimal")), 11)
        self.assertEqual(len(mcp_server.tools_for_profile("research")), 21)
        self.assertEqual(len(mcp_server.tools_for_profile("diagnostic")), 24)

    def test_no_tool_was_added_for_the_projection(self):
        from pdrw_agent.integrations import mcp_server
        self.assertEqual(len(mcp_server.CORE_TOOLS), 11)
        self.assertEqual(len(mcp_server.AUDIT_TOOLS), 6)
        self.assertEqual(len(mcp_server.CASE_TOOLS), 4)
        self.assertEqual(len(mcp_server.DIAGNOSTIC_TOOLS), 3)
        self.assertFalse(any("feedback" in name for name in
                             mcp_server.PROFILE_TOOLS["diagnostic"]))

    def test_bad_profile_still_fails_closed(self):
        from pdrw_agent.integrations import mcp_server
        with self.assertRaises(ValueError):
            mcp_server.tools_for_profile("everything")

    def test_session_instructions_keep_every_boundary_and_stay_short(self):
        from pdrw_agent.integrations import mcp_server
        text = mcp_server.INSTRUCTIONS
        for claim in (
                "PD-RW is the only scientific rule source",
                "never research artifacts",
                "not original-user authorization or scientific validation",
                "keyword similarity is NOT scientific premise",
                "no GO/STOP",
                "no STATE/Run/SEALED or research rule is modified",
                "never H9 alone",
                "G1>G2>G3>T1>T2",
                "NOT a host state-transition hard gate",
                "H6/H8 author choices and writing permissions are unchanged",
                "never rewrites or approves a card",
                "Do not auto-restart uncertain GPU jobs or open SEALED"):
            self.assertIn(claim, text)
        self.assertLess(len(text), 1300, "session guidance must stay bounded")

    def test_projection_vocabulary_matches_the_gate(self):
        # Two small closed sets live on both sides of the seam; a silent
        # divergence would let a status become unreadable at the gate.
        from pdrw_agent.science import feedback_link
        self.assertEqual(feedback_link.GATE_VALIDITY, case_gates.RUN_FEEDBACK_VALIDITY)
        self.assertEqual(feedback_link.GATE_OUTCOMES, case_gates.RUN_FEEDBACK_OUTCOMES)
        self.assertTrue(set(feedback_link.GATE_REVIEWS.values())
                        <= case_gates.RUN_FEEDBACK_REVIEWS)
        self.assertEqual(feedback_link.LINK_STATUSES,
                         case_gates.RUN_FEEDBACK_LINK_STATUSES - {"UNKNOWN"})


class EndToEndProjectionTests(unittest.TestCase):
    """A real fixture goes link -> CLI projection -> gate, without hand typing."""

    def test_cli_projection_reaches_the_gate_as_declared_not_certified(self):
        import json
        import subprocess
        import tempfile

        from tests.test_science_feedback_link import _Project

        with tempfile.TemporaryDirectory() as temp:
            project = _Project(Path(temp))
            link_path = project.root / "protocol" / "LINK.json"
            link_path.write_text(json.dumps(project.link(), ensure_ascii=False),
                                 encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-m", "pdrw_agent.science.cli", "feedback-link",
                 "--link", str(link_path), "--project-root", str(project.root),
                 "--as-run-feedback"],
                capture_output=True, text=True, encoding="utf-8", timeout=120,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        projected = json.loads(completed.stdout)
        self.assertEqual(sorted(projected), sorted([
            "run_ref", "validity", "outcome", "prediction_review", "provenance",
            "compatible", "contradicted", "evidence_refs", "link_status",
            "proposal_sha256"]))
        self.assertEqual(projected["link_status"], "ADVISORY_FEEDBACK_ONLY")
        self.assertEqual(projected["prediction_review"], "DECLARED_PREDICTION_CONTRAST")
        self.assertEqual(projected["provenance"], PROVENANCE_VERIFIED)
        self.assertEqual(len(projected["proposal_sha256"]), 64)

        feedback = case_gates._declared_run_feedback({"run_feedback": projected})
        # The binder did the file/order checks; the gate still may not inherit
        # them across a public JSON boundary, so credibility stays declared.
        self.assertEqual(feedback["provenance"], PROVENANCE_VERIFIED)
        self.assertEqual(feedback["provenance_effective"], PROVENANCE_UNVERIFIED)
        self.assertEqual(feedback["link_status_declared"], "ADVISORY_FEEDBACK_ONLY")
        # The fixture declares INCREASE, so one explanation is supported and one
        # contradicted: the split must survive the projection unchanged.
        self.assertEqual(projected["compatible"], ["real-gain"])
        self.assertEqual(projected["contradicted"], ["leakage-explains-gain"])
        self.assertEqual(case_gates._run_situation(
            feedback, {"status": "NO_EXECUTION_EVIDENCE_DECLARED"}),
            "COMPETING_EXPLANATIONS_SPLIT")


class DocumentationBoundaryTests(unittest.TestCase):
    """The docs must not silently contradict the code or the current version."""

    def read(self, name):
        return (ROOT / "docs" / name).read_text(encoding="utf-8")

    def test_architecture_names_six_layers_and_each_forbidden_action(self):
        text = self.read("ARCHITECTURE.md")
        for layer in ("PD-RW rule checkout", "Research project", "Skill (prompt adapter)",
                      "Python science checks", "Service + adapters",
                      "Runtime + host diagnostics"):
            self.assertIn(layer, text)
        self.assertIn("Must NOT do", text)
        self.assertIn("ATTESTED_BY_ORIGINAL_SOURCE", text)
        self.assertIn("NOT_ATTESTED", text)
        self.assertIn("WorkBuddy host", text)
        # The stale "current v0.7.1 / not implemented in v0.4" entry is gone.
        self.assertNotIn("not implemented in v0.4", text)
        self.assertIn(f"honest scope for v{__version__}", text)

    def test_runtime_doc_has_one_current_entry(self):
        text = self.read("RUNTIME_AND_MCP.md")
        self.assertIn(f"Current release: {__version__}", text)
        self.assertIn("**11**", text)
        self.assertIn("**21**", text)
        self.assertIn("**24**", text)
        self.assertIn("NOT_MEASURED", text)
        self.assertNotIn("Current v0.8.2", text)
        self.assertIn("Historical index", text)

    def test_preservation_map_states_its_open_gaps(self):
        text = self.read("DECISION_COVERAGE.md")
        self.assertIn("Constraint preservation map", text)
        self.assertIn("PRESERVATION_UNVERIFIED", text)
        self.assertIn("downgrade-only", text)
        self.assertIn("NOT_MEASURED", text)

    def test_feedback_doc_covers_the_projection_and_new_situations(self):
        text = self.read("EXPERIMENT_FEEDBACK_LINK.md")
        self.assertIn("to_run_feedback", text)
        for situation in ("RUN_RECORD_CONFLICT", "RUN_EVIDENCE_MISSING",
                          "MEASUREMENT_AXES_CHANGED"):
            self.assertIn(situation, text)

    def test_skill_tells_the_model_to_project_instead_of_typing(self):
        text = (ROOT / "skills" / "pd-rw-research" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("to_run_feedback", text)
        self.assertIn("the gate never reports", text)
        self.assertIn("a verified provenance", text)


if __name__ == "__main__":
    unittest.main()
