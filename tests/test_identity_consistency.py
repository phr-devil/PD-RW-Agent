"""Project identity metadata must agree across context and readiness."""
import json
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.config import Settings
from pdrw_agent.project_identity import parse_markdown_project_id
from pdrw_agent.projects import get_project_context
from pdrw_agent.runtime.readiness import inspect_project_readiness


class IdentityConsistencyTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        base = Path(work.name)
        rules = base / "rules"
        rules.mkdir()
        (rules / "AGENTS.md").write_text("# router", encoding="utf-8")
        (rules / "WORKFLOW.md").write_text("# authority", encoding="utf-8")
        project = base / "project"
        project.mkdir()
        (project / "RESEARCH_RECORD.md").write_text(
            "## 0. Snapshot\nCurrent source\n## 1. History\n", encoding="utf-8")
        cfg = base / "map.json"
        cfg.write_text(json.dumps({"schema_version": 1, "projects": {
            "44": {"root": str(project), "state": "STATE.md",
                   "expected_state_project_id": "44"}}}), encoding="utf-8")
        self.project = project
        self.settings = Settings.load(str(cfg), str(rules))

    def test_real_world_markdown_variants(self):
        variants = (
            "PROJECT_ID: 44\n",
            "PROJECT_ID = 44\n",
            "**项目身份**：PROJECT_ID = 44\n",
            "- **项目身份**：PROJECT_ID = 44\n",
            "**PROJECT_ID**: 44\n",
            "PROJECT_ID: \x6044\x60\n",
        )
        for content in variants:
            with self.subTest(content=content):
                (self.project / "STATE.md").write_text(content, encoding="utf-8")
                context = get_project_context(self.settings, "44")
                self.assertEqual(context["status"], "SOURCE_REVIEW_REQUIRED")
                self.assertEqual(context["state_index"]["PROJECT_ID"], "44")
                self.assertEqual(context["markdown_identity_parse_status"], "DECLARED")
                status = inspect_project_readiness(self.settings, "44")
                self.assertEqual(status["status"], "LEGACY_READ_ONLY")

    def test_wrong_project_id_blocks_affected_context(self):
        (self.project / "STATE.md").write_text(
            "**项目身份**：PROJECT_ID = 43\n", encoding="utf-8")
        self.assertEqual(get_project_context(self.settings, "44")["status"],
                         "IDENTITY_CONFLICT")
        self.assertEqual(inspect_project_readiness(self.settings, "44")["status"],
                         "STATE_IDENTITY_CONFLICT")

    def test_duplicate_conflicting_and_malformed_ids(self):
        for content in ("PROJECT_ID: 44\nPROJECT_ID = 43\n",
                        "PROJECT_ID: ?\n"):
            with self.subTest(content=content):
                self.assertEqual(parse_markdown_project_id(content)[1], "AMBIGUOUS")
                (self.project / "STATE.md").write_text(content, encoding="utf-8")
                self.assertEqual(get_project_context(self.settings, "44")["status"],
                                 "IDENTITY_CONFLICT")
                self.assertEqual(inspect_project_readiness(self.settings, "44")["status"],
                                 "STATE_IDENTITY_CONFLICT")

    def test_fenced_examples_and_prose_do_not_claim_identity(self):
        content = ("# project\nUnrelated project 43 is different.\n"
                   "~~~text\nPROJECT_ID: 43\n~~~\n")
        (self.project / "STATE.md").write_text(content, encoding="utf-8")
        ctx = get_project_context(self.settings, "44")
        self.assertEqual(ctx["markdown_identity_parse_status"], "MISSING")
        self.assertNotIn("PROJECT_ID", ctx["state_index"])
        self.assertEqual(ctx["identity"], "UNVERIFIED_REQUIRE_RAW_SOURCE")

    def test_machine_and_markdown_collision(self):
        (self.project / "STATE.md").write_text(
            "**项目身份**：PROJECT_ID = 43\n", encoding="utf-8")
        (self.project / "STATE.json").write_text(json.dumps(
            {"schema_version": "1.4", "project_id": "44"}), encoding="utf-8")
        self.assertEqual(inspect_project_readiness(self.settings, "44")["status"],
                         "STATE_IDENTITY_CONFLICT")


if __name__ == "__main__":
    unittest.main()
