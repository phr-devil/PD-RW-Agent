"""Linked feedback tests: declaration + real Run + case candidates.

These are engineering contract tests on synthetic fixtures. They do NOT
measure scientific benefit; see docs/EXPERIMENT_FEEDBACK_LINK.md.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from pdrw_agent.schemas import AgentError
from pdrw_agent.science import feedback_link
from pdrw_agent.science.feedback import proposal_sha256

REAL_LIBRARY = Path(os.environ.get("PDRW_CASE_LIBRARY_ROOT", "D:/workbuddy-work/CASE_LIBRARY"))
HAS_RETRIEVER = (REAL_LIBRARY / "scripts" / "search_cases.py").is_file()


def _proposal():
    return {
        "question": "Does the raw signal beat a matched simple baseline under held-out subjects?",
        "claim_type": "MECHANISM",
        "hypotheses": ["real-gain", "leakage-explains-gain"],
        "proposed_premise": {
            "premise_id": "subject-independent-gain",
            "scope": {"dataset": "synthetic-dev", "group_unit": "subject"},
        },
        "probes": [{
            "id": "heldout-probe",
            "observable": "balanced-accuracy-delta",
            "evaluation_unit": "held-out-subject",
            "comparison_reference": "matched-simple-baseline",
            "predictions": {"real-gain": "INCREASE", "leakage-explains-gain": "NO_CHANGE"},
            "prediction_evidence_refs": ["frozen-protocol"],
            "cost_band": "LOW",
        }],
    }


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class _Project:
    """Minimal research project: one frozen proposal, one Run, one evidence file."""

    def __init__(self, base: Path):
        self.root = base / "project"
        (self.root / "protocol").mkdir(parents=True)
        run = self.root / "DEV" / "runs" / "RUN-001"
        run.mkdir(parents=True)
        proposal = _proposal()
        self.proposal_path = self.root / "protocol" / "PRIOR-PROPOSAL.json"
        self.proposal_path.write_text(json.dumps(proposal, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
        self.prereg_path = self.root / "protocol" / "PRIOR-DECLARATION.json"
        self.prereg_path.write_text(json.dumps({
            "declaration_id": "PRIOR-001",
            "frozen_at": "2026-01-01T09:00:00+00:00",
            "scientific_hypotheses": {"real-gain": "declared", "leakage-explains-gain": "declared"},
            "frozen_decision_rules": {"POS": "delta > 0", "NEG": "delta <= 0"},
            "proposal_ref": "protocol/PRIOR-PROPOSAL.json",
            "proposal_sha256": proposal_sha256(proposal),
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        self.metrics = run / "metrics.json"
        self.metrics.write_text(json.dumps({"delta": 0.031, "n_folds": 12}), encoding="utf-8")
        self.record_path = run / "run_record.json"
        self.record_path.write_text(json.dumps({
            "run_id": "RUN-001", "status": "VALID", "protocol_id": "PRIOR-001",
            "metrics": {"delta": 0.031}, "sample_ids_hash": "0" * 64,
            "artifact_refs": {"metrics": "DEV/runs/RUN-001/metrics.json"},
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    def observation(self, **overrides):
        data = {
            "run_ref": "DEV/runs/RUN-001",
            "probe_id": "heldout-probe",
            "prior_proposal_sha256": proposal_sha256(_proposal()),
            "observable": "balanced-accuracy-delta",
            "evaluation_unit": "held-out-subject",
            "comparison_reference": "matched-simple-baseline",
            "validity": "VALID",
            "outcome": "INCREASE",
            "evidence_refs": ["DEV/runs/RUN-001/metrics.json"],
        }
        data.update(overrides)
        return data

    def link(self, **overrides):
        data = {
            "schema_version": feedback_link.LINK_SCHEMA,
            "project_id": "T1",
            "prereg": {
                "ref": "protocol/PRIOR-DECLARATION.json",
                "sha256": _sha(self.prereg_path),
                "declared_at": "2026-01-01T09:00:00+00:00",
                "proposal_ref": "protocol/PRIOR-PROPOSAL.json",
            },
            "run": {
                "ref": "DEV/runs/RUN-001",
                "run_record_ref": "DEV/runs/RUN-001/run_record.json",
                "started_at": "2026-01-02T09:00:00+00:00",
                "observation": self.observation(),
            },
        }
        data.update(overrides)
        return data


class LinkedFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = _Project(Path(self.temp.name))

    def review(self, link=None, **kwargs):
        return feedback_link.review_linked_feedback(
            link or self.project.link(), project_root=self.project.root, **kwargs)

    # -- valid outcomes -----------------------------------------------------
    def test_positive_result_is_advisory_and_keeps_limits(self):
        result = self.review()
        self.assertEqual(result["status"], "ADVISORY_FEEDBACK_ONLY")
        self.assertEqual(result["order_check"], "DECLARED_BEFORE_RUN")
        self.assertTrue(result["prediction_verification_performed"])
        self.assertEqual(result["feedback"]["declared_prediction_review"],
                         "DECLARED_PREDICTION_CONTRAST")
        self.assertEqual(result["feedback"]["compatible_predictions"], ["real-gain"])
        self.assertEqual(result["feedback"]["contradicted_predictions"], ["leakage-explains-gain"])
        self.assertFalse(result["automatic_go"])
        self.assertFalse(result["automatic_stop"])
        self.assertFalse(result["permission_to_execute"])
        self.assertFalse(result["scientific_inference_verified"])

    def test_negative_result_challenges_only_the_tested_premise(self):
        link = self.project.link()
        link["run"]["observation"] = self.project.observation(outcome="NO_CHANGE")
        result = self.review(link)
        self.assertEqual(result["status"], "ADVISORY_FEEDBACK_ONLY")
        self.assertEqual(result["feedback"]["contradicted_predictions"], ["real-gain"])
        self.assertFalse(result["automatic_stop"])
        self.assertEqual(result["feedback"]["next_science_action"],
                         "VERIFY_ORIGINAL_RUN_AND_RECONSIDER_COMPETING_EXPLANATIONS")

    def test_invalid_and_not_run_are_not_scientific_failures(self):
        for status, validity in (("INVALID", "INVALID"), ("NOT_RUN", "NOT_RUN")):
            self.project.record_path.write_text(json.dumps(
                {"run_id": "RUN-001", "status": status}), encoding="utf-8")
            link = self.project.link(prereg={
                **self.project.link()["prereg"],
                "sha256": _sha(self.project.prereg_path),
            })
            observation = self.project.observation(validity=validity, outcome="UNKNOWN")
            link["run"]["observation"] = observation
            result = self.review(link)
            self.assertEqual(result["status"], "ADVISORY_FEEDBACK_ONLY")
            self.assertEqual(result["feedback"]["declared_prediction_review"],
                             "NO_VALID_SCIENTIFIC_INFERENCE")
            self.assertEqual(result["feedback"]["compatible_predictions"], [])
            self.assertEqual(result["feedback"]["contradicted_predictions"], [])
            self.assertEqual(result["feedback"]["next_science_action"],
                             "REPAIR_OR_REASSESS_EVIDENCE_BEFORE_SCIENTIFIC_UPDATE")

    def test_changed_evaluation_unit_is_not_a_failed_hypothesis(self):
        link = self.project.link()
        link["run"]["observation"] = self.project.observation(evaluation_unit="per-frame")
        result = self.review(link)
        self.assertEqual(result["status"], "NOT_COMPARABLE")
        self.assertEqual(result["reason"], "MEASUREMENT_AXIS_CHANGED_SINCE_PREREG")
        self.assertIsNone(result["feedback"])
        self.assertFalse(result["prediction_verification_performed"])

    # -- unverified pre-result records --------------------------------------
    def test_missing_prereg_preserves_observation_without_verification(self):
        link = self.project.link()
        link["prereg"] = {"ref": "protocol/PRIOR-DECLARATION.json",
                          "sha256": _sha(self.project.prereg_path)}
        result = self.review(link)
        self.assertEqual(result["status"], "PRE_RESULT_RECORD_UNVERIFIED")
        self.assertEqual(result["reason"], "PREREG_WITHOUT_FEEDBACK_PROPOSAL")
        self.assertEqual(result["observation_preserved"]["declared_outcome"], "INCREASE")
        self.assertFalse(result["prediction_verification_performed"])

    def test_declaration_after_run_is_not_a_prior_prediction(self):
        link = self.project.link()
        link["prereg"]["declared_at"] = "2026-01-03T09:00:00+00:00"
        result = self.review(link)
        self.assertEqual(result["status"], "PRE_RESULT_RECORD_UNVERIFIED")
        self.assertEqual(result["reason"], "PREREG_DECLARED_AFTER_RUN")
        self.assertEqual(result["order_check"], "DECLARED_AFTER_RUN")
        self.assertIsNone(result["feedback"])

    def test_hash_mismatch_blocks_binding(self):
        link = self.project.link()
        link["prereg"]["sha256"] = "0" * 64
        result = self.review(link)
        self.assertEqual(result["status"], "PRE_RESULT_RECORD_UNVERIFIED")
        self.assertEqual(result["reason"], "PREREG_HASH_MISMATCH")

    def test_missing_evidence_file_blocks_binding(self):
        link = self.project.link()
        link["run"]["observation"] = self.project.observation(
            evidence_refs=["DEV/runs/RUN-001/absent.json"])
        result = self.review(link)
        self.assertEqual(result["status"], "RUN_EVIDENCE_UNVERIFIED")
        self.assertEqual(result["reason"], "EVIDENCE_REF_MISSING_OR_HASH_CHANGED")
        self.assertEqual(result["run"]["evidence_problems"][0]["problem"], "MISSING")

    def test_changed_evidence_hash_is_reported(self):
        link = self.project.link()
        link["run"]["observation"] = self.project.observation(
            evidence_sha256={"DEV/runs/RUN-001/metrics.json": "0" * 64})
        result = self.review(link)
        self.assertEqual(result["status"], "RUN_EVIDENCE_UNVERIFIED")
        self.assertEqual(result["run"]["evidence_problems"][0]["problem"], "HASH_CHANGED")

    def test_declared_validity_conflicting_with_run_record(self):
        link = self.project.link()
        link["run"]["observation"] = self.project.observation(validity="INVALID", outcome="UNKNOWN")
        result = self.review(link)
        self.assertEqual(result["status"], "RUN_STATUS_CONFLICT")
        self.assertEqual(result["reason"], "RUN_RECORD_VALID_VS_OBSERVATION_INVALID")

    def test_sealed_paths_are_refused(self):
        sealed = self.project.root / "SEALED" / "run.json"
        sealed.parent.mkdir()
        sealed.write_text("{}", encoding="utf-8")
        for mutate in ("prereg", "run"):
            link = self.project.link()
            if mutate == "prereg":
                link["prereg"]["ref"] = "SEALED/run.json"
            else:
                link["run"]["ref"] = "SEALED"
            with self.assertRaises(AgentError) as ctx:
                self.review(link)
            self.assertEqual(ctx.exception.code, "FEEDBACK_LINK_PATH_REJECTED")

    def test_path_outside_project_is_refused(self):
        link = self.project.link()
        link["prereg"]["ref"] = "../outside.json"
        with self.assertRaises(AgentError) as ctx:
            self.review(link)
        self.assertEqual(ctx.exception.code, "FEEDBACK_LINK_PATH_REJECTED")

    def test_schema_and_project_root_are_required(self):
        with self.assertRaises(AgentError):
            feedback_link.review_linked_feedback({"schema_version": "other"},
                                                 project_root=self.project.root)
        with self.assertRaises(AgentError):
            feedback_link.review_linked_feedback(self.project.link(), project_root=None)


@unittest.skipUnless(HAS_RETRIEVER, "CASE_LIBRARY/scripts/search_cases.py not present")
class LinkedCaseContextTests(unittest.TestCase):
    """A case match explains a candidate; it never certifies the current Run."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.project = _Project(self.base)
        self.library = self.base / "CASE_LIBRARY"
        (self.library / "cases" / "external").mkdir(parents=True)
        (self.library / "scripts").mkdir(parents=True)
        shutil.copyfile(REAL_LIBRARY / "scripts" / "search_cases.py",
                        self.library / "scripts" / "search_cases.py")
        (self.library / "taxonomy.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        cases = [
            self._card("T-S1", "SUCCESS", ["ORIGINAL_VERIFIED"], "EXTERNAL",
                       "cases/external/T-S1.md", "10.1000/shared"),
            self._card("T-S1B", "SUCCESS", ["ORIGINAL_VERIFIED"], "EXTERNAL",
                       "cases/external/T-S1B.md", "10.1000/shared"),
            self._card("T-R1", "FAILURE", ["ORIGINAL_VERIFIED"], "INTERNAL",
                       "cases/internal/T-R1.md", "internal/T-R1"),
        ]
        (self.library / "index.json").write_text(json.dumps({
            "schema_version": 1, "taxonomy_version": 1, "case_count": 3,
            "source_of_truth": "cases/internal/*.md + cases/external/*.md",
            "cases": cases, "by_mechanism": {}, "by_domain": {},
            "by_verdict": {}, "by_evidence_class": {}, "by_evidence_level": {},
        }, ensure_ascii=False), encoding="utf-8")

    def _card(self, cid, verdict, levels, origin, rel, ref):
        meta = {
            "case_id": cid, "title": f"夹具 {cid}", "verdict": verdict, "origin": origin,
            "evidence_class": "VERIFIED_SUCCESS" if verdict == "SUCCESS" else "VERIFIED_FAILURE",
            "mechanisms": ["GROUP_INDEPENDENCE"],
            "research_domains": ["WEARABLE_SENSING"],
            "premises": ["分组独立且评价单位是受试者"],
            "applicability": {"conditions": ["受试者独立划分"],
                              "boundaries": ["结论限于所测数据集"]},
            "counterexamples": ["若分组泄漏则增益消失"],
            "transferable_lesson": "先按受试者分组再比较",
            "next_minimal_check": ["成对报告随机划分与受试者划分差值"],
            "evidence_levels": levels, "source_refs": [ref],
            "source_paths": ["https://example.invalid/x"],
            "evidence_paths": [rel],
            "secondary_claims_not_admitted": [], "scope_warning": "", "status": "ACTIVE",
            "evidence_role": ["PRIMARY_EMPIRICAL"],
            "search_blob": "受试者 分组 泄漏 平衡准确率 增益 评价单位 基线 可穿戴传感",
        }
        path = self.library / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("---json\n" + json.dumps(meta, ensure_ascii=False)
                        + "\n---\n\n# " + meta["title"] + "\n", encoding="utf-8")
        return meta

    def test_cases_stay_candidates_and_same_source_is_not_double_counted(self):
        result = self.review_with_cases()
        cases = result["case_context"]
        self.assertEqual(cases["status"], "MATCHES_FOUND")
        self.assertEqual(cases["cases_in_index"], 3)
        self.assertTrue(cases["cases_do_not_certify_current_run"])
        self.assertEqual(cases["independent_units"], 2)
        same = [e["same_source_with"] for e in cases["experiences"]
                if e["case_id"] in {"T-S1", "T-S1B"}]
        self.assertTrue(all(same), same)
        for item in cases["experiences"]:
            self.assertEqual(item["independent_confirmation"],
                             "SOURCE_VERIFIED_NOT_SCIENTIFIC_PROOF")
        self.assertFalse(result["feedback"]["automatic_go"])

    def test_mirror_scope_is_reported_when_supplied(self):
        manifest = self.base / "manifest.json"
        manifest.write_text(json.dumps({
            "mirror_version": "1.1", "content_sha256": "a" * 64,
            "publish_state": "READY_FOR_CONFIRMED_PUBLICATION",
            "scope": {"mode": "SUBSET", "included": 5, "library_total": 65},
        }), encoding="utf-8")
        result = self.review_with_cases(mirror_manifest=manifest)
        self.assertEqual(result["case_context"]["mirror"]["manifest_scope_cases"], 5)
        self.assertEqual(result["case_context"]["mirror"]["library_total"], 65)
        self.assertIn("publication_note", result["case_context"]["mirror"])

    def review_with_cases(self, **kwargs):
        link = self.project.link()
        link["cases"] = {"query": "受试者分组 泄漏 平衡准确率", "limit": 3}
        return feedback_link.review_linked_feedback(
            link, project_root=self.project.root, case_root=self.library, **kwargs)


