"""Synthetic author-card checks; neither source authentication nor execution."""
import copy
import unittest

from pdrw_agent.science.staged_selection import (
    review_early_choice, validate_early_plan
)
from pdrw_agent.science.plan_selection import (
    review_h6_plan_choice, validate_h6_plan
)
from pdrw_agent.schemas import AgentError

H3 = {"plan_sha256":"a"*64, "original_user_message_ref":"message-h3", "choice":"option-a"}
H4 = {"plan_sha256":"b"*64, "original_user_message_ref":"message-h4", "choice":"option-b"}


def early(stage="H3"):
    return {
        "schema_version": "pdrw-early-plan-v1", "stage":stage,
        "research_line_ref":"project-line-1", "scope_ref":"original-startup",
        "upstream_choices": {} if stage=="H3" else {"H3":dict(H3)},
        "options":[{"id":"option-a", "question_or_evidence_path":"first scientifically meaningful path",
                    "paper_value":"specific audience and reusable finding",
                    "nearest_prior":"named paper or NOT_ACCESSED",
                    "truth_and_independence":"independent groups not yet verified",
                    "discriminating_probe":"lawful group-level pilot",
                    "cost_and_risk":"LOW, missing labels possible"}],
        "recommended_option_id":"option-a",
        "recommendation_rationale":"best credible route given evidence",
    }


def response(plan, message):
    _, digest = validate_early_plan(plan)
    return {"schema_version":"pdrw-early-choice-v1", "plan_sha256":digest,
            "kind":"USER_SELECTED", "original_user_message_ref":message,
            "selected_option_id":"option-a", "allowed_option_ids":[],
            "delegated_scope":None}


def h6():
    return {
        "schema_version":"pdrw-h6-plan-v3", "scope_ref":"original-startup",
        "research_line_ref":"project-line-1", "upstream_choices":{"H3":dict(H3),"H4":dict(H4)},
        "options":[{"id":"A", "scientific_question":"important question",
                    "core_task":"real prediction task",
                    "dataset_or_proof_path":"licensed DEV dataset",
                    "nearest_work_or_unknown":"named prior",
                    "truth_and_independence":"group evaluation",
                    "competing_explanation":"possible confounder",
                    "decisive_probe":"matched strong baseline",
                    "cost_and_risk":"bounded cost with no protected access",
                    "science_fit":"UNKNOWN_NEEDS_PROBE", "primary_type":"C02",
                    "route":"R1", "p_orientation":"P1",
                    "adaptive_pivot_envelope":"in-scope traditional-model improvements and measurement findings"}],
        "recommended_option_id":"A",
        "recommendation_rationale":"fastest independently defensible paper route",
    }


class ThreeCardTests(unittest.TestCase):
    def test_h3_h4_have_separate_source_references(self):
        p = early("H3")
        self.assertEqual(review_early_choice(p)["status"], "AUTHOR_CHOICE_REQUIRED")
        self.assertEqual(review_early_choice(p, response(p,"message-h3"))["status"],
                         "DECLARED_CHOICE_UNAUTHENTICATED")
        p4 = early("H4")
        self.assertEqual(review_early_choice(p4,response(p4,"message-h3"))["status"],
                         "REUSED_UPSTREAM_AUTHOR_MESSAGE")
        self.assertEqual(review_early_choice(p4,response(p4,"message-h4"))["status"],
                         "DECLARED_CHOICE_UNAUTHENTICATED")

    def test_changed_h3_breaks_h4_card_digest(self):
        p = early("H4")
        choice = response(p,"message-h4")
        p["upstream_choices"]["H3"]["plan_sha256"] = "f"*64
        self.assertEqual(review_early_choice(p,choice)["status"],
                         "CHOICE_PLAN_MISMATCH")

    def test_h6_v3_binds_upstream_cards_and_pivot_scope(self):
        p = h6()
        _,digest = validate_h6_plan(p)
        c = {"schema_version":"pdrw-h6-choice-v1",
             "plan_sha256":digest,"kind":"USER_SELECTED",
             "original_user_message_ref":"message-h6",
             "selected_option_id":"A","allowed_option_ids":[],
             "delegated_scope":None}
        self.assertEqual(review_h6_plan_choice(p,c)["status"],
                         "DECLARED_CHOICE_UNAUTHENTICATED")
        p["upstream_choices"]["H4"]["plan_sha256"] = "f"*64
        self.assertEqual(review_h6_plan_choice(p,c)["status"],"CHOICE_PLAN_MISMATCH")
        p = h6()
        _,digest = validate_h6_plan(p)
        c["plan_sha256"] = digest
        c["original_user_message_ref"] = "message-h3"
        self.assertEqual(review_h6_plan_choice(p,c)["status"],
                         "REUSED_UPSTREAM_AUTHOR_MESSAGE")

    def test_missing_pivot_envelope_is_rejected(self):
        p = h6()
        del p["options"][0]["adaptive_pivot_envelope"]
        with self.assertRaises(AgentError):
            validate_h6_plan(p)

    def test_early_plan_rejects_fake_multiple_options(self):
        p = early()
        p["options"].append({**p["options"][0],"id":"option-b"})
        with self.assertRaises(AgentError):
            validate_early_plan(p)


if __name__ == "__main__":
    unittest.main()
