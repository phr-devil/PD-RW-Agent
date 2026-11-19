"""WP2 regressions: cold-DB receipts, Markdown project identity, error classes.

All fixtures are synthetic TemporaryDirectory data. No real project state,
Run, SEALED or frozen artifact is read or written.
"""
import json
import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from pdrw_agent.config import Settings
from pdrw_agent.projects import get_project_context, markdown_project_id
from pdrw_agent.runtime import receipts as receipts_mod
from pdrw_agent.service import ResearchService


def _fixture(state_name="STATE.md", state_text=None, expected="44"):
    """Build an independent synthetic project/config/runtime triple."""
    base = Path(tempfile.mkdtemp(prefix="pdrw-wp2-"))
    runtime = Path(tempfile.mkdtemp(prefix="pdrw-wp2-rt-"))
    rules = base / "rules"
    rules.mkdir()
    for name in ("AGENTS.md", "WORKFLOW.md"):
        (rules / name).write_text("# synthetic\n", encoding="utf-8")
    root = base / "science"
    root.mkdir()
    if state_text is None:
        state_text = "## 0. Snapshot\n- ACTIVE_TASK: dev-task\n## 1. History\nold\n"
    (root / state_name).write_text(state_text, encoding="utf-8")
    (root / "RESEARCH_RECORD.md").write_text(
        "## 0. Snapshot\nsynthetic\n## 1. History\nold\n", encoding="utf-8")
    (root / "PAPER_BLUEPRINT.md").write_text("outline\n", encoding="utf-8")
    cfgdir = base / "config"
    cfgdir.mkdir()
    cfg = cfgdir / "projects.json"
    entry = {"root": str(root), "state": state_name}
    if expected is not None:
        entry["expected_state_project_id"] = expected
    cfg.write_text(json.dumps({"schema_version": 1, "projects": {"p": entry}}),
                   encoding="utf-8")
    settings = Settings.load(str(cfg), str(rules))
    return base, runtime, settings


