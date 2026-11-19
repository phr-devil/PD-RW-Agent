"""Read-only CASE_LIBRARY adapter: case learning and decision reuse.

Design constraints (verified on this machine, 2026-11-15):
* The ONLY sources are CASE_LIBRARY/index.json and the existing
  scripts/search_cases.py retriever functions (imported, not reimplemented).
  No second database, no copy of the index, no new research rules.
* No writes to CASE_LIBRARY, PD-RW workflow, SEALED, original Run, STATE,
  EVENTS or any A/B/C frozen snapshot. No network fetch of source URLs.
* No GO/STOP, no scientific-equivalence verdict, no authorization change.
* Keyword similarity is NOT scientific premise equivalence. Every comparison
  is a declared-text triage with equivalence_verified=false.
* Local PD-RW-Agent baseline is 0.5.3; the operator-stated 0.7.6 was NOT
  found locally (REMOTE_NOT_CHECKED). This module is a local increment.

Evidence roles are read from the case card frontmatter for returned cases
only, so that original empirical work, author reports, independent
replication, opinion/review and unverified speculation stay distinguishable.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import re
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

from .config import read_json
from .schemas import AgentError

CASE_LEARNING_VERSION = "1.0"
MAX_INDEX_BYTES = 8 * 1024 * 1024
MAX_CASES = 5
# Real 65-card CASE_LIBRARY entries are longer than the synthetic fixtures:
# five fully detailed cases plus their source verification, 8-dimension review
# and decision experiences exceed 12k chars. A bounded 16k cap still admits
# 3 coherent cases (= 3 decision experiences) without unbounded tool output.
MAX_TOTAL_CHARS = 16000
MAX_FIELD_CHARS = 240
MAX_PROFILE_FIELDS = 12
CACHE_SIZE = 32
PROTECTED_PARTS = {"sealed", "holdout", "confirmation"}

FILTER_KEYS = ("mechanism", "domain", "applicability", "evidence_level",
               "verdict", "evidence_class", "origin", "keyword")

# 8 required migration-review dimensions -> controlled keywords.
DIMENSION_KEYWORDS = {
    "mechanisms": ["leakage", "泄漏", "分组", "group", "label", "标签", "baseline",
                   "基线", "causal", "因果", "calibration", "标定", "shift", "偏移",
                   "shortcut", "捷径", "baseline", "泛化", "generalization"],
    "legal_inputs": ["合法输入", "预测时刻", "部署时可得", "illegitimate", "oracle",
                     "proxy", "结果代理", "leakage", "泄漏", "feature", "特征",
                     "可得", "test label", "测试标签"],
    "labels": ["标签", "label", "错标", "伪标签", "真值", "truth", "proxy",
               "标注", "噪声", "noise"],
    "grouping": ["分组", "group", "subject", "受试者", "LOSO", "伪重复",
                 "独立单位", "split", "划分", "window", "窗口", "session", "录制"],
    "evaluation_unit": ["评价单位", "evaluation unit", "独立单位", "AUC", "AUROC",
                        "R²", "准确率", "accuracy", "指标", "metric", "窗口级",
                        "受试者级", "评价母体"],
    "baseline": ["基线", "baseline", "简单", "线性", "逻辑回归", "调参预算",
                 "强基线", "ablation", "消融"],
    "boundaries": ["适用", "不适用", "边界", "仅限", "不得", "限制", "外推",
                   "scope", "boundary", "limitation", "只对应"],
    "counterexamples": ["反例", "不适用", "例外", "不成立", "counterexample",
                        "完全失败", "退化", "若", "反例", "不适用"],
}
DIMENSIONS = tuple(DIMENSION_KEYWORDS)
CORE_DIMENSIONS = ("legal_inputs", "labels", "grouping", "evaluation_unit", "baseline")
EXCLUSION_MARKERS = ("不适用", "不得", "禁止", "仅限", "不成立", "完全失败",
                     "不外推", "不得泛化", "not applicable", "does not",
                     "cannot", "do not", "could not", "failed to")
VERSION_PATTERN = re.compile(r"\bv[0-9]+(?:[.,][0-9]+)?\b|版本\s*[0-9]+", re.I)

ADMISSIBLE_LEVELS = {"ORIGINAL_VERIFIED", "PARTIAL_TEXT_VERIFIED"}
BLOCKED_LEVELS = {"NOT_ACCESSED", "SECONDARY_ONLY", "UNVERIFIED_REPORT", "SPECULATION"}

ROLE_CLASS = {
    "PRIMARY_EMPIRICAL": "ORIGINAL_EMPIRICAL",
    "THIRD_PARTY_REPLICATION": "INDEPENDENT_REPLICATION",
    "THIRD_PARTY_EXTERNAL_VALIDATION": "INDEPENDENT_EXTERNAL_VALIDATION",
    "LOCAL_INDEPENDENT_VERIFICATION": "LOCAL_VERIFICATION",
    "AUTHOR_REPORT": "AUTHOR_REPORT",
    "INTERNAL_PROJECT_REPORT": "INTERNAL_REPORT",
    "REVIEW_OR_PERSPECTIVE": "OPINION_OR_REVIEW",
    "SECONDARY_REPORT": "UNVERIFIED_SECONDARY",
}

WARNING = ("WARNING: 关键词/标签相似 != 科学前提等价。命中只是候选，"
           "必须逐条比对 premises 与 applicability.conditions/boundaries 及 counterexamples。")
NOTICE = ("NOTICE: 本工具只输出候选、证据路径与适用风险，不输出 GO/STOP，"
          "不判定科学等价性，不修改科研授权、STATE、Run 或 SEALED。")

_RETRIEVER_CACHE: dict[str, object] = {}
_RESULT_CACHE: "OrderedDict[str, dict]" = OrderedDict()


def _text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return " ".join(str(x) for x in value)
    if isinstance(value, dict):
        return " ".join(f"{k} {v}" for k, v in value.items())
    return "" if value is None else str(value)


def _clip(value, n: int = MAX_FIELD_CHARS) -> str:
    s = str(value).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _cliplist(values, k: int = 2, n: int = MAX_FIELD_CHARS) -> list[str]:
    return [_clip(v, n) for v in list(values or [])[:k]]


# --------------------------------------------------------------------------
# Path-safe, read-only resolution of the single CASE_LIBRARY source
# --------------------------------------------------------------------------
def resolve_root(settings) -> Path | None:
    """Operator-supplied locator only: env var or private project map key."""
    raw = os.environ.get("PDRW_CASE_LIBRARY_ROOT")
    if not raw or not isinstance(raw, str) or not raw.strip():
        try:
            raw = read_json(settings.project_map).get("case_library_root")
        except (AgentError, OSError, ValueError):
            return None
    if not isinstance(raw, str) or not raw.strip():
        return None
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise AgentError("CASE_LIBRARY_ROOT_INVALID", "Configured CASE_LIBRARY root is not a directory")
    if any(part.casefold() in PROTECTED_PARTS for part in root.parts):
        raise AgentError("PROTECTED_PATH_REJECTED", "CASE_LIBRARY root must not be a SEALED/holdout/confirmation subtree")
    index = (root / "index.json").resolve()
    if root != index and root not in index.parents:
        raise AgentError("PATH_OUTSIDE_LIBRARY", "index.json resolves outside the configured root")
    if index.is_symlink() or not index.is_file():
        raise AgentError("CASE_INDEX_MISSING", "CASE_LIBRARY/index.json is missing or a symlink")
    if index.stat().st_size > MAX_INDEX_BYTES:
        raise AgentError("CASE_INDEX_TOO_LARGE", "CASE_LIBRARY index exceeds the bounded size")
    if not (root / "cases").is_dir() or not (root / "scripts" / "search_cases.py").is_file():
        raise AgentError("CASE_LIBRARY_INCOMPLETE", "cases/ and scripts/search_cases.py are required to reuse the existing retriever")
    return root


def load_index(root: Path) -> dict:
    """Read the generated index once; verify provenance and staleness."""
    index = root / "index.json"
    raw = index.read_bytes()
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, ValueError) as exc:
        raise AgentError("CASE_INDEX_INVALID_JSON", "Cannot parse CASE_LIBRARY index.json") from exc
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise AgentError("CASE_INDEX_SCHEMA_MISMATCH", "index.json must contain a cases list")
    if data.get("case_count") != len(data["cases"]):
        raise AgentError("CASE_INDEX_COUNT_MISMATCH", "case_count does not match cases; rebuild the index")
    if not data.get("source_of_truth") or not data.get("schema_version"):
        raise AgentError("CASE_INDEX_PROVENANCE_MISSING", "index.json lacks source_of_truth/schema_version")
    cards = [p for p in (root / "cases").rglob("*.md") if p.is_file() and not p.name.startswith("_")]
    newest = max((p.stat().st_mtime for p in cards), default=0.0)
    return {
        "data": data,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "index_stale": newest > index.stat().st_mtime + 1.0,
        "card_count": len(cards),
        "root": root,
    }


def load_retriever(root: Path):
    """Import the EXISTING search_cases.py; do not reimplement its scoring."""
    path = (root / "scripts" / "search_cases.py").resolve()
    if root != path and root not in path.parents:
        raise AgentError("PATH_OUTSIDE_LIBRARY", "search_cases.py resolves outside the configured root")
    if path.is_symlink() or path.stat().st_size > 256 * 1024:
        raise AgentError("RETRIEVER_UNSAFE", "Existing retriever is a symlink or unexpectedly large")
    key = str(path)
    if key not in _RETRIEVER_CACHE:
        spec = importlib.util.spec_from_file_location("pdrw_case_library_retriever", key)
        if spec is None or spec.loader is None:
            raise AgentError("RETRIEVER_UNAVAILABLE", "Cannot load the existing CASE_LIBRARY retriever")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for needed in ("score_case", "compact", "divergence_note", "norm"):
            if not hasattr(module, needed):
                raise AgentError("RETRIEVER_INCOMPATIBLE", f"search_cases.py lacks {needed}")
        _RETRIEVER_CACHE[key] = module
    return _RETRIEVER_CACHE[key]


def _card_path(root: Path, rel: str) -> Path | None:
    """Only allow case-card-relative paths fully inside root/cases."""
    if not isinstance(rel, str) or not rel or rel.startswith(("http://", "https://")):
        return None
    if Path(rel).is_absolute() or ".." in Path(rel).parts:
        return None
    base = (root / "cases").resolve()
    target = (root / rel).resolve()
    if target == base or base not in target.parents or not target.is_file() or target.is_symlink():
        return None
    if any(part.casefold() in PROTECTED_PARTS for part in target.relative_to(root).parts):
        return None
    return target


def _card_meta(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        return {}
    m = re.match(r"^---json\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}
    try:
        return json.loads(m.group(1))
    except ValueError:
        return {}


def verify_sources(index_bundle: dict, results: list[dict]) -> dict:
    """Per-case source check: card exists, ID matches, evidence grade and role."""
    root = index_bundle["root"]
    by_id = {c["case_id"]: c for c in index_bundle["data"]["cases"]}
    out = {}
    for r in results:
        cid = r["case_id"]
        c = by_id.get(cid, {})
        local_paths = [p for p in c.get("evidence_paths", []) if _card_path(root, p)]
        cards = [(p, _card_path(root, p)) for p in c.get("evidence_paths", [])]
        resolved = [t for _, t in cards if t is not None]
        meta = _card_meta(resolved[0]) if resolved else {}
        id_ok = bool(meta) and meta.get("case_id") == cid
        levels = list(c.get("evidence_levels", []))
        roles = meta.get("evidence_role") or []
        if isinstance(roles, str):
            roles = [roles]
        role_classes = sorted({ROLE_CLASS.get(str(x), "ROLE_UNDECLARED") for x in roles})
        status = str(c.get("status") or "")
        refs = list(c.get("source_refs", []))
        if index_bundle["index_stale"]:
            grade = "INDEX_STALE_REBUILD_REQUIRED"
        elif not resolved or not id_ok:
            grade = "UNVERIFIED_CARD_MISSING_OR_ID_MISMATCH"
        elif any(x in BLOCKED_LEVELS for x in levels):
            grade = "NON_DECISION_GRADE"
        elif any(x in ADMISSIBLE_LEVELS for x in levels):
            # Mixed levels are normal: a case may cite one full-text paper and
            # one abstract-only source. Only a case whose *only* verified level
            # is abstract may not carry numeric/full-text claims.
            grade = "DECISION_GRADE"
        elif "ABSTRACT_VERIFIED" in levels or "PAPER_LIMITATION" in levels:
            grade = "ABSTRACT_OR_LIMITATION_ONLY"
        else:
            grade = "REVIEW_REQUIRED"
        if "PREPRINT" in status.upper():
            grade += "+PREPRINT_NOT_PEER_REVIEWED"
        # An author report explicitly marked non-peer-reviewed is not an
        # independent scientific confirmation, even if its own numbers were
        # re-read from the original file.
        if "NON_PEER_REVIEWED" in status.upper():
            grade += "+NON_PEER_REVIEWED"
        if c.get("origin") == "EXTERNAL" and not refs:
            grade += "+SOURCE_REFS_MISSING"
        reasons = []
        if not resolved:
            reasons.append("NO_LOCAL_CASE_CARD_RESOLVED")
        if not id_ok:
            reasons.append("CARD_ID_MISMATCH_OR_UNPARSEABLE")
        if any(x in BLOCKED_LEVELS for x in levels):
            reasons.append("BLOCKED_EVIDENCE_LEVEL_PRESENT")
        if not role_classes or role_classes == ["ROLE_UNDECLARED"]:
            reasons.append("EVIDENCE_ROLE_UNDECLARED")
        caveats = []
        if "ABSTRACT_VERIFIED" in levels:
            caveats.append("ABSTRACT_VERIFIED_SOURCES_PRESENT_DO_NOT_UPGRADE_TO_FULLTEXT_CLAIMS")
        if "INTERNAL_REPORT" in levels:
            caveats.append("INTERNAL_REPORT_NOT_INDEPENDENTLY_RECOMPUTED")
        if "SECONDARY_ONLY" in levels:
            caveats.append("SECONDARY_NUMBERS_NOT_ADMITTED")
        if "NON_PEER_REVIEWED" in status.upper():
            caveats.append("AUTHOR_REPORT_NOT_PEER_REVIEWED_EXPLORATORY_ONLY")
        out[cid] = {
            "evidence_grade": grade,
            "evidence_levels": levels,
            "evidence_roles": roles,
            "role_classes": role_classes,
            "caveats": caveats,
            "local_card_paths": [str(t.relative_to(root)).replace("\\", "/") for t in resolved[:2]],
            "external_refs_not_fetched": [p for p in c.get("evidence_paths", [])
                                          if isinstance(p, str) and p.startswith(("http://", "https://"))][:2],
            "source_refs_present": bool(refs),
            "card_id_matches": id_ok,
            "preprint": "PREPRINT" in status.upper(),
            "reasons": reasons,
        }
    return {
        "index_sha256": index_bundle["sha256"],
        "index_stale": index_bundle["index_stale"],
        "cards_on_disk": index_bundle["card_count"],
        "cases_in_index": len(by_id),
        "source_of_truth": index_bundle["data"].get("source_of_truth"),
        "schema_version": index_bundle["data"].get("schema_version"),
        "per_case": out,
        "note": "External URLs are recorded but never fetched; byte/hash checks do not prove scientific truth.",
    }


# --------------------------------------------------------------------------
# Reuse the existing retriever functions
# --------------------------------------------------------------------------
def _profile_filters(profile: dict | None) -> dict:
    """Only controlled taxonomy labels become hard filters.

    Free-text Chinese descriptions must NOT be turned into AND-filters, or the
    reused retriever would silently return zero cases and hide applicable risk.
    They remain in the comparison text instead.
    """
    if not profile:
        return {}
    out = {}
    for key, target in (("mechanisms", "mechanism"), ("research_domains", "domain")):
        labels = re.findall(r"[A-Z][A-Z0-9_]{3,}", profile.get(key, "") or "")
        if labels:
            out[target] = ",".join(labels)
    return out


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[\w\u4e00-\u9fff-]+", text) if len(t) >= 2]


# --------------------------------------------------------------------------
# Recall for long natural-language questions (WP6-A)
#
# The reused retriever ANDs a single keyword substring, so one long question
# sentence would return nothing and silently hide applicable risk. This path
# only runs when the primary query already returned zero candidates, so the
# existing behaviour and ranking are unchanged for every other call.
# --------------------------------------------------------------------------
_WORD_TERM = re.compile(r"[A-Za-z][A-Za-z0-9_-]{3,}")
_CJK_RUN = re.compile(r"[\u4e00-\u9fff]+")
TERM_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "our", "are", "was",
    "were", "have", "has", "not", "but", "can", "does", "did", "how", "what",
    "which", "when", "why", "using", "use", "based", "into", "than", "then",
    "数据", "我们", "需要", "是否", "一个", "这个", "可以", "必须", "问题",
    "分析", "结果", "模型", "方法", "实验", "研究", "论文", "如果", "因为",
    "所以", "以及", "进行", "使用", "通过", "没有", "已经", "应该", "可能",
    "如何", "什么", "哪些", "这样", "那样", "同时", "而且", "但是", "由于",
}
_CJK_STOP_CHARS = set("的了在和与或是有对为上个我你他它这那很都也就要会能")
MAX_RECALL_TERMS = 4

# Concept aliases: the library is written in a specific research vocabulary, so
# an everyday word ("同一个人") must be allowed to reach the vocabulary term
# ("受试者"). This is a fixed, auditable mapping - not a learned index - and it
# only widens recall; ranking still decides what is shown.
CONCEPT_ALIASES = {
    ("受试者", "被试", "同一个人", "个体", "subject"): ["受试者", "subject"],
    ("泄漏", "泄露", "虚高", "高估", "作弊", "非法信息"): ["泄漏", "leak"],
    ("滑窗", "滑动窗口", "窗口"): ["滑窗", "window"],
    ("排行榜", "榜单", "提交次数", "public"): ["排行榜", "leaderboard"],
    ("消融", "ablation"): ["消融", "ablation"],
    ("基线", "baseline", "对照"): ["基线", "baseline"],
    ("泛化", "generaliz", "外推"): ["泛化", "generaliz"],
    ("标签", "标注", "label"): ["标签", "label"],
    ("噪声", "noise", "干扰"): ["噪声", "noise"],
    ("复现", "重复实验", "reproduc"): ["复现", "reproduc"],
    ("校准", "标定", "calibrat"): ["校准", "calibrat"],
    ("迁移", "transfer"): ["迁移", "transfer"],
    ("触觉", "压力", "法向力", "tactile"): ["触觉", "tactile"],
    ("可穿戴", "imu", "活动识别", "步态", "har"): ["可穿戴", "har", "imu"],
    ("真值", "ground truth", "金标准"): ["真值", "truth"],
    ("划分", "切分", "k折", "k-fold", "交叉验证"): ["划分", "fold"],
    ("预注册", "预登记", "preregist"): ["预注册", "preregist"],
    ("功效", "样本量", "mde", "power"): ["功效", "power"],
    ("统计显著", "显著性", "多重比较"): ["显著", "多重比较"],
}


def core_terms(query: str, limit: int = 48) -> list[str]:
    """Concept candidates from a long question, without a segmenter.

    Latin words are taken whole; CJK runs are expanded into 2-4 character
    n-grams, longest first, so a specific phrase outranks a generic bigram.
    """
    out, seen = [], set()
    lower = (query or "").lower()
    for triggers, aliases in CONCEPT_ALIASES.items():
        if any(t in lower for t in triggers):
            for alias in aliases:
                if alias not in seen:
                    seen.add(alias)
                    out.append(alias)
    for word in _WORD_TERM.findall(query or ""):
        token = word.lower()
        if token in TERM_STOP or token in seen:
            continue
        seen.add(token)
        out.append(token)
    for run in _CJK_RUN.findall(query or ""):
        for size in (4, 3, 2):
            for start in range(len(run) - size + 1):
                gram = run[start:start + size]
                if gram in seen or gram in TERM_STOP:
                    continue
                if all(ch in _CJK_STOP_CHARS for ch in gram):
                    continue
                seen.add(gram)
                out.append(gram)
                if len(out) >= limit:
                    return out
    return out[:limit]


def recall_terms(index_bundle: dict, query: str,
                 limit: int = MAX_RECALL_TERMS) -> list[str]:
    """Keep only terms that actually occur in the library, most specific first.

    A long phrase (3-4 characters) pins the exact concept; a bigram keeps recall
    wide when the exact phrase is worded differently in the library. Both are
    needed, which is why the list mixes lengths instead of taking only the
    longest grams.
    """
    cases = index_bundle["data"]["cases"]
    blobs = [(c["case_id"], str(c.get("search_blob") or "").lower()) for c in cases]
    if not blobs:
        return []
    ceiling = max(3, int(len(blobs) * 0.8))
    scored = []
    for term in core_terms(query, limit=64):
        df = sum(1 for _, blob in blobs if term in blob)
        if 0 < df <= ceiling:
            scored.append((len(term), df, term))
    long_terms = sorted([x for x in scored if x[0] >= 3],
                        key=lambda x: (-x[0], -x[1], x[2]))
    short_terms = sorted([x for x in scored if x[0] < 3],
                         key=lambda x: (-x[1], -x[0], x[2]))
    picked = [t for _, _, t in long_terms[:max(1, limit - 2)]]
    for _, _, term in short_terms:
        if len(picked) >= limit:
            break
        picked.append(term)
    return picked


def _applicability_overlap(profile: dict | None, case: dict) -> int:
    """Cheap applicability re-ranking: shared condition/boundary wording."""
    if not profile:
        return 0
    text = " ".join(list((case.get("applicability") or {}).get("conditions") or [])
                    + list((case.get("applicability") or {}).get("boundaries") or [])
                    + list(case.get("premises") or []))
    hits = 0
    for key in ("labels", "grouping", "evaluation_unit", "baseline", "boundaries",
                "decision"):
        for term in core_terms(str(profile.get(key) or ""), limit=8):
            if term and term in text:
                hits += 1
    return hits


def _case_text(case: dict) -> str:
    app = case.get("applicability") or {}
    return " ".join(list(case.get("premises") or [])
                    + list(app.get("conditions") or [])
                    + list(app.get("boundaries") or [])
                    + list(case.get("counterexamples") or [])
                    + list(case.get("transferable_lesson") or [])
                    + [str(case.get("title") or "")]).lower()


def _recall(index_bundle: dict, q: dict, query: str,
            profile: dict | None) -> tuple[list[tuple], list[str]]:
    """Union recall over core concepts, ranked by concept weight then fit.

    Weight = matched concept length x bounded occurrence, so a case that
    contains the specific phrase ("随机划分") outranks one that only shares a
    generic bigram ("数据"). Applicability wording and the profile are the
    second and third tie-breakers; the reused retriever score stays last
    because it cannot be computed when no single keyword matches.
    """
    terms = recall_terms(index_bundle, query)
    if not terms:
        return [], []
    retriever = load_retriever(index_bundle["root"])
    cases = index_bundle["data"]["cases"]
    broad = core_terms(query, limit=24)
    pool: dict[str, dict] = {}
    for term in terms:
        q2 = dict(q)
        q2["keyword"] = retriever.norm([term])
        for score, cid, comp in _score_all(retriever, index_bundle, q2):
            entry = pool.setdefault(cid, {"weight": 0, "coverage": 0,
                                          "score": 0, "compact": comp})
            entry["coverage"] += 1
            entry["weight"] += len(term)
            entry["score"] = max(entry["score"], score)
    ranked = []
    for cid, entry in pool.items():
        record = next((c for c in cases if c["case_id"] == cid), {})
        text = _case_text(record)
        fit = sum(1 for t in broad if t in text) + _applicability_overlap(profile, record)
        ranked.append((entry["weight"], entry["coverage"], fit,
                       entry["score"], cid, entry["compact"]))
    ranked.sort(key=lambda r: (-r[0], -r[1], -r[2], -r[3], r[4]))
    return [(r[3], r[4], r[5]) for r in ranked], terms


def _recall(index_bundle: dict, q: dict, query: str,
            profile: dict | None) -> tuple[list[tuple], list[str]]:
    """Union recall over core terms, ranked by coverage then applicability."""
    terms = recall_terms(index_bundle, query)
    if not terms:
        return [], []
    retriever = load_retriever(index_bundle["root"])
    by_id = {c["case_id"]: c for c in index_bundle["data"]["cases"]}
    pool: dict[str, dict] = {}
    for term in terms:
        q2 = dict(q)
        q2["keyword"] = retriever.norm([term])
        for score, cid, comp in _score_all(retriever, index_bundle, q2):
            entry = pool.setdefault(cid, {"coverage": 0, "score": 0, "compact": comp})
            entry["coverage"] += 1
            entry["score"] = max(entry["score"], score)
    ranked = []
    for cid, entry in pool.items():
        overlap = _applicability_overlap(profile, by_id.get(cid, {}))
        rank = (entry["coverage"], overlap, entry["score"])
        ranked.append((rank, cid, entry["compact"]))
    ranked.sort(key=lambda r: (-r[0][0], -r[0][1], -r[0][2], r[1]))
    return [(r[0][2], r[1], r[2]) for r in ranked], terms


def _score_all(retriever, index_bundle: dict, q: dict) -> list[tuple]:
    hits = []
    for case in index_bundle["data"]["cases"]:
        matched = retriever.score_case(case, q)
        if matched:
            hits.append((matched[0], case["case_id"], retriever.compact(case, matched)))
    hits.sort(key=lambda h: (-h[0], h[1]))
    return hits


def _filters(filters: dict | None, query: str, norm, profile: dict | None = None,
             *, keyword_source: str = "query") -> dict:
    f = dict(_profile_filters(profile))
    f.update({k: v for k, v in (filters or {}).items() if v})
    q = {}
    for key in FILTER_KEYS:
        raw = f.get(key, "")
        if isinstance(raw, str):
            raw = [x for x in re.split(r"[,，;；\s]+", raw) if x.strip()]
        q[key] = norm(raw)[:6]
    if not any(q[k] for k in FILTER_KEYS):
        # The reused retriever ANDs keyword terms, so a long natural-language
        # query would silently produce zero candidates and hide applicable
        # risk. Use ONE term. The explicit query is the operator's stated
        # intent and must not be discarded merely because a task_profile was
        # also supplied; profile wording is the secondary fallback.
        pool = profile or {}
        task_text = " ".join(str(pool.get(k, "")) for k in
                             ("decision", "mechanisms", "labels", "grouping", "boundaries"))
        query_tokens = _tokens(query)
        task_tokens = _tokens(task_text)
        order = (query_tokens, task_tokens) if keyword_source == "query" \
            else (task_tokens, query_tokens)
        picked = order[0][:1] or order[1][:1]
        q["keyword"] = norm(picked)
    return q


VISIBILITY_KEYS = ("visibility_time", "library_added_at", "as_of_visible_at")


def _timestamp(value):
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def _as_of_view(index_bundle: dict, as_of: str | None) -> tuple[dict, dict]:
    """Restrict to cases that were visibly in the library at ``as_of``.

    Default (``as_of=None``) changes nothing: real research retrieval must not
    be blocked merely because a card lacks a history field. When a caller does
    ask for strict replay, a card without a trustworthy visibility time is
    EXCLUDED rather than assumed visible -- the safe direction.
    """
    if as_of is None:
        return index_bundle, {"strict_historical_mode": False}
    if not isinstance(as_of, str):
        raise AgentError("AS_OF_INVALID", "as_of must be an ISO timestamp string")
    cutoff = _timestamp(as_of)
    if cutoff is None:
        raise AgentError("AS_OF_INVALID", "as_of requires an ISO timestamp with timezone")
    visible, unknown = [], []
    for case in index_bundle["data"]["cases"]:
        stamp = None
        for key in VISIBILITY_KEYS:
            stamp = _timestamp(case.get(key))
            if stamp is not None:
                break
        if stamp is None:
            unknown.append(case["case_id"])
        elif stamp <= cutoff:
            visible.append(case)
    data = {**index_bundle["data"], "cases": visible, "case_count": len(visible)}
    return {**index_bundle, "data": data}, {
        "strict_historical_mode": True,
        "as_of": as_of,
        "visible_cases": len(visible),
        "excluded_unknown_visibility": len(unknown),
        "excluded_unknown_case_ids": unknown[:5],
        "visibility_basis": "CASE_METADATA_VISIBILITY_TIME",
        "blocked": ("NO_CASE_IN_INDEX_CARRIES_A_VISIBILITY_TIME"
                    if unknown and not visible else None),
        "zero_hit_meaning": ("在 as_of 可见范围内未命中；不等于不存在历史证据"),
        "same_source_note": "同源案例仍只算一份独立经验，不因时间过滤而重复计数",
    }


def search(index_bundle: dict, filters: dict | None, query: str, limit: int = 5,
           profile: dict | None = None, as_of: str | None = None) -> dict:
    """Call the existing score_case/compact/divergence_note; no new ranking."""
    if type(limit) is not int or limit < 1:
        raise AgentError("LIMIT_INVALID", "limit must be a positive integer")
    index_bundle, as_of_block = _as_of_view(index_bundle, as_of)
    retriever = load_retriever(index_bundle["root"])

    def score_all(q: dict) -> list[tuple]:
        hits = []
        for c in index_bundle["data"]["cases"]:
            matched = retriever.score_case(c, q)
            if matched:
                hits.append((matched[0], c["case_id"], retriever.compact(c, matched)))
        hits.sort(key=lambda h: (-h[0], h[1]))
        return hits

    q = _filters(filters, query, retriever.norm, profile)
    scored = score_all(q)
    retrieval_mode, used_terms = "PRIMARY", []
    # A generic default query (e.g. "case transfer review") may not exist in
    # any case blob. Retry once with a declared task term so a profile-driven
    # review does not silently lose all applicable-risk candidates.
    if not scored and q.get("keyword") and profile:
        alt = _filters(filters, query, retriever.norm, profile,
                       keyword_source="profile")
        if alt.get("keyword") != q.get("keyword"):
            q = alt
            scored = score_all(q)
    if not scored:
        # Long natural-language question: the single-keyword AND path cannot
        # match it. Fall back to union recall over core concepts, then rank by
        # coverage and applicability. Declared filters (mechanism/domain/...)
        # are still applied, so an explicit "no such mechanism" stays empty.
        scored, used_terms = _recall(index_bundle, q, query, profile)
        if scored:
            retrieval_mode = "TOKEN_UNION_FALLBACK"
    cap = min(limit, MAX_CASES)
    raw_results = [h[2] for h in scored[:cap]]
    slim = []
    for r in raw_results:
        app = r["applicability"]
        slim.append({
            "case_id": r["case_id"], "title": _clip(r["title"]), "score": r["score"],
            "verdict": r["verdict"], "origin": r["origin"],
            "evidence_class": r["evidence_class"],
            "all_mechanisms": list(r["all_mechanisms"])[:6],
            "matched_mechanisms": list(r["matched_mechanisms"]),
            "matched_domains": list(r["matched_domains"]),
            "evidence_levels": list(r["evidence_levels"]),
            "premises": _cliplist(r["premises"]),
            "applicability": {
                "conditions": _cliplist(app.get("conditions", [])),
                "boundaries": _cliplist(app.get("boundaries", [])),
            },
            "counterexamples": _cliplist(r["counterexamples"]),
            "transferable_lesson": _clip(r["transferable_lesson"]),
            "next_minimal_check": _cliplist(r["next_minimal_check"]),
            "source_refs": _cliplist(r["source_refs"], 3),
            "evidence_paths": _cliplist(r["evidence_paths"], 3),
            "secondary_claims_not_admitted_count": len(r["secondary_claims_not_admitted"]),
            "scope_warning": _clip(r["scope_warning"]),
            "status": _clip(r["status"], 80),
        })
    # Hard output cap: drop the lowest-ranked cases until the JSON fits.
    while len(slim) > 1 and len(json.dumps(slim, ensure_ascii=False)) > MAX_TOTAL_CHARS:
        slim.pop()
    verification = verify_sources(index_bundle, [{"case_id": r["case_id"]} for r in slim])
    out = {
        "status": "MATCHES_FOUND" if slim else "NO_CASE_MATCH",
        "query": query, "filters": {k: v for k, v in q.items() if v},
        "total_matches": len(scored), "returned": len(slim),
        "truncated": len(scored) > len(slim),
        "results": slim,
        "applicability_divergence": retriever.divergence_note(slim, q["mechanism"]),
        "source_verification": verification,
        "warning": WARNING, "notice": NOTICE,
        "retrieval_mode": retrieval_mode,
        "recall_terms": used_terms,
        "source_independence": _source_independence(index_bundle, slim),
        "retriever": "CASE_LIBRARY/scripts/search_cases.py (score_case/compact/divergence_note reused)",
        "automatic_go_stop": False,
        "token_budget": {"max_cases": cap, "max_total_chars": MAX_TOTAL_CHARS,
                         "payload_chars": len(json.dumps(slim, ensure_ascii=False))},
    }
    # Only present in strict replay: the default path must stay byte-stable.
    if as_of_block.get("strict_historical_mode"):
        out["as_of"] = as_of_block
    return out


def _source_independence(index_bundle: dict, results: list[dict]) -> dict:
    """Flag cases that share a source: they are one piece of evidence, not two."""
    from . import case_export  # local import: case_export depends on this module
    by_id = {c["case_id"]: c for c in index_bundle["data"]["cases"]}
    ids = {}
    for r in results:
        record = by_id.get(r.get("case_id"), {})
        ids[r.get("case_id")] = set(case_export.normalise_identifiers(
            record.get("source_refs"), record.get("evidence_paths")))
    pairs = []
    ordered = [r.get("case_id") for r in results]
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            if ids.get(a) and ids.get(b) and ids[a] & ids[b]:
                pairs.append([a, b, sorted(ids[a] & ids[b])[:2]])
    return {
        "returned": len(ordered),
        "independent_units": len(ordered) - len(pairs),
        "same_source_pairs": pairs,
        "note": ("同一来源的案例只算一份独立证据；相似度不等于证据独立性。"
                 if pairs else "返回案例之间未发现共享文献标识。"),
    }


# --------------------------------------------------------------------------
# Independent case migration review (8 dimensions, never GO/STOP)
# --------------------------------------------------------------------------
def _validate_profile(profile) -> dict:
    if not isinstance(profile, dict) or not profile:
        raise AgentError("TASK_PROFILE_REQUIRED", "review requires a nonempty task_profile object")
    if len(profile) > MAX_PROFILE_FIELDS + 3:
        raise AgentError("TASK_PROFILE_TOO_LARGE", "task_profile has too many fields")
    allowed = set(DIMENSIONS) | {"decision", "mechanisms", "research_domains",
                                 "applicability_conditions", "evidence_refs", "project_id"}
    out = {}
    for key, value in profile.items():
        if not isinstance(key, str) or len(key) > 48:
            raise AgentError("TASK_PROFILE_INVALID", "Profile keys must be bounded strings")
        text = _text(value)
        if len(text) > 1200:
            raise AgentError("TASK_PROFILE_INVALID", f"{key} exceeds the bounded length")
        out[key] = text
    out["_unknown_keys"] = ",".join(sorted(set(out) - allowed))
    return out


def _case_text(case: dict) -> str:
    app = case.get("applicability", {})
    return " ".join([
        _text(case.get("title")), _text(case.get("premises")),
        _text(app.get("conditions")), _text(app.get("boundaries")),
        _text(case.get("counterexamples")), _text(case.get("next_minimal_check")),
        _text(case.get("transferable_lesson")), _text(case.get("all_mechanisms")),
    ]).casefold()


def compare_dimensions(profile: dict, case: dict) -> dict:
    """Transparent declared-text triage; equivalence is never asserted.

    IMPORTANT: keyword overlap is only a *hint*. A case counterexample that
    says "premise does not hold IF X" must NOT be read as a contradiction of a
    task that does not assert X. Automatic contradiction requires an explicit
    version/scope exclusion, never shared keywords alone.
    """
    task_all = " ".join(v for k, v in profile.items() if not k.startswith("_"))
    case_all = _case_text(case)
    comparisons = {}
    for dim in DIMENSIONS:
        keywords = DIMENSION_KEYWORDS[dim]
        declared = profile.get(dim, "") or (profile.get("research_domains", "")
                                            if dim == "mechanisms" else "")
        if not declared.strip():
            comparisons[dim] = {"status": "UNDECLARED", "shared_keywords": [],
                                "method": "NONE_TASK_DID_NOT_DECLARE"}
            continue
        # Use the DIMENSION'S OWN declared text, not the whole profile, so a
        # generic word in another dimension cannot manufacture a match.
        declared_cf = declared.casefold()
        task_hits = sorted({k for k in keywords if k.casefold() in declared_cf})
        case_hits = sorted({k for k in keywords if k.casefold() in case_all})
        shared = sorted(set(task_hits) & set(case_hits))
        status = ("TEXT_OVERLAP_SIMILARITY_ONLY" if shared else
                  "NO_TEXT_OVERLAP" if case_hits else "NOT_IN_CASE")
        comparisons[dim] = {"status": status, "shared": shared[:4]}
    return comparisons


def explicit_scope_conflicts(profile: dict, case: dict) -> list[str]:
    """Only explicit v1/v2 (or similarly declared scope) mismatches count.

    Example: case EXT-X6B boundary says "only v1, must not generalise to v2"
    while the task declares ESM v2 -> CONDITIONS_DIFFER. Shared keywords alone
    never produce a contradiction verdict.
    """
    task_all = " ".join(v for k, v in profile.items() if not k.startswith("_"))
    boundary = " ".join([_text(case.get("applicability", {}).get("boundaries")),
                         _text(case.get("counterexamples"))])
    declared = {m.casefold() for m in VERSION_PATTERN.findall(task_all)}
    if not declared:
        return []
    conflicts = []
    # A version mentioned inside an EXCLUSION clause is a different signal
    # from a version merely mentioned in a neutral boundary. Only the former
    # establishes "the task's version is outside this case's scope".
    for clause in re.split(r"[。；;！!？?\n]", boundary):
        low = clause.casefold()
        if not any(m.casefold() in low for m in EXCLUSION_MARKERS):
            continue
        hit = declared & {m.casefold() for m in VERSION_PATTERN.findall(clause)}
        if hit:
            conflicts.append("DECLARED_VERSION_EXPLICITLY_EXCLUDED:" + ",".join(sorted(hit)))
    return list(dict.fromkeys(conflicts))[:2]


def classify_transfer(comparisons: dict, grade: str, mechanism_matched: bool,
                      scope_conflicts: list[str]) -> tuple[str, list[str]]:
    reasons = []
    # An explicit scope exclusion is the most actionable signal for preventing
    # a v1->v2 misapplication, so it outranks a weak evidence grade (which is
    # still reported alongside it).
    if scope_conflicts:
        return "CONDITIONS_DIFFER", scope_conflicts + ["EVIDENCE_GRADE_ALSO_LIMITED:" + grade]
    if "UNVERIFIED" in grade or "STALE" in grade or "REVIEW_REQUIRED" in grade \
            or "NON_DECISION" in grade or "ABSTRACT" in grade or "LIMITATION" in grade \
            or "NON_PEER_REVIEWED" in grade.upper():
        return "EVIDENCE_INSUFFICIENT", ["EVIDENCE_GRADE_NOT_DECISION_GRADE: " + grade]
    core_bad = [d for d in CORE_DIMENSIONS
                if comparisons[d]["status"] in {"NO_TEXT_OVERLAP", "NOT_IN_CASE"}]
    undeclared = [d for d in CORE_DIMENSIONS if comparisons[d]["status"] == "UNDECLARED"]
    if not mechanism_matched:
        reasons.append("NO_MECHANISM_TAG_INTERSECTION")
    if core_bad:
        reasons.append("CORE_PREMISE_NOT_COVERED:" + ",".join(core_bad))
    if undeclared:
        reasons.append("CORE_DIMENSION_NOT_DECLARED_BY_TASK:" + ",".join(undeclared))
    if core_bad or undeclared or not mechanism_matched:
        return "APPLICABILITY_RISK", reasons
    return "USEFUL_ANALOGY", ["MECHANISM_MATCH_AND_DECLARED_CORE_DIMENSIONS_OVERLAP"]


def review(task_profile: dict, search_result: dict, filters: dict | None) -> dict:
    """Independent migration review; outputs risk/different/analogy/insufficient."""
    profile = _validate_profile(task_profile)
    req_mechs = {x.strip().casefold() for x in re.split(r"[,，;；\s]+", profile.get("mechanisms", "")) if x.strip()}
    source = search_result.get("source_verification", {}).get("per_case", {})
    items = []
    for case in search_result.get("results", []):
        cid = case["case_id"]
        grade = source.get(cid, {}).get("evidence_grade", "UNVERIFIED")
        matched = bool(case.get("matched_mechanisms")) or bool(
            req_mechs & {m.casefold() for m in case.get("all_mechanisms", [])})
        comparisons = compare_dimensions(profile, case)
        conflicts = explicit_scope_conflicts(profile, case)
        classification, reasons = classify_transfer(comparisons, grade, matched, conflicts)
        items.append({
            "case_id": cid, "verdict": case["verdict"],
            "evidence_class": case["evidence_class"],
            "evidence_grade": grade,
            "mechanism_matched": matched,
            "classification": classification,
            "reasons": reasons,
            "explicit_scope_conflicts": conflicts,
            "dimension_comparison": comparisons,
            # Boundaries/counterexamples stay next to the applicability verdict;
            # premises and evidence paths are NOT duplicated here (they are in
            # cases.results under the same case_id) so more cases fit the cap.
            "case_boundaries": case["applicability"]["boundaries"],
            "case_counterexamples": case["counterexamples"],
            "case_details_at": "case_library.cases.results[case_id=" + cid + "]",
        })
    payload = json.dumps(items, ensure_ascii=False)
    while len(items) > 1 and len(payload) > MAX_TOTAL_CHARS:
        items.pop()
        payload = json.dumps(items, ensure_ascii=False)
    counts = {}
    for x in items:
        counts[x["classification"]] = counts.get(x["classification"], 0) + 1
    return {
        "status": "ADVISORY_REVIEW_ONLY",
        "task_profile_declared_fields": sorted(k for k in profile if not k.startswith("_")),
        "unknown_profile_keys": profile.get("_unknown_keys", ""),
        "reviewed": len(items), "classification_counts": counts,
        "comparisons": items,
        "applicability_divergence": search_result.get("applicability_divergence"),
        "dimension_list": list(DIMENSIONS),
        "comparison_method": "DECLARED_TEXT_KEYWORD_TRIAGE_ONLY",
        "keyword_similarity_is_not_premise_equivalence": True,
        "scientific_equivalence_verified": False,
        "original_run_verified": False,
        "decision_authority": "PD-RW_WORKFLOW_ONLY",
        "automatic_go_stop": False,
        "warning": WARNING, "notice": NOTICE,
        "token_budget": {"payload_chars": len(payload), "max_total_chars": MAX_TOTAL_CHARS},
    }


# --------------------------------------------------------------------------
# Evidence tiers + negative warnings / success transfer
# --------------------------------------------------------------------------
def evidence_tier(info: dict) -> tuple[str, list[str]]:
    """Classify a case's evidence WITHOUT silently discarding weak successes.

    DECISION_GRADE     -> may enter the decision brief as a sourced experience.
    EXPLORATORY_LEAD   -> preprint / internal report / abstract-only: an
                          explicitly labelled clue only, NEVER an independently
                          confirmed scientific conclusion.
    CANDIDATE_ONLY     -> missing card, stale index, secondary/speculative or
                          undeclared source: retained but not used as a brief.
    """
    grade = str(info.get("evidence_grade", "UNVERIFIED"))
    levels = set(info.get("evidence_levels") or [])
    caveats = list(info.get("caveats") or [])
    if "INDEX_STALE" in grade or "UNVERIFIED_CARD" in grade or "MISSING" in grade:
        return "CANDIDATE_ONLY", caveats + ["SOURCE_CARD_OR_INDEX_NOT_VERIFIED"]
    if levels & {"SECONDARY_ONLY", "NOT_ACCESSED", "SPECULATION", "UNVERIFIED_REPORT"}:
        return "CANDIDATE_ONLY", caveats + ["SECONDARY_OR_UNVERIFIED_SOURCE_NOT_ADMITTED"]
    if grade == "DECISION_GRADE":
        return "DECISION_GRADE", caveats
    if (grade.startswith("DECISION_GRADE") or "ABSTRACT" in grade or
            "LIMITATION" in grade or "NON_DECISION_GRADE" in grade or
            "REVIEW_REQUIRED" in grade or "INTERNAL_REPORT" in levels or
            "PREPRINT" in grade.upper() or "PAPER_LIMITATION" in levels):
        return "EXPLORATORY_LEAD", caveats + [
            "EXPLORATORY_LEAD_ONLY_NOT_INDEPENDENTLY_CONFIRMED"]
    return "CANDIDATE_ONLY", caveats + ["EVIDENCE_GRADE_NOT_ADMITTED:" + grade]


def _success_transfer_detail(case: dict, profile: dict | None,
                             comparison: dict | None) -> dict:
    """Success conditions, task agreement/differences and minimal validation."""
    app = case.get("applicability") or {}
    conditions = _cliplist(app.get("conditions"), 2, 150)
    boundaries = _cliplist(app.get("boundaries"), 2, 150)
    dims = (comparison or {}).get("dimension_comparison") or {}
    matching = sorted(d for d, v in dims.items()
                      if v.get("status") == "TEXT_OVERLAP_SIMILARITY_ONLY")
    differing = sorted(d for d, v in dims.items()
                       if v.get("status") in {"NO_TEXT_OVERLAP", "NOT_IN_CASE", "UNDECLARED"})
    task_premises = {k: _clip(profile.get(k, ""), 140)
                     for k in ("legal_inputs", "grouping", "evaluation_unit", "baseline")
                     if isinstance(profile, dict) and profile.get(k)}
    check = (case.get("next_minimal_check") or ["核对成功条件是否在当前任务成立"])[0]
    return {
        "success_key_conditions": (conditions + boundaries)[:3],
        "conditions_matching_current_task": matching[:4],
        "conditions_differing_from_current_task": differing[:4],
        "current_task_premises": task_premises,
        "transferable_mechanism": _clip(
            f"{','.join(case['matched_mechanisms'] or case['all_mechanisms'][:2])}: "
            f"{case.get('transferable_lesson', '')}", 220),
        "minimal_validation_experiment": _clip(
            f"在本任务条件下成对复现「{check}」，并核对 "
            f"{','.join(boundaries[:1]) or '案例适用边界'} 是否成立", 220),
        "condition_comparison_method": "DECLARED_TEXT_TRIAGE_NOT_EQUIVALENCE_VERIFIED",
    }


def _source_groups(pairs: list) -> dict[str, str]:
    """Union same-source case IDs; the group label is the smallest member.

    Two cards describing the same paper or the same Run are one independent
    experience. Grouping does not merge their content or drop either card.
    """
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for pair in pairs:
        if not isinstance(pair, (list, tuple)) or len(pair) < 2:
            continue
        a, b = str(pair[0]), str(pair[1])
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    return {node: find(node) for node in parent}


def decision_brief(search_result: dict, review_result: dict | None,
                   max_experiences: int = 5,
                   task_profile: dict | None = None) -> dict:
    if type(max_experiences) is not int or max_experiences < 1:
        raise AgentError("EXPERIENCE_LIMIT_INVALID", "max_experiences must be a positive integer")
    cap = min(max_experiences, MAX_CASES)
    source = search_result.get("source_verification", {}).get("per_case", {})
    reviews = {x["case_id"]: x
               for x in (review_result or {}).get("comparisons", [])}
    negatives, successes, candidates_only = [], [], []
    for case in search_result.get("results", []):
        cid = case["case_id"]
        info = source.get(cid, {})
        grade = info.get("evidence_grade", "UNVERIFIED")
        roles = set(info.get("role_classes", []))
        v = case["verdict"]
        # An INVALID case records a broken measurement, not a failed mechanism.
        # Treating it as a negative warning would turn an execution defect into
        # scientific evidence against the next direction.
        if str(v).upper() == "INVALID":
            candidates_only.append({
                "case_id": cid,
                "reason": "CASE_VERDICT_INVALID_NOT_A_SCIENTIFIC_NEGATIVE",
                "retained_as": "CANDIDATE_ONLY_NOT_DECISION_INPUT"})
            continue
        # A case with explicitly different declared conditions must not be
        # transferred as an active negative warning against a new direction.
        if reviews.get(cid, {}).get("classification") == "CONDITIONS_DIFFER":
            candidates_only.append({"case_id": cid,
                                    "reason": "DECLARED_CONDITIONS_DIFFER_NOT_TRANSFERRED",
                                    "retained_as": "CANDIDATE_ONLY_NOT_DECISION_INPUT"})
            continue
        tier, tier_caveats = evidence_tier(info)
        opinion_only = bool(roles) and roles <= {"OPINION_OR_REVIEW", "UNVERIFIED_SECONDARY",
                                                 "ROLE_UNDECLARED"}
        if tier == "CANDIDATE_ONLY":
            candidates_only.append({"case_id": cid, "reason": "EVIDENCE_GRADE=" + grade,
                                    "retained_as": "CANDIDATE_ONLY_NOT_DECISION_INPUT"})
            continue
        if opinion_only:
            candidates_only.append({"case_id": cid,
                                    "reason": "ROLE_CLASSES=" + ",".join(sorted(roles)),
                                    "retained_as": "CONTEXT_ONLY_NOT_ORIGINAL_EMPIRICAL_RESULT"})
            continue
        polarity = ("NEGATIVE_WARNING" if v in {"FAILURE", "INVALID", "MIXED"}
                    else "SUCCESS_TRANSFER" if v in {"SUCCESS"} or
                    case["evidence_class"] in {"VERIFIED_SUCCESS", "REPAIR_PROTOCOL"}
                    else "MIXED_CAUTION")
        check = (case["next_minimal_check"] or ["核对原始 Run 与适用条件"])[0]
        item = {
            "case_id": cid, "polarity": polarity, "verdict": v,
            "mechanism_match": case["matched_mechanisms"] or case["all_mechanisms"][:3],
            "evidence_grade": grade,
            "evidence_tier": tier,
            "exploratory_lead_only": tier == "EXPLORATORY_LEAD",
            "independent_confirmation": ("NOT_ESTABLISHED" if tier == "EXPLORATORY_LEAD"
                                         else "SOURCE_VERIFIED_NOT_SCIENTIFIC_PROOF"),
            "role_classes": sorted(roles),
            "caveats": tier_caveats,
            "transfer_classification": reviews.get(cid, {}).get("classification",
                                                                "NOT_REVIEWED"),
            "concrete_impact": _clip(
                f"{polarity} · {cid}: 在前提「{(case['premises'] or ['未声明'])[0]}」下"
                f"该案例为 {v}；本次决策应执行「{check}」。", 300),
            "risk_if_ignored": _clip((case["counterexamples"] or
                                      ["适用边界未逐条核对，可能重复既有失败前提"])[0]),
            "impact_source": "DERIVED_FROM_CASE_CARD_FIELDS",
            "not_a_scientific_conclusion": True,
            "verification_required": True,
            "evidence_paths": case["evidence_paths"][:2],
        }
        if polarity == "SUCCESS_TRANSFER":
            item["success_transfer"] = _success_transfer_detail(
                case, task_profile, reviews.get(cid))
        (negatives if polarity == "NEGATIVE_WARNING" else
         successes if polarity == "SUCCESS_TRANSFER" else negatives).append(item)
    # Guarantee both polarities are represented when available, <= cap total.
    picked: list[dict] = []
    seen: set[str] = set()

    def take(item) -> bool:
        if item["case_id"] in seen:
            return False
        seen.add(item["case_id"])
        picked.append(item)
        return True

    for pool in (negatives, successes):
        if pool and len(picked) < cap:
            take(pool.pop(0))
    while (negatives or successes) and len(picked) < cap:
        if negatives:
            take(negatives.pop(0))
        if successes and len(picked) < cap:
            take(successes.pop(0))
    # Same paper / same Run / aggregate cards are ONE independent experience.
    # Both cards stay visible; only the independence count is deduplicated.
    # The annotation is only emitted when a shared source actually exists, so
    # the common single-source payload pays no extra bytes.
    groups = _source_groups((search_result.get("source_independence") or {}).get(
        "same_source_pairs") or [])
    if groups:
        seen_groups: set[str] = set()
        for item in picked:
            group = groups.get(item["case_id"], item["case_id"])
            item["source_group_id"] = group
            item["independent_evidence_unit"] = group not in seen_groups
            seen_groups.add(group)
    brief = {
        "status": "DECISION_EXPERIENCES_ONLY",
        "returned": len(picked),
        "negative_warning_count": sum(1 for x in picked if x["polarity"] == "NEGATIVE_WARNING"),
        "success_transfer_count": sum(1 for x in picked if x["polarity"] == "SUCCESS_TRANSFER"),
        "exploratory_lead_count": sum(1 for x in picked if x["exploratory_lead_only"]),
        "experiences": picked[:cap],
        "candidates_only_not_admitted": candidates_only[:3],
        "candidate_policy": ("Secondary/unverified/speculative cases stay candidates. "
                             "Preprints, internal reports and abstract-only sources enter only "
                             "as EXPLICITLY LABELLED exploratory leads, never as independently "
                             "confirmed scientific conclusions."),
        "automatic_go_stop": False,
        "warning": WARNING, "notice": NOTICE,
    }
    if groups:
        # Only paid for when a shared source exists; absence means every
        # returned case is its own independent unit.
        brief["independent_source_units"] = len(
            {groups.get(x["case_id"], x["case_id"]) for x in picked})
        brief["same_source_deduplicated"] = True
    return brief


# --------------------------------------------------------------------------
# Compact-by-default advisory (full evidence stays on demand)
# --------------------------------------------------------------------------
def compact_for_search(out: dict) -> dict:
    """Drop duplicated nested metadata and raw 8-dimension dumps.

    This does NOT change the single case source: the full 8-dimension review
    is still produced by ``review_case_transfer`` and the full payload by
    ``case_gate_check(detail='full')``. It only removes copies that made the
    default advisory too large to retain a coherent five-case set.
    """
    for section in (out.get("cases"), out.get("case_review"),
                    out.get("decision_experiences")):
        if isinstance(section, dict):
            for redundant in ("warning", "notice", "automatic_go_stop"):
                section.pop(redundant, None)
    rev = out.get("case_review")
    if isinstance(rev, dict):
        for c in rev.get("comparisons", []):
            dims = c.pop("dimension_comparison", None) or {}
            c["dimension_status"] = {d: v.get("status") for d, v in dims.items()}
            c.pop("case_boundaries", None)
            c.pop("case_counterexamples", None)
            c["full_evidence_at"] = ("case_library.cases.results | "
                                     "review_case_transfer.comparisons")
    out["compact_by_default"] = True
    out["full_evidence_at"] = ["review_case_transfer",
                               "case_gate_check(detail='full')"]
    return out


# --------------------------------------------------------------------------
# Service-level wrappers with bounded in-process dedup (no second memory store)
# --------------------------------------------------------------------------
def _retain(out: dict, k: int) -> dict:
    """Deep-copy the payload restricted to the first k RANKED case IDs.

    Every section is filtered by the same retained set, so a truncated payload
    can never cite an experience/review/source-verification entry whose case
    details were dropped. Counters are recomputed from the retained items.
    """
    o = copy.deepcopy(out)
    cases = o.get("cases") or {}
    results = cases.get("results") or []
    original_n = len(results)
    kept = results[:max(1, k)]
    ids = {r["case_id"] for r in kept}
    cases["results"] = kept
    cases["returned"] = len(kept)
    cases["truncated"] = bool(cases.get("total_matches", len(kept)) > len(kept)) \
        or len(kept) < original_n
    cases["token_budget"] = {
        "max_cases": MAX_CASES, "max_total_chars": MAX_TOTAL_CHARS,
        "payload_chars": len(json.dumps(kept, ensure_ascii=False))}
    sv = cases.get("source_verification") or {}
    if isinstance(sv.get("per_case"), dict):
        sv["per_case"] = {cid: v for cid, v in sv["per_case"].items() if cid in ids}
    rev = o.get("case_review")
    if isinstance(rev, dict):
        comps = [c for c in rev.get("comparisons", []) if c.get("case_id") in ids]
        rev["comparisons"] = comps
        rev["reviewed"] = len(comps)
        counts: dict[str, int] = {}
        for c in comps:
            counts[c["classification"]] = counts.get(c["classification"], 0) + 1
        rev["classification_counts"] = counts
        rev["token_budget"] = {
            "payload_chars": len(json.dumps(comps, ensure_ascii=False)),
            "max_total_chars": MAX_TOTAL_CHARS}
    brief = o.get("decision_experiences")
    if isinstance(brief, dict):
        exps = [e for e in brief.get("experiences", []) if e.get("case_id") in ids]
        brief["experiences"] = exps
        brief["returned"] = len(exps)
        brief["negative_warning_count"] = sum(
            1 for e in exps if e["polarity"] == "NEGATIVE_WARNING")
        brief["success_transfer_count"] = sum(
            1 for e in exps if e["polarity"] == "SUCCESS_TRANSFER")
        brief["exploratory_lead_count"] = sum(
            1 for e in exps if e.get("exploratory_lead_only"))
        if brief.get("same_source_deduplicated"):
            brief["independent_source_units"] = len({
                e.get("source_group_id", e.get("case_id")) for e in exps})
        brief["candidates_only_not_admitted"] = [
            c for c in brief.get("candidates_only_not_admitted", [])
            if c.get("case_id") in ids][:3]
    return o


def _cap_total(out: dict, cap: int = MAX_TOTAL_CHARS) -> dict:
    """Bound the WHOLE advisory payload with ONE coherent retained case set."""
    def size(obj) -> int:
        return len(json.dumps(obj, ensure_ascii=False))

    n = len((out.get("cases") or {}).get("results") or [])
    if size(out) <= cap:
        out["output_truncated"] = False
        out["retained_case_ids"] = [r["case_id"] for r in out["cases"]["results"]]
        out["token_budget"] = {"max_total_chars": cap, "payload_chars": size(out),
                               "retained_cases": n, "cases_before_truncation": n,
                               "output_truncated": False}
        return out
    # Find the largest k whose FULL, internally consistent payload still fits.
    chosen = (1, _retain(out, 1))
    for k in range(n, 0, -1):
        cand = _retain(out, k)
        if size(cand) <= cap - 250:  # room for the truncation metadata below
            chosen = (k, cand)
            break
    k, result = chosen
    result["output_truncated"] = k < n
    result["retained_case_ids"] = [r["case_id"] for r in result["cases"]["results"]]
    result["token_budget"] = {"max_total_chars": cap,
                              "payload_chars": size(result),
                              "retained_cases": k, "cases_before_truncation": n,
                              "output_truncated": k < n}
    # The metadata itself slightly changes the size; report the true final size.
    result["token_budget"]["payload_chars"] = size(result)
    return result


def _fingerprint(name: str, payload: dict, sha: str) -> str:
    canonical = json.dumps({"tool": name, "args": payload, "index_sha256": sha},
                           ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _cached(name: str, payload: dict, sha: str, producer):
    key = _fingerprint(name, payload, sha)
    if key in _RESULT_CACHE:
        _RESULT_CACHE.move_to_end(key)
        out = dict(_RESULT_CACHE[key])
        out["cache_hit"] = True
        out["query_fingerprint"] = key
        return out
    out = producer()
    out["cache_hit"] = False
    out["query_fingerprint"] = key
    _RESULT_CACHE[key] = {k: v for k, v in out.items() if k not in {"cache_hit", "query_fingerprint"}}
    while len(_RESULT_CACHE) > CACHE_SIZE:
        _RESULT_CACHE.popitem(last=False)
    return out


def case_search(settings, query: str, filters: dict | None, limit: int = 5,
                task_profile: dict | None = None, max_experiences: int = 5,
                *, index_override: dict | None = None,
                as_of: str | None = None) -> dict:
    if not isinstance(query, str) or len(query.strip()) < 2:
        raise AgentError("QUERY_REQUIRED", "Use a query of at least two characters")
    root = resolve_root(settings)
    if root is None:
        return {"status": "CASE_LIBRARY_NOT_CONFIGURED",
                "detail": "Set PDRW_CASE_LIBRARY_ROOT or case_library_root in the private project map.",
                "legacy_memory_still_available": True,
                "automatic_go_stop": False}
    bundle = index_override or load_index(root)
    validated_profile = _validate_profile(task_profile) if task_profile else None
    payload = {"query": query, "filters": filters or {}, "limit": limit,
               "profile": validated_profile, "max_experiences": max_experiences,
               "as_of": as_of,
               # A stale index must not reuse a previously "source_verified"
               # advisory even though index.json's sha256 is unchanged.
               "index_stale": bool(bundle["index_stale"])}

    def produce():
        found = search(bundle, filters, query, limit, profile=validated_profile,
                       as_of=as_of)
        rev = review(task_profile, found, filters) if task_profile else None
        # The success-transfer detail needs the DECLARED current-task premises;
        # without them only a placeholder could be produced.
        brief = decision_brief(found, rev, max_experiences,
                               task_profile=validated_profile)
        out = {"status": found["status"], "case_learning_version": CASE_LEARNING_VERSION,
               "cases": found, "case_review": rev,
               "decision_experiences": brief,
               "source_verified": not found["source_verification"]["index_stale"],
               "index_stale": bool(found["source_verification"]["index_stale"]),
               "warning": WARNING, "notice": NOTICE,
               "automatic_go_stop": False}
        if found.get("as_of"):
            out["as_of"] = found["as_of"]
        return _cap_total(compact_for_search(out))

    return _cached("case_search", payload, bundle["sha256"], produce)


def case_transfer_review(settings, task_profile: dict, filters: dict | None = None,
                         query: str = "case transfer review", limit: int = 5,
                         *, index_override: dict | None = None) -> dict:
    root = resolve_root(settings)
    if root is None:
        return {"status": "CASE_LIBRARY_NOT_CONFIGURED", "automatic_go_stop": False}
    bundle = index_override or load_index(root)
    validated = _validate_profile(task_profile)
    payload = {"profile": validated, "filters": filters or {}, "limit": limit, "query": query}

    def produce():
        found = search(bundle, filters, query, limit, profile=validated)
        return {"status": "ADVISORY_REVIEW_ONLY",
                "case_learning_version": CASE_LEARNING_VERSION,
                "case_review": review(task_profile, found, filters),
                "source_verification": found["source_verification"],
                "warning": WARNING, "notice": NOTICE,
                "automatic_go_stop": False}
    return _cached("case_transfer_review", payload, bundle["sha256"], produce)


def extract_candidates(settings, project_id: str, observations: list,
                       evidence_root: str | None = None,
                       evidence_manifest: dict | None = None) -> dict:
    """Candidate experience extraction from the ORIGINAL Run + existing science audit.

    Reuses compile_declared_lessons() and bind_source_refs() verbatim. Produces
    CANDIDATES_ONLY; never writes CASE_LIBRARY/STATE/Run/EVENTS.
    """
    if not isinstance(project_id, str) or not project_id.strip():
        raise AgentError("PROJECT_ID_REQUIRED", "A registered project id is required")
    if not isinstance(observations, list) or not 1 <= len(observations) <= 20:
        raise AgentError("OBSERVATIONS_INVALID", "1..20 declared observations are required")
    from .evidence import find_experiment_evidence
    from .science.lessons import compile_declared_lessons
    from .science.provenance import bind_source_refs

    run_evidence = find_experiment_evidence(settings, project_id=project_id, limit=6)
    refs = [r for o in observations if isinstance(o, dict)
            for r in (o.get("evidence_refs") or []) if isinstance(r, str)]
    packet = {"observations": [
        {k: o[k] for k in ("run_id", "outcome", "evidence_refs", "tested_premise_id", "scope")
         if isinstance(o, dict) and k in o}
        for o in observations]}
    try:
        audited = compile_declared_lessons(packet)
    except AgentError as exc:
        return {"status": "CANDIDATE_EXTRACTION_FAILED", "error_code": exc.code,
                "detail": str(exc)[:200], "no_writes": True}
    binding = {"status": "NOT_CHECKED"}
    if evidence_root and evidence_manifest is not None:
        try:
            binding = bind_source_refs(Path(evidence_root).expanduser().resolve(),
                                       evidence_manifest, refs)
        except (AgentError, OSError, ValueError) as exc:
            binding = {"status": "BINDING_FAILED", "detail": str(exc)[:160]}
    candidates = []
    for item in audited.get("items", []):
        candidates.append({
            "candidate_id": "CAND-" + hashlib.sha256(
                (project_id + str(item.get("run_id"))).encode("utf-8")).hexdigest()[:10],
            "run_id": item.get("run_id"),
            "outcome_declared": item.get("outcome_declared"),
            "declared_premise_fingerprint_sha256": item.get("declared_premise_fingerprint_sha256"),
            "evidence_refs": item.get("evidence_refs", [])[:4],
            "verification": "NOT_INDEPENDENTLY_VERIFIED",
            "source_verified": item.get("source_verified", False),
            "negative_scientific_evidence": item.get("negative_scientific_evidence", False),
            "scientific_equivalence_verified": False,
            "promoted_to_formal_case": False,
            "science_record_written": False,
            "state_or_run_modified": False,
            "requires": "OPERATOR_REVIEW_AGAINST_ORIGINAL_RUN_AND_AUDIT_BEFORE_ANY_PROMOTION",
        })
    return {
        "status": "CANDIDATE_EXPERIENCES_ONLY",
        "project_id": project_id,
        "original_run_evidence_status": run_evidence.get("status"),
        "original_run_evidence_matches": len(run_evidence.get("matches", [])),
        "audit_status": audited.get("status"),
        "audit_negative_candidates": len(audited.get("candidate_prior_negative_lessons", [])),
        "source_binding": binding,
        "candidates": candidates,
        "no_writes": True,
        "case_library_modified": False,
        "formal_case_promotion": "FORBIDDEN_WITHOUT_INDEPENDENT_VERIFICATION_AND_EXPLICIT_AUTHORIZATION",
        "automatic_go_stop": False,
        "notice": "Declared outcomes only; an engineering failure or declared negative is NOT an independently verified scientific conclusion.",
    }
