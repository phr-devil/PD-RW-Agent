"""Synthetic-only checks: cited source bytes != scientific truth."""
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.science.provenance import bind_frozen_evidence, bind_source_refs
from pdrw_agent.schemas import AgentError


class EvidenceBindingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name)
        self.root = self.path / "frozen"
        self.root.mkdir()
        source = self.root / "known.md"
        source.write_text("Synthetic evidence, not a real Run.\n", encoding="utf-8")
        self.case = {
            "schema_version": 1, "case_id": "synthetic",
            "frozen_at": "2026-01-01T00:00:00+09:00",
            "sources": [{
                "ref": "known.md",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest()
            }],
            "allowed_evidence_refs": ["known.md"]
        }
        self.packet = {
            "question": "Can the two hypotheses be distinguished?",
            "claim_type": "MECHANISM",
            "proposed_premise": {"premise_id": "test", "scope": {"domain": "synthetic"}},
            "hypotheses": ["h1", "h2"],
            "claim_evidence_refs": ["known.md"],
            "probes": [{
                "id": "p1", "observable": "signed effect",
                "evaluation_unit": "independent group",
                "comparison_reference": "fixed baseline",
                "predictions": {"h1": "INCREASE", "h2": "DECREASE"},
                "prediction_evidence_refs": ["known.md"]
            }],
            "prechecks": {"group_independence": {
                "status": "UNKNOWN", "evidence_refs": ["known.md"]}},
            "prior_negative_lessons": []
        }

    def test_binds_byte_integrity_only(self):
        result = bind_frozen_evidence(self.root, self.case, self.packet)
        self.assertEqual(result["status"], "SOURCE_BYTES_MATCHED_ONLY")
        self.assertEqual(result["referenced"], ["known.md"])
        self.assertFalse(result["scientific_claims_verified"])
        self.assertFalse(result["historical_fidelity_verified"])
        self.assertFalse(result["permission_to_execute"])

    def test_outside_reference_fails_not_silent(self):
        self.packet["claim_evidence_refs"] = ["future-result.json"]
        result = bind_frozen_evidence(self.root, self.case, self.packet)
        self.assertEqual(result["status"], "EVIDENCE_OUT_OF_FREEZE")
        self.assertEqual(result["unlisted_refs"], ["future-result.json"])

    def test_changed_source_fails(self):
        (self.root / "known.md").write_text("Changed after freeze", encoding="utf-8")
        result = bind_frozen_evidence(self.root, self.case, self.packet)
        self.assertEqual(result["status"], "NOT_REPLAYABLE")

    def test_missing_citation_not_evidence(self):
        result = bind_source_refs(self.root, self.case, [])
        self.assertEqual(result["status"], "NO_REFERENCES_DECLARED")

    def test_protected_sources_rejected(self):
        protected = dict(self.case)
        protected["sources"] = [{
            "ref": "B_SEALED/data.json", "sha256": "a"*64
        }]
        protected["allowed_evidence_refs"] = ["B_SEALED/data.json"]
        with self.assertRaises(AgentError):
            bind_source_refs(self.root, protected, ["B_SEALED/data.json"])

    def test_cli_evidence_binding_success_and_reject_unknown(self):
        packet_path = self.path / "packet.json"
        manifest_path = self.path / "case.json"
        manifest_path.write_text(json.dumps(self.case), encoding="utf-8")
        packet_path.write_text(json.dumps(self.packet), encoding="utf-8")
        cmd = [
            sys.executable, "-m", "pdrw_agent.science.cli",
            "decision", "--packet", str(packet_path),
            "--evidence-root", str(self.root),
            "--evidence-manifest", str(manifest_path)
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["source_binding"]["status"],
                         "SOURCE_BYTES_MATCHED_ONLY")
        self.packet["claim_evidence_refs"] = ["future.md"]
        packet_path.write_text(json.dumps(self.packet), encoding="utf-8")
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 3, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["status"], "EVIDENCE_BINDING_FAILED")

    def test_cli_requires_both_source_options(self):
        packet_path = self.path / "packet.json"
        packet_path.write_text(json.dumps(self.packet), encoding="utf-8")
        p = subprocess.run([
            sys.executable, "-m", "pdrw_agent.science.cli",
            "decision", "--packet", str(packet_path),
            "--evidence-root", str(self.root)
        ], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)["error_code"], "EVIDENCE_CONFIG_INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
