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

    def test_structured_memory_retains_failure_boundaries(self):
        index = self.rules / "LESSONS" / "CASE_REGISTRY.md"
        index.write_text(
            "| CASE_ID / 号（非强制唯一编号） | 已有证据与真实结果（严格限定义） | 各成功轴 / 当前边界 | 来源 |\n"
            "|---|---|---|---|\n"
            "| `TACTILE-X` | 触觉数据 分组泄漏 | `INVALID_EXPERIMENT`；不能推广到其他数据集 | `CHAT` |\n"
            "| `IMU-Y` | 跨人数据 合法对照 | `ALGO_DEV_POSITIVE`；仅DEV成立 | `REPORT` |\n",
            encoding="utf-8")
        item = self.service.call("search_research_memory", query="TACTILE-X")
        self.assertEqual(item["status"], "MATCHES_FOUND")
        self.assertEqual(item["matches"][0]["case_id"], "TACTILE-X")
        self.assertIn("INVALID_EXPERIMENT", item["matches"][0]["declared_status_tags"])
        self.assertFalse(item["matches"][0]["original_run_verified"])
        self.assertFalse(item["matches"][0]["premise_equivalence_verified"])

    def test_markdown_project_id_collision_is_not_ignored(self):
        (self.project / "STATE.md").write_text(
            "PROJECT_ID: different-project\\nACTIVE_TASK: demo\\n", encoding="utf-8")
        config = self.settings.project_map
        config.write_text(json.dumps({"schema_version": 1, "projects": {
            "37": {"root": str(self.project),
                   "expected_state_project_id": "approved-project"}}}),
            encoding="utf-8")
        result = self.service.call("get_project_context", project_id="37")
        self.assertEqual(result["status"], "IDENTITY_CONFLICT")

    def test_sqlite_readonly_status_cannot_modify_receipts(self):
        import sqlite3
        from pdrw_agent.runtime.receipts import _open
        path = self.project.parent / "readonly-receipts.sqlite"
        db = sqlite3.connect(str(path))
        db.execute("CREATE TABLE sample (id INTEGER)")
        db.commit()
        db.close()
        with _open(path, write=False) as readonly:
            self.assertEqual(readonly.execute("SELECT COUNT(*) FROM sample").fetchone()[0], 0)
            with self.assertRaises(sqlite3.OperationalError):
                readonly.execute("INSERT INTO sample VALUES (1)")
        with sqlite3.connect(str(path)) as reopened:
            self.assertEqual(reopened.execute("SELECT COUNT(*) FROM sample").fetchone()[0], 0)

    def test_missing_index_distinct_from_no_runs(self):
        data = self.service.call("find_experiment_evidence", project_id="37")
        self.assertEqual(data["status"], "EVIDENCE_INDEX_MISSING")
        self.assertEqual(data["index_status"], "MISSING")


if __name__ == "__main__":
    unittest.main()
