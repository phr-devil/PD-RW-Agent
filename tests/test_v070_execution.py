"""v0.7 fixed synthetic CPU execution: idempotency and recovery boundary.

No real research execution, downloads, GPU, arbitrary model-supplied commands,
SEALED access, or model-based authorization in these tests.
"""
import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pdrw_agent.config import Settings
from pdrw_agent.runtime.plan import preflight_execution_plan
from pdrw_agent.runtime.synthetic_executor import (
    get_synthetic_job_status, run_synthetic_in_host
)
from pdrw_agent.service import ResearchService


def fixture_plan(**kwargs):
    base = {
        "schema_version": "pdrw-exec-plan-v1",
        "project_id": "demo", "operation_id": "synthetic-op-1",
        "task_id": "selftest", "profile": "CPU_SELFTEST_V1",
        "scenario": "SUCCESS", "iterations": 2000, "timeout_seconds": 2,
        "network": False, "gpu": False,
    }
    base.update(kwargs)
    return base


class SyntheticHostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.project = base / "project"
        self.project.mkdir()
        self.rules = base / "workflow"
        self.rules.mkdir()
        (self.rules / "AGENTS.md").write_text("# routes", encoding="utf-8")
        (self.rules / "WORKFLOW.md").write_text("# PD-RW v1.13", encoding="utf-8")
        (self.project / "RESEARCH_RECORD.md").write_text(
            "## 0. Snapshot\nsynthetic no active Task\n## 1. Historic\n",
            encoding="utf-8")
        (self.project / "STATE.json").write_text(json.dumps({
            "schema_version": "1.4", "project_id": "synthetic-project",
            "active_task_id": None, "latest_valid_run_id": None,
            "last_event_id": None, "evidence_refs": [],
        }), encoding="utf-8")
        (self.project / "EVENTS.jsonl").write_text("", encoding="utf-8")
        cfg = base / "cfg"
        cfg.mkdir()
        path = cfg / "mapping.json"
        path.write_text(json.dumps({"schema_version": 1, "projects": {
            "demo": {"root": str(self.project),
                     "expected_state_project_id": "synthetic-project"},
        }}), encoding="utf-8")
        self.settings = Settings.load(str(path), str(self.rules))
        self.svc = ResearchService(self.settings)
        self.private = base / "private"
        env = patch.dict(os.environ, {"PDRW_RUNTIME_DIR": str(self.private)})
        env.start()
        self.addCleanup(env.stop)

    def snapshot(self):
        return {p.relative_to(self.project).as_posix(): p.read_bytes()
                for p in self.project.rglob("*") if p.is_file()}

    def test_preflight_is_readonly_and_never_authorizes_science(self):
        before = self.snapshot()
        result = self.svc.call("preflight_execution_plan", plan=fixture_plan())
        self.assertEqual(result["status"], "HOST_ONLY_SYNTHETIC_PREFLIGHT_READY")
        self.assertFalse(result["execution_authorized"])
        self.assertFalse(result["original_authorization_verified"])
        self.assertTrue(result["synthetic_only"])
        self.assertEqual(before, self.snapshot())
        self.assertFalse(self.private.exists())

    def test_plan_schema_refuses_arbitrary_command_and_gpu(self):
        for packet in (
            fixture_plan(command="python train.py"),
            fixture_plan(profile="DEV_TRAIN"),
            fixture_plan(gpu=True),
            fixture_plan(network=True),
            fixture_plan(iterations=1000001),
            fixture_plan(timeout_seconds=99),
            fixture_plan(operation_id="../escape"),
            fixture_plan(timeout_seconds=True),
        ):
            self.assertEqual(self.svc.call("preflight_execution_plan", plan=packet)["status"],
                             "ERROR")
        self.assertFalse(self.private.exists())

    def test_state_divergence_blocks_preflight_and_execution(self):
        (self.project / "EVENTS.jsonl").write_text(
            '{"event_id":"e1","project_id":"synthetic-project","kind":"note",'
            '"prev_event_id":null}\n', encoding="utf-8")
        plan = fixture_plan()
        self.assertEqual(preflight_execution_plan(self.settings, plan)["status"],
                         "BLOCKED_PROJECT_HISTORY")
        attempted = run_synthetic_in_host(self.settings, plan)
        self.assertFalse(attempted["actual_synthetic_subprocess_executed"])
        self.assertFalse(self.private.exists())

    def test_complete_one_fixed_cpu_selftest_and_idempotent_retry(self):
        before = self.snapshot()
        initial = get_synthetic_job_status(self.settings, "demo", "synthetic-op-1")
        self.assertEqual(initial["status"], "SYNTHETIC_JOB_NOT_FOUND")
        result = run_synthetic_in_host(self.settings, fixture_plan())
        self.assertEqual(result["status"], "SYNTHETIC_EXECUTION_COMPLETED", result)
        self.assertEqual(result["phase"], "COMPLETED")
        self.assertTrue(result["actual_synthetic_subprocess_executed"])
        self.assertEqual(result["attempt_count"], 1)
        repeated = run_synthetic_in_host(self.settings, fixture_plan())
        self.assertEqual(repeated["status"], "ALREADY_COMPLETED_NO_REEXECUTION")
        self.assertFalse(repeated["actual_synthetic_subprocess_executed"])
        status = get_synthetic_job_status(self.settings, "demo", "synthetic-op-1")
        self.assertEqual(status["job"]["attempt_count"], 1)
        self.assertEqual(status["job"]["output_integrity"], "MATCH")
        resume = self.svc.call("get_resume_context", project_id="demo")
        self.assertEqual(resume["synthetic_selftest_checkpoints"]["status"],
                         "SYNTHETIC_JOBS_FOUND")
        self.assertFalse(
            resume["synthetic_selftest_checkpoints"]["reconciliation_required"])
        self.assertEqual(before, self.snapshot())  # no project science writes
        self.assertFalse((self.project / "Run.json").exists())

    def test_completed_checkpoint_requires_surviving_output_bytes(self):
        run_synthetic_in_host(self.settings, fixture_plan())
        key = hashlib.sha256(b"demo").hexdigest()
        output = self.private / "synthetic_jobs" / key / "synthetic-op-1" / "result.json"
        self.assertTrue(output.is_file())
        output.write_text('{"tampered":true}', encoding="utf-8")
        check = get_synthetic_job_status(self.settings, "demo", "synthetic-op-1")
        self.assertEqual(check["status"], "SYNTHETIC_CHECKPOINT_ARTIFACT_MISMATCH")
        self.assertEqual(check["job"]["output_integrity"], "CHANGED_OR_MISSING")
        again = run_synthetic_in_host(self.settings, fixture_plan())
        self.assertFalse(again["actual_synthetic_subprocess_executed"])
        self.assertEqual(again["job"]["attempt_count"], 1)

    def test_same_operation_id_different_plan_is_conflict_not_reexecution(self):
        run_synthetic_in_host(self.settings, fixture_plan())
        conflict = run_synthetic_in_host(self.settings, fixture_plan(iterations=3000))
        self.assertEqual(conflict["status"], "SYNTHETIC_PLAN_CONFLICT")
        self.assertFalse(conflict["actual_synthetic_subprocess_executed"])

    def test_nonzero_exit_is_terminal_and_never_auto_retried(self):
        plan = fixture_plan(scenario="EXIT_NONZERO", operation_id="fail-1")
        result = run_synthetic_in_host(self.settings, plan)
        self.assertEqual(result["phase"], "FAILED_NONZERO_EXIT", result)
        next_attempt = run_synthetic_in_host(self.settings, plan)
        self.assertEqual(next_attempt["status"],
                         "RECONCILIATION_REQUIRED_NO_AUTOMATIC_RESTART")
        self.assertEqual(next_attempt["job"]["attempt_count"], 1)

    def test_timeout_is_terminal_with_no_blind_restart(self):
        plan = fixture_plan(scenario="SLEEP", operation_id="sleep-1",
                            timeout_seconds=1)
        result = run_synthetic_in_host(self.settings, plan)
        self.assertEqual(result["phase"], "TIMED_OUT", result)
        status = get_synthetic_job_status(self.settings, "demo", "sleep-1")
        self.assertEqual(status["status"], "SYNTHETIC_JOB_TERMINAL_RECORDED")
        self.assertFalse(status["process_liveness_verified"])

    def test_interrupted_host_marks_running_unverified(self):
        with patch("pdrw_agent.runtime.synthetic_executor.preflight_execution_plan",
                   return_value={"status": "HOST_ONLY_SYNTHETIC_PREFLIGHT_READY"}):
            with patch("pdrw_agent.runtime.synthetic_executor.subprocess.run",
                       side_effect=KeyboardInterrupt()):
                with self.assertRaises(KeyboardInterrupt):
                    run_synthetic_in_host(self.settings,
                                          fixture_plan(operation_id="crash-1"))
        record = get_synthetic_job_status(self.settings, "demo", "crash-1")
        self.assertEqual(record["status"],
                         "RECONCILIATION_REQUIRED_NO_AUTOMATIC_RESTART")
        resume = self.svc.call("get_resume_context", project_id="demo")
        self.assertTrue(
            resume["synthetic_selftest_checkpoints"]["reconciliation_required"])
        # This engineering-only checkpoint does not block unrelated science
        # or claim that the interrupted process is alive.
        self.assertEqual(resume["status"], "SOURCE_REVIEW_REQUIRED")
        again = run_synthetic_in_host(
            self.settings, fixture_plan(operation_id="crash-1"))
        self.assertFalse(again["actual_synthetic_subprocess_executed"])
        self.assertEqual(again["job"]["attempt_count"], 1)

    def test_status_query_is_readonly_for_existing_legacy_receipt_db(self):
        self.private.mkdir()
        database = self.private / "runtime.sqlite"
        db = sqlite3.connect(str(database))
        db.execute("CREATE TABLE operations (dummy TEXT)")
        db.commit()
        db.close()
        before = database.read_bytes()
        status = self.svc.call("get_synthetic_job_status",
                               project_id="demo", operation_id="x")
        self.assertEqual(status["status"], "SYNTHETIC_JOB_NOT_FOUND")
        self.assertEqual(before, database.read_bytes())

    def test_get_status_never_runs_worker_and_checks_project_map(self):
        status = self.svc.call("get_synthetic_job_status",
                               project_id="demo", operation_id="x")
        self.assertEqual(status["status"], "SYNTHETIC_JOB_NOT_FOUND")
        unknown = self.svc.call("get_synthetic_job_status",
                                project_id="unregistered", operation_id="x")
        self.assertEqual(unknown["status"], "ERROR")
        self.assertEqual(unknown["error_code"], "PROJECT_NOT_REGISTERED")


if __name__ == "__main__":
    unittest.main()
