"""v0.7.1 contract, source readiness, DB migration and host-negative tests.

No real DEV/GPU execution, raw project state mutation, network or SEALED read.
"""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pdrw_agent.config import Settings, under_root
from pdrw_agent.host.contracts import validate_dev_proposal
from pdrw_agent.host.authorization import (
    preview_dev_admission, submit_dev_in_trusted_host)
from pdrw_agent.host.process_identity import (
    observe_process, compare_process_identity)
from pdrw_agent.runtime.readiness import inspect_project_readiness
from pdrw_agent.runtime.receipts import _open, begin_operation
from pdrw_agent.runtime.plan import preflight_execution_plan
from pdrw_agent.service import ResearchService
from pdrw_agent.schemas import AgentError


def dev_packet(**updates):
    packet = {
        "schema_version": "pdrw-dev-plan-v1", "project_id": "demo",
        "operation_id": "dev-op-1", "task_id": "task-a",
        "action": "DEV_TRAIN", "runner_id": "registered-runner-1",
        "task_spec_sha256": "a" * 64, "code_sha256": "b" * 64,
        "dataset_manifest_sha256": "c" * 64,
        "time_limit_seconds": 600, "cpu_limit": 2,
        "gpu_count": 0, "network": False, "data_split": "dev",
    }
    packet.update(updates)
    return packet


class ReadinessAndHostContractTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        self.root = self.base / "project"
        self.root.mkdir()
        rules = self.base / "rules"
        rules.mkdir()
        for n in ("AGENTS.md", "WORKFLOW.md"):
            (rules / n).write_text("# PD-RW v1.13", encoding="utf-8")
        (self.root / "RESEARCH_RECORD.md").write_text(
            "## 0. Snapshot\nreported state\n## 1. History\n",
            encoding="utf-8")
        cfg_dir = self.base / "cfg"
        cfg_dir.mkdir()
        self.cfg = cfg_dir / "map.json"
        self.cfg.write_text(json.dumps({"schema_version": 1, "projects": {
            "demo": {"root": str(self.root),
                     "expected_state_project_id": "canonical-id"}
        }}), encoding="utf-8")
        self.settings = Settings.load(str(self.cfg), str(rules))
        self.svc = ResearchService(self.settings)

    def install_machine(self):
        (self.root / "STATE.json").write_text(json.dumps({
            "schema_version": "1.4", "project_id": "canonical-id",
            "active_task_id": None, "latest_valid_run_id": None,
            "last_event_id": None, "evidence_refs": [],
        }), encoding="utf-8")
        (self.root / "EVENTS.jsonl").write_text("", encoding="utf-8")

    def test_legacy_readonly_without_implicit_state_creation(self):
        (self.root / "STATE.md").write_text(
            "PROJECT_ID: canonical-id\nACTIVE_TASK: task-a\n", encoding="utf-8")
        before = sorted(x.name for x in self.root.iterdir())
        state = inspect_project_readiness(self.settings, "demo")
        self.assertEqual(state["status"], "LEGACY_READ_ONLY")
        self.assertTrue(state["historical_read_only_allowed"])
        self.assertFalse(state["execution_authorized"])
        self.assertEqual(before, sorted(x.name for x in self.root.iterdir()))
        dev = preview_dev_admission(self.settings, dev_packet())
        self.assertEqual(dev["status"], "PROJECT_MACHINE_STATE_BLOCKED")

    def test_full_machine_source_without_extra_sha256_manifest_is_not_blocked(self):
        self.install_machine()
        state = inspect_project_readiness(self.settings, "demo")
        self.assertEqual(state["status"], "MACHINE_METADATA_READY", state)
        audit = self.svc.call("audit_project_state", project_id="demo")
        self.assertEqual(audit["status"], "SOURCE_REVIEW_REQUIRED", audit)
        self.assertNotIn("EVIDENCE_MANIFEST_ABSENT", audit["blockers"])
        self.assertIn("OPTIONAL_STANDALONE_MANIFEST_NOT_PRESENT", audit["advisories"])
        self.assertFalse(audit["original_authorization_verified"])
        admission = preview_dev_admission(self.settings, dev_packet())
        self.assertEqual(admission["status"], "TRUSTED_HOST_NOT_CONNECTED")
        self.assertFalse(admission["execute_performed"])
        self.assertFalse(admission["execution_authorized"])

    def test_machine_legacy_identity_collision(self):
        self.install_machine()
        (self.root / "STATE.md").write_text("PROJECT_ID: different-id\n",
                                            encoding="utf-8")
        result = inspect_project_readiness(self.settings, "demo")
        self.assertEqual(result["status"], "STATE_IDENTITY_CONFLICT")
        self.assertFalse(result["execution_authorized"])

    def test_invalid_machine_json_is_diagnostic_not_a_silent_fallback(self):
        self.install_machine()
        (self.root / "STATE.json").write_text("{", encoding="utf-8")
        (self.root / "STATE.md").write_text("PROJECT_ID: canonical-id\n",
                                            encoding="utf-8")
        status = inspect_project_readiness(self.settings, "demo")
        self.assertEqual(status["status"], "MACHINE_STATE_INVALID")

    def test_history_conflict_blocks_execution_preflight(self):
        self.install_machine()
        (self.root / "EVENTS.jsonl").write_text(
            '{"event_id":"note1","kind":"note","project_id":"canonical-id",'
            '"prev_event_id":null}\n', encoding="utf-8")
        result = inspect_project_readiness(self.settings, "demo")
        self.assertEqual(result["status"], "MACHINE_LEDGER_CONFLICT")
        plan = {"schema_version": "pdrw-exec-plan-v1", "project_id": "demo",
                "operation_id": "dry", "task_id": "task-a",
                "profile": "CPU_SELFTEST_V1", "scenario": "SUCCESS",
                "iterations": 20, "timeout_seconds": 2,
                "network": False, "gpu": False}
        self.assertEqual(preflight_execution_plan(self.settings, plan)["status"],
                         "BLOCKED_PROJECT_HISTORY")
        self.assertEqual(
            preview_dev_admission(self.settings, dev_packet())["status"],
            "PROJECT_MACHINE_STATE_BLOCKED")

    def test_exact_dev_contract_is_fingerprint_stable(self):
        packet = dev_packet()
        _, a = validate_dev_proposal(packet)
        _, b = validate_dev_proposal(dict(reversed(list(packet.items()))))
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)

    def test_forged_authorization_or_arbitrary_command_cannot_enter_proposal(self):
        attempts = [
            dev_packet(approved=True),
            dev_packet(command="python train.py"),
            dev_packet(data_split="sealed"),
            dev_packet(action="WRITE_CLAIM"),
            dev_packet(network=True),
            dev_packet(cpu_limit=500),
            dev_packet(gpu_count=5),
            dev_packet(time_limit_seconds=True),
            dev_packet(code_sha256="not-a-fingerprint"),
            dev_packet(runner_id="../../escape"),
        ]
        for proposal in attempts:
            with self.subTest(proposal=proposal):
                with self.assertRaises(AgentError):
                    validate_dev_proposal(proposal)

    def test_dev_submission_remains_non_executable(self):
        self.install_machine()
        before = sorted(p.relative_to(self.root).as_posix() for p
                        in self.root.rglob("*") if p.is_file())
        denied = submit_dev_in_trusted_host(
            settings=self.settings, proposal=dev_packet(), approve=True)
        self.assertEqual(denied["status"], "TRUSTED_HOST_NOT_CONNECTED")
        self.assertFalse(denied["execute_performed"])
        self.assertEqual(before, sorted(p.relative_to(self.root).as_posix()
                                        for p in self.root.rglob("*") if p.is_file()))

    def test_lexically_protected_subtree_is_never_normalized_away(self):
        d = self.root / "SEALED"
        d.mkdir()
        (self.root / "ordinary.txt").write_text("ok", encoding="utf-8")
        with self.assertRaises(AgentError):
            under_root(self.root, "SEALED/../ordinary.txt", must_exist=True)
        self.assertTrue(under_root(self.root, "ordinary.txt", must_exist=True).is_file())


