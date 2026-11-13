"""Real MCP v2 in-process handshake. Optional locally, required in CI."""
import asyncio
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from pdrw_agent.config import Settings

@unittest.skipUnless(importlib.util.find_spec("mcp") is not None,
                     "Install optional MCP SDK for wire-level tests")
class MCPTests(unittest.TestCase):
    def test_registered_tools_and_tool_call(self):
        from mcp import Client
        from pdrw_agent.integrations.mcp_server import create_server
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            workflow = root / "rules"
            workflow.mkdir()
            for name in ("AGENTS.md", "WORKFLOW.md"):
                (workflow / name).write_text("# minimal", encoding="utf-8")
            mapping = root / "project-map.json"
            mapping.write_text('{"schema_version":1,"projects":{}}', encoding="utf-8")
            server = create_server(Settings.load(str(mapping), str(workflow)))

            async def do_test():
                async with Client(server) as client:
                    registered = await client.list_tools()
                    names = {t.name for t in registered.tools}
                    self.assertEqual(names, {
                        "get_project_context", "get_applicable_rules",
                        "search_research_memory", "find_experiment_evidence",
                        "check_duplicate_experiment",
                        "get_resume_context", "get_execution_status",
                        "begin_operation_receipt", "checkpoint_operation_receipt",
                        "preview_experiment_record", "prepare_handoff",
                    })
                    self.assertNotIn("record_experiment_result", names)
                    response = await client.call_tool(
                        "get_project_context", {"project_id": "missing"})
                    self.assertFalse(response.is_error)
                    text = str(response.structured_content or response.content)
                    self.assertIn("PROJECT_NOT_REGISTERED", text)

            asyncio.run(do_test())

    def test_v05_mcp_receipt_resume_roundtrip(self):
        from unittest.mock import patch
        from mcp import Client
        from pdrw_agent.integrations.mcp_server import create_server
        import json

        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            rule_root = base / "rules"
            rule_root.mkdir()
            for name in ("AGENTS.md", "WORKFLOW.md"):
                (rule_root / name).write_text("# synthetic", encoding="utf-8")
            project = base / "science"
            project.mkdir()
            (project / "STATE.json").write_text(json.dumps({
                "schema_version": "1.4", "project_id": "science",
                "active_task_id": "t1", "latest_valid_run_id": None,
                "last_event_id": None, "evidence_refs": []
            }), encoding="utf-8")
            (project / "RESEARCH_RECORD.md").write_text(
                "## 0. Snapshot\\nReady for test\\n## 1. History\\n",
                encoding="utf-8")
            cfg = base / "config"
            cfg.mkdir()
            registry = cfg / "projects.json"
            registry.write_text(json.dumps({"schema_version": 1, "projects": {
                "demo": {"root": str(project),
                         "expected_state_project_id": "science"}
            }}), encoding="utf-8")
            settings = Settings.load(str(registry), str(rule_root))

            async def exercise():
                server = create_server(settings)
                async with Client(server) as client:
                    began = await client.call_tool("begin_operation_receipt", {
                        "project_id": "demo", "operation_id": "op-wire",
                        "task_id": "t1", "action": "DEV_EVALUATE"})
                    self.assertFalse(began.is_error)
                    self.assertIn("RECEIPT_CREATED",
                                  str(began.structured_content or began.content))
                    resumed = await client.call_tool("get_resume_context",
                                                     {"project_id": "demo"})
                    self.assertFalse(resumed.is_error)
                    self.assertIn("NEEDS_RECONCILIATION",
                                  str(resumed.structured_content or resumed.content))
                    checked = await client.call_tool("get_execution_status",
                                                     {"project_id": "demo"})
                    self.assertFalse(checked.is_error)
                    self.assertIn("op-wire",
                                  str(checked.structured_content or checked.content))
                    retry = await client.call_tool("begin_operation_receipt", {
                        "project_id": "demo", "operation_id": "op-wire",
                        "task_id": "t1", "action": "DEV_EVALUATE"})
                    self.assertIn("ALREADY_RECEIPTED",
                                  str(retry.structured_content or retry.content))

            with patch.dict(os.environ, {"PDRW_RUNTIME_DIR": str(base / "private")}):
                asyncio.run(exercise())

if __name__ == "__main__":
    unittest.main()
