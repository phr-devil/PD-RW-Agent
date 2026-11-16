"""H6 candidate card and author-choice anti-bypass regression tests.

These fixtures verify structural protection only. They do NOT simulate a
trusted WorkBuddy message source or permit real training.
"""
import copy
import hashlib
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
    return {
        "schema_version": "pdrw-h6-plan-v1",
        "scope_ref": "launch-message-1",
        "options": [option("A", "UNKNOWN_NEEDS_PROBE"),
                    option("B", "SUPPORTED_BY_METADATA")],
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

    def test_cli_review_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = root / "plan.json"
            plan.write_text(json.dumps(sample_plan()), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-m", "pdrw_agent.science.cli",
                 "h6-review", "--plan", str(plan)],
                capture_output=True, text=True, check=False)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(data["status"], "AUTHOR_CHOICE_REQUIRED")
            self.assertEqual(set(root.iterdir()), {plan})


if __name__ == "__main__":
    unittest.main()
