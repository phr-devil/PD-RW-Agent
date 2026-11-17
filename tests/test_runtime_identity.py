"""Runtime identity is available in existing bounded context responses."""
import json
import tempfile
import tomllib
import unittest
from pathlib import Path

from pdrw_agent import __version__
from pdrw_agent.config import Settings
from pdrw_agent.runtime_identity import capture_runtime_identity
from pdrw_agent.service import ResearchService


class BuildIdentityTests(unittest.TestCase):
    def test_distribution_version_matches_package_source(self):
        repo = Path(__file__).resolve().parents[1]
        with (repo / "pyproject.toml").open("rb") as fp:
            declared = tomllib.load(fp)["project"]["version"]
        self.assertEqual(declared, __version__)

    def test_identity_has_bounded_snapshot_and_no_science_claim(self):
        identity = capture_runtime_identity()
        self.assertEqual(identity["reported_agent_version"], __version__)
        self.assertEqual(identity["source_snapshot_status"], "CAPTURED")
        self.assertEqual(len(identity["source_snapshot_sha256"]), 64)
        self.assertFalse(identity["loaded_bytecode_attested"])
        self.assertFalse(identity["mcp_host_reloaded_attested"])

    def test_recovery_and_context_report_same_service_snapshot(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        rules = base / "rules"
        rules.mkdir()
        for name in ("AGENTS.md", "WORKFLOW.md"):
            (rules / name).write_text("# fixture", encoding="utf-8")
        project = base / "project"
        project.mkdir()
        (project / "STATE.md").write_text("PROJECT_ID: 44\n", encoding="utf-8")
        (project / "RESEARCH_RECORD.md").write_text(
            "## 0. Snapshot\nnot scientifically verified\n", encoding="utf-8")
        config = base / "map.json"
        config.write_text(json.dumps({"schema_version": 1, "projects": {
            "44": {"root": str(project), "state": "STATE.md",
                   "expected_state_project_id": "44"}}}), encoding="utf-8")
        service = ResearchService(Settings.load(str(config), str(rules)))
        context = service.call("get_project_context", project_id="44")
        resume = service.call("get_resume_context", project_id="44", detail_level="compact")
        self.assertEqual(context["agent_runtime"], resume["agent_runtime"])
        self.assertEqual(context["agent_runtime"], service.runtime_identity)
        self.assertFalse(resume["authorization_verified"])


if __name__ == "__main__":
    unittest.main()
