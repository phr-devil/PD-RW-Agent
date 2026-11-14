"""v0.7.3 bounded host reliability and synthetic ACL acceptance probes.

Tests do not create a trusted OS service or read actual research SEALED data.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from pdrw_agent.config import Settings
from pdrw_agent.host.acl_probe import DEV_MARKER, probe_host_fixture_acl
from pdrw_agent.host.process_identity import observe_process, compare_process_identity
from pdrw_agent.host.supervisor import HostSupervisor, get_host_diagnostic_status


def fixed_plan(operation="interrupted-1"):
    return {"schema_version": "pdrw-exec-plan-v1", "project_id": "demo",
            "operation_id": operation, "task_id": "selftest",
            "profile": "CPU_SELFTEST_V1", "scenario": "SUCCESS",
            "iterations": 100, "timeout_seconds": 3,
            "network": False, "gpu": False}


class HostReliabilityTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.project = self.base / "project"
        self.project.mkdir()
        self.rules = self.base / "rules"
        self.rules.mkdir()
        for filename in ("AGENTS.md", "WORKFLOW.md"):
            (self.rules / filename).write_text("# rules", encoding="utf-8")
        (self.project / "STATE.json").write_text(
            json.dumps({"schema_version":"1.4", "project_id":"pilot",
                        "active_task_id":None, "latest_valid_run_id":None,
                        "last_event_id":None, "evidence_refs":[]}), encoding="utf-8")
        (self.project / "EVENTS.jsonl").write_text("", encoding="utf-8")
        (self.project / "RESEARCH_RECORD.md").write_text(
            "## 0. Snapshot\nFixture\n## 1. History\n", encoding="utf-8")
        self.cfgdir = self.base / "cfg"
        self.cfgdir.mkdir()
        cfg = self.cfgdir / "projects.json"
        cfg.write_text(json.dumps({"schema_version":1,"projects":{
            "demo":{"root":str(self.project),"expected_state_project_id":"pilot"}}}),
            encoding="utf-8")
        self.settings = Settings.load(str(cfg), str(self.rules))
        self.runtime = self.base / "private-runtime"
        self.env = patch.dict(os.environ, {"PDRW_RUNTIME_DIR":str(self.runtime)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.host = HostSupervisor(self.settings)
        self.fixtures = self.base / "fixtures"
        self.fixtures.mkdir()
        self.dev = self.fixtures / "dev-readable.fixture"
        self.denied = self.fixtures / "sealed-denied.fixture"
        self.dev.write_bytes(DEV_MARKER)
        self.denied.write_bytes(b"SYNTHETIC_MARKER_NOT_REAL_SEALED")

    def test_same_account_reading_both_fixture_files_is_an_acl_gap(self):
        out = probe_host_fixture_acl(
            self.settings, "demo", str(self.dev), str(self.denied))
        self.assertEqual(out["status"], "HOST_FIXTURE_ACL_GAP")
        self.assertFalse(out["execution_authorized"])
        self.assertFalse(out["real_dev_sealed_access_verified"])

    def test_simulated_os_denial_is_observation_only_not_authorization(self):
        original_open = Path.open
        def simulated_open(path, mode="r", *args, **kwargs):
            if Path(path) == self.denied and mode == "rb":
                raise PermissionError("simulated restricted ACL")
            return original_open(path, mode, *args, **kwargs)
        with patch.object(Path, "open", simulated_open):
            out = probe_host_fixture_acl(
                self.settings, "demo", str(self.dev), str(self.denied))
        self.assertEqual(out["status"], "HOST_FIXTURE_ACL_DENIAL_OBSERVED_ONLY")
        self.assertFalse(out["trusted_host_authenticated"])
        self.assertFalse(out["execution_authorized"])

    def test_acl_fixture_missing_is_unknown(self):
        self.denied.unlink()
        out = probe_host_fixture_acl(
            self.settings, "demo", str(self.dev), str(self.denied))
        self.assertEqual(out["status"], "HOST_DENIED_FIXTURE_INCONCLUSIVE")

    def test_acl_probe_refuses_real_project_and_renamed_fixtures(self):
        dev_inside = self.project / "dev-readable.fixture"
        dev_inside.write_bytes(DEV_MARKER)
        for dev, denied in [
            (dev_inside, self.denied),
            (self.dev, self.project / "sealed-denied.fixture"),
            (self.dev, self.fixtures / "other-name.txt"),
        ]:
            with self.subTest(dev=str(dev), denied=str(denied)):
                with self.assertRaises(ValueError):
                    probe_host_fixture_acl(self.settings, "demo",
                                           str(dev), str(denied))

    def test_acl_probe_rejects_symlinked_fixture(self):
        linked = self.fixtures / "dev-readable.fixture"
        linked.unlink()
        target = self.fixtures / "target.fixture"
        try:
            linked.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation not allowed on this Windows runner")
        with self.assertRaises(ValueError):
            probe_host_fixture_acl(
                self.settings, "demo", str(linked), str(self.denied))

    def test_acl_probe_cli_fails_when_same_account_can_read_denied_fixture(self):
        cmd = [sys.executable, "-m", "pdrw_agent.host.cli",
               "--project-map", str(self.settings.project_map),
               "--workflow-root", str(self.rules),
               "acl-probe", "--project-id", "demo",
               "--dev-fixture", str(self.dev),
               "--denied-fixture", str(self.denied)]
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=12, check=False)
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "HOST_FIXTURE_ACL_GAP")

    def test_operator_interrupt_marks_checkpoint_explicitly(self):
        with patch("pdrw_agent.host.supervisor._launch_worker",
                   side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.host.run_fixed_diagnostic(fixed_plan())
        out = get_host_diagnostic_status(self.settings, "demo", "interrupted-1")
        self.assertEqual(out["job"]["phase"], "INTERRUPTED")
        again = self.host.run_fixed_diagnostic(fixed_plan())
        self.assertEqual(again["status"], "HOST_ALREADY_RECORDED_NO_RELAUNCH")
        self.assertFalse(again["execute_performed"])

    def test_stale_or_exited_pid_is_never_reported_as_running(self):
        self.host.run_fixed_diagnostic(fixed_plan("finished"))
        from pdrw_agent.runtime.receipts import _open
        dbpath = self.runtime / "runtime.sqlite"
        with _open(dbpath) as db:
            db.execute("""UPDATE host_jobs
               SET phase='RUNNING_UNVERIFIED', pid=?,start_token=?
               WHERE project_id='demo' AND operation_id='finished'""",
               (os.getpid(), "same-token"))
        with patch("pdrw_agent.host.supervisor.observe_process",
                   return_value={"status":"EXITED",
                                 "start_token":"same-token",
                                 "liveness_verified":False}):
            out = get_host_diagnostic_status(self.settings, "demo", "finished")
        self.assertEqual(out["status"], "HOST_RECONCILIATION_REQUIRED")
        self.assertTrue(out["job"]["process_identity_matched"])
        self.assertFalse(out["job"]["running_snapshot_observed"])

    def test_live_process_snapshot_still_never_adopts_process(self):
        me = observe_process(os.getpid())
        self.assertTrue(me["start_token"])
        same = compare_process_identity(os.getpid(), me["start_token"])
        self.assertTrue(same["identity_matched"])
        self.assertFalse(same["host_ownership_verified"])
        self.assertFalse(same["execution_authorized"])


if __name__ == "__main__":
    unittest.main()