class ReceiptConcurrencyTests(unittest.TestCase):
    def setUp(self):
        self.base, self.runtime, self.settings = _fixture(
            state_name="STATE.json",
            state_text=json.dumps({"schema_version": "1.4", "project_id": "44",
                                   "active_task_id": "dev-task",
                                   "latest_valid_run_id": None,
                                   "last_event_id": None, "evidence_refs": []}))
        self.addCleanup(lambda: None)
        self.env = patch.dict(os.environ, {"PDRW_RUNTIME_DIR": str(self.runtime)})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.svc = ResearchService(self.settings)

    def call(self, **kwargs):
        return self.svc.call("begin_operation_receipt", project_id="p", **kwargs)

    def test_cold_db_concurrent_init_is_idempotent(self):
        """Repeat the real cold-start scenario: 8 writers, one new DB."""
        for _ in range(3):
            self.runtime  # same dir; each iteration uses a distinct op id below
        # One fresh DB only; run 10 independent rounds against fresh dirs.
        for round_no in range(10):
            rt = Path(tempfile.mkdtemp(prefix="pdrw-wp2-cold-"))
            with patch.dict(os.environ, {"PDRW_RUNTIME_DIR": str(rt)}):
                receipts_mod._SCHEMA_READY.clear()
                op = f"op-{round_no}"

                def begin(_):
                    out = self.svc.call(
                        "begin_operation_receipt", project_id="p",
                        operation_id=op, task_id="dev-task",
                        action="DEV_CODE")
                    return (out["status"] if out["status"] != "ERROR"
                            else "ERROR:" + str(out.get("error_code")))

                with ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(begin, range(8)))
                self.assertEqual(results.count("RECEIPT_CREATED"), 1, results)
                self.assertEqual(results.count("ALREADY_RECEIPTED"), 7, results)
                self.assertFalse([r for r in results if r.startswith("ERROR")], results)
                rows = self.svc.call("get_execution_status", project_id="p")["operations"]
                self.assertEqual(len(rows), 1, rows)

    def test_checkpoint_and_idempotent_retry_after_cold_start(self):
        first = self.call(operation_id="op-a", task_id="dev-task", action="DEV_CODE")
        self.assertEqual(first["status"], "RECEIPT_CREATED")
        again = self.call(operation_id="op-a", task_id="dev-task", action="DEV_CODE")
        self.assertEqual(again["status"], "ALREADY_RECEIPTED")
        cp = self.svc.call("checkpoint_operation_receipt", project_id="p",
                           operation_id="op-a", expected_revision=0,
                           phase="RUNNING_DECLARED")
        self.assertEqual(cp["status"], "CHECKPOINT_SAVED")
        retry = self.svc.call("checkpoint_operation_receipt", project_id="p",
                              operation_id="op-a", expected_revision=0,
                              phase="RUNNING_DECLARED")
        self.assertEqual(retry["status"], "ALREADY_CHECKPOINTED")
        self.assertEqual(len(self.svc.call("get_execution_status", project_id="p")["operations"]), 1)

    def test_real_sqlite_error_is_not_invalid_input(self):
        """A genuine readonly DB must surface as a storage error, not INVALID_INPUT."""
        self.call(operation_id="op-ro", task_id="dev-task", action="DEV_CODE")
        db = self.runtime / "runtime.sqlite"
        os.chmod(db, 0o444)
        try:
            result = self.svc.call("begin_operation_receipt", project_id="p",
                                   operation_id="op-new", task_id="dev-task",
                                   action="DEV_CODE")
            # Recovery: make writable again and confirm the same call succeeds.
            os.chmod(db, 0o644)
            recovered = self.svc.call("begin_operation_receipt", project_id="p",
                                      operation_id="op-new", task_id="dev-task",
                                      action="DEV_CODE")
            self.assertEqual(recovered["status"], "RECEIPT_CREATED")
            if result["status"] == "ERROR":
                self.assertTrue(result["error_code"].startswith("RECEIPT_STORAGE_"),
                                result)
                self.assertNotEqual(result["error_code"], "INVALID_INPUT")
                self.assertIn("sqlite3", result.get("storage_error_class", ""))
        finally:
            try:
                os.chmod(db, 0o644)
            except OSError:
                pass

    def test_read_never_creates_receipt_database(self):
        fresh = Path(tempfile.mkdtemp(prefix="pdrw-wp2-empty-"))
        with patch.dict(os.environ, {"PDRW_RUNTIME_DIR": str(fresh)}):
            result = self.svc.call("get_execution_status", project_id="p")
            self.assertEqual(result["status"], "NO_RECEIPTS")
            self.assertFalse((fresh / "runtime.sqlite").exists())

    def test_storage_error_classifier(self):
        from pdrw_agent.schemas import classify_storage_error
        cases = {
            "attempt to write a readonly database": "RECEIPT_STORAGE_READONLY",
            "database is locked": "RECEIPT_STORAGE_BUSY",
            "no such table: operations": "RECEIPT_STORAGE_SCHEMA_MISSING",
            "file is not a database": "RECEIPT_STORAGE_CORRUPT",
            "unable to open database file": "RECEIPT_STORAGE_UNAVAILABLE",
            "some other sqlite failure": "RECEIPT_STORAGE_ERROR",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(classify_storage_error(sqlite3.OperationalError(text)),
                                 expected)


class MarkdownIdentityTests(unittest.TestCase):
    def _context(self, state_text, expected):
        base, _, settings = _fixture(state_text=state_text, expected=expected)
        return get_project_context(settings, "p")

    def test_42_43_44_style_identity_line_matches(self):
        line = ("**项目身份**：`PROJECT_ID = 44`｜`PROJECT_ROOT = D:/workbuddy-work/44`｜"
                "P37 与 ws42/43 为不同研究线，不继承其 Run/Claim/分组。\n"
                "## 0. Snapshot\n- ACTIVE_TASK: dev-task\n## 1. History\nold\n")
        r = self._context(line, "44")
        self.assertEqual(r["identity"], "DECLARED_ID_MATCH")
        self.assertEqual(r["declared_state_project_id"], "44")
        self.assertEqual(r["identity_basis"], "EXPLICIT_PROJECT_ID")
        self.assertEqual(r["status"], "SOURCE_REVIEW_REQUIRED")
        self.assertFalse(r["identity_verified"])

    def test_explicit_wrong_project_id_is_conflict(self):
        text = ("**项目身份**：`PROJECT_ID = 43`｜不同研究线\n"
                "## 0. Snapshot\n- ACTIVE_TASK: dev-task\n## 1. History\nold\n")
        r = self._context(text, "44")
        self.assertEqual(r["status"], "IDENTITY_CONFLICT")
        self.assertEqual(r["identity"], "DECLARED_ID_MISMATCH")
        self.assertEqual(r["declared_state_project_id"], "43")

    def test_plain_markdown_variants(self):
        for text in ("- PROJECT_ID: 44\n## 0. Snapshot\nx\n## 1. History\ny\n",
                     "PROJECT_ID = 44\n## 0. Snapshot\nx\n## 1. History\ny\n",
                     "**项目编号**：44\n## 0. Snapshot\nx\n## 1. History\ny\n"):
            with self.subTest(text=text[:28]):
                r = self._context(text, "44")
                self.assertEqual(r["identity"], "DECLARED_ID_MATCH")

    def test_missing_identity_is_unknown_and_blocks_restricted_paths(self):
        text = "## 0. Snapshot\n- ACTIVE_TASK: dev-task\n## 1. History\nold\n"
        r = self._context(text, "44")
        self.assertEqual(r["identity"], "UNKNOWN")
        self.assertEqual(r["status"], "IDENTITY_UNKNOWN")
        self.assertEqual(r["identity_basis"], "ABSENT")
        self.assertEqual(r["cross_project_run_or_claim_reuse"], "NOT_ATTESTED")
        base, runtime, settings = _fixture(state_text=text, expected="44")
        svc = ResearchService(settings)
        with patch.dict(os.environ, {"PDRW_RUNTIME_DIR": str(runtime)}):
            resume = svc.call("get_resume_context", project_id="p")
            self.assertEqual(resume["status"], "BLOCKED_IDENTITY_UNKNOWN")
            receipt = svc.call("begin_operation_receipt", project_id="p",
                               operation_id="op-x", task_id="dev-task",
                               action="DEV_CODE")
            self.assertEqual(receipt["error_code"], "PROJECT_CONTEXT_NOT_READY")

    def test_no_expected_id_still_allows_readonly_recovery(self):
        """UNKNOWN without a pinned expected ID must not block legal DEV work."""
        text = "## 0. Snapshot\n- ACTIVE_TASK: dev-task\n## 1. History\nold\n"
        r = self._context(text, None)
        self.assertEqual(r["identity"], "UNKNOWN")
        self.assertEqual(r["status"], "SOURCE_REVIEW_REQUIRED")

    def test_conflicting_declarations_are_unknown_not_silent_pass(self):
        text = ("PROJECT_ID = 44\nPROJECT_ID: 43\n"
                "## 0. Snapshot\nx\n## 1. History\ny\n")
        declared, basis = markdown_project_id(text)
        self.assertIsNone(declared)
        self.assertEqual(basis, "AMBIGUOUS")
        r = self._context(text, "44")
        self.assertEqual(r["status"], "IDENTITY_UNKNOWN")

    def test_prose_mentioning_other_projects_is_not_an_identity(self):
        text = ("# 说明\nP37 与 ws42/43（D1=17376717 IMU-GRF）为不同研究线；"
                "PROJECT_IDENTITY_CHECK 通过。\n"
                "## 0. Snapshot\nx\n## 1. History\ny\n")
        declared, basis = markdown_project_id(text)
        self.assertIsNone(declared)
        self.assertEqual(basis, "ABSENT")

    def test_json_state_identity_still_works(self):
        state = json.dumps({"schema_version": "1.4", "project_id": "44",
                            "active_task_id": "dev-task", "evidence_refs": []})
        base, _, settings = _fixture(state_name="STATE.json",
                                     state_text=state, expected="44")
        r = get_project_context(settings, "p")
        self.assertEqual(r["identity"], "DECLARED_ID_MATCH")
        self.assertEqual(r["identity_basis"], "STATE_JSON")


if __name__ == "__main__":
    unittest.main()
