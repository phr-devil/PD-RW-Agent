"""H6 candidate card and author-choice anti-bypass regression tests.

These fixtures verify structural protection only. They do NOT simulate a
trusted WorkBuddy message source or permit real training.
"""
import copy
import hashlib
import os
import runpy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.science.plan_selection import (
    validate_h6_plan, review_h6_plan_choice,
)
from pdrw_agent.schemas import AgentError
from pdrw_agent.science.h6_bridge import to_pd_rw_h6_checkpoint


def sample_plan():
    def option(ident, fit):
        return {
            "id": ident,
            "scientific_question": "Does cross-sensor drift affect reliability?",
            "core_task": "Cross-device evaluation under independent groups",
            "dataset_or_proof_path": "Official dataset metadata / proof pending",
            "nearest_work_or_unknown": "NOT_ACCESSED",
            "truth_and_independence": "Device x subject crossing UNKNOWN",
            "competing_explanation": "Label or session leakage",
            "decisive_probe": "Independent-device and simple-baseline comparison",
            "cost_and_risk": "Small metadata/DEV probe; may fail identifiability",
            "science_fit": fit,
            "primary_type": "C09", "route": "R4", "p_orientation": "P2",
        }
    b = option("B", "SUPPORTED_BY_METADATA")
    b["scientific_question"] = "Is the training label protocol independent of acquisition sessions?"
    b["competing_explanation"] = "A session-specific shortcut dominates target class"
    return {
        "schema_version": "pdrw-h6-plan-v2",
        "scope_ref": "launch-message-1",
        "research_line_ref": "new-line-unique-20261116",
        "options": [option("A", "UNKNOWN_NEEDS_PROBE"), b],
        "recommended_option_id": "B",
        "recommendation_rationale": "Better public evidence route, still uncertain",
    }


def sample_choice(plan, **overrides):
    _, digest = validate_h6_plan(plan)
    out = {
        "schema_version": "pdrw-h6-choice-v1",
        "plan_sha256": digest,
        "kind": "USER_SELECTED",
        "original_user_message_ref": "reply-after-card-1",
        "selected_option_id": "B",
        "allowed_option_ids": [],
        "delegated_scope": None,
    }
    out.update(overrides)
    return out


