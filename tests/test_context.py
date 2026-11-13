"""Check the wrapper only; PD-RW's own science/authorization tests live in PD-RW."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "pd-rw-research" / "scripts" / "context.py"


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.rules = root / "pd-rw"
        self.rules.mkdir()
        (self.rules / "AGENTS.md").write_text(
            "# Agent\n## 2. Routing\n"
            "| Task | Authority |\n| --- | --- |\n"
            "| DEV 算法/实验/负结果 | [EXPERIMENT_LOOP.md](EXPERIMENT_LOOP.md) 或 [ALGORITHM_ENGINEERING.md](ALGORITHM_ENGINEERING.md) |\n"
            "| 出图 | [FIGURE_POLICY.md](FIGURE_POLICY.md) |\n"
            "## 3. End\n", encoding="utf-8"
        )
        for path in ("WORKFLOW.md", "EXPERIMENT_LOOP.md",
                     "ALGORITHM_ENGINEERING.md", "FIGURE_POLICY.md"):
            (self.rules / path).write_text("# dummy\n", encoding="utf-8")
        (self.rules / "core").mkdir()
        (self.rules / "core" / "__init__.py").write_text("", encoding="utf-8")
        (self.rules / "core" / "execution_preflight.py").write_text(
            "import json\nprint(json.dumps({'decision':'UNKNOWN','reason':'UNAUTHENTICATED'}))\n",
            encoding="utf-8",
        )
        (self.rules / "core" / "delivery_check.py").write_text(
            "import json\nprint(json.dumps({'result':'PASS_PATHS_ONLY'}))\n",
            encoding="utf-8",
        )
        self.packet = root / "packet.json"
        self.packet.write_text(json.dumps({"action": "READ_SEALED", "approved": True}),
                               encoding="utf-8")

    def call(self, *args):
        p = subprocess.run([sys.executable, str(SCRIPT), *args,
                            "--workflow-root", str(self.rules)],
                           text=True, capture_output=True, check=False)
        return p.returncode, json.loads(p.stdout)

    def test_route_is_sourced_from_live_agents(self):
        code, data = self.call("route", "--topic", "DEV 算法")
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "ROUTE_FOUND")
        self.assertEqual(data["matches"][0]["rule_paths"],
                         ["EXPERIMENT_LOOP.md", "ALGORITHM_ENGINEERING.md"])
        self.assertTrue(data["no_authorization_granted"])

    def test_route_lists_available_topics_when_missing(self):
        code, data = self.call("route", "--topic", "not found")
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "ROUTE_SELECTION_REQUIRED")
        self.assertEqual(data["matches"], [])

    def test_action_review_never_authenticates_approval(self):
        code, data = self.call("action-review", "--packet", str(self.packet))
        self.assertEqual(code, 0)
        self.assertEqual(data["status"], "ADVISORY_ONLY")
        self.assertFalse(data["original_user_permission_authenticated"])
        self.assertFalse(data["trusted_tool_interceptor_connected"])
        self.assertEqual(data["pd_rw_action_result"]["decision"], "UNKNOWN")

    def test_delivery_review_is_only_path_check(self):
        code, data = self.call("delivery-review",
                               "--output-root", str(self.rules),
                               "--primary", "output.txt")
        self.assertEqual(code, 0)
        self.assertEqual(data["pd_rw_delivery_result"]["result"],
                         "PASS_PATHS_ONLY")
        self.assertFalse(data["scientific_truth_verified"])

    def test_missing_authoritative_route_file_is_not_invented(self):
        (self.rules / "EXPERIMENT_LOOP.md").unlink()
        code, data = self.call("route", "--topic", "DEV")
        self.assertEqual(code, 0)
        self.assertEqual(data["matches"][0]["rule_paths"],
                         ["ALGORITHM_ENGINEERING.md"])


if __name__ == "__main__":
    unittest.main()
