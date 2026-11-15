"""Integration, compatibility, source-verification, path-safety, token-cap,
applicability-counterexample and real-MCP tests for CASE_LIBRARY reuse.

These tests measure TOOL BEHAVIOUR on local fixtures only. They are NOT a
measurement of scientific research benefit; see evals/case_learning_ablation.py.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pdrw_agent import case_learning
from pdrw_agent.config import Settings
from pdrw_agent.service import ResearchService

ROOT = Path(__file__).resolve().parents[1]
REAL_LIBRARY = Path(os.environ.get("PDRW_CASE_LIBRARY_ROOT", "D:/workbuddy-work/CASE_LIBRARY"))
HAS_RETRIEVER = (REAL_LIBRARY / "scripts" / "search_cases.py").is_file()


def _case(cid: str, verdict: str = "FAILURE", levels=None, mechanisms=None,
          boundaries=None, counterexamples=None, status="", origin="EXTERNAL",
          role="PRIMARY_EMPIRICAL") -> dict:
    mechanisms = mechanisms or ["DATA_LEAKAGE"]
    boundaries = boundaries or ["结论限于所测数据集，不得外推"]
    counterexamples = counterexamples or ["若分组独立且无泄漏，本案例前提不成立"]
    text = " ".join(["数据泄漏 分组 标签 基线 评价单位 合法输入",
                     " ".join(mechanisms), " ".join(boundaries),
                     " ".join(counterexamples)])
    return {
        "case_id": cid, "title": f"测试案例 {cid}", "verdict": verdict,
        "origin": origin,
        "evidence_class": "VERIFIED_FAILURE" if verdict == "FAILURE" else "VERIFIED_SUCCESS",
        "mechanisms": mechanisms,
        "research_domains": ["HAR_WEARABLE"],
        "premises": ["随机 k-fold 使同一受试者窗口跨集合，性能虚高"],
        "applicability": {"conditions": ["滑窗分类、以窗口数作独立单位"],
                          "boundaries": boundaries},
        "counterexamples": counterexamples,
        "transferable_lesson": "先按独立单位分组，再成对报告随机与分组划分差值",
        "next_minimal_check": ["登记划分层级与窗口重叠率",
                               "随机 k-fold 与 subject-wise 成对报告"],
        "evidence_levels": levels or ["ORIGINAL_VERIFIED"],
        "source_refs": [f"TEST-REF-{cid}"] if origin == "EXTERNAL" else [f"internal/{cid}"],
        "source_paths": ["https://example.invalid/not-fetched"],
        "evidence_paths": [f"cases/external/{cid}.md"],
        "secondary_claims_not_admitted": [],
        "scope_warning": "", "status": status,
        "search_blob": text,
        "legacy_refs": {}, "related_cases": [], "success_notes": "",
        "_evidence_role": [role],
    }


class _Fixture:
    def __init__(self, base: Path, cases: list[dict], *, corrupt_index=False):
        self.root = base / "CASE_LIBRARY"
        (self.root / "cases" / "external").mkdir(parents=True)
        (self.root / "scripts").mkdir(parents=True)
        shutil.copyfile(REAL_LIBRARY / "scripts" / "search_cases.py",
                        self.root / "scripts" / "search_cases.py")
        (self.root / "taxonomy.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        for c in cases:
            path = self.root / "cases" / "external" / f"{c['case_id']}.md"
            meta = {k: v for k, v in c.items() if not k.startswith("_")}
            meta["evidence_role"] = c["_evidence_role"]
            path.write_text("---json\n" + json.dumps(meta, ensure_ascii=False, indent=1)
                            + "\n---\n\n# " + c["title"] + "\n", encoding="utf-8")
        index = {"schema_version": 1, "taxonomy_version": 1,
                 "source_of_truth": "cases/internal/*.md + cases/external/*.md",
                 "case_count": len(cases) if not corrupt_index else len(cases) + 1,
                 "cases": cases, "by_mechanism": {}, "by_domain": {},
                 "by_verdict": {}, "by_evidence_class": {}, "by_evidence_level": {}}
        (self.root / "index.json").write_text(
            json.dumps(index, ensure_ascii=False), encoding="utf-8")
        rules = base / "rules"
        rules.mkdir(exist_ok=True)
        (rules / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
        (rules / "WORKFLOW.md").write_text("# workflow\n", encoding="utf-8")
        (rules / "LESSONS").mkdir(exist_ok=True)
        (rules / "LESSONS" / "CASE_REGISTRY.md").write_text(
            "# Cases\n| CASE_ID | Lesson |\n| --- | --- |\n"
            "| P25 | HAR 平滑 gain 分组泄漏；核对置换对照 |\n", encoding="utf-8")
        cfg = base / "project-map.json"
        # A minimal registered project is required by the EXISTING science
        # audit path (find_experiment_evidence -> Settings.project). Registering
        # it does not touch any real project STATE/Run; the directory is empty.
        project_root = base / "project19"
        project_root.mkdir(exist_ok=True)
        cfg.write_text(json.dumps({
            "schema_version": 1,
            "case_library_root": str(self.root),
            "projects": {"19": {"root": str(project_root)}},
        }), encoding="utf-8")
        self.settings = Settings.load(str(cfg), str(rules))
        self.service = ResearchService(self.settings)


@unittest.skipUnless(HAS_RETRIEVER, "CASE_LIBRARY/scripts/search_cases.py not present")
class CaseLearningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        case_learning._RESULT_CACHE.clear()
        case_learning._RETRIEVER_CACHE.clear()
        self.base = Path(self.temp.name)
        cases = [
            _case("T-F1", "FAILURE", ["ORIGINAL_VERIFIED"],
                  ["GROUP_INDEPENDENCE", "DATA_LEAKAGE"]),
            _case("T-S1", "SUCCESS", ["PARTIAL_TEXT_VERIFIED"],
                  ["SENSOR_CALIBRATION"],
                  boundaries=["仅适用于可施加已知物理激励的电容式阵列"],
                  counterexamples=["光学视触觉在凝胶互换后完全无法迁移"],
                  role="THIRD_PARTY_REPLICATION"),
            _case("T-V1", "FAILURE", ["ORIGINAL_VERIFIED"], ["EXTERNAL_VALIDATION"],
                  boundaries=["本卡结论只适用于 Epic Sepsis Model v1；不得泛化到 v2 或后续版本"],
                  counterexamples=["v2 多中心前瞻验证 AUROC 0.82–0.92"]),
            _case("T-ABS", "FAILURE", ["ABSTRACT_VERIFIED"], ["LABEL_ERROR"]),
            _case("T-SEC", "FAILURE", ["SECONDARY_ONLY"], ["LABEL_ERROR"]),
            _case("T-INT", "FAILURE", ["INTERNAL_REPORT"], ["LABEL_ERROR"],
                  origin="INTERNAL", role="AUTHOR_REPORT"),
        ]
        self.fx = _Fixture(self.base, cases)
        self.env = patch.dict(os.environ, {"PDRW_CASE_LIBRARY_ROOT": str(self.fx.root)})
        self.env.start()
        self.addCleanup(self.env.stop)

    # -- 1. Compatibility --------------------------------------------------
    def test_legacy_call_shape_is_preserved(self):
        r = self.fx.service.call("search_research_memory", query="HAR 分组")
        for key in ("status", "query", "matches", "truncated", "limitations"):
            self.assertIn(key, r)
        self.assertEqual(r["status"], "MATCHES_FOUND")
        self.assertEqual(r["matches"][0]["source_file"], "LESSONS/CASE_REGISTRY.md")
        self.assertIn("NOT_RAW_RUN", r["matches"][0]["evidence_level"])
        self.assertIn("case_library", r)
        self.assertFalse(r["case_library"]["automatic_go_stop"])

    def test_legacy_only_optout_and_invalid_limit(self):
        r = self.fx.service.call("search_research_memory", query="HAR", include_cases=False)
        self.assertNotIn("case_library", r)
        for bad in (0, -1, True, "3"):
            with self.subTest(limit=bad):
                out = self.fx.service.call("search_research_memory", query="HAR", limit=bad)
                self.assertEqual(out["error_code"], "LIMIT_INVALID")

    def test_missing_case_library_degrades_without_breaking_legacy(self):
        with patch.dict(os.environ, {"PDRW_CASE_LIBRARY_ROOT": str(self.base / "nope")}):
            r = self.fx.service.call("search_research_memory", query="HAR")
        self.assertEqual(r["status"], "MATCHES_FOUND")
        self.assertEqual(r["case_library"]["status"], "CASE_LIBRARY_UNAVAILABLE")

    # -- 2. Source verification / role separation --------------------------
    def test_source_verification_grades_and_roles(self):
        r = self.fx.service.call("search_research_memory", query="分组 泄漏", limit=6)
        per = r["case_library"]["cases"]["source_verification"]["per_case"]
        self.assertEqual(per["T-F1"]["evidence_grade"], "DECISION_GRADE")
        self.assertTrue(per["T-F1"]["card_id_matches"])
        self.assertIn("ORIGINAL_EMPIRICAL", per["T-F1"]["role_classes"])
        self.assertIn("INDEPENDENT_REPLICATION", per["T-S1"]["role_classes"])
        self.assertTrue(any("ABSTRACT_VERIFIED_SOURCES_PRESENT" in c
                            for c in per["T-ABS"]["caveats"]))
        self.assertEqual(per["T-SEC"]["evidence_grade"], "NON_DECISION_GRADE")
        self.assertTrue(all(not p.startswith("http")
                            for c in per.values() for p in c["local_card_paths"]))
        # MAX_CASES caps the returned set at 5, so a 6th case is intentionally
        # not verified. Reach the internal-report card through an explicit
        # origin filter instead of assuming it survives the ranked truncation.
        internal = self.fx.service.call(
            "search_research_memory", query="分组 泄漏", origin="INTERNAL")
        per_int = internal["case_library"]["cases"]["source_verification"]["per_case"]
        self.assertIn("T-INT", per_int)
        self.assertEqual(per_int["T-INT"]["role_classes"], ["AUTHOR_REPORT"])
        self.assertEqual(per_int["T-INT"]["evidence_levels"], ["INTERNAL_REPORT"])
        self.assertTrue(all(not p.startswith("http")
                            for p in per_int["T-INT"]["local_card_paths"]))

    def test_corrupt_index_is_rejected(self):
        bad = _Fixture(self.base / "bad", [_case("B1")], corrupt_index=True)
        with patch.dict(os.environ, {"PDRW_CASE_LIBRARY_ROOT": str(bad.root)}):
            r = self.fx.service.call("search_research_memory", query="分组")
        self.assertEqual(r["case_library"]["error_code"], "CASE_INDEX_COUNT_MISMATCH")
        self.assertEqual(r["status"], "MATCHES_FOUND")

    def test_url_evidence_paths_are_never_fetched(self):
        r = self.fx.service.call("search_research_memory", query="分组", limit=3)
        for res in r["case_library"]["cases"]["results"]:
            for p in res["evidence_paths"]:
                self.assertFalse(p.startswith("http"))
        self.assertNotIn("requests", str(case_learning.__dict__.keys()))

    # -- 3. Path safety ----------------------------------------------------
    def test_protected_root_and_symlink_are_rejected(self):
        sealed = self.base / "sealed"
        sealed.mkdir()
        with patch.dict(os.environ, {"PDRW_CASE_LIBRARY_ROOT": str(sealed)}):
            r = self.fx.service.call("search_research_memory", query="分组")
        self.assertEqual(r["case_library"]["error_code"], "PROTECTED_PATH_REJECTED")
        (self.fx.root / "index.json").unlink()
        try:
            (self.fx.root / "index.json").symlink_to(self.base / "outside.json")
        except (OSError, NotImplementedError):
            # Windows without Developer Mode / elevated privilege denies
            # symlink creation. The non-symlink half of this test above still
            # ran; path traversal and protected-root checks are covered by
            # test_card_path_traversal_is_ignored. No product defect implied.
            self.skipTest("SKIP: host OS denies symlink creation (Windows "
                          "requires Developer Mode or elevated privilege); "
                          "symlink branch is environment-dependent only")
        r = self.fx.service.call("search_research_memory", query="分组")
        self.assertIn(r["case_library"]["error_code"],
                      {"CASE_INDEX_MISSING", "CASE_LIBRARY_UNAVAILABLE",
                       "PATH_OUTSIDE_LIBRARY"})

    def test_card_path_traversal_is_ignored(self):
        self.assertIsNone(case_learning._card_path(self.fx.root, "../escape.md"))
        self.assertIsNone(case_learning._card_path(self.fx.root, "C:/absolute.md"))
        self.assertIsNone(case_learning._card_path(self.fx.root, "https://example.invalid/x"))
        self.assertIsNone(case_learning._card_path(self.fx.root, "sealed/secret.md"))
        self.assertIsNotNone(case_learning._card_path(self.fx.root, "cases/external/T-F1.md"))

    # -- 4. Applicability counterexample / divergence ---------------------
    def test_v1_v2_explicit_exclusion_is_conditions_differ(self):
        profile = {"decision": "评估 Epic Sepsis Model v2 在本院表现",
                   "mechanisms": "EXTERNAL_VALIDATION",
                   "legal_inputs": "院内 EHR 预测时刻可得",
                   "labels": "复合脓毒症标签", "grouping": "独立住院次",
                   "evaluation_unit": "encounter AUROC", "baseline": "厂商报告 AUC",
                   "boundaries": "v2 多中心前瞻", "counterexamples": "v1 不得泛化到 v2"}
        r = self.fx.service.call("review_case_transfer", task_profile=profile,
                                 filters={"mechanism": "EXTERNAL_VALIDATION"},
                                 query="ESM v1 v2")
        found = [c for c in r["case_review"]["comparisons"] if c["case_id"] == "T-V1"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["classification"], "CONDITIONS_DIFFER")
        self.assertIn("DECLARED_VERSION_EXPLICITLY_EXCLUDED:v2",
                      found[0]["explicit_scope_conflicts"])
        self.assertFalse(r["automatic_go_stop"])
        self.assertFalse(r["case_review"]["scientific_equivalence_verified"])

    def test_counterexample_does_not_fabricate_a_conflict(self):
        """A 'premise does not hold IF X' counterexample is not a contradiction
        of a task that does not assert X."""
        profile = {"decision": "随机 k-fold 滑窗分类", "mechanisms": "GROUP_INDEPENDENCE",
                   "grouping": "随机 k-fold 窗口级", "labels": "受试者活动标注",
                   "legal_inputs": "预测时刻可得", "evaluation_unit": "窗口级 accuracy",
                   "baseline": "未配对简单基线"}
        r = self.fx.service.call("review_case_transfer", task_profile=profile,
                                 filters={"mechanism": "GROUP_INDEPENDENCE"}, limit=3)
        self.assertGreaterEqual(len(r["case_review"]["comparisons"]), 1)
        for c in r["case_review"]["comparisons"]:
            self.assertEqual(c["explicit_scope_conflicts"], [])
            self.assertNotEqual(c["classification"], "CONDITIONS_DIFFER")
        self.assertIn("applicability_divergence", r["case_review"])
        self.assertIn("dimension_list", r["case_review"])
        self.assertEqual(len(r["case_review"]["dimension_list"]), 8)

    # -- 5. Negative warnings + success transfer --------------------------
    def test_both_polarities_and_no_duplicates(self):
        r = self.fx.service.call("search_research_memory", query="分组 泄漏 标定", limit=6)
        d = r["case_library"]["decision_experiences"]
        ids = [e["case_id"] for e in d["experiences"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertLessEqual(len(ids), 5)
        self.assertGreaterEqual(d["negative_warning_count"], 1)
        self.assertGreaterEqual(d["success_transfer_count"], 1)
        for e in d["experiences"]:
            self.assertIn("应执行", e["concrete_impact"])
            self.assertTrue(e["verification_required"])
            self.assertTrue(e["not_a_scientific_conclusion"])
        for c in d["candidates_only_not_admitted"]:
            self.assertIn(c["retained_as"], {"CANDIDATE_ONLY_NOT_DECISION_INPUT",
                                             "CONTEXT_ONLY_NOT_ORIGINAL_EMPIRICAL_RESULT"})

    # -- 6. Token cap / dedup ---------------------------------------------
    def test_token_cap_bounds_whole_payload(self):
        r = self.fx.service.call("search_research_memory", query="分组 泄漏 标签",
                                 limit=5, task_profile={"mechanisms": "DATA_LEAKAGE",
                                                        "grouping": "随机 k-fold"})
        payload = r["case_library"]
        self.assertLessEqual(len(json.dumps(payload, ensure_ascii=False)),
                             case_learning.MAX_TOTAL_CHARS + 400)
        self.assertLessEqual(payload["cases"]["returned"], 5)

    def test_truncated_payload_retains_one_coherent_case_set(self):
        """A tight cap must never leave experiences/review/source checks that
        cite a case whose details were dropped from cases.results."""
        profile = {
            "decision": "滑窗分类", "mechanisms": "分组独立性不足",
            "legal_inputs": "预测时刻可得", "labels": "活动标注",
            "grouping": "随机 k-fold 窗口级", "evaluation_unit": "窗口级 accuracy",
            "baseline": "简单基线", "boundaries": "本数据集",
            "counterexamples": "按受试者分组则不成立",
        }
        r = self.fx.service.call(
            "search_research_memory", query="分组 泄漏 标签", limit=5,
            task_profile=profile)
        raw = r["case_library"]
        self.assertEqual(raw["cases"]["returned"], 5)  # query is not discarded
        capped = case_learning._cap_total(copy.deepcopy(raw), cap=10000)
        ids = set(capped["retained_case_ids"])
        self.assertTrue(ids)
        self.assertTrue(capped["output_truncated"])
        self.assertLess(len(ids), 5)
        self.assertLessEqual(len(json.dumps(capped, ensure_ascii=False)), 10000)
        self.assertEqual(ids, {x["case_id"] for x in capped["cases"]["results"]})
        self.assertEqual(capped["cases"]["returned"], len(ids))
        self.assertTrue(set(capped["cases"]["source_verification"]["per_case"]) <= ids)
        comps = capped["case_review"]["comparisons"]
        exps = capped["decision_experiences"]["experiences"]
        self.assertTrue(all(c["case_id"] in ids for c in comps))
        self.assertTrue(all(e["case_id"] in ids for e in exps))
        self.assertEqual(capped["case_review"]["reviewed"], len(comps))
        self.assertEqual(capped["decision_experiences"]["returned"], len(exps))
        self.assertEqual(capped["decision_experiences"]["negative_warning_count"],
                         sum(1 for e in exps if e["polarity"] == "NEGATIVE_WARNING"))
        counts = {}
        for c in comps:
            counts[c["classification"]] = counts.get(c["classification"], 0) + 1
        self.assertEqual(capped["case_review"]["classification_counts"], counts)

    def test_identical_query_is_deduplicated_by_fingerprint(self):
        a = self.fx.service.call("review_case_transfer",
                                 task_profile={"mechanisms": "DATA_LEAKAGE",
                                               "grouping": "随机 k-fold"},
                                 query="分组泄漏")
        b = self.fx.service.call("review_case_transfer",
                                 task_profile={"mechanisms": "DATA_LEAKAGE",
                                               "grouping": "随机 k-fold"},
                                 query="分组泄漏")
        self.assertFalse(a["cache_hit"])
        self.assertTrue(b["cache_hit"])
        self.assertEqual(a["query_fingerprint"], b["query_fingerprint"])
        c = self.fx.service.call("review_case_transfer",
                                 task_profile={"mechanisms": "LABEL_ERROR",
                                               "grouping": "随机 k-fold"},
                                 query="分组泄漏")
        self.assertNotEqual(a["query_fingerprint"], c["query_fingerprint"])

    # -- 7. Candidate extraction: no writes, no promotion -----------------
    def test_candidate_extraction_never_promotes_or_writes(self):
        before = sorted(p.read_bytes() for p in (self.fx.root / "cases").rglob("*.md"))
        obs = [{"run_id": "run-001", "outcome": "VALID_NEGATIVE",
                "evidence_refs": ["runs/run-001.json"],
                "tested_premise_id": "grouping-independence",
                "scope": {"split": "random-kfold"}},
               {"run_id": "run-002", "outcome": "ENGINEERING_FAILURE",
                "evidence_refs": ["runs/run-002.json"]}]
        r = self.fx.service.call("extract_case_candidates",
                                 project_id="19", observations=obs)
        self.assertEqual(r["status"], "CANDIDATE_EXPERIENCES_ONLY")
        self.assertTrue(r["no_writes"])
        self.assertFalse(r["case_library_modified"])
        self.assertTrue(all(not c["promoted_to_formal_case"] and
                            not c["science_record_written"] and
                            not c["state_or_run_modified"] and
                            c["verification"] == "NOT_INDEPENDENTLY_VERIFIED"
                            for c in r["candidates"]))
        self.assertEqual(len(r["candidates"]), 2)
        after = sorted(p.read_bytes() for p in (self.fx.root / "cases").rglob("*.md"))
        self.assertEqual(before, after)

    # -- 8. Real MCP wire-level call --------------------------------------
    @unittest.skipUnless(importlib.util.find_spec("mcp") is not None,
                         "Install optional MCP SDK for wire-level tests")
    def test_real_mcp_wire_call_returns_case_library(self):
        import asyncio
        from mcp import Client
        from pdrw_agent.integrations.mcp_server import create_server

        async def exercise():
            server = create_server(self.fx.settings)
            async with Client(server) as client:
                tools = {t.name for t in (await client.list_tools()).tools}
                self.assertIn("review_case_transfer", tools)
                self.assertIn("extract_case_candidates", tools)
                legacy = await client.call_tool("search_research_memory",
                                                {"query": "HAR 分组"})
                text = str(legacy.structured_content or legacy.content)
                self.assertIn("REPOSITORY_CASE_INDEX_NOT_RAW_RUN", text)
                review = await client.call_tool("review_case_transfer", {
                    "task_profile": {"decision": "评估 ESM v2",
                                     "mechanisms": "EXTERNAL_VALIDATION",
                                     "boundaries": "v2 前瞻",
                                     "counterexamples": "v1 不得泛化到 v2"},
                    "mechanism": "EXTERNAL_VALIDATION", "query": "ESM v1 v2"})
                self.assertFalse(review.is_error)
                review_text = str(review.structured_content or review.content)
                self.assertIn("CONDITIONS_DIFFER", review_text)
                self.assertIn("automatic_go_stop", review_text)
                cand = await client.call_tool("extract_case_candidates", {
                    "project_id": "19",
                    "observations": [{"run_id": "r1", "outcome": "VALID_NEGATIVE",
                                      "evidence_refs": ["runs/r1.json"],
                                      "tested_premise_id": "p1",
                                      "scope": {"split": "kfold"}}]})
                self.assertFalse(cand.is_error)
                self.assertIn("CANDIDATE_EXPERIENCES_ONLY",
                              str(cand.structured_content or cand.content))

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
