"""Live integration against a pinned, separate PD-RW checkout in CI.

All fixtures are synthetic under TemporaryDirectory. Never touches SEALED.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from pdrw_agent.config import Settings
from pdrw_agent.service import ResearchService
from pdrw_agent.runtime.registration import register_run_in_trusted_host


@unittest.skipUnless(os.getenv("PDRW_TEST_RULE_ROOT"), "No pinned PD-RW test checkout")
class OriginalPD_RWTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        rule_root = Path(os.environ["PDRW_TEST_RULE_ROOT"]).resolve()
        self.assertTrue((rule_root / "core" / "state.py").is_file())
        root = base / "science"
        root.mkdir()
        (root / "runs").mkdir()
        (root / "RESEARCH_RECORD.md").write_text(
            "## 0. Snapshot\nStill in DEV\n## 1. History\n", encoding="utf-8")
        (root / "PAPER_BLUEPRINT.md").write_text("outline\n", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "core.cli", "init", "--root", str(root),
             "--project-id", "science-test"],
            cwd=str(rule_root), capture_output=True, text=True,
            encoding="utf-8", errors="replace", check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        run = {
            "run_id": "run-1", "task_id": "task-1", "protocol_id": "frozen-1",
            "dataset_version": "dataset-v1", "evaluator_version": "eval-v1",
            "group_split": "synthetic-group", "sample_ids_hash": "12345",
            "split": "dev", "status": "INVALID", "legal_inputs": [],
            "metrics": {},
            "approval": "APPROVED"
        }
        artifact = root / "runs" / "run-1.json"
        artifact.write_text(json.dumps(run), encoding="utf-8")
        cfgfolder = base / "config"
        cfgfolder.mkdir()
        self.config = cfgfolder / "projects.json"
        self.config.write_text(json.dumps({
            "schema_version": 1,
            "projects": {"demo": {"root": str(root),
                                  "state": "STATE.json",
                                  "expected_state_project_id": "science-test"}}
        }), encoding="utf-8")
        self.rules = rule_root
        self.root = root
        self.artifact = artifact
        self.svc = ResearchService(Settings.load(str(self.config), str(rule_root)))
        self.settings = self.svc.settings

    def preview(self):
        return self.svc.call("preview_experiment_record", project_id="demo",
                             artifact_ref="runs/run-1.json")

    def test_preview_and_host_gate_without_permission(self):
        pre = self.preview()
        self.assertEqual(pre["status"], "READY_FOR_TRUSTED_HOST_REVIEW", pre)
        self.assertFalse(pre["write_authorized"])
        denial = register_run_in_trusted_host(self.settings, "demo", "runs/run-1.json",
                                               "op-1", None)
        self.assertEqual(denial["status"], "TRUSTED_HOST_NOT_CONFIGURED")
        denied = register_run_in_trusted_host(
            self.settings, "demo", "runs/run-1.json", "op-1",
            lambda *_: False)
        self.assertEqual(denied["status"], "AUTHORIZATION_NOT_ATTESTED")
        self.assertFalse((self.root / "EVENTS.jsonl").read_text(encoding="utf-8"))

    def test_registration_and_retry_idempotency(self):
        grant = lambda *_: True  # Synthetic host fixture, NEVER user authorization.
        done = register_run_in_trusted_host(
            self.settings, "demo", "runs/run-1.json", "op-1", grant)
        self.assertEqual(done["status"], "RECORDED", done)
        same = register_run_in_trusted_host(
            self.settings, "demo", "runs/run-1.json", "op-1", grant)
        self.assertEqual(same["status"], "ALREADY_RECORDED", same)
        self.assertEqual(len((self.root / "EVENTS.jsonl").read_text(encoding="utf-8").splitlines()), 1)
        self.assertEqual(self.preview()["status"], "ALREADY_RECORDED")

    def test_concurrent_registration_never_duplicates(self):
        def record(_):
            return register_run_in_trusted_host(
                self.settings, "demo", "runs/run-1.json", "same-op",
                lambda *_: True)["status"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(record, [1, 2]))
        self.assertIn("RECORDED", statuses)
        self.assertTrue(set(statuses).issubset({
            "RECORDED", "ALREADY_RECORDED", "RECORD_INDETERMINATE",
            "RECONCILIATION_REQUIRED"
        }))
        events = (self.root / "EVENTS.jsonl").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(events), 1)
        self.assertEqual(self.preview()["status"], "ALREADY_RECORDED")

    def test_conflicting_run_id_is_blocked(self):
        register_run_in_trusted_host(
            self.settings, "demo", "runs/run-1.json", "op-1",
            lambda *_: True)
        obj = json.loads(self.artifact.read_text(encoding="utf-8"))
        obj["dataset_version"] = "changed-after-registration"
        self.artifact.write_text(json.dumps(obj), encoding="utf-8")
        new = self.preview()
        # PD-RW first detects immutable original evidence mutation.
        self.assertEqual(new["status"], "RECONCILIATION_REQUIRED")

    def test_crash_between_event_and_state_detected(self):
        digest = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        orphan = {
            "event_id": "synthetic-event", "prev_event_id": None,
            "project_id": "science-test", "kind": "run",
            "artifact_id": "run-1", "artifact_path": "runs/run-1.json",
            "artifact_sha256": digest, "task_id": "task-1", "split": "dev",
            "status": "INVALID", "recorded_at": "2026-01-01T00:00:00Z",
            "note": "fault-injection"
        }
        (self.root / "EVENTS.jsonl").write_text(json.dumps(orphan) + "\n", encoding="utf-8")
        result = self.preview()
        self.assertEqual(result["status"], "RECONCILIATION_REQUIRED", result)
        blocked = register_run_in_trusted_host(
            self.settings, "demo", "runs/run-1.json", "op-1", lambda *_: True)
        self.assertEqual(blocked["status"], "RECONCILIATION_REQUIRED")
        self.assertFalse(blocked.get("write_performed"))
        self.assertEqual(len((self.root / "EVENTS.jsonl").read_text(encoding="utf-8").splitlines()), 1)

    def test_sealed_history_not_opened_by_preview(self):
        secret = {
            "event_id": "sealed-event", "prev_event_id": None,
            "project_id": "science-test", "kind": "run",
            "artifact_id": "sealed-run", "artifact_path": "B_SEALED/data.json",
            "artifact_sha256": "a"*64, "task_id": "other", "split": "sealed",
            "status": "VALID"
        }
        (self.root / "EVENTS.jsonl").write_text(json.dumps(secret) + "\n", encoding="utf-8")
        self.assertEqual(self.preview()["status"],
                         "PROTECTED_HISTORY_REQUIRES_ISOLATED_HOST")

    def test_handoff_is_paths_only(self):
        out = self.svc.call("prepare_handoff", project_id="demo",
                            primary_ref="runs/run-1.json",
                            supporting_refs=["RESEARCH_RECORD.md"])
        self.assertEqual(out["status"], "PATHS_VERIFIED_ONLY", out)
        self.assertFalse(out["scientific_truth_verified"])
        self.assertFalse(out["new_files_created"])


if __name__ == "__main__":
    unittest.main()
