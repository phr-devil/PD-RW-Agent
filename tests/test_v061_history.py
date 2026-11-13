"""v0.6.1 state replay / original Run / lesson applicability regression tests.

All project data here is synthetic. Real Run schemas are checked against a
separately pinned PD-RW repository in CI, never against a mock scientific rule.
"""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.config import Settings
from pdrw_agent.service import ResearchService
from pdrw_agent.runtime.history import reconstruct_project_history
from pdrw_agent.science.applicability import review_lesson_applicability


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.rules = self.base / "rules"
        self.rules.mkdir()
        (self.rules / "AGENTS.md").write_text("# routes", encoding="utf-8")
        (self.rules / "WORKFLOW.md").write_text("# science", encoding="utf-8")
        self.root = self.base / "project"
        self.root.mkdir()
        (self.root / "RESEARCH_RECORD.md").write_text(
            "## 0. Snapshot\nready\n## 1. Older\n", encoding="utf-8")
        self.state = {
            "schema_version": "1.4", "project_id": "science-test",
            "active_task_id": None, "latest_valid_run_id": None,
            "last_event_id": None, "evidence_refs": [],
        }
        self.save_state()
        self.ledger = self.root / "EVENTS.jsonl"
        self.ledger.write_text("", encoding="utf-8")
        cfg = self.base / "projects.json"
        cfg.write_text(json.dumps({"schema_version": 1, "projects": {
            "demo": {"root": str(self.root), "state": "STATE.json",
                     "expected_state_project_id": "science-test"}}}), encoding="utf-8")
        self.svc = ResearchService(Settings.load(str(cfg), str(self.rules)))

    def save_state(self):
        (self.root / "STATE.json").write_text(
            json.dumps(self.state), encoding="utf-8")

    def run_event(self, source: str, sha: str, *, split="dev", run_id="r1",
                  status="INVALID", linked=None):
        e = {"event_id": "e1", "prev_event_id": None,
             "project_id": "science-test", "kind": "run",
             "artifact_id": run_id, "artifact_path": source,
             "artifact_sha256": sha, "task_id": "task-1",
             "status": status, "split": split}
        if linked is not None:
            e["linked_sha256"] = linked
        return e

    def register(self, event):
        self.ledger.write_text(json.dumps(event) + "\n", encoding="utf-8")
        self.state["last_event_id"] = event["event_id"]
        self.state["active_task_id"] = event["task_id"]
        self.state["latest_valid_run_id"] = (
            event["artifact_id"] if event["status"] == "VALID"
            and event["split"] != "sealed" else None)
        self.state["evidence_refs"] = [{
            "kind": "run", "id": event["artifact_id"],
            "path": event["artifact_path"], "sha256": event["artifact_sha256"]}]
        self.save_state()

    def test_initial_state_exact_reconstruction(self):
        out = self.svc.call("reconstruct_project_history", project_id="demo")
        self.assertEqual(out["status"], "METADATA_CHAIN_MATCHED_ONLY")
        self.assertEqual(out["event_count"], 0)
        self.assertTrue(out["event_chain_valid"])
        self.assertTrue(out["state_matches_events"])
        self.assertFalse(out["scientific_claims_verified"])

    def test_missing_events_and_state_are_distinct(self):
        self.ledger.unlink()
        out = self.svc.call("reconstruct_project_history", project_id="demo")
        self.assertEqual(out["status"], "HISTORY_SOURCES_MISSING")
        self.assertEqual(out["missing"], ["EVENTS.jsonl"])

    def test_crash_after_event_append_is_detected_and_blocks_resume(self):
        e = self.run_event("runs/orphan.json", "b" * 64)
        self.ledger.write_text(json.dumps(e) + "\n", encoding="utf-8")
        out = self.svc.call("reconstruct_project_history", project_id="demo")
        self.assertEqual(out["status"], "STATE_EVENTS_MISMATCH")
        self.assertIn("last_event_id", out["differing_state_fields"])
        resume = self.svc.call("get_resume_context", project_id="demo")
        self.assertEqual(resume["status"], "BLOCKED_HISTORY_INCONSISTENT")
        self.assertFalse(resume["restart_permitted"])

    def test_broken_event_chain_is_not_treated_as_recoverable(self):
        e = self.run_event("runs/r1.json", "c" * 64)
        e["prev_event_id"] = "wrong"
        self.ledger.write_text(json.dumps(e) + "\n", encoding="utf-8")
        out = self.svc.call("reconstruct_project_history", project_id="demo")
        self.assertEqual(out["status"], "EVENT_CHAIN_INVALID")
        self.assertEqual(out["first_invalid_line"], 1)

    def test_sealed_event_metadata_is_not_a_sealed_artifact_read(self):
        e = self.run_event("B_SEALED/secret.json", "d" * 64,
                           split="sealed", status="VALID")
        self.register(e)
        out = self.svc.call("reconstruct_project_history", project_id="demo")
        self.assertEqual(out["status"], "METADATA_CHAIN_MATCHED_ONLY")
        self.assertEqual(out["protected_event_count_metadata_only"], 1)
        self.assertFalse(out["sealed_artifacts_opened"])
        source = self.svc.call("verify_run_evidence", project_id="demo", run_id="r1")
        self.assertEqual(source["status"], "PROTECTED_RUN_NOT_OPENED")

    def test_bad_metadata_and_malformed_json_do_not_trigger_repair(self):
        self.ledger.write_text("{broken\n", encoding="utf-8")
        out = self.svc.call("reconstruct_project_history", project_id="demo")
        self.assertEqual(out["status"], "HISTORY_SOURCE_INVALID")
        self.assertFalse(out["execution_authorized"])