class H6PlanChoiceTests(unittest.TestCase):
    def test_no_choice_is_blocked_without_conflating_unknown_with_failure(self):
        out = review_h6_plan_choice(sample_plan())
        self.assertEqual(out["status"], "AUTHOR_CHOICE_REQUIRED")
        self.assertEqual(out["recommended_option_id"], "B")
        self.assertFalse(out["execution_authorized"])
        self.assertFalse(out["user_choice_authenticated"])

    def test_provisional_metadata_fit_does_not_suppress_truth_warnings(self):
        out = review_h6_plan_choice(sample_plan())
        risks = {row["option_id"]: row for row in out["science_risk_flags"]}
        self.assertIn("B", risks)
        self.assertIn("INDEPENDENT_TRUTH_OR_GROUPS_UNVERIFIED", risks["B"]["warnings"])
        self.assertIn("NEAREST_WORK_NOT_FULLY_ACCESSED", risks["B"]["warnings"])
        self.assertFalse(out["science_risks_authoritatively_verified"])
        self.assertFalse(out["scientific_truth_verified"])

    def test_declared_specific_reply_is_still_not_authenticated(self):
        plan = sample_plan()
        out = review_h6_plan_choice(plan, sample_choice(plan))
        self.assertEqual(out["status"], "DECLARED_CHOICE_UNAUTHENTICATED")
        self.assertEqual(out["selection"]["selected_option_id"], "B")
        self.assertFalse(out["execution_authorized"])
        self.assertFalse(out["user_choice_authenticated"])

    def test_simple_continue_or_agent_approval_cannot_be_a_user_choice(self):
        plan = sample_plan()
        for bad in ({"approved": True}, {"kind": "AGENT_SELECTED"},
                    {"kind": "CONTINUE"}):
            with self.subTest(bad=bad):
                with self.assertRaises(AgentError):
                    review_h6_plan_choice(plan, bad)

    def test_plan_digest_change_invalidates_prior_choice(self):
        plan = sample_plan()
        choice = sample_choice(plan)
        altered = copy.deepcopy(plan)
        altered["options"][0]["core_task"] = "Changed primary task"
        out = review_h6_plan_choice(altered, choice)
        self.assertEqual(out["status"], "CHOICE_PLAN_MISMATCH")
        self.assertFalse(out["execution_authorized"])

    def test_wrong_option_and_unbounded_delegation_are_blocked(self):
        plan = sample_plan()
        out = review_h6_plan_choice(
            plan, sample_choice(plan, selected_option_id="C"))
        self.assertEqual(out["status"], "CHOICE_SCOPE_INVALID")
        out = review_h6_plan_choice(plan, sample_choice(
            plan, kind="USER_DELEGATED", selected_option_id=None,
            allowed_option_ids=["A", "C"], delegated_scope="Only the listed options"))
        self.assertEqual(out["status"], "CHOICE_SCOPE_INVALID")
        out = review_h6_plan_choice(plan, sample_choice(
            plan, kind="USER_DELEGATED", selected_option_id=None,
            allowed_option_ids=["A", "B"], delegated_scope="Same core question"))
        self.assertEqual(out["status"], "DECLARED_CHOICE_UNAUTHENTICATED")
        self.assertFalse(out["user_choice_authenticated"])

    def test_duplicate_option_missing_evidence_and_fake_status_are_rejected(self):
        plan = sample_plan()
        plan["options"][1]["id"] = "A"
        with self.assertRaises(AgentError):
            validate_h6_plan(plan)
        plan = sample_plan()
        plan["options"][0]["science_fit"] = "PASS"
        with self.assertRaises(AgentError):
            validate_h6_plan(plan)
        plan = sample_plan()
        plan["options"][0]["truth_and_independence"] = ""
        with self.assertRaises(AgentError):
            validate_h6_plan(plan)
        plan = sample_plan()
        plan["options"][0]["route"] = "R7"
        with self.assertRaises(AgentError):
            validate_h6_plan(plan)
        plan = sample_plan()
        plan["approved"] = True
        with self.assertRaises(AgentError):
            validate_h6_plan(plan)

    def test_single_option_is_valid_when_evidence_supports_one_only(self):
        plan = sample_plan()
        plan["options"] = [plan["options"][0]]
        plan["recommended_option_id"] = "A"
        out = review_h6_plan_choice(plan)
        self.assertEqual(out["available_option_ids"], ["A"])

    def test_cross_project_h6_choice_cannot_reuse_plan_digest(self):
        plan = sample_plan()
        reply = sample_choice(plan)
        other_line = copy.deepcopy(plan)
        other_line["research_line_ref"] = "different-line"
        out = review_h6_plan_choice(other_line, reply)
        self.assertEqual(out["status"], "CHOICE_PLAN_MISMATCH")
        self.assertEqual(out["research_line_ref_declared"], "different-line")
        self.assertFalse(out["user_choice_authenticated"])

    def test_legacy_v1_digest_and_user_reply_are_preserved(self):
        legacy = sample_plan()
        legacy["schema_version"] = "pdrw-h6-plan-v1"
        del legacy["research_line_ref"]
        expected = hashlib.sha256(json.dumps(
            legacy, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode("utf-8")).hexdigest()
        self.assertEqual(validate_h6_plan(legacy)[1], expected)
        self.assertEqual(review_h6_plan_choice(
            legacy, sample_choice(legacy))["status"],
            "DECLARED_CHOICE_UNAUTHENTICATED")

    def test_rewording_recommendation_does_not_invalidate_science_scope(self):
        plan = sample_plan()
        choice = sample_choice(plan)
        adjusted = copy.deepcopy(plan)
        adjusted["recommendation_rationale"] += "  Updated editorial wording."
        out = review_h6_plan_choice(adjusted, choice)
        self.assertEqual(out["status"], "DECLARED_CHOICE_UNAUTHENTICATED")
        self.assertFalse(out["execution_authorized"])

    def test_contradicted_scientific_claim_cannot_be_selected(self):
        plan = sample_plan()
        plan["options"][1]["science_fit"] = "CONTRADICTED_FOR_CLAIM"
        out = review_h6_plan_choice(plan)
        self.assertEqual(out["status"], "RECOMMENDED_SCIENCE_CONTRADICTED")
        plan["recommended_option_id"] = "A"
        out = review_h6_plan_choice(plan, sample_choice(plan, selected_option_id="B"))
        self.assertEqual(out["status"], "SELECTED_SCIENCE_CONTRADICTED")

    def test_identical_option_premises_are_not_distinct(self):
        plan = sample_plan()
        plan["options"][1]["scientific_question"] = plan["options"][0]["scientific_question"]
        plan["options"][1]["competing_explanation"] = plan["options"][0]["competing_explanation"]
        with self.assertRaises(AgentError):
            validate_h6_plan(plan)

    def test_bridge_maps_to_real_pd_rw_checkpoint_without_authorization(self):
        plan = sample_plan()
        candidate = to_pd_rw_h6_checkpoint(plan)
        selected = to_pd_rw_h6_checkpoint(plan, sample_choice(plan))
        self.assertEqual(candidate["trigger"], "H6_TASK")
        self.assertNotIn("selection", candidate["author_review"])
        self.assertEqual(selected["author_review"]["selection"]["chosen_option_id"], "B")
        self.assertFalse(selected["h6_user_message_authenticated"])
        rule_root = os.environ.get("PDRW_TEST_RULE_ROOT")
        if rule_root:
            src = Path(rule_root) / "core" / "execution_preflight.py"
            self.assertTrue(src.is_file())
            science_checkpoint = runpy.run_path(str(src))["science_checkpoint"]
            no_reply = science_checkpoint(candidate)
            declared_reply = science_checkpoint(selected)
            self.assertEqual(no_reply["result"], "AUTHOR_CHOICE_REQUIRED")
            self.assertEqual(declared_reply["result"], "READY_FOR_SCIENTIFIC_REVIEW")
            self.assertFalse(declared_reply["author_approval_authenticated"])

    def test_cli_emits_checkable_pd_rw_contract_not_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = root / "plan.json"
            plan.write_text(json.dumps(sample_plan()), encoding="utf-8")
            proc = subprocess.run([
                sys.executable, "-m", "pdrw_agent.science.cli", "h6-review",
                "--plan", str(plan), "--pd-rw-checkpoint"
            ], capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 3, proc.stderr)
            output = json.loads(proc.stdout)
            self.assertEqual(output["pd_rw_checkpoint"]["trigger"], "H6_TASK")
            self.assertFalse(output["user_choice_authenticated"])
            self.assertEqual(set(root.iterdir()), {plan})

    def test_cli_review_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = root / "plan.json"
            plan.write_text(json.dumps(sample_plan()), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-m", "pdrw_agent.science.cli",
                 "h6-review", "--plan", str(plan)],
                capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 3, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(data["status"], "AUTHOR_CHOICE_REQUIRED")
            self.assertEqual(set(root.iterdir()), {plan})


if __name__ == "__main__":
    unittest.main()
