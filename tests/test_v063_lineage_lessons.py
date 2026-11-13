"""v0.6.3: immutable-source AST, reported content fingerprints and Run-grounded lessons."""
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.science.lineage import audit_python_code
from pdrw_agent.config import Settings
from pdrw_agent.service import ResearchService


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class StaticCodeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.code = self.root / "train.py"

    def inspect(self, source):
        self.code.write_text(source, encoding="utf-8")
        return audit_python_code(self.root, "train.py", ["sensor", "temperature"])

    def test_literal_forbidden_feature_as_model_input(self):
        out = self.inspect("raise RuntimeError('never execute this')\n"
                           "X_train = df[['sensor', 'future_label']]\n")
        self.assertEqual(out["status"], "REVIEW")
        self.assertIn("STATIC_FEATURE_ALLOWLIST_CONFLICT", out["risk_types"])
        self.assertEqual(out["forbidden_feature_sink_occurrences"], 1)
        self.assertFalse(out["code_executed"])
        self.assertFalse(out["runtime_feature_lineage_verified"])

    def test_static_list_alias_is_resolved(self):
        out = self.inspect("feature_cols = ['sensor', 'future_label']\n"
                           "X_train = table[feature_cols]\n")
        self.assertEqual(out["status"], "REVIEW")

    def test_dynamic_reassignment_does_not_assert_proof(self):
        out = self.inspect("cols = ['future_label']\ncols = choose_columns()\n"
                           "X_train = table[cols]\n")
        self.assertEqual(out["status"], "UNKNOWN")
        self.assertEqual(out["unresolved_feature_sinks"], 1)

    def test_fit_on_evaluation_named_input_requires_review(self):
        out = self.inspect("scaler.fit_transform(X_test)\n")
        self.assertEqual(out["status"], "REVIEW")
        self.assertIn("POSSIBLE_EVALUATION_FIT_OR_PREPROCESSING_LEAK",
                      out["risk_types"])

    def test_no_static_conflict_never_claims_dynamic_execution_proven(self):
        out = self.inspect("X_train = df[['sensor']]\n")
        self.assertEqual(out["status"], "UNKNOWN")
        self.assertFalse(out["trained_code_proven"])

    def test_syntax_error_is_not_a_pass(self):
        out = self.inspect("def broken(\n")
        self.assertEqual(out["status"], "UNKNOWN")
        self.assertEqual(out["reason"], "CODE_NOT_PARSEABLE")


@unittest.skipUnless(os.getenv("PDRW_TEST_RULE_ROOT"),
                     "Requires pinned original PD-RW backend")
class BoundScienceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root = base / "project"
        self.root.mkdir()
        self.rules = Path(os.environ["PDRW_TEST_RULE_ROOT"]).resolve()
        self.runs = {}
        self.events = []
        self._make_run("r-base", 1.0, ["1,0", "3,2"])
        self._make_run("r-main", 0.1, ["1,1.1", "3,3.1"])
        self._write_ledgers()
        cfg = base / "projects.json"
        cfg.write_text(json.dumps({"schema_version": 1, "projects": {
            "demo": {"root": str(self.root),
                     "expected_state_project_id": "science-test"}}}), encoding="utf-8")
        self.service = ResearchService(Settings.load(str(cfg), str(self.rules)))

    def _write(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value, encoding="utf-8")
        return name

    def _make_run(self, name, mae, pairs):
        directory = f"runs/{name}/"
        pred = self._write(directory+"predictions.csv",
                           "sample_id,group_id,y_true,y_pred\n"
                           f"s1,g3,{pairs[0]}\ns2,g4,{pairs[1]}\n")
        train = self._write(directory+"train_index.csv",
                            "sample_id,group_id\nt1,g1\nt2,g2\n")
        code = self._write(directory+"code.py", "X_train = table[['sensor']]\n")
        metrics = self._write(directory+"metrics.json", json.dumps({"MAE": mae}))
        refs = {"predictions": pred, "train_index": train,
                "code": code, "metrics": metrics}
        if name == "r-main":
            spec = {"schema_version": "pdrw-science-audit-v1",
                    "run_id": name, "metric": "MAE", "evaluation_unit": "sample",
                    "independence_unit": "group", "baseline_run_id": "r-base",
                    "used_inputs_declared": ["sensor"]}
            refs["science_audit"] = self._write(
                directory+"science_audit.json", json.dumps(spec))
        run = {
            "run_id": name, "task_id": "task-1", "protocol_id": "P1",
            "dataset_version": "D1", "evaluator_version": "E1",
            "group_split": "group-disjoint", "sample_ids_hash": "eval-v1",
            "status": "VALID", "split": "dev", "legal_inputs": ["sensor"],
            "metrics": {"MAE": mae}, "artifact_refs": refs,
            "evaluation_unit": "sample", "independence_unit": "group",
            "label_definition": "force-v1", "metric_direction": "min",
            "budget_basis": "B1"}
        run_ref = self._write(directory+"run.json", json.dumps(run))
        event = {"kind": "run", "project_id": "science-test",
                 "event_id": "e-"+name,
                 "prev_event_id": "e-r-base" if name == "r-main" else None,
                 "artifact_id": name, "artifact_path": run_ref,
                 "artifact_sha256": sha(self.root / run_ref),
                 "task_id": "task-1", "split": "dev", "status": "VALID",
                 "linked_sha256": {ref: sha(self.root / ref) for ref in refs.values()}}
        self.runs[name] = (run, event, run_ref)
        self.events.append(event)

    def _write_ledgers(self):
        self._write("EVENTS.jsonl",
                    "".join(json.dumps(e)+"\n" for e in self.events))
        self._write("STATE.json", json.dumps({
            "schema_version": "1.4", "project_id": "science-test",
            "active_task_id": "task-1", "last_event_id": "e-r-main",
            "latest_valid_run_id": "r-main",
            "evidence_refs": [
                {"kind": "run", "id": e["artifact_id"],
                 "path": e["artifact_path"], "sha256": e["artifact_sha256"]}
                for e in self.events]}))

    def link(self, name, key, content, suffix="json"):
        run, event, ref = self.runs[name]
        path = f"runs/{name}/{key}.{suffix}"
        self._write(path, content)
        run["artifact_refs"][key] = path
        event["linked_sha256"][path] = sha(self.root / path)
        self._rewrite(name)

    def rewrite_link(self, name, key, content):
        run, event, ref = self.runs[name]
        path = run["artifact_refs"][key]
        self._write(path, content)
        event["linked_sha256"][path] = sha(self.root / path)
        self._write_ledgers()

    def _rewrite(self, name):
        run, event, ref = self.runs[name]
        self._write(ref, json.dumps(run))
        event["artifact_sha256"] = sha(self.root / ref)
        self._write_ledgers()

    def science(self):
        return self.service.call("audit_scientific_experiment",
                                 project_id="demo", run_id="r-main")

    def scope(self):
        return {
            "dataset_version": "D1",
            "label_definition": "force-v1",
            "evaluation_unit": "sample",
            "group_split": "group-disjoint",
            "legal_inputs": "sensor",
            "metric": "MAE",
            "comparison_reference": "r-base",
        }

    def add_lesson(self, threshold=0.05, **changes):
        run = self.runs["r-main"][0]
        context = {
            "schema_version": "pdrw-run-lesson-v1",
            "run_id": "r-main", "premise_id": "hypothesis-A",
            "outcome": "DECLARED_NEGATIVE",
            "minimum_important_improvement": threshold,
            "scope": self.scope(),
        }
        context.update(changes)
        self.link("r-main", "lesson_context", json.dumps(context))

    def review(self, proposal=None):
        return self.service.call(
            "review_evidenced_lesson", project_id="demo", run_id="r-main",
            proposal=proposal or {"premise_id": "hypothesis-A", "scope": self.scope()})

    def test_unresolved_code_is_unknown_not_pass(self):
        out = self.science()
        self.assertEqual(out["checks"]["source_code_lineage"]["status"], "UNKNOWN")
        self.assertEqual(out["checks"]["cross_split_content_identity"]["status"],
                         "UNKNOWN")
        self.assertFalse(out["original_code_inputs_traced"])

    def test_literal_forbidden_code_sink_requires_review(self):
        self.rewrite_link("r-main", "code",
                          "X_train = frame[['sensor', 'future_label']]\n")
        out = self.science()
        self.assertEqual(out["checks"]["source_code_lineage"]["status"], "REVIEW")
        self.assertIn("source_code_lineage", out["review_checks"])
        self.assertEqual(out["status"], "SCIENTIFIC_AUDIT_REVIEW_REQUIRED")

    def _fingerprints(self, overlap):
        run = self.runs["r-main"][0]
        spec_ref = run["artifact_refs"]["science_audit"]
        spec = json.loads((self.root / spec_ref).read_text(encoding="utf-8"))
        spec["content_fingerprint_rule"] = "sha256_canonical_input_v1"
        self.rewrite_link("r-main", "science_audit", json.dumps(spec))
        a = "a" * 64
        b = "b" * 64
        c = "c" * 64
        d = "d" * 64
        train = (f"sample_id,group_id,feature_sha256\n"
                 f"t1,g1,{a}\nt2,g2,{b}\n")
        eval_ = (f"sample_id,group_id,feature_sha256\n"
                 f"s1,g3,{a if overlap else c}\ns2,g4,{d}\n")
        self.link("r-main", "train_content_hashes", train, "csv")
        self.link("r-main", "eval_content_hashes", eval_, "csv")

    def test_content_collision_across_different_ids_is_detected(self):
        self._fingerprints(True)
        out = self.science()
        check = out["checks"]["cross_split_content_identity"]
        self.assertEqual(check["status"], "FAIL", out)
        self.assertEqual(check["cross_split_content_hash_matches"], 1)
        self.assertFalse(check["source_truth_verified"])
        self.assertEqual(out["status"], "SCIENTIFIC_AUDIT_CONFLICT")

    def test_content_fingerprint_without_frozen_rule_remains_unknown(self):
        self._fingerprints(True)
        run = self.runs["r-main"][0]
        spec_ref = run["artifact_refs"]["science_audit"]
        spec = json.loads((self.root / spec_ref).read_text(encoding="utf-8"))
        spec.pop("content_fingerprint_rule")
        self.rewrite_link("r-main", "science_audit", json.dumps(spec))
        check = self.science()["checks"]["cross_split_content_identity"]
        self.assertEqual(check["status"], "UNKNOWN")
        self.assertEqual(check["reason"],
                         "CANONICAL_INPUT_FINGERPRINT_RULE_NOT_DECLARED")

    def test_no_content_collision_remains_unknown(self):
        self._fingerprints(False)
        check = self.science()["checks"]["cross_split_content_identity"]
        self.assertEqual(check["status"], "UNKNOWN")
        self.assertEqual(check["cross_split_content_hash_matches"], 0)

    def test_content_manifest_membership_mismatch_is_detected(self):
        self._fingerprints(False)
        ref = self.runs["r-main"][0]["artifact_refs"]["eval_content_hashes"]
        text = (self.root / ref).read_text(encoding="utf-8").replace("s1,g3", "other,g3")
        self.rewrite_link("r-main", "eval_content_hashes", text)
        out = self.science()
        self.assertEqual(out["checks"]["cross_split_content_identity"]["status"], "FAIL")

    def test_original_code_hash_tampering_blocks_audit(self):
        p = self.root / self.runs["r-main"][0]["artifact_refs"]["code"]
        p.write_text("X_train = frame[['future_label']]\n", encoding="utf-8")
        out = self.science()
        self.assertEqual(out["status"], "AUDIT_PREREQUISITE_UNVERIFIED")
        self.assertEqual(out["run_evidence_status"], "RUN_LINK_HASH_MISMATCH")

    def test_unbound_lesson_is_not_promoted_from_chat_text(self):
        self.assertEqual(self.review()["status"], "LESSON_CONTEXT_UNBOUND")

    def test_evidenced_no_improvement_is_only_a_candidate(self):
        # Reproduce a zero-improvement DEV result from original predictions.
        self.rewrite_link("r-main", "predictions",
                          "sample_id,group_id,y_true,y_pred\ns1,g3,1,0\ns2,g4,3,2\n")
        run = self.runs["r-main"][0]
        run["metrics"]["MAE"] = 1.0
        self._rewrite("r-main")
        self.add_lesson()
        out = self.review()
        self.assertEqual(out["status"], "RUN_LINKED_NEGATIVE_METRIC_CANDIDATE", out)
        self.assertEqual(out["improvement_over_baseline"], 0.0)
        self.assertTrue(out["original_run_hash_bound"])
        self.assertFalse(out["automatic_stop"])
        self.assertFalse(out["scientific_equivalence_verified"])

    def test_real_improvement_cannot_be_declared_negative(self):
        self.add_lesson()
        out = self.review()
        self.assertEqual(out["status"], "NEGATIVE_METRIC_NOT_OBSERVED", out)
        self.assertFalse(out["negative_metric_observation"])

    def test_premise_scope_contradiction_prevents_reuse(self):
        self.rewrite_link("r-main", "predictions",
                          "sample_id,group_id,y_true,y_pred\ns1,g3,1,0\ns2,g4,3,2\n")
        run = self.runs["r-main"][0]
        run["metrics"]["MAE"] = 1.0
        self._rewrite("r-main")
        self.add_lesson()
        p = {"premise_id": "hypothesis-A",
             "scope": {**self.scope(), "group_split": "random"}}
        self.assertEqual(self.review(p)["status"],
                         "LESSON_PREMISE_SCOPE_NOT_MATCHED")

    def test_lesson_claim_unanchored_to_run_is_blocked(self):
        self.add_lesson(scope={**self.scope(), "dataset_version": "wrong"})
        self.assertEqual(self.review()["status"], "LESSON_RUN_SCOPE_NOT_ANCHORED")

    def test_illegal_static_code_risk_blocks_negative_lesson(self):
        self.add_lesson()
        self.rewrite_link("r-main", "code",
                          "X_train = table[['future_label']]\n")
        out = self.review()
        self.assertEqual(out["status"], "LESSON_SCIENCE_EVIDENCE_BLOCKED")
        self.assertIn("source_code_lineage",
                      out["scientific_review_or_conflict_checks"])

    def test_unhashed_context_never_validated(self):
        self.add_lesson()
        path = self.root / self.runs["r-main"][0]["artifact_refs"]["lesson_context"]
        path.write_text(path.read_text(encoding="utf-8")+" ", encoding="utf-8")
        out = self.review()
        self.assertEqual(out["status"], "LESSON_RUN_NOT_ATTESTABLE")
        self.assertEqual(out["run_evidence_status"], "RUN_LINK_HASH_MISMATCH")

    def test_invalid_threshold_rejected_without_scientific_inference(self):
        self.add_lesson(threshold=-1)
        self.assertEqual(self.review()["status"], "LESSON_THRESHOLD_INVALID")


if __name__ == "__main__":
    unittest.main()