class NoNewToolSurfaceTests(unittest.TestCase):
    def test_feedback_link_is_not_registered_as_mcp_tool(self):
        from pdrw_agent.integrations import mcp_server
        names = set(mcp_server.PROFILE_TOOLS["diagnostic"])
        self.assertEqual(len(names), 24)
        self.assertFalse(any("feedback" in name for name in names))


class RunRecordBoundTests(unittest.TestCase):
    """The bounded read must be larger than the records it exists to read.

    Measured on project 44: `DEV/runs/RUN-002/metrics.json` is 411 202 bytes of
    fold-level metrics. At the old 128 KiB cap the binder answered
    RUN_RECORD_TOO_LARGE, so a Run that really ran could not be attributed and
    fell into `unverified_closure_ids`.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "DEV" / "runs" / "RUN-BIG"
        self.run.mkdir(parents=True)

    def _write(self, run_id, size):
        record = {"run_id": run_id, "status": "COMPLETED", "anchor_pass": True,
                  "folds": [{"fold": i, "mae": 0.1 + i / 1000} for i in range(size // 40)]}
        path = self.run.parent / run_id / "metrics.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record), encoding="utf-8")
        return path

    def test_a_fold_level_record_larger_than_the_old_cap_is_still_bound(self):
        path = self._write("RUN-BIG", 400_000)
        self.assertGreater(path.stat().st_size, 128 * 1024)
        result = feedback_link.bind_run_reference(self.root, "DEV/runs/RUN-BIG")
        self.assertEqual("RUN_RECORD_BOUND", result["status"])
        self.assertEqual("RUN-BIG", result["run_id_declared"])

    def test_an_oversized_dump_is_still_refused(self):
        path = self._write("RUN-BIG", 5_000_000)
        self.assertGreater(path.stat().st_size, feedback_link.MAX_RUN_RECORD_BYTES)
        result = feedback_link.bind_run_reference(self.root, "DEV/runs/RUN-BIG")
        self.assertEqual("RUN_RECORD_TOO_LARGE", result["status"])


class ReservedRootTests(unittest.TestCase):
    """PD-RW reserves VAL / HOLDOUT / SEALED. Two of the three were refused.

    On project 44 `VAL/README.md` was read and offered to the JSON parser while
    `SEALED/` was rejected. Reading a reserved split for attribution is the one
    operation that cannot be undone, so it is refused by path, not by advice.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for rel in ("VAL/README.md", "SEALED/lock.md", "data/val/README.md",
                    "DEV/runs/RUN-1/metrics.json"):
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"run_id": "RUN-1", "status": "COMPLETED"}),
                            encoding="utf-8")

    def test_a_reserved_root_is_refused_whatever_it_contains(self):
        for ref in ("VAL/README.md", "SEALED/lock.md"):
            result = feedback_link.bind_run_reference(self.root, ref)
            self.assertEqual("RUN_REF_REJECTED", result["status"])
            self.assertEqual("FEEDBACK_LINK_PATH_REJECTED", result["reason"])
            self.assertIsNone(result.get("record_ref"))

    def test_a_val_named_split_inside_dev_is_not_a_reserved_root(self):
        # A directory called `val` under a working tree is not the reserved set;
        # only the root segment is. Refusing it would be a false positive.
        result = feedback_link.bind_run_reference(self.root, "data/val/README.md")
        self.assertEqual("RUN_RECORD_BOUND", result["status"])


if __name__ == "__main__":
    unittest.main()
