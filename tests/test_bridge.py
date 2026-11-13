import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "skills" / "pd-rw-research" / "scripts" / "bridge.py"


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.rules = base / "pd-rw"
        self.rules.mkdir()
        (self.rules / "AGENTS.md").write_text("route", encoding="utf-8")
        (self.rules / "WORKFLOW.md").write_text("science", encoding="utf-8")
        self.project = base / "project"
        self.project.mkdir()
        (self.project / "STATE.md").write_text(
            "- ACTIVE_TASK: task-1\n- NEXT: validate-dev\n", encoding="utf-8"
        )
        (self.project / "RESEARCH_RECORD.md").write_text(
            "## 0. Current snapshot\n- Best: run-1\n## 1. History\nOLD_SECRET_HISTORY\n",
            encoding="utf-8",
        )
        self.mapping = base / "project-map.local.json"
        self.write_map()

    def write_map(self, state="STATE.md"):
        self.mapping.write_text(json.dumps({
            "schema_version": 1,
            "projects": {"demo": {
                "root": str(self.project),
                "state": state,
                "research_record": "RESEARCH_RECORD.md"
            }}
        }), encoding="utf-8")

    def call(self, *args):
        proc = subprocess.run(
            [sys.executable, str(BRIDGE), *args],
            text=True, capture_output=True, check=False,
        )
        return proc.returncode, json.loads(proc.stdout)

    def resume(self, project="demo"):
        return self.call(
            "resume", "--workflow-root", str(self.rules),
            "--project-id", project, "--project-map", str(self.mapping),
        )

    def test_doctor_is_read_only_local(self):
        code, data = self.call("doctor", "--workflow-root", str(self.rules))
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "OK")
        self.assertEqual(data["rule_version_status"], "RULE_VERSION_UNVERIFIED")
        self.assertEqual(data["authorization_status"], "NOT_AUTHENTICATED")

    def test_resume_bounds_context_and_never_authenticates(self):
        code, data = self.resume()
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "READY_FOR_SOURCE_REVIEW")
        self.assertIn("run-1", data["research_snapshot"])
        self.assertNotIn("OLD_SECRET_HISTORY", data["research_snapshot"])
        self.assertEqual(data["state_index"]["NEXT"], "validate-dev")
        self.assertEqual(data["original_user_authorization"], "UNVERIFIED")

    def test_unknown_project_fails_without_guess(self):
        code, data = self.resume("project-19")
        self.assertEqual(code, 2)
        self.assertEqual(data["error_code"], "INVALID_INPUT")

    def test_escape_is_rejected(self):
        self.write_map(state="../outside/STATE.md")
        code, data = self.resume()
        self.assertEqual(code, 2)
        self.assertEqual(data["error_code"], "INVALID_INPUT")

    def test_missing_authority_fails(self):
        (self.rules / "WORKFLOW.md").unlink()
        code, data = self.resume()
        self.assertEqual(code, 2)
        self.assertEqual(data["error_code"], "WORKFLOW_NOT_FOUND")

    def test_missing_record_stays_incomplete(self):
        (self.project / "RESEARCH_RECORD.md").unlink()
        code, data = self.resume()
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "INCOMPLETE_CONTEXT")
        self.assertIn("research_record", data["missing"])


if __name__ == "__main__":
    unittest.main()
