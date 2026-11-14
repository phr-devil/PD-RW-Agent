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
            server = create_server(Settings.load(str(mapping), str(workflow)), profile="diagnostic")

            async def do_test():
                async with Client(server) as client:
                    registered = await client.list_tools()
                    names = {t.name for t in registered.tools}
                    self.assertEqual(names, {
                        "get_project_context", "audit_project_state", "get_applicable_rules",
                        "preflight_execution_plan", "get_synthetic_job_status",
                        "get_host_diagnostic_status",
                        "reconstruct_project_history", "verify_run_evidence",
                        "audit_scientific_experiment", "review_evidenced_lesson",
                        "review_lesson_applicability",
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

    def test_research_and_minimal_profiles_hide_unselected_wire_tools(self):
        from mcp import Client
        from pdrw_agent.integrations.mcp_server import create_server
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            rules = base / "rules"
            rules.mkdir()
            for name in ("AGENTS.md", "WORKFLOW.md"):
                (rules / name).write_text("# original", encoding="utf-8")
            mapping = base / "map.json"
            mapping.write_text('{"schema_version":1,"projects":{}}', encoding="utf-8")
            settings = Settings.load(str(mapping), str(rules))

            async def check():
                for profile, expected_count in (("minimal", 11), ("research", 17)):
                    async with Client(create_server(settings, profile=profile)) as client:
                        response = await client.list_tools()
                        names = {t.name for t in response.tools}
                        self.assertEqual(len(names), expected_count)
                        self.assertIn("get_resume_context", names)
                        self.assertNotIn("get_host_diagnostic_status", names)
                        self.assertEqual("audit_scientific_experiment" in names,
                                         profile == "research")
            asyncio.run(check())

    def test_registered_incomplete_project_triad_is_read_only(self):
        """Wire-level Python/MCP preflight: incomplete project blocks resume, rules still route."""
        import json
        from mcp import Client
        from pdrw_agent.integrations.mcp_server import create_server

        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            rule_root = base / "rules"
            rule_root.mkdir()
            (rule_root / "AGENTS.md").write_text(
                "## 2. Rules\n| Topic | Owner |\n| --- | --- |\n"
                "| DEV 算法/实验/负结果 | [Experimental](EXPERIMENT_LOOP.md) |\n"
                "## 3. Next\n", encoding="utf-8")
            (rule_root / "WORKFLOW.md").write_text("# science", encoding="utf-8")
            (rule_root / "EXPERIMENT_LOOP.md").write_text("# dev", encoding="utf-8")
            project = base / "frozen"
            project.mkdir()
            record = project / "RESEARCH_RECORD.md"
            record.write_text("## 0. Snapshot\nUnverified\n## 1. History\n", encoding="utf-8")
            registry = base / "project-map.json"
            registry.write_text(json.dumps({
                "schema_version": 1, "projects": {"37": {"root": str(project)}}
            }), encoding="utf-8")
            server = create_server(Settings.load(str(registry), str(rule_root)), profile="diagnostic")

            async def exercise():
                async with Client(server) as client:
                    context = await client.call_tool("get_project_context", {"project_id": "37"})
                    resume = await client.call_tool("get_resume_context", {"project_id": "37"})
                    rules = await client.call_tool("get_applicable_rules", {"topic": "DEV"})
                    history = await client.call_tool(
                        "reconstruct_project_history", {"project_id": "37"})
                    host_checkpoint = await client.call_tool(
                        "get_host_diagnostic_status", {
                            "project_id": "37", "operation_id": "dry-test-1"})
                    plan = await client.call_tool("preflight_execution_plan", {
                        "plan": {
                            "schema_version": "pdrw-exec-plan-v1",
                            "project_id": "37", "operation_id": "dry-test-1",
                            "task_id": "selftest", "profile": "CPU_SELFTEST_V1",
                            "scenario": "SUCCESS", "iterations": 10,
                            "timeout_seconds": 2, "network": False, "gpu": False}})
                    checkpoint = await client.call_tool(
                        "get_synthetic_job_status", {
                            "project_id": "37", "operation_id": "dry-test-1"})
                    run = await client.call_tool(
                        "verify_run_evidence", {"project_id": "37", "run_id": "r1"})
                    science = await client.call_tool(
                        "audit_scientific_experiment", {"project_id": "37", "run_id": "r1"})
                    evidenced = await client.call_tool(
                        "review_evidenced_lesson", {
                            "project_id": "37", "run_id": "r1",
                            "proposal": {"premise_id": "p1", "scope": {
                                "dataset_version": "D1", "evaluation_unit": "subject",
                                "group_split": "LOSO", "label_definition": "labels-v1",
                                "legal_inputs": "sensor", "metric": "MAE",
                                "comparison_reference": "b1"}}})
                    scope = {
                        "dataset_version": "D1", "label_definition": "L1",
                        "evaluation_unit": "subject", "group_split": "LOSO",
                        "legal_inputs": "IMU", "metric": "macro-F1",
                        "comparison_reference": "baseline"
                    }
                    lessons = await client.call_tool(
                        "review_lesson_applicability", {
                            "proposal": {"premise_id": "p1", "scope": scope},
                            "lessons": [{"premise_id": "p1", "scope": scope,
                                        "validity": "VALID_NEGATIVE",
                                        "evidence_refs": ["r1"]}]})
                    for response in (context, resume, rules, history, run, science,
                                     evidenced, lessons, plan, checkpoint, host_checkpoint):
                        self.assertFalse(response.is_error)
                    self.assertIn("INCOMPLETE_CONTEXT", str(context.structured_content or context.content))
                    self.assertIn("BLOCKED_INCOMPLETE_CONTEXT", str(resume.structured_content or resume.content))
                    self.assertIn("ROUTE_FOUND", str(rules.structured_content or rules.content))
                    self.assertIn("EXPERIMENT_LOOP.md", str(rules.structured_content or rules.content))
                    self.assertIn("HISTORY_SOURCES_MISSING",
                                  str(history.structured_content or history.content))
                    self.assertIn("BLOCKED_PROJECT_CONTEXT",
                                  str(plan.structured_content or plan.content))
                    self.assertIn("SYNTHETIC_JOB_NOT_FOUND",
                                  str(checkpoint.structured_content or checkpoint.content))
                    self.assertIn("HOST_JOB_NOT_FOUND",
                                  str(host_checkpoint.structured_content or host_checkpoint.content))
                    self.assertIn("RUN_HISTORY_NOT_ATTESTABLE",
                                  str(run.structured_content or run.content))
                    self.assertIn("AUDIT_PREREQUISITE_UNVERIFIED",
                                  str(science.structured_content or science.content))
                    self.assertIn("LESSON_RUN_NOT_ATTESTABLE",
                                  str(evidenced.structured_content or evidenced.content))
                    self.assertIn("EXACT_DECLARED_SCOPE_CANDIDATE",
                                  str(lessons.structured_content or lessons.content))

            asyncio.run(exercise())
            self.assertFalse((project / "STATE.md").exists())
            self.assertEqual(record.read_text(encoding="utf-8"),
                             "## 0. Snapshot\nUnverified\n## 1. History\n")

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
                "## 0. Snapshot\nReady for test\n## 1. History\n",
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
                server = create_server(settings, profile="diagnostic")
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
