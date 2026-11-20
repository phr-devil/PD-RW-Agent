"""WP9-C: strict ``as_of`` view for historical replay.

No case, index or Run is written. The point is that a card without a
trustworthy visibility time is excluded from a strict replay instead of being
silently treated as visible, while ordinary research retrieval is unchanged.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from pdrw_agent import case_learning
from pdrw_agent.schemas import AgentError

REAL_LIBRARY = Path(os.environ.get("PDRW_CASE_LIBRARY_ROOT", "D:/workbuddy-work/CASE_LIBRARY"))
HAS_RETRIEVER = (REAL_LIBRARY / "scripts" / "search_cases.py").is_file()


def _card(cid: str, *, visible: str | None) -> dict:
    meta = {
        "case_id": cid, "title": f"夹具 {cid}", "verdict": "FAILURE", "origin": "EXTERNAL",
        "evidence_class": "VERIFIED_FAILURE", "mechanisms": ["GROUP_INDEPENDENCE"],
        "research_domains": ["WEARABLE_SENSING"],
        "premises": ["分组独立且评价单位是受试者"],
        "applicability": {"conditions": ["受试者独立划分"], "boundaries": ["结论限于所测数据集"]},
        "counterexamples": ["若分组泄漏则增益消失"],
        "transferable_lesson": "先按受试者分组再比较",
        "next_minimal_check": ["成对报告随机划分与受试者划分差值"],
        "evidence_levels": ["ORIGINAL_VERIFIED"], "source_refs": [f"10.1000/{cid}"],
        "source_paths": ["https://example.invalid/x"],
        "evidence_paths": [f"cases/external/{cid}.md"],
        "secondary_claims_not_admitted": [], "scope_warning": "",
        "status": "ACTIVE", "evidence_role": ["PRIMARY_EMPIRICAL"],
        "search_blob": "受试者 分组 泄漏 平衡准确率 增益 评价单位 基线 可穿戴传感",
    }
    if visible is not None:
        meta["visibility_time"] = visible
    return meta


@unittest.skipUnless(HAS_RETRIEVER, "CASE_LIBRARY/scripts/search_cases.py not present")
class AsOfVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.library = Path(self.temp.name) / "CASE_LIBRARY"
        (self.library / "cases" / "external").mkdir(parents=True)
        (self.library / "scripts").mkdir(parents=True)
        shutil.copyfile(REAL_LIBRARY / "scripts" / "search_cases.py",
                        self.library / "scripts" / "search_cases.py")
        (self.library / "taxonomy.yaml").write_text("schema_version: 1\n", encoding="utf-8")
        self.cases = [_card("T-OLD", visible="2026-01-01T00:00:00+00:00"),
                      _card("T-NODATE", visible=None)]
        for meta in self.cases:
            path = self.library / meta["evidence_paths"][0]
            path.write_text("---json\n" + json.dumps(meta, ensure_ascii=False)
                            + "\n---\n\n# " + meta["title"] + "\n", encoding="utf-8")
        (self.library / "index.json").write_text(json.dumps({
            "schema_version": 1, "taxonomy_version": 1, "case_count": len(self.cases),
            "source_of_truth": "cases/external/*.md",
            "cases": self.cases, "by_mechanism": {}, "by_domain": {},
            "by_verdict": {}, "by_evidence_class": {}, "by_evidence_level": {},
        }, ensure_ascii=False), encoding="utf-8")
        self.bundle = case_learning.load_index(self.library)

    def test_default_search_is_unchanged_and_not_blocked(self):
        found = case_learning.search(self.bundle, {}, "受试者 分组 泄漏 平衡准确率", 5)
        self.assertEqual(found["status"], "MATCHES_FOUND")
        self.assertNotIn("as_of", found)
        self.assertEqual({r["case_id"] for r in found["results"]}, {"T-OLD", "T-NODATE"})

    def test_strict_as_of_excludes_cards_without_visibility_time(self):
        found = case_learning.search(self.bundle, {}, "受试者 分组 泄漏 平衡准确率", 5,
                                     as_of="2026-06-01T00:00:00+00:00")
        self.assertTrue(found["as_of"]["strict_historical_mode"])
        self.assertEqual([r["case_id"] for r in found["results"]], ["T-OLD"])
        self.assertEqual(found["as_of"]["excluded_unknown_visibility"], 1)
        self.assertIn("T-NODATE", found["as_of"]["excluded_unknown_case_ids"])

    def test_as_of_before_any_visibility_reports_a_blocker(self):
        found = case_learning.search(self.bundle, {}, "受试者 分组 泄漏 平衡准确率", 5,
                                     as_of="2025-01-01T00:00:00+00:00")
        self.assertEqual(found["status"], "NO_CASE_MATCH")
        self.assertEqual(found["as_of"]["visible_cases"], 0)
        self.assertEqual(found["as_of"]["blocked"],
                         "NO_CASE_IN_INDEX_CARRIES_A_VISIBILITY_TIME")

    def test_invalid_as_of_is_rejected(self):
        for bad in ("2026-06-01", 20260601):
            with self.assertRaises(AgentError) as ctx:
                case_learning.search(self.bundle, {}, "受试者", 5, as_of=bad)
            self.assertEqual(ctx.exception.code, "AS_OF_INVALID")


if __name__ == "__main__":
    unittest.main()