@unittest.skipUnless(os.getenv("PDRW_TEST_RULE_ROOT"),
                     "Requires pinned original PD-RW checker")
class RealContractRunTests(HistoryTests):
    def setUp(self):
        super().setUp()
        rule_root = Path(os.environ["PDRW_TEST_RULE_ROOT"]).resolve()
        self.svc = ResearchService(Settings.load(
            str(self.svc.settings.project_map), str(rule_root)))
        (self.root / "runs").mkdir()

    def create_run(self, valid: bool):
        run = {
            "run_id": "r1", "task_id": "task-1",
            "protocol_id": "frozen-v1",
            "dataset_version": "synthetic-v1",
            "evaluator_version": "metric-v1",
            "group_split": "group-test",
            "sample_ids_hash": "keys-v1", "split": "dev",
            "status": "VALID" if valid else "INVALID",
            "legal_inputs": ["sensor_input"], "metrics": {},
        }
        links = {}
        if valid:
            for name, body in [("metrics.json", b"{}"),
                               ("predictions.csv", b"one,two\n"),
                               ("code.py", b"pass\n")]:
                file = self.root / "runs" / name
                file.write_bytes(body)
                links["runs/" + name] = digest(file)
            run["metrics"] = {"MAE": 0.5}
            run["artifact_refs"] = {
                "metrics": "runs/metrics.json",
                "predictions": "runs/predictions.csv",
                "code": "runs/code.py",
            }
        file = self.root / "runs" / "r1.json"
        file.write_text(json.dumps(run), encoding="utf-8")
        event = self.run_event("runs/r1.json", digest(file),
                               status=run["status"], linked=links if valid else None)
        self.register(event)
        return file

    def test_invalid_run_is_not_negative_science_evidence(self):
        self.create_run(valid=False)
        data = self.svc.call("verify_run_evidence", project_id="demo", run_id="r1")
        self.assertEqual(data["status"], "RUN_SOURCE_MATCHED_ONLY", data)
        self.assertFalse(data["scientific_validity_verified"])

    def test_valid_run_linked_hashes_and_tampering(self):
        self.create_run(valid=True)
        data = self.svc.call("verify_run_evidence", project_id="demo", run_id="r1")
        self.assertEqual(data["status"], "RUN_BYTES_MATCHED_ONLY", data)
        self.assertEqual(data["links_checked"], 3)
        self.assertFalse(data["scientific_validity_verified"])
        (self.root / "runs" / "predictions.csv").write_text("tampered",
                                                         encoding="utf-8")
        changed = self.svc.call("verify_run_evidence", project_id="demo", run_id="r1")
        self.assertEqual(changed["status"], "RUN_LINK_HASH_MISMATCH", changed)

    def test_unhashed_valid_run_never_claims_fully_checked(self):
        self.create_run(valid=True)
        e = json.loads(self.ledger.read_text(encoding="utf-8"))
        e.pop("linked_sha256", None)
        self.ledger.write_text(json.dumps(e) + "\n", encoding="utf-8")
        data = self.svc.call("verify_run_evidence", project_id="demo", run_id="r1")
        self.assertEqual(data["status"], "RUN_LINK_HASHES_MISSING")

    def test_original_run_change_is_detected(self):
        file = self.create_run(valid=False)
        file.write_text(file.read_text(encoding="utf-8") + " ",
                        encoding="utf-8")
        result = self.svc.call("verify_run_evidence", project_id="demo", run_id="r1")
        self.assertEqual(result["status"], "RUN_HASH_MISMATCH")

    def test_authoritative_run_contract_rejects_invalid_structure(self):
        file = self.create_run(valid=False)
        obj = json.loads(file.read_text(encoding="utf-8"))
        obj.pop("group_split")
        file.write_text(json.dumps(obj), encoding="utf-8")
        event = json.loads(self.ledger.read_text(encoding="utf-8"))
        event["artifact_sha256"] = digest(file)
        self.register(event)
        result = self.svc.call("verify_run_evidence", project_id="demo", run_id="r1")
        self.assertEqual(result["status"], "RUN_CONTRACT_INVALID")


