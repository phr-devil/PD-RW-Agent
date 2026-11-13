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

if __name__ == "__main__":
    unittest.main()