class RuntimeMigrationTests(unittest.TestCase):
    def test_legacy_v0_receipts_are_preserved_and_attempt_table_created(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "legacy.sqlite"
            db = sqlite3.connect(str(path))
            db.execute("""CREATE TABLE operations (
                project_id TEXT NOT NULL, operation_id TEXT NOT NULL,
                task_id TEXT NOT NULL, action TEXT NOT NULL,
                phase TEXT NOT NULL, revision INTEGER NOT NULL,
                artifact_ref TEXT NOT NULL DEFAULT '',
                artifact_sha256 TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                PRIMARY KEY(project_id, operation_id))""")
            db.execute("INSERT INTO operations VALUES (?,?,?,?,?,?,?,?,?,?)",
                       ("p", "o", "t", "DEV_CODE", "PLANNED", 0, "", "",
                        "2026-01-01", "2026-01-01"))
            db.commit()
            db.close()
            with _open(path, write=False) as ro:
                self.assertEqual(ro.execute("PRAGMA user_version").fetchone()[0], 0)
            with _open(path, write=True) as writable:
                self.assertEqual(writable.execute("PRAGMA user_version").fetchone()[0], 3)
                self.assertEqual(writable.execute(
                    "SELECT COUNT(*) FROM operation_attempts").fetchone()[0], 0)
                self.assertEqual(writable.execute(
                    "SELECT COUNT(*) FROM host_jobs").fetchone()[0], 0)
                self.assertEqual(writable.execute(
                    "SELECT phase FROM operations").fetchone()[0], "PLANNED")
            with _open(path, write=False) as ro:
                self.assertEqual(ro.execute("PRAGMA user_version").fetchone()[0], 3)

    def test_unknown_newer_schema_rejected_and_not_downgraded(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "new.sqlite"
            db = sqlite3.connect(str(path))
            db.execute("PRAGMA user_version=999")
            db.close()
            with self.assertRaises(AgentError):
                with _open(path, write=True):
                    pass
            with _open(path, write=False) as ro:
                self.assertEqual(ro.execute("PRAGMA user_version").fetchone()[0], 999)


class ProcessIdentityTests(unittest.TestCase):
    def test_current_process_identity_can_be_compared_but_not_authorized(self):
        observed = observe_process(os.getpid())
        self.assertEqual(observed["status"], "OBSERVED", observed)
        self.assertTrue(observed["start_token"])
        correct = compare_process_identity(os.getpid(), observed["start_token"])
        self.assertTrue(correct["identity_matched"])
        self.assertFalse(correct["host_ownership_verified"])
        self.assertFalse(correct["execution_authorized"])
        mismatch = compare_process_identity(os.getpid(), "wrong")
        self.assertFalse(mismatch["identity_matched"])

    def test_actual_child_process_observation_and_termination(self):
        proc = subprocess.Popen(
            [sys.executable, "-B", "-c", "import time; time.sleep(10)"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            observed = observe_process(proc.pid)
            self.assertEqual(observed["status"], "OBSERVED", observed)
            self.assertTrue(compare_process_identity(
                proc.pid, observed["start_token"])["identity_matched"])
            proc.terminate()
            proc.wait(timeout=8)
            self.assertIsNotNone(proc.returncode)
            self.assertFalse(compare_process_identity(
                proc.pid, "deliberately-wrong-token")["identity_matched"])
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait()


if __name__ == "__main__":
    unittest.main()
