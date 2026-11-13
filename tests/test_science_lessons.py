"""Read-only negative outcome compiler tests: declared != validated."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.science.lessons import premise_fingerprint, compile_declared_lessons
from pdrw_agent.science.decision import assess_proposal
from pdrw_agent.schemas import AgentError


class LessonTests(unittest.TestCase):
    def packet(self):
        return {"observations": [
            {"run_id": "run-crash", "outcome": "ENGINEERING_FAILURE",
             "evidence_refs": ["engineering-log"]},
            {"run_id": "run-invalid", "outcome": "INVALID_EXPERIMENT",
             "evidence_refs": ["evaluation-diagnostics"]},
            {"run_id": "run-negative", "outcome": "VALID_NEGATIVE",
             "tested_premise_id": "smoothing-controls-noise",
             "scope": {"group_unit": "person", "dataset": "synthetic"},
             "evidence_refs": ["DEV-run-meta"]},
            {"run_id": "run-inconclusive", "outcome": "INCONCLUSIVE",
             "evidence_refs": ["insufficient-Run"]},
        ]}

    def test_crashes_and_invalid_are_not_scientific_negatives(self):
        out = compile_declared_lessons(self.packet())
        self.assertEqual(out["status"], "DECLARED_LESSONS_ONLY")
        self.assertEqual(len(out["candidate_prior_negative_lessons"]), 1)
        self.assertFalse(out["all_sources_verified"])
        self.assertFalse(out["stop_or_go_authorized"])
        self.assertFalse(out["items"][0]["negative_scientific_evidence"])
        self.assertFalse(out["items"][1]["negative_scientific_evidence"])

    def test_exact_fingerprint_stable_and_scope_sensitive(self):
        a = premise_fingerprint("p", {"dataset": "x", "unit": "subject"})
        b = premise_fingerprint("p", {"unit": "subject", "dataset": "x"})
        c = premise_fingerprint("p", {"dataset": "x", "unit": "session"})
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(len(a), 64)

    def test_compiled_negative_remains_advisory(self):
        prior = compile_declared_lessons(self.packet())["candidate_prior_negative_lessons"]
        decision = {
            "question": "Is the identical prior premise still viable?",
            "claim_type": "MECHANISM",
            "proposed_premise": {
                "premise_id": "smoothing-controls-noise",
                "scope": {"dataset": "synthetic", "group_unit": "person"}
            },
            "hypotheses": ["h1", "h2"],
            "probes": [{
                "id": "p1", "observable": "held-out paired effect",
                "evaluation_unit": "person", "comparison_reference": "fixed baseline",
                "predictions": {"h1": "INCREASE", "h2": "NO_CHANGE"}
            }],
            "prior_negative_lessons": prior
        }
        result = assess_proposal(decision)
        self.assertEqual(result["premise_candidates"][0]["status"],
                         "DECLARED_SAME_PREMISE_SCOPE_CANDIDATE")
        self.assertFalse(result["premise_candidates"][0]["scientific_equivalence_verified"])
        self.assertFalse(result["automatic_stop"])

    def test_missing_evidence_fails(self):
        packet = self.packet()
        packet["observations"][2]["evidence_refs"] = []
        with self.assertRaises(AgentError):
            compile_declared_lessons(packet)

    def test_duplicate_run_id_fails(self):
        packet = self.packet()
        packet["observations"][1]["run_id"] = "run-crash"
        with self.assertRaises(AgentError):
            compile_declared_lessons(packet)

    def test_missing_scope_for_negative_fails(self):
        packet = self.packet()
        packet["observations"][2].pop("scope")
        with self.assertRaises(AgentError):
            compile_declared_lessons(packet)

    def test_cli_with_frozen_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            frozen = root / "frozen"
            frozen.mkdir()
            (frozen / "DEV-run-meta").write_text("synthetic source", encoding="utf-8")
            manifest = {
                "schema_version": 1, "case_id": "lesson-test",
                "frozen_at": "2026-01-01T00:00:00+09:00",
                "sources": [{
                    "ref": "DEV-run-meta",
                    "sha256": hashlib.sha256(
                        (frozen / "DEV-run-meta").read_bytes()).hexdigest()
                }],
                "allowed_evidence_refs": ["DEV-run-meta"],
            }
            packet = {"observations": [self.packet()["observations"][2]]}
            mp = root / "manifest.json"
            lp = root / "lessons.json"
            mp.write_text(json.dumps(manifest), encoding="utf-8")
            lp.write_text(json.dumps(packet), encoding="utf-8")
            cmd = [
                sys.executable, "-m", "pdrw_agent.science.cli",
                "lessons", "--packet", str(lp),
                "--evidence-root", str(frozen),
                "--evidence-manifest", str(mp)
            ]
            p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            result = json.loads(p.stdout)
            self.assertEqual(result["source_binding"]["status"],
                             "SOURCE_BYTES_MATCHED_ONLY")
            self.assertFalse(result["all_sources_verified"])


if __name__ == "__main__":
    unittest.main()
