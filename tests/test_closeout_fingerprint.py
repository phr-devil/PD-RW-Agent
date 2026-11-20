"""ARCH-CLOSEOUT: the gate cache key covers the whole bounded declaration.

These tests reproduce a defect found in PR #19 HEAD `cca068f`: the fingerprint
hashed `run_feedback` clipped to 900 characters and a derived
`evidence_declaration` string clipped to 500, so two inputs that differ only
past the clip produced the *same* key. A second call was then answered from the
first call's cached advisory while the declared evidence had materially
changed.

The clip itself is legitimate — an advisory payload must stay bounded — but it
belongs to the returned projection only. The digest must see every field the
event is allowed to carry (`MAX_EVENT_FIELDS` x `MAX_TEXT_CHARS`).

Engineering contract tests; they say nothing about scientific benefit.
"""
from __future__ import annotations

import json
import unittest

from pdrw_agent import case_gates

KEYWORDS = {"trigger": "T1", "index_sha256": "f" * 64}


def long_feedback(tail: str) -> dict:
    """A legal `run_feedback`: 1033 chars of JSON, well under MAX_TEXT_CHARS."""
    return {"a_note": "n" * 1000, "z_verdict": tail}


def long_evidence(outcome: str, signal: str, **overrides) -> dict:
    event = {
        "task_id": "T",
        "outcome_class": outcome,
        "evidence_refs": ["DEV/runs/RUN-002/artifacts/measurement_table_part_%02d.csv" % i
                          for i in range(8)],
        "signals": [signal],
    }
    event.update(overrides)
    return event


class LegalInputCollisionTests(unittest.TestCase):
    def test_the_declarations_used_here_are_inside_the_event_limits(self):
        # Otherwise the point would be "rejected input", not "legal input".
        self.assertLessEqual(
            len(json.dumps(long_feedback("VALID"), ensure_ascii=False,
                           sort_keys=True, separators=(",", ":"))),
            case_gates.MAX_TEXT_CHARS)
        event = long_evidence("VALID_SCIENTIFIC_NEGATIVE", "negative_result")
        for value in event.values():
            self.assertLessEqual(len(case_gates._text(value)),
                                 case_gates.MAX_TEXT_CHARS)
        case_gates.gate_fingerprint(event, **KEYWORDS)  # must not raise

    def test_a_run_feedback_tail_beyond_the_display_clip_changes_the_key(self):
        a, _ = case_gates.gate_fingerprint(
            {"task_id": "T", "run_feedback": long_feedback("VALID")}, **KEYWORDS)
        b, _ = case_gates.gate_fingerprint(
            {"task_id": "T", "run_feedback": long_feedback("INVALID")}, **KEYWORDS)
        self.assertNotEqual(a, b)

    def test_a_declared_outcome_tail_beyond_the_display_clip_changes_the_key(self):
        # `outcome_class` and `signals` sit at the end of the declaration object.
        negative, _ = case_gates.gate_fingerprint(
            long_evidence("VALID_SCIENTIFIC_NEGATIVE", "negative_result"),
            **KEYWORDS)
        engineering, _ = case_gates.gate_fingerprint(
            long_evidence("ENGINEERING_FAILURE", "implementation_bug"), **KEYWORDS)
        self.assertNotEqual(negative, engineering)

    def test_a_changed_evidence_ref_list_changes_the_key(self):
        event = long_evidence("VALID_SCIENTIFIC_NEGATIVE", "negative_result")
        other = json.loads(json.dumps(event))
        other["evidence_refs"][-1] = "DEV/runs/RUN-002/artifacts/other.csv"
        a, _ = case_gates.gate_fingerprint(event, **KEYWORDS)
        b, _ = case_gates.gate_fingerprint(other, **KEYWORDS)
        self.assertNotEqual(a, b)

    def test_two_identical_declarations_still_share_a_key(self):
        a, _ = case_gates.gate_fingerprint(
            long_evidence("ENGINEERING_FAILURE", "implementation_bug"), **KEYWORDS)
        b, _ = case_gates.gate_fingerprint(
            long_evidence("ENGINEERING_FAILURE", "implementation_bug"), **KEYWORDS)
        self.assertEqual(a, b)


class DisplayProjectionTests(unittest.TestCase):
    """Truncation is allowed in the returned basis, never in the digest input."""

    def test_the_returned_basis_is_clipped(self):
        event = long_evidence("VALID_SCIENTIFIC_NEGATIVE", "negative_result")
        event["run_feedback"] = long_feedback("VALID")
        _, parts = case_gates.gate_fingerprint(event, **KEYWORDS)
        self.assertLessEqual(len(parts["run_feedback"]), 901)
        self.assertLessEqual(len(parts["evidence_declaration"]), 501)
        self.assertTrue(parts["run_feedback"].endswith("…"))
        self.assertTrue(parts["evidence_declaration"].endswith("…"))

    def test_the_basis_still_carries_the_named_output_fields(self):
        event = {"task_id": "T", "hypothesis": "h", "protocol": "p",
                 "decision": "d"}
        _, parts = case_gates.gate_fingerprint(event, "G1", "sha")
        for field in ("trigger", "decision", "hypothesis", "protocol",
                      "case_library_index_sha256", "case_library_index_stale"):
            self.assertIn(field, parts)


if __name__ == "__main__":
    unittest.main()
