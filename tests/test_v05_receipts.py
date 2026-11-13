"""Synthetic operational receipts: no model training, no real research data."""
import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from pdrw_agent.config import Settings
from pdrw_agent.service import ResearchService


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        rules = base / "rules"
        rules.mkdir()
        for name in ("AGENTS.md", "WORKFLOW.md"):
            (rules / name).write_text("# test\n", encoding="utf-8")
        root = base / "science"
        root.mkdir()
        (root / "STATE.json").write_text(json.dumps({
            "schema_version": "1.4", "project_id": "test-project",
            "active_task_id": "dev-task", "latest_valid_run_id": None,
            "last_event_id": None, "evidence_refs": []
        }), encoding="utf-8")
        (root / "RESEARCH_RECORD.md").write_text(
            "## 0. Snapshot\nStill testing\n## 1. History\n", encoding="utf-8")
        (root / "PAPER_BLUEPRINT.md").write_text("Plan\n", encoding="utf-8")
        (root / "runs").mkdir()
        (root / "runs" / "run.json").write_text('{"result": "DEV metadata"}', encoding="utf-8")
        conf = base / "config"
        conf.mkdir()
        cfg = conf / "projects.json"
        cfg.write_text(json.dumps({"schema_version": 1,
                                  "projects": {"project-1": {
                                      "root": str(root),
                                      "expected_state_project_id": "test-project"
                                  }}}), encoding="utf-8")
        self.env = patch.dict(os.environ, {"PDRW_RUNTIME_DIR": str(base / "private-runtime")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.root = root
        self.service = ResearchService(Settings.load(str(cfg), str(rules)))

    def call(self, tool, **kwargs):
        return self.service.call(tool, project_id="project-1", **kwargs)

    def test_creation_retry_and_conflicting_id(self):
        first = self.call("begin_operation_receipt", operation_id="op-1",
                          task_id="dev-task", action="DEV_TRAIN")
        self.assertEqual(first["status"], "RECEIPT_CREATED")
        self.assertFalse(first["execution_authorized"])
        retry = self.call("begin_operation_receipt", operation_id="op-1",
                          task_id="dev-task", action="DEV_TRAIN")
        self.assertEqual(retry["status"], "ALREADY_RECEIPTED")
        clash = self.call("begin_operation_receipt", operation_id="op-1",
                          task_id="other", action="DEV_TRAIN")
        self.assertEqual(clash["status"], "OPERATION_ID_CONFLICT")
        self.assertEqual(len(self.call("get_execution_status")["operations"]), 1)

    def test_checkpoint_cas_retry_and_artifact_change(self):
        self.call("begin_operation_receipt", operation_id="op-2",
                  task_id="dev-task", action="DEV_EVALUATE")
        running = self.call("checkpoint_operation_receipt", operation_id="op-2",
                            expected_revision=0, phase="RUNNING_DECLARED")
        self.assertEqual(running["receipt"]["revision"], 1)
        self.assertFalse(running["scientific_evidence_verified"])
        same = self.call("checkpoint_operation_receipt", operation_id="op-2",
                         expected_revision=0, phase="RUNNING_DECLARED")
        self.assertEqual(same["status"], "ALREADY_CHECKPOINTED")
        stale = self.call("checkpoint_operation_receipt", operation_id="op-2",
                          expected_revision=0, phase="TECHNICAL_FAILED")
        self.assertEqual(stale["status"], "REVISION_CONFLICT")
        artifact = self.call("checkpoint_operation_receipt", operation_id="op-2",
                             expected_revision=1, phase="ARTIFACT_REPORTED",
                             artifact_ref="runs/run.json")
        self.assertEqual(artifact["status"], "CHECKPOINT_SAVED")
        self.assertEqual(self.call("get_execution_status")["operations"][0]["artifact_integrity"], "MATCH")
        resume = self.call("get_resume_context")
        self.assertEqual(resume["status"], "NEEDS_RECONCILIATION")
        self.assertFalse(resume["process_liveness_verified"])
        (self.root / "runs" / "run.json").write_text('{"changed": true}', encoding="utf-8")
        second = self.call("get_resume_context")
        self.assertEqual(second["next"], "RECONCILE_CHANGED_ARTIFACTS")
        self.assertEqual(second["active_operations"][0]["artifact_integrity"], "CHANGED")

    def test_unknown_and_protected_actions_cannot_be_executed(self):
        result = self.call("begin_operation_receipt", operation_id="op-sealed",
                           task_id="dev-task", action="READ_SEALED")
        self.assertEqual(result["error_code"], "INVALID_ACTION")
        self.call("begin_operation_receipt", operation_id="op-x",
                  task_id="dev-task", action="DEV_CODE")
        change = self.call("checkpoint_operation_receipt", operation_id="op-x",
                           expected_revision=0, phase="ARTIFACT_REPORTED",
                           artifact_ref="B_SEALED_MATERIAL/data.json")
        self.assertEqual(change["error_code"], "PROTECTED_PROJECT_PATH")

    def test_concurrent_receipts_only_one_row(self):
        def begin(_):
            return self.call("begin_operation_receipt", operation_id="same",
                             task_id="dev-task", action="DEV_CODE")["status"]
        with ThreadPoolExecutor(max_workers=4) as worker:
            results = list(worker.map(begin, range(8)))
        self.assertEqual(results.count("RECEIPT_CREATED"), 1)
        self.assertEqual(results.count("ALREADY_RECEIPTED"), 7)
        self.assertEqual(len(self.call("get_execution_status")["operations"]), 1)

    def test_runtime_database_is_outside_project(self):
        runtime = Path(os.environ["PDRW_RUNTIME_DIR"])
        self.call("begin_operation_receipt", operation_id="op-z",
                  task_id="dev-task", action="DEV_CODE")
        self.assertTrue((runtime / "runtime.sqlite").is_file())
        self.assertFalse((self.root / "runtime.sqlite").exists())

    def test_absent_runtime_remains_readable(self):
        with patch.dict(os.environ, {"PDRW_RUNTIME_DIR": ""}):
            r = self.call("get_execution_status")
            self.assertEqual(r["status"], "RECEIPTS_NOT_CONFIGURED")
            r2 = self.call("begin_operation_receipt", operation_id="blocked",
                           task_id="dev-task", action="DEV_FIX")
            self.assertEqual(r2["error_code"], "RUNTIME_DIR_NOT_CONFIGURED")


if __name__ == "__main__":
    unittest.main()