class LessonApplicabilityTests(unittest.TestCase):
    def test_valid_scope_exact_vs_conflicting_and_missing(self):
        scope = {
            "dataset_version": "D1", "evaluation_unit": "subject",
            "group_split": "LOSO", "metric": "macro-F1",
            "legal_inputs": "PPG-only"
        }
        lessons = [
            {"premise_id": "p1", "scope": scope, "validity": "VALID_NEGATIVE",
             "evidence_refs": ["runs/r1.json"]},
            {"premise_id": "p1", "scope": {**scope, "group_split": "random"},
             "validity": "VALID_NEGATIVE", "evidence_refs": ["runs/r2.json"]},
            {"premise_id": "p1", "scope": {"dataset_version": "D1"},
             "validity": "VALID_NEGATIVE", "evidence_refs": ["r3"]},
            {"premise_id": "p1", "scope": scope, "validity": "INVALID",
             "evidence_refs": ["r4"]},
            {"premise_id": "different", "scope": scope,
             "validity": "VALID_NEGATIVE", "evidence_refs": ["r5"]},
        ]
        result = review_lesson_applicability(
            {"premise_id": "p1", "scope": scope}, lessons)
        self.assertEqual(result["status"], "ADVISORY_SCOPE_COMPARISON_ONLY")
        self.assertEqual([x["classification"] for x in result["reviews"]],
                         ["EXACT_DECLARED_SCOPE_CANDIDATE", "CONFLICTING_SCOPE",
                          "CRITICAL_SCOPE_UNKNOWN", "NOT_VALID_NEGATIVE",
                          "DIFFERENT_PREMISE"])
        self.assertEqual(result["exact_declared_candidates"], 1)
        self.assertFalse(result["automatic_stop"])
        self.assertFalse(result["scientific_equivalence_verified"])

    def test_missing_critical_and_partial_scope_are_not_exact(self):
        s = {"dataset_version": "D1", "evaluation_unit": "trial",
             "group_split": "group", "metric": "MAE"}
        partial = review_lesson_applicability(
            {"premise_id": "x", "scope": {**s, "new": "A"}},
            [{"premise_id": "x", "scope": s,
              "validity": "VALID_NEGATIVE", "evidence_refs": ["r"]}])
        self.assertEqual(partial["reviews"][0]["classification"],
                         "PARTIAL_SCOPE_OVERLAP")
        missing = review_lesson_applicability(
            {"premise_id": "x", "scope": {"metric": "MAE"}},
            [{"premise_id": "x", "scope": {"metric": "MAE"},
              "validity": "VALID_NEGATIVE", "evidence_refs": ["r"]}])
        self.assertEqual(missing["reviews"][0]["classification"],
                         "CRITICAL_SCOPE_UNKNOWN")

    def test_invalid_declared_packet_fails(self):
        with self.assertRaises(ValueError):
            review_lesson_applicability({"premise_id": "", "scope": {}}, [])
