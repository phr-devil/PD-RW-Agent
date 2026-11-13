"""Small realistic fixtures for the shared Python runtime (no actual data)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from pdrw_agent.config import Settings
from pdrw_agent.service import ResearchService

FINGERPRINT = {
    "task_id": "har-task", "protocol_id": "frozen-v1",
    "dataset_version": "dev-d1", "evaluator_version": "metric-v1",
    "code_sha256": "a" * 64, "config_sha256": "b" * 64,
    "sample_ids_hash": "c" * 64, "seed": 23,
}

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        rules = base / "pd-rw"
        rules.mkdir()
        (rules / "AGENTS.md").write_text(
            "# Router\n## 2. 按需加载专题\n"
            "| Topic | Files |\n| --- | --- |\n"
            "| DEV 算法/实验/负结果 | [EXPERIMENT_LOOP.md](EXPERIMENT_LOOP.md) |\n"
            "| 正式写作 | [WRITING_GATE.md](WRITING_GATE.md) |\n"
            "| 独立确认 | [CONFIRMATION.md](CONFIRMATION.md) |\n"
            "## 3. End\n", encoding="utf-8")
        for n in ("WORKFLOW.md", "EXPERIMENT_LOOP.md", "WRITING_GATE.md", "CONFIRMATION.md"):
            (rules / n).write_text("# active\n", encoding="utf-8")
        (rules / "LESSONS").mkdir()
        (rules / "LESSONS" / "CASE_REGISTRY.md").write_text(
            "# Cases\n| CASE_ID | Lesson |\n| --- | --- |\n"
            "| P25 | HAR 平滑 gain may be evaluation artefact; check permuted control |\n"
            "| P19 | Skill recognition on DEV only |\n",
            encoding="utf-8")
        project = base / "project"
        project.mkdir()
        (project / "STATE.json").write_text(json.dumps({
            "schema_version": "1.4", "project_id": "real-p19",
            "active_task_id": "har-task", "latest_valid_run_id": "run-001",
            "last_event_id": "e1", "evidence_refs": [],
        }), encoding="utf-8")
        (project / "RESEARCH_RECORD.md").write_text(
            "## 0. Snapshot\n- Best: run-001\n"
            "## 1. Older events\nPRIVATE_OLD_HISTORY\n", encoding="utf-8")
        (project / "PAPER_BLUEPRINT.md").write_text("Outline", encoding="utf-8")
        (project / "runs").mkdir()
        run_path = project / "runs" / "r1.json"
        run_path.write_text(json.dumps({
            "run_id": "run-001", "split": "dev", "status": "VALID",
            "task_id": "har-task",
            "experiment_fingerprint": FINGERPRINT,
        }), encoding="utf-8")
        digest = hashlib.sha256(run_path.read_bytes()).hexdigest()
        entries = [
            {"kind": "run", "task_id": "har-task", "artifact_id": "sealed-run",
             "artifact_path": "sealed/secret.json", "split": "sealed", "status": "VALID",
             "artifact_sha256": "d"*64},
            {"kind": "run", "task_id": "har-task", "artifact_id": "run-001",
             "artifact_path": "runs/r1.json", "split": "dev", "status": "VALID",
             "artifact_sha256": digest},
        ]
        (project / "EVENTS.jsonl").write_text(
            "".join(json.dumps(x) + "\n" for x in entries), encoding="utf-8")
        self.config = base / "project-map.local.json"
        self.config.write_text(json.dumps({
            "schema_version": 1, "projects": {
                "19": {"root": str(project),
                       "expected_state_project_id": "real-p19"}
            }
        }), encoding="utf-8")
        self.service = ResearchService(Settings.load(str(self.config), str(rules)))
        self.project = project

    def test_context_and_state_integrity_limit(self):
        r = self.service.call("get_project_context", project_id="19")
        self.assertEqual(r["status"], "SOURCE_REVIEW_REQUIRED")
        self.assertEqual(r["state_index"]["latest_valid_run_id"], "run-001")
        self.assertNotIn("PRIVATE_OLD_HISTORY", r["snapshot_excerpt"])
        self.assertEqual(r["original_user_authorization"], "UNVERIFIED")
        self.assertEqual(r["state_integrity"], "NOT_VERIFIED_AGAINST_EVENTS")

    def test_rule_routing_uses_actual_pdrw_files(self):
        result = self.service.call("get_applicable_rules", topic="DEV 算法")
        self.assertEqual(result["status"], "ROUTE_FOUND")
        self.assertEqual(result["matches"][0]["rule_paths"], ["EXPERIMENT_LOOP.md"])
        self.assertFalse(result["authorization_verified"])

    def test_confirmation_rule_is_navigable_but_never_authorized(self):
        r = self.service.call("get_applicable_rules", topic="独立确认")
        self.assertEqual(r["status"], "ROUTE_FOUND")
        self.assertEqual(r["matches"][0]["rule_paths"], ["CONFIRMATION.md"])
        self.assertFalse(r["authorization_verified"])

    def test_case_memory_is_scoped_as_secondary(self):
        r = self.service.call("search_research_memory", query="HAR")
        self.assertEqual(r["status"], "MATCHES_FOUND")
        self.assertEqual(r["matches"][0]["source_file"], "LESSONS/CASE_REGISTRY.md")
        self.assertIn("NOT_RAW_RUN", r["matches"][0]["evidence_level"])

    def test_memory_limit_rejects_zero_negative_and_boolean(self):
        for bad in (0, -1, True, "3"):
            with self.subTest(limit=bad):
                result = self.service.call("search_research_memory", query="HAR",
                                           limit=bad)
                self.assertEqual(result["status"], "ERROR")
                self.assertEqual(result["error_code"], "LIMIT_INVALID")

    def test_evidence_hash_details_distinguish_unknown_and_mismatch(self):
        ledger = self.project / "EVENTS.jsonl"
        events = [json.loads(x) for x in ledger.read_text(encoding="utf-8").splitlines()]
        for event in events:
            if event.get("artifact_id") == "run-001":
                event.pop("artifact_sha256", None)
        ledger.write_text("".join(json.dumps(x) + chr(10) for x in events), encoding="utf-8")
        result = self.service.call("find_experiment_evidence", project_id="19")
        self.assertIn("matches", result, result)
        self.assertEqual(result["matches"][0]["hash_detail"], "HASH_UNKNOWN")
        self.assertEqual(result["matches"][0]["artifact_sha256_status"],
                         "MISMATCH_OR_UNKNOWN")  # Compatible field.
        for event in events:
            if event.get("artifact_id") == "run-001":
                event["artifact_sha256"] = "0" * 64
        ledger.write_text("".join(json.dumps(x) + chr(10) for x in events), encoding="utf-8")
        result = self.service.call("find_experiment_evidence", project_id="19")
        self.assertEqual(result["matches"][0]["hash_detail"], "HASH_MISMATCH")

    def test_evidence_hides_sealed(self):
        r = self.service.call("find_experiment_evidence", project_id="19")
        self.assertEqual(len(r["matches"]), 1)
        self.assertEqual(r["matches"][0]["run_id"], "run-001")
        self.assertEqual(r["matches"][0]["artifact_sha256_status"], "MATCH")
        self.assertEqual(r["sealed_access"], "NOT_ATTEMPTED")

    def test_duplicate_exact_is_only_a_candidate(self):
        r = self.service.call("check_duplicate_experiment", project_id="19",
                              spec=FINGERPRINT)
        self.assertEqual(r["status"], "DECLARED_DUPLICATE_CANDIDATE")
        self.assertEqual(r["matches"][0]["run_id"], "run-001")
        self.assertFalse(r["scientific_equivalence_verified"])

    def test_duplicate_missing_fingerprint_is_not_guess(self):
        r = self.service.call("check_duplicate_experiment", project_id="19",
                              spec={"task_id": "har-task"})
        self.assertEqual(r["status"], "INSUFFICIENT_FINGERPRINT")
        self.assertEqual(r["matches"], [])

    def test_declared_sealed_state_mapping_is_rejected(self):
        manifest = json.loads(self.config.read_text(encoding="utf-8"))
        manifest["projects"]["19"]["state"] = "B_SEALED_MATERIAL/STATE.json"
        self.config.write_text(json.dumps(manifest), encoding="utf-8")
        r = self.service.call("get_project_context", project_id="19")
        self.assertEqual(r["status"], "ERROR")
        self.assertEqual(r["error_code"], "PROTECTED_PROJECT_PATH")

    def test_mismatched_run_split_is_not_duplicate(self):
        run_path = self.project / "runs" / "r1.json"
        obj = json.loads(run_path.read_text(encoding="utf-8"))
        obj["split"] = "sealed"
        run_path.write_text(json.dumps(obj), encoding="utf-8")
        # The immutable event hash now differs, so this is not usable.
        r = self.service.call("check_duplicate_experiment", project_id="19",
                              spec=FINGERPRINT)
        self.assertEqual(r["status"], "UNVERIFIABLE_HISTORY")
        self.assertEqual(r["matches"], [])

    def test_project_identity_conflict_not_silently_accepted(self):
        manifest = json.loads(self.config.read_text(encoding="utf-8"))
        manifest["projects"]["19"]["expected_state_project_id"] = "not-real"
        self.config.write_text(json.dumps(manifest), encoding="utf-8")
        r = self.service.call("get_project_context", project_id="19")
        self.assertEqual(r["status"], "IDENTITY_CONFLICT")

    def test_unknown_project_does_not_scan(self):
        r = self.service.call("get_project_context", project_id="wrong-number")
        self.assertEqual(r["status"], "ERROR")
        self.assertEqual(r["error_code"], "PROJECT_NOT_REGISTERED")

    def test_outside_mapping_does_not_read(self):
        manifest = json.loads(self.config.read_text(encoding="utf-8"))
        manifest["projects"]["19"]["state"] = "../outside.json"
        self.config.write_text(json.dumps(manifest), encoding="utf-8")
        r = self.service.call("get_project_context", project_id="19")
        self.assertEqual(r["status"], "ERROR")
        self.assertEqual(r["error_code"], "PATH_OUTSIDE_PROJECT")

if __name__ == "__main__":
    unittest.main()
