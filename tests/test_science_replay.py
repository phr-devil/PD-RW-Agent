"""A/B/C protocol: synthetic time-frozen source validation and blinding only."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from pdrw_agent.schemas import AgentError
from pdrw_agent.science.replay import validate_case, blind_responses, REQUIRED


def response(label):
    return {
        "ROUTE": "Review synthetic data provenance",
        "EVIDENCE_USED": ["snapshot.md"],
        "NEXT_ACTION": f"Test the distinct hypothesis {label}",
        "AUTH": "READ_ONLY",
        "DECISION_SCOPE": "Existing DEV Task",
        "CLAIM_BOUNDARY": "No claim is validated",
        "COST_CAP": "NO_TRAIN",
        "EXPECTED_DECISION_CHANGE": "Distinguish two explanations",
    }


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "frozen"
        self.root.mkdir()
        (self.root / "snapshot.md").write_text(
            "Synthetic state known at freeze\n", encoding="utf-8")
        digest = hashlib.sha256((self.root / "snapshot.md").read_bytes()).hexdigest()
        self.manifest = {
            "schema_version": 1,
            "case_id": "synthetic-no-future",
            "frozen_at": "2026-01-05T10:00:00+09:00",
            "sources": [{"ref": "snapshot.md", "sha256": digest}],
            "allowed_evidence_refs": ["snapshot.md"],
        }
        self.responses = {k: response(k) for k in ("A", "B", "C")}

    def test_snapshots_have_source_integrity_but_not_history_attestation(self):
        result = validate_case(self.root, self.manifest)
        self.assertEqual(result["status"], "STRUCTURAL_SNAPSHOT_VERIFIED")
        self.assertFalse(result["historical_fidelity_verified"])
        self.assertFalse(result["future_information_leakage_excluded"])

    def test_altered_snapshot_not_replayable(self):
        (self.root / "snapshot.md").write_text("changed after freeze")
        x = validate_case(self.root, self.manifest)
        self.assertEqual(x["status"], "NOT_REPLAYABLE")
        with self.assertRaises(AgentError):
            blind_responses(self.root, self.manifest, self.responses, 7)

    def test_reject_paths_outside_and_sealed(self):
        p = dict(self.manifest)
        p["sources"] = [{"ref": "../outside.md", "sha256": "0" * 64}]
        p["allowed_evidence_refs"] = ["../outside.md"]
        with self.assertRaises(AgentError):
            validate_case(self.root, p)
        p["sources"] = [{"ref": "B_SEALED/data.json", "sha256": "0" * 64}]
        p["allowed_evidence_refs"] = ["B_SEALED/data.json"]
        with self.assertRaises(AgentError):
            validate_case(self.root, p)

    def test_blinding_hides_arm_labels_and_returns_separate_mapping(self):
        result = blind_responses(self.root, self.manifest, self.responses, 17)
        self.assertEqual(set(result["review_packet"]["responses"]), {"X", "Y", "Z"})
        self.assertEqual(set(result["private_unblinding_key"].values()), {"A", "B", "C"})
        self.assertNotIn("private_unblinding_key", result["review_packet"])
        self.assertEqual(result, blind_responses(self.root, self.manifest,
                                                  self.responses, 17))
        self.assertEqual(result["review_packet"]["review_status"],
                         "AWAITING_INDEPENDENT_BLIND_REVIEW")

    def test_future_evidence_ref_rejected(self):
        self.responses["A"]["EVIDENCE_USED"] = ["post-freeze-paper.pdf"]
        with self.assertRaises(AgentError):
            blind_responses(self.root, self.manifest, self.responses, 7)

    def test_unknown_metadata_not_silently_included(self):
        self.responses["A"]["model_name"] = "FUTURE_AGENT"
        with self.assertRaises(AgentError):
            blind_responses(self.root, self.manifest, self.responses, 7)

    def test_missing_or_invalid_response_fails_closed(self):
        self.responses["B"].pop("AUTH")
        with self.assertRaises(AgentError):
            blind_responses(self.root, self.manifest, self.responses, 7)
        self.responses["B"]["AUTH"] = 0
        with self.assertRaises(AgentError):
            blind_responses(self.root, self.manifest, self.responses, 7)

    def test_duplicate_sources_fail_and_naive_timestamp_fails(self):
        p = dict(self.manifest)
        p["sources"] = [self.manifest["sources"][0]] * 2
        with self.assertRaises(AgentError):
            validate_case(self.root, p)
        p = dict(self.manifest)
        p["frozen_at"] = "2026-01-05T10:00:00"
        with self.assertRaises(AgentError):
            validate_case(self.root, p)

    def test_cli_check_and_private_key_separate_from_packet(self):
        folder = Path(self.tmp.name)
        config_path = folder / "case.json"
        config_path.write_text(json.dumps(self.manifest), encoding="utf-8")
        args = [sys.executable, "-m", "pdrw_agent.science.cli"]
        good = subprocess.run(args + [
            "replay-check", "--root", str(self.root), "--manifest", str(config_path)
        ], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertEqual(json.loads(good.stdout)["status"], "STRUCTURAL_SNAPSHOT_VERIFIED")
        response_paths = {}
        for arm, body in self.responses.items():
            path = folder / f"{arm}.json"
            path.write_text(json.dumps(body), encoding="utf-8")
            response_paths[arm.lower()] = path
        private = folder / "private"
        private.mkdir()
        key_path = private / "unblind.json"
        cmd = args + [
            "replay-blind", "--root", str(self.root), "--manifest", str(config_path),
            "--a", str(response_paths["a"]), "--b", str(response_paths["b"]),
            "--c", str(response_paths["c"]), "--seed", "5",
            "--private-key", str(key_path),
        ]
        run = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        packet = json.loads(run.stdout)
        self.assertEqual(set(packet["responses"]), {"X", "Y", "Z"})
        self.assertNotIn("private_unblinding_key", run.stdout)
        self.assertTrue(key_path.is_file())
        again = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(again.returncode, 2)
        self.assertEqual(json.loads(again.stdout)["status"], "ERROR")

    def test_cli_decision(self):
        folder = Path(self.tmp.name)
        candidate = {
            "question": "Can two physical explanations be differentiated?",
            "claim_type": "LAW",
            "proposed_premise": {"premise_id": "diff", "scope": {"domain": "synthetic"}},
            "hypotheses": ["h1", "h2"],
            "probes": [{"id": "p1",
                        "observable": "synthetic signed effect",
                        "evaluation_unit": "independent subject",
                        "comparison_reference": "fixed baseline",
                        "predictions": {
                "h1": "INCREASE", "h2": "DECREASE"
            }, "cost_band": "LOW"}],
        }
        p = folder / "candidate.json"
        p.write_text(json.dumps(candidate), encoding="utf-8")
        command = [sys.executable, "-m", "pdrw_agent.science.cli",
                   "decision", "--packet", str(p)]
        run = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["status"], "ADVISORY_REVIEW_ONLY")


if __name__ == "__main__":
    unittest.main()
