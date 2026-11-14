"""v0.7.2 actual OS child diagnostic supervision and deny-by-default DEV.

No scientific DEV, GPUs, project files, user approval or SEALED are used.
"""
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from pdrw_agent.config import Settings
from pdrw_agent.host.authorization import preview_dev_admission
from pdrw_agent.host.isolation import assess_host_isolation, current_os_identity
from pdrw_agent.host.runner_registry import inspect_registered_runner
from pdrw_agent.host.supervisor import HostSupervisor, get_host_diagnostic_status
from pdrw_agent.runtime.receipts import _open
from pdrw_agent.service import ResearchService


def plan(**kw):
    p = {"schema_version": "pdrw-exec-plan-v1", "project_id": "demo",
         "operation_id": "host-test-1", "task_id": "task-a",
         "profile": "CPU_SELFTEST_V1", "scenario": "SUCCESS",
         "iterations": 500, "timeout_seconds": 4,
         "network": False, "gpu": False}
    p.update(kw)
    return p


class HostPilotTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        root = self.base / "project"
        root.mkdir()
        self.project = root
        (root / "STATE.json").write_text(json.dumps({
            "schema_version": "1.4", "project_id": "trusted-id",
            "active_task_id": None, "latest_valid_run_id": None,
            "last_event_id": None, "evidence_refs": [],
        }), encoding="utf-8")
        (root / "EVENTS.jsonl").write_text("", encoding="utf-8")
        (root / "RESEARCH_RECORD.md").write_text(
            "## 0. Snapshot\nSynthetic project only\n## 1. History\n", encoding="utf-8")
        self.rules = self.base / "rules"
        self.rules.mkdir()
        for f in ("WORKFLOW.md", "AGENTS.md"):
            (self.rules / f).write_text("# Synthetic original\n", encoding="utf-8")
        cfgdir = self.base / "cfg"
        cfgdir.mkdir()
        self.cfg = cfgdir / "map.json"
        self.cfg.write_text(json.dumps({
            "schema_version": 1,
            "projects": {"demo": {"root": str(root),
                                   "expected_state_project_id": "trusted-id"}}
        }), encoding="utf-8")
        self.private = self.base / "private"
        self.env = patch.dict(os.environ, {
            "PDRW_RUNTIME_DIR": str(self.private),
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.settings = Settings.load(str(self.cfg), str(self.rules))
        self.host = HostSupervisor(self.settings)

    def snapshot(self):
        return {p.relative_to(self.project).as_posix(): p.read_bytes()
                for p in self.project.rglob("*") if p.is_file()}

    def test_supervised_fixed_cpu_process_success_and_output_hash(self):
        before = self.snapshot()
        result = self.host.run_fixed_diagnostic(plan())
        self.assertEqual(result["status"], "HOST_DIAGNOSTIC_COMPLETED", result)
        self.assertTrue(result["execute_performed"])
        self.assertIsInstance(result["pid"], int)
        self.assertFalse(result["scientific_result"])
        self.assertFalse(result["execution_authorized"])
        persisted = get_host_diagnostic_status(self.settings, "demo", "host-test-1")
        self.assertEqual(persisted["status"], "HOST_COMPLETED_HASH_MATCHED_ONLY")
        self.assertEqual(persisted["job"]["output_integrity"], "MATCH")
        resume = ResearchService(self.settings).call(
            "get_resume_context", project_id="demo")
        self.assertEqual(resume["host_fixed_cpu_checkpoints"]["status"],
                         "HOST_DIAGNOSTICS_FOUND")
        self.assertFalse(
            resume["host_fixed_cpu_checkpoints"]["reconciliation_required"])
        self.assertEqual(before, self.snapshot())
        again = self.host.run_fixed_diagnostic(plan())
        self.assertEqual(again["status"], "HOST_ALREADY_RECORDED_NO_RELAUNCH")
        self.assertFalse(again["execute_performed"])

    def test_real_parallel_requests_submit_exactly_one_child(self):
        p = plan(operation_id="multi-1")
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(lambda _: self.host.run_fixed_diagnostic(p),
                                    range(10)))
        launched = [x for x in results if x.get("execute_performed") is True]
        self.assertEqual(len(launched), 1, results)
        self.assertEqual(launched[0]["status"], "HOST_DIAGNOSTIC_COMPLETED", results)
        self.assertEqual(get_host_diagnostic_status(
            self.settings, "demo", "multi-1")["job"]["phase"], "COMPLETED")

    def test_same_operation_different_plan_fails_closed(self):
        self.host.run_fixed_diagnostic(plan())
        conflict = self.host.run_fixed_diagnostic(plan(iterations=600))
        self.assertEqual(conflict["status"], "HOST_PLAN_CONFLICT")
        self.assertFalse(conflict["execute_performed"])

    def test_os_child_nonzero_exit_never_restarts(self):
        p = plan(operation_id="nonzero", scenario="EXIT_NONZERO")
        result = self.host.run_fixed_diagnostic(p)
        self.assertEqual(result["phase"], "FAILED_NONZERO_EXIT", result)
        self.assertEqual(self.host.run_fixed_diagnostic(p)["status"],
                         "HOST_ALREADY_RECORDED_NO_RELAUNCH")

    def test_timeout_terminates_child_process(self):
        p = plan(operation_id="slow", scenario="SLEEP", timeout_seconds=1)
        result = self.host.run_fixed_diagnostic(p)
        self.assertEqual(result["phase"], "TIMED_OUT", result)
        self.assertEqual(get_host_diagnostic_status(
            self.settings, "demo", "slow")["job"]["phase"], "TIMED_OUT")

    def test_cancel_owned_running_child(self):
        p = plan(operation_id="cancel-1", scenario="SLEEP", timeout_seconds=4)
        with ThreadPoolExecutor(max_workers=1) as pool:
            ongoing = pool.submit(self.host.run_fixed_diagnostic, p)
            for _ in range(100):
                with self.host._lock:
                    live = bool(self.host._live)
                if live:
                    break
                time.sleep(0.02)
            self.assertTrue(live, "Host did not register the live child")
            cancelled = self.host.cancel("demo", "cancel-1")
            self.assertTrue(cancelled["cancelled"], cancelled)
            result = ongoing.result(timeout=8)
        self.assertEqual(result["phase"], "CANCELLED", result)
        self.assertFalse(self.host.cancel("demo", "cancel-1")["cancelled"])

    def test_recorded_crash_state_is_not_adopted_or_rerun(self):
        self.host.run_fixed_diagnostic(plan(operation_id="setup"))
        dbpath = self.private / "runtime.sqlite"
        with _open(dbpath) as db:
            db.execute("""INSERT INTO host_jobs
               (project_id,operation_id,task_id,plan_sha256,attempt_id,
                phase,created_at,updated_at) VALUES
               ('demo','crashed','task-a','a','attempt','STARTING_UNVERIFIED','t','t')""")
        status = get_host_diagnostic_status(self.settings, "demo", "crashed")
        self.assertEqual(status["status"], "HOST_RECONCILIATION_REQUIRED")
        self.assertFalse(status["safe_to_restart"])
        again = self.host.run_fixed_diagnostic(plan(operation_id="crashed"))
        self.assertEqual(again["status"], "HOST_PLAN_CONFLICT")
        self.assertFalse(again["execute_performed"])

    def test_hash_tamper_and_missing_output_detected_readonly(self):
        self.host.run_fixed_diagnostic(plan())
        key = hashlib.sha256(b"demo").hexdigest()
        output = (self.private / "host_jobs" / key / "host-test-1" / "result.json")
        output.write_text("not original", encoding="utf-8")
        result = get_host_diagnostic_status(self.settings, "demo", "host-test-1")
        self.assertEqual(result["status"], "HOST_COMPLETION_ARTIFACT_CONFLICT")
        self.assertEqual(result["job"]["output_integrity"], "TAMPERED")
        output.unlink()
        self.assertEqual(get_host_diagnostic_status(
            self.settings, "demo", "host-test-1")["job"]["output_integrity"],
                         "MISSING_OR_UNTRUSTED")

    def test_private_old_schema_status_never_migrates(self):
        self.private.mkdir()
        dbpath = self.private / "runtime.sqlite"
        db = sqlite3.connect(dbpath)
        try:
            db.execute("CREATE TABLE old_receipts (id TEXT)")
            db.execute("PRAGMA user_version=2")
            db.commit()
        finally:
            db.close()
        before = dbpath.read_bytes()
        status = get_host_diagnostic_status(self.settings, "demo", "none")
        self.assertEqual(status["status"], "HOST_JOB_NOT_FOUND")
        self.assertEqual(dbpath.read_bytes(), before)

    def test_host_cli_runs_as_separate_os_process(self):
        p = self.base / "synthetic.json"
        p.write_text(json.dumps(plan(operation_id="standalone")), encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "pdrw_agent.host.cli",
             "--project-map", str(self.cfg),
             "--workflow-root", str(self.rules),
             "run-fixed-diagnostic", "--plan-file", str(p)],
            env=dict(os.environ), text=True, capture_output=True,
            timeout=12, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        value = json.loads(completed.stdout)
        self.assertEqual(value["status"], "HOST_DIAGNOSTIC_COMPLETED", value)

    def test_arbitrary_plan_command_and_dev_execution_refused(self):
        invalid = plan(command="python -c 'danger'")
        from pdrw_agent.runtime.plan import validate_execution_plan
        with self.assertRaises(ValueError):
            validate_execution_plan(invalid)
        proposal = {
            "schema_version": "pdrw-dev-plan-v1",
            "project_id": "demo", "operation_id": "dev-1",
            "task_id": "task-a", "action": "DEV_TRAIN",
            "runner_id": "r1",
            "task_spec_sha256": "a"*64, "code_sha256": "b"*64,
            "dataset_manifest_sha256": "c"*64,
            "time_limit_seconds": 10, "cpu_limit": 1, "gpu_count": 0,
            "network": False, "data_split": "dev",
        }
        denied = preview_dev_admission(self.settings, proposal)
        self.assertEqual(denied["status"], "TRUSTED_HOST_NOT_CONNECTED")
        self.assertFalse(denied["execution_authorized"])

    def test_isolation_probe_never_self_certifies(self):
        observed = current_os_identity()
        self.assertIn(observed["status"], {"IDENTITY_OBSERVED", "IDENTITY_UNOBSERVABLE"})
        isolated = assess_host_isolation()
        self.assertEqual(isolated["status"], "HOST_OS_ISOLATION_NOT_ATTESTED")
        self.assertFalse(isolated["execution_authorized"])
        self.assertFalse(isolated["dev_sealed_acl_verified"])

    def test_registry_bytes_check_does_not_authorize_execution(self):
        registry = self.base / "operator-catalog"
        registry.mkdir()
        (registry / "sources").mkdir()
        script = registry / "sources" / "runner.py"
        script.write_text("print('not executed')\n", encoding="utf-8")
        src_sha = hashlib.sha256(script.read_bytes()).hexdigest()
        manifest = {"schema_version": "pdrw-runner-catalog-v1",
                    "runners": [{
                        "runner_id": "safe-runner",
                        "entrypoint": "sources/runner.py",
                        "sha256": src_sha, "cpu_only": True, "network": False
                    }]}
        (registry / "registry.json").write_text(json.dumps(manifest), encoding="utf-8")
        first = inspect_registered_runner(
            self.settings, "demo", "safe-runner", registry)
        self.assertEqual(first["status"], "HOST_RUNNER_SOURCE_HASH_MATCHED_ONLY")
        self.assertFalse(first["execution_authorized"])
        script.write_text("print('changed')\n", encoding="utf-8")
        mismatch = inspect_registered_runner(
            self.settings, "demo", "safe-runner", registry)
        self.assertEqual(mismatch["status"], "HOST_RUNNER_SOURCE_HASH_MISMATCH")

    def test_registry_cannot_reside_in_science_project(self):
        registry = self.project / "runner-catalog"
        registry.mkdir()
        self.assertEqual(inspect_registered_runner(
            self.settings, "demo", "runner", registry)["status"],
            "HOST_REGISTRY_OVERLAPS_UNTRUSTED_SOURCES")


if __name__ == "__main__":
    unittest.main()
