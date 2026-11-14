"""v0.7.5 compact recovery and evidence-preserving visibility tests."""
import json
import tempfile
import unittest
from pathlib import Path
from pdrw_agent.config import Settings
from pdrw_agent.runtime.recovery import get_resume_context
from pdrw_agent.integrations.mcp_server import tools_for_profile


class CoreConvergenceTests(unittest.TestCase):
    def test_profile_tool_selection_has_no_implicit_host_registration(self):
        core = tools_for_profile("minimal")
        research = tools_for_profile("research")
        diagnostic = tools_for_profile("diagnostic")
        self.assertEqual((len(core), len(research), len(diagnostic)), (11, 17, 20))
        self.assertTrue(core < research < diagnostic)
        self.assertNotIn("get_host_diagnostic_status", research)
        self.assertIn("audit_scientific_experiment", research)
        with self.assertRaises(ValueError):
            tools_for_profile("unrestricted")

    def test_resume_compact_preserves_unsafe_recovery_boundaries(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            rules = base / "rules"
            rules.mkdir()
            for name in ("AGENTS.md", "WORKFLOW.md"):
                (rules / name).write_text("# example", encoding="utf-8")
            project = base / "project"
            project.mkdir()
            (project / "STATE.json").write_text(json.dumps({
                "schema_version": "1.4", "project_id": "source-id",
                "active_task_id": "task-1", "latest_valid_run_id": None,
                "last_event_id": None, "evidence_refs": [],
            }), encoding="utf-8")
            (project / "EVENTS.jsonl").write_text("", encoding="utf-8")
            (project / "RESEARCH_RECORD.md").write_text(
                "## 0. Snapshot\\nCurrent task\\n## 1. History\\n", encoding="utf-8")
            registry = base / "map.json"
            registry.write_text(json.dumps({"schema_version": 1, "projects": {
                "demo": {"root": str(project),
                         "expected_state_project_id": "source-id"}
            }}), encoding="utf-8")
            settings = Settings.load(str(registry), str(rules))
            full = get_resume_context(settings, "demo")
            compact = get_resume_context(settings, "demo", detail_level="compact")
            self.assertEqual(compact["status"], full["status"])
            self.assertEqual(compact["scientific_context"]["active_task_id_declared"], "task-1")
            self.assertFalse(compact["authorization_verified"])
            self.assertFalse(compact["restart_permitted"])
            self.assertFalse(compact["next_action_hint"]["execution_authorized"])
            self.assertNotIn("host_fixed_cpu_checkpoints", compact)
            self.assertIn("host_fixed_cpu_checkpoints", full)
            self.assertLess(len(json.dumps(compact)), len(json.dumps(full)))
            with self.assertRaises(ValueError):
                get_resume_context(settings, "demo", detail_level="wrong")

    def test_incomplete_project_preserves_blocker_and_readonly_review(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            rules = base / "rules"
            rules.mkdir()
            for name in ("AGENTS.md", "WORKFLOW.md"):
                (rules / name).write_text("# authority", encoding="utf-8")
            project = base / "project"
            project.mkdir()
            config = base / "map.json"
            config.write_text(json.dumps({"schema_version":1,"projects":{
                "demo":{"root":str(project)}
            }}), encoding="utf-8")
            out = get_resume_context(Settings.load(str(config),str(rules)), "demo",
                                     detail_level="compact")
            self.assertEqual(out["status"], "BLOCKED_INCOMPLETE_CONTEXT")
            self.assertEqual(out["next_action_hint"]["action"],
                             "RECONCILE_AFFECTED_ORIGINAL_SOURCES")
            self.assertTrue(out["next_action_hint"][
                "independent_permitted_read_only_review_allowed"])
            self.assertFalse(out["next_action_hint"]["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
