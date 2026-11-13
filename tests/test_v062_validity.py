"""v0.6.2 scientific check engine: synthetic original-PD-RW-contract fixtures.

Every source belongs to an explicit registered DEV project; no SEALED reads,
research commits, download, models, external APIs or scientific assumptions.
"""
import hashlib
import json
import math
import os
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.config import Settings
from pdrw_agent.service import ResearchService


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(os.getenv("PDRW_TEST_RULE_ROOT"),
                     "Requires original pinned PD-RW Run contract in CI")
class ScientificAuditTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "project"
        self.root.mkdir()
        self.rules = Path(os.environ["PDRW_TEST_RULE_ROOT"]).resolve()
        self.info = {}
        self.events = []
        self.base_rows = [
            "sample_id,group_id,y_true,y_pred",
            "s1,g3,1,0", "s2,g4,3,2",
        ]
        self.main_rows = [
            "sample_id,group_id,y_true,y_pred",
            "s1,g3,1,1.1", "s2,g4,3,3.1",
        ]
        self.train_rows = [
            "sample_id,group_id", "t1,g1", "t2,g2"
        ]
        self._create_run("r-base", self.base_rows, metric=1.0,
                         with_audit=False)
        self._create_run("r-main", self.main_rows, metric=0.1,
                         with_audit=True)
        self._update_ledger()
        cfg = self.root.parent / "projects.json"
        cfg.write_text(json.dumps({"schema_version": 1, "projects": {
            "demo": {"root": str(self.root),
                     "expected_state_project_id": "science-test"}}}),
            encoding="utf-8")
        self.svc = ResearchService(Settings.load(str(cfg), str(self.rules)))

    def _write(self, path, content):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path.relative_to(self.root).as_posix()

    def _create_run(self, name, rows, metric, *, with_audit):
        directory = self.root / "runs" / name
        directory.mkdir(parents=True)
        predictions = self._write(directory / "predictions.csv", "\n".join(rows) + "\n")
        training = self._write(directory / "train_index.csv", "\n".join(self.train_rows) + "\n")
        metrics = self._write(directory / "metrics.json", json.dumps({"MAE": metric}))
        code = self._write(directory / "code.py", "pass\n")
        refs = {"predictions": predictions, "train_index": training,
                "metrics": metrics, "code": code}
        if with_audit:
            spec = {
                "schema_version": "pdrw-science-audit-v1",
                "run_id": name, "metric": "MAE", "evaluation_unit": "sample",
                "independence_unit": "group", "baseline_run_id": "r-base",
                "used_inputs_declared": ["sensor"],
            }
            refs["science_audit"] = self._write(directory / "audit.json", json.dumps(spec))
        run = {
            "run_id": name, "task_id": "task-1", "protocol_id": "protocol-v1",
            "dataset_version": "synthetic-v1", "evaluator_version": "MAE-v1",
            "group_split": "group-disjoint", "sample_ids_hash": "evaluation-v1",
            "status": "VALID", "split": "dev", "legal_inputs": ["sensor"],
            "metrics": {"MAE": metric}, "artifact_refs": refs,
            "evaluation_unit": "sample", "budget_basis": "CPU-hours-v1",
            "label_definition": "synthetic-force-v1", "metric_direction": "min",
            "independence_unit": "group"
        }
        run_path = self._write(directory / "run.json", json.dumps(run))
        event = {
            "kind": "run", "project_id": "science-test",
            "event_id": "event-" + name,
            "prev_event_id": ("event-r-base" if name == "r-main" else None),
            "artifact_id": name, "artifact_path": run_path,
            "artifact_sha256": sha(self.root / run_path),
            "task_id": "task-1", "split": "dev", "status": "VALID",
            "linked_sha256": {p: sha(self.root / p) for p in refs.values()},
        }
        self.info[name] = (run, event, run_path)
        self.events.append(event)

    def _update_ledger(self):
        self._write(self.root / "EVENTS.jsonl",
                    "".join(json.dumps(e) + "\n" for e in self.events))
        self._write(self.root / "STATE.json", json.dumps({
            "schema_version": "1.4", "project_id": "science-test",
            "active_task_id": "task-1", "last_event_id": "event-r-main",
            "latest_valid_run_id": "r-main",
            "evidence_refs": [
                {"kind": "run", "id": e["artifact_id"],
                 "path": e["artifact_path"], "sha256": e["artifact_sha256"]}
                for e in self.events
            ],
        }))

    def _rewrite_link(self, name, key, text):
        run, event, _ = self.info[name]
        ref = run["artifact_refs"][key]
        self._write(self.root / ref, text)
        event["linked_sha256"][ref] = sha(self.root / ref)
        self._update_ledger()

    def _rewrite_run(self, name):
        run, event, ref = self.info[name]
        self._write(self.root / ref, json.dumps(run))
        event["artifact_sha256"] = sha(self.root / ref)
        self._update_ledger()

    def audit(self, **kwargs):
        return self.svc.call("audit_scientific_experiment",
                             project_id="demo", run_id="r-main", **kwargs)

    def test_matched_sources_metric_baseline_and_split(self):
        result = self.audit()
        self.assertEqual(result["status"], "SCIENTIFIC_AUDIT_INCOMPLETE", result)
        for key in ("split_leakage", "metric_recomputation", "baseline_fairness",
                    "evaluation_unit"):
            self.assertEqual(result["checks"][key]["status"], "PASS", result)
        self.assertEqual(result["checks"]["input_legality"]["status"], "UNKNOWN")
        self.assertAlmostEqual(result["checks"]["metric_recomputation"]["computed"], 0.1)
        self.assertFalse(result["scientific_validity_verified"])
        self.assertFalse(result["original_code_inputs_traced"])
        self.assertFalse(result["dataset_label_semantics_verified"])

    def test_detect_sample_leakage_and_group_overlap(self):
        self._rewrite_link("r-main", "train_index",
                           "sample_id,group_id\nt1,g1\ns1,g3\n")
        result = self.audit()
        self.assertEqual(result["checks"]["split_leakage"]["status"], "FAIL")
        self.assertEqual(result["checks"]["split_leakage"]["shared_sample_ids"], 1)
        self.assertEqual(result["checks"]["split_leakage"]["shared_groups"], 1)
        self.assertEqual(result["status"], "SCIENTIFIC_AUDIT_CONFLICT")

    def test_group_only_overlap_detected_under_group_policy(self):
        self._rewrite_link("r-main", "train_index",
                           "sample_id,group_id\nt1,g3\nt2,g2\n")
        result = self.audit()
        self.assertEqual(result["checks"]["split_leakage"]["status"], "FAIL")
        self.assertEqual(result["checks"]["split_leakage"]["shared_sample_ids"], 0)
        self.assertEqual(result["checks"]["split_leakage"]["shared_groups"], 1)

    def test_metric_disagreement_after_honest_file_update(self):
        run, _, _ = self.info["r-main"]
        run["metrics"]["MAE"] = 0.8
        self._rewrite_run("r-main")
        result = self.audit()
        self.assertEqual(result["checks"]["metric_recomputation"]["status"], "FAIL")
        self.assertAlmostEqual(result["checks"]["metric_recomputation"]["computed"], 0.1)

    def test_mismatch_with_canonical_sample_fingerprint_is_found(self):
        run, _, _ = self.info["r-main"]
        spec_ref = run["artifact_refs"]["science_audit"]
        spec = json.loads((self.root / spec_ref).read_text(encoding="utf-8"))
        spec["sample_ids_hash_rule"] = "sha256_sorted_ids_v1"
        self._rewrite_link("r-main", "science_audit", json.dumps(spec))
        run["sample_ids_hash"] = "0" * 64
        self._rewrite_run("r-main")
        output = self.audit()
        self.assertEqual(output["checks"]["sample_identity_fingerprint"]["status"], "FAIL")

    def test_matched_canonical_sample_fingerprint_is_found(self):
        run, _, _ = self.info["r-main"]
        spec_ref = run["artifact_refs"]["science_audit"]
        spec = json.loads((self.root / spec_ref).read_text(encoding="utf-8"))
        spec["sample_ids_hash_rule"] = "sha256_sorted_ids_v1"
        self._rewrite_link("r-main", "science_audit", json.dumps(spec))
        fingerprint = hashlib.sha256(b"s1\ns2\n").hexdigest()
        run["sample_ids_hash"] = fingerprint
        self._rewrite_run("r-main")
        # Baseline ID hash must match if the declared evaluation set is shared.
        prior, _, _ = self.info["r-base"]
        prior["sample_ids_hash"] = fingerprint
        self._rewrite_run("r-base")
        output = self.audit()
        self.assertEqual(output["checks"]["sample_identity_fingerprint"]["status"], "PASS")
        self.assertEqual(output["checks"]["baseline_fairness"]["status"], "PASS")

    def test_split_independence_claim_conflict_is_detected(self):
        run, _, _ = self.info["r-main"]
        run["independence_unit"] = "sample"
        self._rewrite_run("r-main")
        result = self.audit()
        self.assertEqual(result["checks"]["split_policy_alignment"]["status"], "FAIL")
        self.assertEqual(result["status"], "SCIENTIFIC_AUDIT_CONFLICT")

    def test_tampered_predictions_block_even_if_metric_is_correct(self):
        p = self.root / self.info["r-main"][0]["artifact_refs"]["predictions"]
        p.write_text(p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        result = self.audit()
        self.assertEqual(result["status"], "AUDIT_PREREQUISITE_UNVERIFIED")
        self.assertEqual(result["run_evidence_status"], "RUN_LINK_HASH_MISMATCH")

    def test_spec_must_be_hash_bound(self):
        run, event, _ = self.info["r-main"]
        spec = run["artifact_refs"].pop("science_audit")
        event["linked_sha256"].pop(spec)
        self._rewrite_run("r-main")
        self.assertEqual(self.audit()["status"], "AUDIT_SPEC_NOT_BOUND_TO_RUN")

    def test_prohibited_declared_input_is_detected(self):
        run, _, _ = self.info["r-main"]
        spec_ref = run["artifact_refs"]["science_audit"]
        spec = json.loads((self.root / spec_ref).read_text(encoding="utf-8"))
        spec["used_inputs_declared"] = ["sensor", "future_label"]
        self._rewrite_link("r-main", "science_audit", json.dumps(spec))
        result = self.audit()
        self.assertEqual(result["checks"]["input_legality"]["status"], "FAIL")
        self.assertEqual(result["checks"]["input_legality"]["declared_out_of_scope"],
                         ["future_label"])

    def test_baseline_ground_truth_or_group_disagreement(self):
        self._rewrite_link("r-base", "predictions",
                           "sample_id,group_id,y_true,y_pred\ns1,g999,1,0\ns2,g4,3,2\n")
        result = self.audit()
        self.assertEqual(result["checks"]["baseline_fairness"]["status"], "FAIL")
        self.assertIn("prediction_identity_or_ground_truth",
                      result["checks"]["baseline_fairness"]["differing_fields"])

    def test_budget_mismatch_requires_comparison_review(self):
        run, _, _ = self.info["r-base"]
        run["budget_basis"] = "different-budget"
        self._rewrite_run("r-base")
        result = self.audit()
        self.assertEqual(result["checks"]["baseline_fairness"]["status"], "FAIL")
        self.assertIn("budget_basis", result["checks"]["baseline_fairness"]["differing_fields"])

    def test_baseline_training_membership_conflict(self):
        self._rewrite_link("r-base", "train_index",
                           "sample_id,group_id\nt1,g1\nt9,g2\n")
        result = self.audit()
        self.assertEqual(result["checks"]["baseline_fairness"]["status"], "FAIL")
        self.assertIn("training_membership",
                      result["checks"]["baseline_fairness"]["differing_fields"])

    def test_missing_budget_is_unknown_not_fairness_pass(self):
        run, _, _ = self.info["r-base"]
        run.pop("budget_basis")
        self._rewrite_run("r-base")
        result = self.audit()
        self.assertEqual(result["checks"]["baseline_fairness"]["status"], "UNKNOWN")
        self.assertIn("budget_basis_not_declared",
                      result["checks"]["baseline_fairness"]["unresolved_fields"])

    def test_missing_train_index_is_unknown_not_no_leakage(self):
        run, event, _ = self.info["r-main"]
        ref = run["artifact_refs"].pop("train_index")
        event["linked_sha256"].pop(ref)
        self._rewrite_run("r-main")
        result = self.audit()
        self.assertEqual(result["checks"]["split_leakage"]["status"], "UNKNOWN")

    def test_malformed_train_index_is_failure_not_false_leakage_pass(self):
        self._rewrite_link("r-main", "train_index",
                           "sample_id,group_id\nt1,g1\nt1,g2\n")
        result = self.audit()
        self.assertEqual(result["checks"]["split_leakage"]["status"], "FAIL")
        self.assertEqual(result["checks"]["split_leakage"]["reason"],
                         "EVALUATION_KEYS_INVALID")

    def test_group_metric_equal_weighting_is_explicit(self):
        run, _, _ = self.info["r-main"]
        ref = run["artifact_refs"]["science_audit"]
        spec = json.loads((self.root / ref).read_text(encoding="utf-8"))
        spec["evaluation_unit"] = "group"
        self._rewrite_link("r-main", "science_audit", json.dumps(spec))
        run["evaluation_unit"] = "group"
        self._rewrite_run("r-main")
        result = self.audit()
        self.assertEqual(result["checks"]["metric_recomputation"]["status"], "PASS")
        self.assertEqual(result["checks"]["metric_recomputation"]["formula"],
                         "equal_group_mean_of_per_group_metrics")

    def test_duplicate_prediction_id_rejected(self):
        self._rewrite_link("r-main", "predictions",
                           "sample_id,group_id,y_true,y_pred\ns1,g3,1,1\ns1,g4,3,3\n")
        result = self.audit()
        self.assertEqual(result["status"], "EVALUATION_SOURCE_INVALID")
        self.assertEqual(result["reason"], "EVALUATION_KEYS_INVALID")

    def test_safeguard_protected_reference(self):
        run, event, _ = self.info["r-main"]
        old = run["artifact_refs"]["train_index"]
        run["artifact_refs"]["train_index"] = "B_SEALED/train_index.csv"
        event["linked_sha256"].pop(old)
        event["linked_sha256"]["B_SEALED/train_index.csv"] = "a"*64
        self._rewrite_run("r-main")
        result = self.audit()
        self.assertEqual(result["status"], "AUDIT_PREREQUISITE_UNVERIFIED")
        self.assertEqual(result["run_evidence_status"], "RUN_LINK_UNAVAILABLE_OR_PROTECTED")

    def test_missing_or_damaged_machine_ledger_blocks_row_checks(self):
        (self.root / "STATE.json").unlink()
        self.assertEqual(self.audit()["status"], "AUDIT_PREREQUISITE_UNVERIFIED")


class MetricFormulaTests(unittest.TestCase):
    def test_fixed_class_macro_f1_includes_unobserved_class(self):
        from pdrw_agent.science.validity import _metric
        rows = [
            {"sample_id": "s1", "group_id": "g1", "y_true": "A", "y_pred": "A"},
            {"sample_id": "s2", "group_id": "g2", "y_true": "A", "y_pred": "B"},
        ]
        score, units = _metric(rows, "macro_f1", "sample", ["A", "B", "C"])
        self.assertAlmostEqual(score, 2/9)
        self.assertEqual(units, 2)
        acc, _ = _metric(rows, "accuracy", "sample", [])
        self.assertEqual(acc, 0.5)

    def test_class_universe_absence_and_group_classification_fail_closed(self):
        from pdrw_agent.science.validity import _metric
        from pdrw_agent.schemas import AgentError
        rows = [{"sample_id": "s1", "group_id": "g1",
                 "y_true": "A", "y_pred": "A"}]
        with self.assertRaises(AgentError):
            _metric(rows, "macro_f1", "sample", [])
        with self.assertRaises(AgentError):
            _metric(rows, "macro_f1", "group", ["A"])

    def test_equal_group_weighting_differs_from_pooled_mae(self):
        from pdrw_agent.science.validity import _metric
        rows = [
            {"sample_id": "s1", "group_id": "g1", "y_true": "0", "y_pred": "0"},
            {"sample_id": "s2", "group_id": "g1", "y_true": "0", "y_pred": "0"},
            {"sample_id": "s3", "group_id": "g2", "y_true": "0", "y_pred": "3"},
        ]
        pooled, _ = _metric(rows, "MAE", "sample", [])
        macro, _ = _metric(rows, "MAE", "group", [])
        self.assertAlmostEqual(pooled, 1.0)
        self.assertAlmostEqual(macro, 1.5)


if __name__ == "__main__":
    unittest.main()
