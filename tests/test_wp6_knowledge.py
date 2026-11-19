"""WP6-A tests: case-knowledge mirror (schema, indexes, incremental, gates).

These are TOOL-BEHAVIOUR tests on a synthetic library plus one read-only
integration pass over the real CASE_LIBRARY. They prove the export is
deterministic, incremental, non-destructive and gated. They are NOT evidence
that the retrieval advice is scientifically better.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_case_learning import HAS_RETRIEVER, REAL_LIBRARY, _Fixture  # noqa: E402

from pdrw_agent import case_export, case_knowledge, case_learning  # noqa: E402

CARD_FILES = "cases"


def _kcase(cid: str, *, verdict="FAILURE", status="", origin="EXTERNAL",
           refs=None, evidence=None, conditions=None, boundaries=None,
           mechanics=None) -> dict:
    mechanics = mechanics or ["DATA_LEAKAGE"]
    refs = refs if refs is not None else [f"arXiv:2101.0000{int(cid[-1]) if cid[-1].isdigit() else 1}"]
    evidence = evidence if evidence is not None else [{
        "source": f"Test source for {cid}", "level": "ORIGINAL_VERIFIED",
        "claim": f"{cid} 的受控实验显示：在随机划分下指标虚高 3–9 个百分点。",
    }]
    text = " ".join(["数据 分组 标签 基线 评价单位 合法输入 受试者 滑窗",
                     " ".join(mechanics)])
    return {
        "case_id": cid, "title": f"测试案例 {cid}", "verdict": verdict,
        "origin": origin,
        "evidence_class": ("VERIFIED_FAILURE" if verdict == "FAILURE"
                           else "VERIFIED_SUCCESS"),
        "mechanisms": mechanics, "research_domains": ["HAR_WEARABLE"],
        "premises": ["随机 k-fold 使同一受试者窗口跨集合，性能虚高"],
        "applicability": {"conditions": conditions or ["滑窗分类、以窗口数作独立单位"],
                          "boundaries": boundaries or ["结论限于所测数据集"]},
        "counterexamples": ["若分组独立且无泄漏，本案例前提不成立"],
        "transferable_lesson": "先按独立单位分组再比较",
        "next_minimal_check": ["登记划分层级"],
        "evidence_levels": ["ORIGINAL_VERIFIED"], "source_refs": refs,
        "source_paths": [], "evidence_paths": [f"cases/external/{cid}.md"],
        "secondary_claims_not_admitted": [], "scope_warning": "", "status": status,
        "search_blob": text, "legacy_refs": {}, "related_cases": [],
        "success_notes": "", "evidence": evidence,
        "_evidence_role": ["PRIMARY_EMPIRICAL"],
    }


class _KnowledgeFixture:
    def __init__(self, base: Path, cases: list[dict]):
        self.base = base
        self.fx = _Fixture(base, cases)
        self.cases = cases
        self.out = base / "mirror"

    def settings(self):
        return self.fx.settings

    def rebuild_index(self, cases: list[dict]) -> None:
        index_path = self.fx.root / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["cases"] = cases
        index["case_count"] = len(cases)
        index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        for case in cases:
            path = self.fx.root / "cases" / "external" / f"{case['case_id']}.md"
            if not path.is_file():
                meta = {k: v for k, v in case.items() if not k.startswith("_")}
                meta["evidence_role"] = case["_evidence_role"]
                path.write_text("---json\n" + json.dumps(meta, ensure_ascii=False, indent=1)
                                + "\n---\n\n# " + case["title"] + "\n", encoding="utf-8")

    def build(self, **kwargs):
        return case_knowledge.build(self.settings(), self.out, **kwargs)


def _read_all(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)).replace("\\", "/"): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


@unittest.skipUnless(HAS_RETRIEVER, "CASE_LIBRARY/scripts/search_cases.py not present")
class KnowledgeMirrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        case_learning._RESULT_CACHE.clear()
        case_learning._RETRIEVER_CACHE.clear()
        self.base = Path(self.temp.name)
        self.fx = _KnowledgeFixture(self.base, [
            _kcase("T-01", refs=["arXiv:2101.00001"]),
            _kcase("T-02", verdict="SUCCESS", refs=["arXiv:2101.00002"],
                   mechanics=["SENSOR_CALIBRATION"]),
            _kcase("T-03", status="ARCHIVE", refs=["arXiv:2101.00003"],
                   mechanics=["GROUP_INDEPENDENCE"]),
        ])

    # -- 1. coverage and structure ----------------------------------------
    def test_every_indexed_case_is_exported_once(self):
        out = self.fx.build()
        self.assertEqual(out["status"], "MIRROR_WRITTEN")
        cards = sorted(p.name for p in (self.fx.out / CARD_FILES).glob("*.md"))
        self.assertEqual(cards, ["T-01.md", "T-02.md", "T-03.md"])
        manifest = json.loads((self.fx.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["case_count"], 3)
        self.assertEqual(manifest["source"]["cases_in_index"], 3)
        self.assertEqual(len([f for f in manifest["files"]
                              if f["path"].startswith("cases/")]), 3)
        for rel in ("README.md", "AGENTS.md", "INDEX.md", "manifest.json",
                    "indexes/cases.jsonl", "docs/SCHEMA.md", "docs/RETRIEVAL.md",
                    "indexes/stages/H3.md", "indexes/stages/H4.md",
                    "indexes/stages/H6.md", "indexes/stages/H7.md",
                    "indexes/stages/H8.md", "insights/README.md"):
            self.assertTrue((self.fx.out / rel).is_file(), rel)

    def test_card_keeps_evidence_level_results_and_source_trace(self):
        self.fx.build()
        text = (self.fx.out / "cases" / "T-01.md").read_text(encoding="utf-8")
        front = json.loads(text.split("---json\n", 1)[1].split("\n---\n", 1)[0])
        self.assertEqual(front["case_id"], "T-01")
        self.assertEqual(front["evidence_level"], ["ORIGINAL_VERIFIED"])
        self.assertEqual(front["source_type"], "EXTERNAL")
        self.assertEqual(front["source_card_path"], "cases/external/T-01.md")
        self.assertTrue(front["source_digest"].startswith("sha256:"))
        self.assertTrue(front["results"] and "受控实验" in front["results"][0])
        self.assertIn("## 前提（复用前逐条核对）", text)
        self.assertIn("## 适用边界", text)
        self.assertIn("## 反例（何时本卡不成立）", text)
        self.assertIn("## 来源与追溯", text)
        self.assertFalse(front["publishable"] is None)

    # -- 2. determinism ----------------------------------------------------
    def test_rebuild_is_byte_identical(self):
        self.fx.build()
        first = _read_all(self.fx.out)
        first_hash = json.loads(first["manifest.json"])["content_sha256"]
        second = self.fx.build()
        self.assertEqual(second["written"], [])
        self.assertEqual(second["reused"], second["file_count"])
        self.assertEqual(_read_all(self.fx.out), first)
        self.assertEqual(second["content_sha256"], first_hash)

    def test_mirror_contains_no_absolute_local_path(self):
        self.fx.build()
        for rel, data in _read_all(self.fx.out).items():
            text = data.decode("utf-8", "replace")
            self.assertNotIn(str(self.base).replace("/", "\\"), text, rel)
            self.assertNotIn(str(self.base), text, rel)
            self.assertEqual(case_knowledge.scan_publish_blockers(text), [], rel)

    # -- 3. incremental ----------------------------------------------------
    def test_only_changed_case_and_its_indexes_are_rewritten(self):
        self.fx.build()
        inode_before = (self.fx.out / "cases" / "T-02.md").stat().st_ino
        changed = []
        for case in self.fx.cases:
            if case["case_id"] == "T-01":
                case = dict(case)
                case["title"] = "测试案例 T-01（修订）"
                case["transferable_lesson"] = "修订后的经验"
            changed.append(case)
        self.fx.rebuild_index(changed)
        out = self.fx.build()
        self.assertIn("cases/T-01.md", out["written"])
        self.assertNotIn("cases/T-02.md", out["written"])
        self.assertEqual((self.fx.out / "cases" / "T-02.md").stat().st_ino, inode_before)
        self.assertIn("修订后的经验",
                      (self.fx.out / "cases" / "T-01.md").read_text(encoding="utf-8"))

    def test_removed_case_is_recorded_not_silently_dropped(self):
        self.fx.build()
        kept = [c for c in self.fx.cases if c["case_id"] != "T-03"]
        self.fx.rebuild_index(kept)
        out = self.fx.build()
        self.assertFalse((self.fx.out / "cases" / "T-03.md").exists())
        self.assertEqual(out["case_count"], 2)
        lifecycle = (self.fx.out / "indexes" / "lifecycle.jsonl").read_text(encoding="utf-8")
        self.assertIn("CASE_RETIRED", lifecycle)
        self.assertIn("T-03", lifecycle)
        manifest = json.loads((self.fx.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([c for c in manifest["privacy_blocked_cases"]], [])

    def test_status_change_is_recorded_in_lifecycle(self):
        self.fx.build()
        changed = []
        for case in self.fx.cases:
            if case["case_id"] == "T-03":
                case = dict(case)
                case["status"] = "PROJECT_CLOSED"
            changed.append(case)
        self.fx.rebuild_index(changed)
        self.fx.build()
        lifecycle = (self.fx.out / "indexes" / "lifecycle.jsonl").read_text(encoding="utf-8")
        self.assertIn("STATUS_CLASS_CHANGED", lifecycle)
        self.assertIn("ARCHIVED", lifecycle)
        self.assertIn("CLOSED_NO_CLAIM", lifecycle)

    # -- 4. gates ----------------------------------------------------------
    def test_privacy_blocker_prevents_publishable_mirror(self):
        leaky = _kcase("T-09", boundaries=[r"取自 D:\private\runs\subject.csv"])
        self.fx.rebuild_index(self.fx.cases + [leaky])
        self.fx.build()
        manifest = json.loads((self.fx.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["publishable"])
        self.assertIn("PRIVACY_OR_CONTENT_BLOCKER", manifest["publish_blockers"])
        self.assertIn("ABSOLUTE_LOCAL_PATH", manifest["privacy_blocked_cases"]["T-09"])
        card = (self.fx.out / "cases" / "T-09.md").read_text(encoding="utf-8")
        self.assertIn("发布阻断", card)

    def test_stale_index_blocks_publish(self):
        self.fx.build()
        card = self.fx.fx.root / "cases" / "external" / "T-01.md"
        future = card.stat().st_mtime + 120
        os.utime(card, (future, future))
        self.fx.build()
        manifest = json.loads((self.fx.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["publishable"])
        self.assertIn("INDEX_STALE_REBUILD_REQUIRED", manifest["publish_blockers"])

    def test_failed_build_keeps_the_previous_mirror(self):
        self.fx.build()
        before = _read_all(self.fx.out)
        verify_before = case_knowledge.verify(self.fx.out)
        self.assertTrue(verify_before["publishable"])

        def explode(*args, **kwargs):
            target = args[0]
            (target / "cases").mkdir(parents=True, exist_ok=True)
            (target / "cases" / "T-01.md").write_text("partial", encoding="utf-8")
            raise RuntimeError("simulated staging failure")

        with patch.object(case_knowledge, "_stage_tree", side_effect=explode):
            with self.assertRaises(RuntimeError):
                self.fx.build()
        self.assertEqual(_read_all(self.fx.out), before)
        self.assertEqual(case_knowledge.verify(self.fx.out), verify_before)
        self.assertFalse(any(p.name.startswith(".mirror.building")
                             for p in self.base.iterdir()))

    def test_verify_blocks_when_library_moved_after_export(self):
        self.fx.build()
        self.assertTrue(case_knowledge.verify(self.fx.out,
                                              settings=self.fx.settings())["publishable"])
        index_path = self.fx.fx.root / "index.json"
        index = json.loads(index_path.read_text(encoding="utf-8"))
        index["cases"][0]["title"] = index["cases"][0]["title"] + "（后续修订）"
        index_path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
        result = case_knowledge.verify(self.fx.out, settings=self.fx.settings())
        self.assertFalse(result["publishable"])
        self.assertIn("SOURCE_LIBRARY_CHANGED_SINCE_EXPORT", result["problems"])

    def test_dry_run_writes_nothing(self):
        out = self.fx.build(dry_run=True)
        self.assertEqual(out["status"], "DRY_RUN_PLAN_ONLY")
        self.assertFalse(self.fx.out.exists())
        self.assertTrue(out["no_writes"])

    def test_verify_detects_tampering(self):
        self.fx.build()
        card = self.fx.out / "cases" / "T-02.md"
        card.write_text(card.read_text(encoding="utf-8") + "\n手工追加\n", encoding="utf-8")
        result = case_knowledge.verify(self.fx.out)
        self.assertEqual(result["status"], "MIRROR_PROBLEMS")
        self.assertIn("FILE_HASH_MISMATCH", result["problems"])
        self.assertFalse(result["publishable"])

    # -- 5. index consistency ---------------------------------------------
    def test_all_indexes_agree_on_the_case_set(self):
        self.fx.build()
        ids_jsonl = {json.loads(line)["case_id"]
                     for line in (self.fx.out / "indexes" / "cases.jsonl")
                     .read_text(encoding="utf-8").splitlines() if line.strip()}
        index_md = (self.fx.out / "INDEX.md").read_text(encoding="utf-8")
        ids_index = {line.split("[", 1)[1].split("]", 1)[0]
                     for line in index_md.splitlines()
                     if line.startswith("| [")}
        ids_stage, ids_topic = set(), set()
        for path in (self.fx.out / "indexes" / "stages").glob("*.md"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("| ["):
                    ids_stage.add(line.split("[", 1)[1].split("]", 1)[0])
        for path in (self.fx.out / "indexes" / "topics").glob("*.md"):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("| ["):
                    ids_topic.add(line.split("[", 1)[1].split("]", 1)[0])
        self.assertEqual(ids_jsonl, {"T-01", "T-02", "T-03"})
        self.assertEqual(ids_index, ids_jsonl)
        self.assertEqual(ids_stage, ids_jsonl)
        self.assertEqual(ids_topic, ids_jsonl)
        manifest = json.loads((self.fx.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(sum(manifest["counts"]["by_outcome"].values()), 3)

    def test_status_class_is_consistent_between_index_and_card(self):
        self.fx.build()
        rows = {json.loads(line)["case_id"]: json.loads(line)
                for line in (self.fx.out / "indexes" / "cases.jsonl")
                .read_text(encoding="utf-8").splitlines() if line.strip()}
        for cid, row in rows.items():
            text = (self.fx.out / row["path"]).read_text(encoding="utf-8")
            front = json.loads(text.split("---json\n", 1)[1].split("\n---\n", 1)[0])
            self.assertEqual(front["status_class"], row["status_class"])
            self.assertEqual(front["evidence_grade"], row["evidence_grade"])
            self.assertEqual(row["sha256"], case_export._sha256(text))

    # -- 6. source identity / unknown fields ------------------------------
    def test_same_paper_cards_share_a_group_but_keep_ids(self):
        twin_a = _kcase("T-11", refs=["doi:10.1000/twin"])
        twin_b = _kcase("T-12", refs=["doi:10.1000/twin", "PMID:12345678"])
        self.fx.rebuild_index([twin_a, twin_b])
        self.fx.build()
        a = json.loads((self.fx.out / "cases" / "T-11.md")
                       .read_text(encoding="utf-8").split("---json\n", 1)[1]
                       .split("\n---\n", 1)[0])
        b = json.loads((self.fx.out / "cases" / "T-12.md")
                       .read_text(encoding="utf-8").split("---json\n", 1)[1]
                       .split("\n---\n", 1)[0])
        self.assertEqual(a["case_id"], "T-11")
        self.assertEqual(b["case_id"], "T-12")
        self.assertEqual(a["source_group_id"], b["source_group_id"])
        self.assertEqual(a["same_source_cases"], ["T-12"])
        self.assertEqual(b["same_source_cases"], ["T-11"])

    def test_missing_fields_stay_unknown_and_never_guessed(self):
        self.fx.build()
        front = json.loads((self.fx.out / "cases" / "T-02.md")
                           .read_text(encoding="utf-8").split("---json\n", 1)[1]
                           .split("\n---\n", 1)[0])
        self.assertEqual(front["updated_at"], "UNKNOWN")
        self.assertEqual(front["research_problem_basis"], "TITLE")
        self.assertEqual(front["h_stages_basis"],
                         case_export.STAGE_ROUTING_BASIS)
        self.assertEqual(front["schema_version"],
                         case_export.KNOWLEDGE_SCHEMA_VERSION)

    # -- 7. retrieval ------------------------------------------------------
    def test_long_question_falls_back_to_loose_recall(self):
        long_q = ("我们在可穿戴数据上做活动识别，用滑动窗口随机划分训练测试，"
                  "性能很高，但怀疑同一个人同时出现在训练和测试里导致虚高")
        bundle = case_learning.load_index(self.fx.fx.root)
        result = case_learning.search(bundle, None, long_q, limit=3)
        self.assertEqual(result["status"], "MATCHES_FOUND")
        self.assertEqual(result["retrieval_mode"], "TOKEN_UNION_FALLBACK")
        self.assertTrue(result["recall_terms"])
        self.assertIn("source_independence", result)

    def test_explicit_mechanism_filter_is_not_bypassed_by_fallback(self):
        bundle = case_learning.load_index(self.fx.fx.root)
        result = case_learning.search(
            bundle, {"mechanism": "NO_SUCH_MECHANISM"},
            "任意长问题，关于数据泄漏与泛化", limit=3)
        self.assertEqual(result["status"], "NO_CASE_MATCH")

    def test_same_source_cases_are_not_counted_as_independent(self):
        self.fx.rebuild_index([
            _kcase("T-21", refs=["doi:10.1000/pair"]),
            _kcase("T-22", refs=["doi:10.1000/pair"]),
        ])
        bundle = case_learning.load_index(self.fx.fx.root)
        result = case_learning.search(bundle, None, "受试者", limit=3)
        self.assertEqual(result["status"], "MATCHES_FOUND")
        independence = result["source_independence"]
        self.assertEqual(independence["same_source_pairs"][0][:2], ["T-21", "T-22"])
        self.assertEqual(independence["independent_units"], 1)


@unittest.skipUnless(HAS_RETRIEVER, "real CASE_LIBRARY not available")
class RealLibraryKnowledgeTests(unittest.TestCase):
    """Read-only pass over the real library; never writes to it."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.temp.name) / "mirror"
        from pdrw_agent.config import Settings
        cfg = Path(cls.temp.name) / "project-map.json"
        cfg.write_text(json.dumps({"schema_version": 1, "projects": {},
                                   "case_library_root": str(REAL_LIBRARY)}),
                       encoding="utf-8")
        rules = Path(cls.temp.name) / "rules"
        rules.mkdir()
        (rules / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
        (rules / "WORKFLOW.md").write_text("# workflow\n", encoding="utf-8")
        cls.settings = Settings.load(str(cfg), str(rules))
        cls.before = cls._library_digest()
        cls.result = case_knowledge.build(cls.settings, cls.out)

    @classmethod
    def tearDownClass(cls):
        assert cls._library_digest() == cls.before, "CASE_LIBRARY was modified"
        cls.temp.cleanup()

    @staticmethod
    def _library_digest() -> str:
        h = __import__("hashlib").sha256()
        for path in sorted(REAL_LIBRARY.rglob("*")):
            if path.is_file():
                h.update(str(path).encode("utf-8"))
                h.update(path.read_bytes())
        return h.hexdigest()

    def test_full_library_is_exported(self):
        cards = sorted(p.name for p in (self.out / "cases").glob("*.md"))
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cards), manifest["case_count"])
        self.assertEqual(manifest["case_count"], manifest["source"]["cases_in_index"])
        self.assertEqual(len(cards), len(set(cards)))
        self.assertTrue(manifest["publishable"], manifest["publish_blockers"])

    def test_every_stage_index_has_candidates(self):
        for stage in case_knowledge.STAGES:
            text = (self.out / "indexes" / "stages" / f"{stage}.md").read_text(encoding="utf-8")
            rows = [x for x in text.splitlines() if x.startswith("| [")]
            self.assertGreater(len(rows), 0, stage)

    def test_weak_and_archived_cases_are_labelled(self):
        rows = [json.loads(line) for line in
                (self.out / "indexes" / "cases.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()]
        classes = {r["status_class"] for r in rows}
        self.assertTrue(classes & {"ARCHIVED", "RETIRED"})
        self.assertIn("WEAK_EVIDENCE", classes)
        self.assertTrue(all(r["publishable"] for r in rows))

    def test_known_same_paper_pairs_are_linked(self):
        rows = {json.loads(line)["case_id"]: json.loads(line)
                for line in (self.out / "indexes" / "cases.jsonl")
                .read_text(encoding="utf-8").splitlines() if line.strip()}
        self.assertEqual(rows["EXT-C04"]["source_group_id"],
                         rows["EXT-C05"]["source_group_id"])
        self.assertEqual(rows["EXT-N01"]["source_group_id"],
                         rows["EXT-N02"]["source_group_id"])
        self.assertNotEqual(rows["EXT-REPAIR-01"]["source_group_id"],
                            rows["EXT-X1"]["source_group_id"])

    def test_tampering_is_detected(self):
        copy = Path(self.temp.name) / "copy"
        shutil.copytree(self.out, copy)
        card = copy / "cases" / "CASE-01.md"
        card.write_text(card.read_text(encoding="utf-8") + "x", encoding="utf-8")
        result = case_knowledge.verify(copy)
        self.assertIn("FILE_HASH_MISMATCH", result["problems"])


if __name__ == "__main__":
    unittest.main()
