"""ARCH-CLOSEOUT: a T1 declaration is not the tool's own scientific finding.

`triage_anomaly` echoes the caller's `outcome_class`. It may do so only as a
declaration. When the same call also declares a Run state that cannot support
that class (invalid, unexecuted, conflicting, not comparable, competing
explanations), the declared value is kept for audit but the effective category
is UNKNOWN — otherwise one payload would say "valid scientific negative" while
its own first next action says "find the real Run record first".

Engineering contract tests; no claim about scientific benefit.
"""
from __future__ import annotations

import unittest

from pdrw_agent import case_gates


def triage(**overrides) -> dict:
    event = {
        "task_id": "T1",
        "outcome_class": "VALID_SCIENTIFIC_NEGATIVE",
        "evidence_refs": ["DEV/runs/RUN-002/metrics.json"],
    }
    event.update(overrides)
    return case_gates.triage_anomaly(event)


def judged(**overrides) -> dict:
    raw = {
        "run_ref": "DEV/runs/RUN-002",
        "validity": "VALID",
        "outcome": "NO_CHANGE",
        "prediction_review": "DECLARED_PREDICTION_CONTRAST",
        "compatible": [],
        "contradicted": ["real-gain"],
        "evidence_refs": ["DEV/runs/RUN-002/metrics.json"],
    }
    raw.update(overrides)
    return raw


class DeclaredCategoryConsistencyTests(unittest.TestCase):
    def test_an_uncontradicted_declaration_keeps_its_category(self):
        result = triage(run_feedback=judged())
        self.assertEqual(result["category"], "VALID_SCIENTIFIC_NEGATIVE")
        self.assertEqual(result["category_effective"], "VALID_SCIENTIFIC_NEGATIVE")
        self.assertEqual(result["status"], "TRIAGE_ADVISORY_ONLY")
        self.assertIsNone(result["declaration_conflict"])

    def test_no_run_feedback_leaves_the_declaration_untouched(self):
        result = triage()
        self.assertEqual(result["category"], "VALID_SCIENTIFIC_NEGATIVE")
        self.assertEqual(result["status"], "TRIAGE_ADVISORY_ONLY")
        self.assertFalse(result["category_effective"] == "UNKNOWN")

    def test_an_invalid_run_downgrades_the_effective_category(self):
        result = triage(run_feedback=judged(validity="INVALID"))
        self.assertEqual(result["category"], "VALID_SCIENTIFIC_NEGATIVE")
        self.assertEqual(result["category_effective"], "UNKNOWN")
        self.assertEqual(result["status"], "UNKNOWN")
        self.assertEqual(result["declaration_conflict"]["declared_validity"], "INVALID")
        self.assertIn("DECLARED_OUTCOME_CLASS_CONTRADICTED_BY_DECLARED_RUN",
                      " ".join(result["unknown_reasons"]))
        self.assertIn("核实", result["next_decisive_action"])

    def test_an_unexecuted_or_conflicting_run_downgrades_too(self):
        cases = [
            judged(validity="NOT_RUN"),
            judged(link_status="RUN_STATUS_CONFLICT"),
            judged(link_status="RUN_EVIDENCE_UNVERIFIED"),
            judged(link_status="NOT_COMPARABLE"),
            judged(prediction_review="NO_VALID_SCIENTIFIC_INFERENCE"),
            judged(compatible=["real-gain"]),  # competing explanations
        ]
        for feedback in cases:
            with self.subTest(feedback=feedback):
                result = triage(run_feedback=feedback)
                self.assertEqual(result["category_effective"], "UNKNOWN")
                self.assertEqual(result["status"], "UNKNOWN")

    def test_a_downgrade_never_touches_the_other_three_classes(self):
        for category in ("ENGINEERING_FAILURE", "INVALID_EVALUATION",
                         "INSUFFICIENT_EVIDENCE"):
            with self.subTest(category=category):
                result = triage(outcome_class=category,
                                run_feedback=judged(validity="INVALID"))
                self.assertEqual(result["category_effective"], category)
                self.assertEqual(result["status"], "TRIAGE_ADVISORY_ONLY")

    def test_the_declared_value_is_auditable_separately(self):
        result = triage(run_feedback=judged(validity="INVALID"))
        self.assertEqual(result["category_declared"], "VALID_SCIENTIFIC_NEGATIVE")
        self.assertEqual(result["category_scope"], "DECLARED_ONLY")
        self.assertEqual(result["verification"],
                         "DECLARED_ONLY_NOT_INDEPENDENTLY_VERIFIED")
        self.assertFalse(result["automatic_go_stop"])


if __name__ == "__main__":
    unittest.main()
