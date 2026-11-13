"""v0.6 bounded, synthetic read-only state and evidence tests."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.config import Settings
from pdrw_agent.projects import get_project_context
from pdrw_agent.rules import get_applicable_rules
from pdrw_agent.service import ResearchService


class V06AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.rules = base / "rules"
        self.rules.mkdir()
        (self.rules / "WORKFLOW.md").write_text("# PD-RW v1.13\n", encoding="utf-8")
        (self.rules / "AGENTS.md").write_text(
            "## 2. Route\n| Block | Owner |\n| --- | --- |\n"
            "| DEV 算法/实验/负结果 | [Loop](EXPERIMENT_LOOP.md) |\n"
            "| 跨项目成功/失败/身份追溯 | [Cases](LESSONS/CASE_REGISTRY.md) |\n"
            "## 3. End\n", encoding="utf-8")
        (self.rules / "EXPERIMENT_LOOP.md").write_text("loop", encoding="utf-8")
        (self.rules / "LESSONS").mkdir()
        (self.rules / "LESSONS" / "CASE_REGISTRY.md").write_text("index", encoding="utf-8")
        self.project = base / "frozen"
        self.project.mkdir()
        (self.project / "RESEARCH_RECORD.md").write_text(
            "# record\nPD-RW v1.12\n## 1. 当前状态快照\n"
            "Project 37, stop here\n## 2. History\n", encoding="utf-8")
        part = self.project / "_work"
        part.mkdir()
        (part / "PROTOCOL.md").write_bytes(b"frozen protocol\n")
        sha = hashlib.sha256((part / "PROTOCOL.md").read_bytes()).hexdigest()
        (part / "FROZEN_HASHES.sha256").write_text(
            f"{sha}  PROTOCOL.md\n{sha}  absent.json\n", encoding="utf-8")
        cfg = base / "map.json"
        cfg.write_text(json.dumps({"schema_version": 1, "projects": {
            "37": {"root": str(self.project)}}}), encoding="utf-8")
        self.settings = Settings.load(str(cfg), str(self.rules))
        self.service = ResearchService(self.settings)

    def test_partial_recovery_preserves_unknowns(self):
        context = get_project_context(self.settings, "37")
        self.assertEqual(context["status"], "INCOMPLETE_CONTEXT")
        self.assertIn("当前状态快照", context["snapshot_excerpt"])
        audit = self.service.call("audit_project_state", project_id="37")
        self.assertEqual(audit["status"], "PARTIAL_RECOVERY")
        self.assertIn("STATE_MISSING", audit["blockers"])
        self.assertIn("EVENTS_MISSING", audit["blockers"])
        self.assertIn("DECLARED_RULE_VERSION_DIFFERS", audit["blockers"])
        self.assertEqual(audit["manifest_audit"]["counts"]["declared"], 2)
        self.assertEqual(audit["manifest_audit"]["counts"]["matched"], 1)
        self.assertEqual(audit["manifest_audit"]["counts"]["missing"], 1)
        self.assertFalse(audit["execution_authorized"])
        self.assertFalse(audit["scientific_claims_verified"])
        self.assertFalse((self.project / "STATE.md").exists())

    def test_hash_mismatch_and_protected_reference_do_not_get_read(self):
        directory = self.project / "_work"
        (directory / "PROTOCOL.md").write_bytes(b"changed")
        content = (directory / "FROZEN_HASHES.sha256").read_text(encoding="utf-8")
        digest = hashlib.sha256(b"protected secret").hexdigest()
        (directory / "FROZEN_HASHES.sha256").write_text(
            content + f"{digest}  ../SEALED/secrets.bin\n", encoding="utf-8")
        audit = self.service.call("audit_project_state", project_id="37")
        counts = audit["manifest_audit"]["counts"]
        self.assertEqual(counts["mismatched"], 1)
        self.assertEqual(counts["unsafe"], 1)

    def test_no_hidden_project_write(self):
        before = {p.relative_to(self.project).as_posix(): p.read_bytes()
                  for p in self.project.rglob("*") if p.is_file()}
        self.service.call("audit_project_state", project_id="37")
        after = {p.relative_to(self.project).as_posix(): p.read_bytes()
                 for p in self.project.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_rules_human_topic_produces_suggestions_not_invented_policy(self):
        result = get_applicable_rules(self.settings, "DEV experiment recovery")
        self.assertEqual(result["status"], "ROUTE_FOUND")
        self.assertIn("EXPERIMENT_LOOP.md", result["matches"][0]["rule_paths"])
        unknown = get_applicable_rules(self.settings, "unmatched request")
        self.assertEqual(unknown["status"], "ROUTE_SELECTION_REQUIRED")
        self.assertEqual(unknown["matches"], [])
        self.assertTrue(unknown["available_topics"])

    def test_missing_index_distinct_from_no_runs(self):
        data = self.service.call("find_experiment_evidence", project_id="37")
        self.assertEqual(data["status"], "EVIDENCE_INDEX_MISSING")
        self.assertEqual(data["index_status"], "MISSING")


if __name__ == "__main__":
    unittest.main()
