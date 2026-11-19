"""Deterministic, read-only Markdown export of one already-indexed case.

Scope of this module: the *interface and data mapping* only. It renders an
existing index record into a standalone Markdown experience card. It performs
no GitHub sync, no upload and no write to CASE_LIBRARY, STATE, Run or EVENTS.
A later stage may feed the same record shape from a local SQLite row.

v1.1 (WP6-A) adds the knowledge-mirror schema (`KNOWLEDGE_SCHEMA_VERSION`),
which is a *superset* of the v1 card: the original `render_markdown_card`
contract is unchanged, and every added field is an explicit mapping of an
existing source field or an explicitly-labelled routing heuristic. Nothing in
this module invents a scientific fact; unknown inputs stay `UNKNOWN`.
"""
from __future__ import annotations

import hashlib
import json
import re

from .schemas import AgentError
from . import case_learning

EXPORT_VERSION = "1.0"
# Stable, machine-readable card contract. Adding a field is a version bump.
FRONT_FIELDS = ("case_id", "title", "verdict", "status", "origin",
                "evidence_class", "evidence_levels", "research_domains",
                "mechanisms", "related_cases", "export_version")
BODY_SECTIONS = ("premises", "applicability.conditions",
                 "applicability.boundaries", "counterexamples",
                 "transferable_lesson", "next_minimal_check", "success_notes")


def _canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _as_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [str(v).strip() for v in value if str(v).strip()]
    return [str(value)]


def _field(record: dict, path: str) -> list[str]:
    node = record
    for part in path.split("."):
        node = (node or {}).get(part) if isinstance(node, dict) else None
    return _as_list(node)


def read_case(settings, case_id: str) -> dict:
    """Load one indexed case without modifying the library."""
    if not isinstance(case_id, str) or not case_id.strip():
        raise AgentError("CASE_ID_REQUIRED", "case_id must be nonempty text")
    root = case_learning.resolve_root(settings)
    if not root:
        raise AgentError("CASE_LIBRARY_NOT_CONFIGURED",
                         "Set PDRW_CASE_LIBRARY_ROOT or case_library_root")
    bundle = case_learning.load_index(root)
    for record in bundle["data"]["cases"]:
        if record.get("case_id") == case_id.strip():
            return {"record": record, "lib_sha256": bundle["sha256"],
                    "index_stale": bundle["index_stale"],
                    "root": str(root)}
    raise AgentError("CASE_NOT_FOUND", "Case ID not present in the index")

def render_markdown_card(record: dict, lib_sha256: str) -> dict:
    """Render a stable card. Same input -> byte-identical output."""
    front = {k: record.get(k) for k in FRONT_FIELDS if k != "export_version"}
    front["query_fingerprint_sha256"] = _sha256(
        _canonical({"case_id": record.get("case_id"),
                    "library_sha256": lib_sha256}))
    front["export_version"] = EXPORT_VERSION
    front["library_index_sha256"] = lib_sha256
    front["evidence_paths"] = _as_list(record.get("evidence_paths"))
    front["source_refs"] = _as_list(record.get("source_refs"))[:8]
    front["scientific_equivalence_verified"] = False
    front["authorization_granted"] = False

    lines = [f"# {record.get('case_id')} · {record.get('title') or 'untitled'}",
             "",
             f"- 结论类型：`{record.get('verdict')}`｜状态：`{record.get('status')}`"
             f"｜来源：`{record.get('origin')}`",
             f"- 证据类别：`{record.get('evidence_class')}`"
             f"｜证据等级：{', '.join(_as_list(record.get('evidence_levels'))) or 'UNKNOWN'}",
             f"- 研究域：{', '.join(_as_list(record.get('research_domains'))) or 'UNKNOWN'}",
             f"- 机制：{', '.join(_as_list(record.get('mechanisms'))) or 'UNKNOWN'}"]
    scope_warning = str(record.get("scope_warning") or "").strip()
    if scope_warning:
        lines.append(f"- 适用范围警告：{scope_warning}")

    labels = {"premises": "前提", "applicability.conditions": "适用条件",
              "applicability.boundaries": "适用边界",
              "counterexamples": "反例", "transferable_lesson": "可迁移经验",
              "next_minimal_check": "最小验证", "success_notes": "成功条件"}
    for section in BODY_SECTIONS:
        values = _field(record, section)
        if not values:
            continue
        lines += ["", f"## {labels[section]}"]
        if section == "transferable_lesson":
            lines.append(values[0])
        else:
            lines += [f"- {v}" for v in values]

    related = _as_list(record.get("related_cases"))
    if related:
        lines += ["", "## 相关案例", ", ".join(related)]

    lines += ["", "---",
              "本卡片由只读渲染器生成：检索结果是候选证据，不是已证实结论；",
              "复用前须核对原始 Run 与本文适用边界；本文件不授予任何权限。"]
    body = "\n".join(lines) + "\n"
    markdown = ("---json\n" + json.dumps(front, ensure_ascii=False,
                                         sort_keys=True, indent=1) + "\n---\n\n" + body)
    return {"markdown": markdown, "sha256": _sha256(markdown),
            "body_sha256": _sha256(body), "front_matter": front}


def export_case_markdown(settings, case_id: str) -> dict:
    """Read-only export result; nothing is written to disk by this call."""
    loaded = read_case(settings, case_id)
    rendered = render_markdown_card(loaded["record"], loaded["lib_sha256"])
    return {
        "status": "MARKDOWN_CARD_RENDERED_NOT_WRITTEN",
        "export_version": EXPORT_VERSION,
        "case_id": loaded["record"].get("case_id"),
        "markdown": rendered["markdown"],
        "sha256": rendered["sha256"],
        "body_sha256": rendered["body_sha256"],
        "front_matter": rendered["front_matter"],
        "source": {"library_root": loaded["root"],
                   "library_index_sha256": loaded["lib_sha256"],
                   "index_stale": loaded["index_stale"],
                   "evidence_paths": _as_list(loaded["record"].get("evidence_paths"))},
        "no_writes": True,
        "sync_performed": False,
        "authorization_granted": False,
    }


# ==========================================================================
# Knowledge mirror schema v1 (WP6-A)
#
# Everything below is a pure mapping of an existing field, an explicitly
# labelled routing heuristic, or `UNKNOWN`. No scientific fact is inferred.
# ==========================================================================
KNOWLEDGE_SCHEMA_VERSION = "1.0"
KNOWLEDGE_CARD_FORMAT = "pdrw-case-card-v2"
MAX_CLAIM_CHARS = 800
MAX_SOURCE_CHARS = 220

# Field order is the published contract; adding a field is a schema bump.
KNOWLEDGE_FIELDS = (
    "schema_version", "format", "case_id", "title",
    "source_type", "source_group_id", "source_ids", "same_source_cases",
    "domains", "h_stages", "h_stages_basis", "problem_tags",
    "outcome", "status", "status_class", "status_flags",
    "evidence_class", "evidence_grade", "evidence_level",
    "source_refs", "research_problem", "research_problem_basis",
    "premises", "conditions", "boundaries", "counterexamples",
    "results", "transferable_lesson", "next_minimal_check", "success_notes",
    "related_cases", "scope_warning",
    "updated_at", "source_digest", "source_card_sha256", "source_card_path",
    "card_path", "publishable", "publish_blockers",
)

# --- 1. Source identity (same-paper detection, never a scientific claim) ----
_ID_PATTERNS = (
    ("DOI", re.compile(r"\b(10\.\d{4,9}/[^\s,;)\]\"'><]+)", re.I)),
    ("ARXIV", re.compile(r"arxiv[:\s/]*(\d{4}\.\d{4,5}(?:v\d+)?)", re.I)),
    ("PMID", re.compile(r"\bpmid[:\s]*(\d{6,9})", re.I)),
    ("PMCID", re.compile(r"\bpmc(\d{5,9})", re.I)),
    ("OPENREVIEW", re.compile(r"openreview[:\s]*([A-Za-z0-9_-]{6,})", re.I)),
)
_ID_RANK = {"DOI": 0, "ARXIV": 1, "OPENREVIEW": 2, "PMID": 3, "PMCID": 4}


_TRIM_CHARS = ".,;:)]}>）】」』\"'"


def _clean_id(kind: str, value: str) -> str:
    value = value.strip().strip(_TRIM_CHARS).replace("\\", "/")
    if kind == "DOI":
        return "DOI:" + value.rstrip(".").lower()
    if kind == "ARXIV":
        return "ARXIV:" + re.sub(r"v\d+$", "", value.lower())
    if kind == "OPENREVIEW":
        return "OPENREVIEW:" + value
    return f"{kind}:{value}"


def normalise_identifiers(*texts) -> list[str]:
    """Bibliographic identifiers only. Order is deterministic (sorted)."""
    found = set()
    for text in texts:
        if not text:
            continue
        if isinstance(text, (list, tuple)):
            found.update(normalise_identifiers(*[str(x) for x in text]))
            continue
        s = str(text)
        for kind, pattern in _ID_PATTERNS:
            for m in pattern.finditer(s):
                token = _clean_id(kind, m.group(1))
                if len(token) > len(kind) + 3:
                    found.add(token)
    return sorted(found)


def case_identifiers(record: dict, card_meta: dict | None = None) -> list[str]:
    """Identifiers declared by the record itself and by its evidence entries."""
    meta = card_meta or {}
    evidence_sources = [e.get("source", "") for e in (meta.get("evidence") or [])
                        if isinstance(e, dict)]
    return normalise_identifiers(record.get("source_refs"),
                                 record.get("evidence_paths"),
                                 evidence_sources)


def _id_key(identifier: str) -> tuple[int, str]:
    kind = identifier.split(":", 1)[0]
    return (_ID_RANK.get(kind, 9), identifier)


MIN_AGGREGATE_SOURCES = 5


def is_aggregate_source(record: dict, card_meta: dict | None = None) -> bool:
    """A card that deliberately aggregates several independent papers.

    It must never be clustered with a single-paper card, or one repair index
    would silently become "the same study" as three unrelated papers. The rule
    is source-count based, not identifier-count based: one paper legitimately
    carries a DOI plus a PMID plus a PMCID.
    """
    if str(record.get("evidence_class") or "").upper() == "REPAIR_PROTOCOL":
        return True
    sources = {str(e.get("source") or "") for e in (card_meta or {}).get("evidence") or []
               if isinstance(e, dict) and str(e.get("source") or "").strip()}
    return len(sources) >= MIN_AGGREGATE_SOURCES


def cluster_sources(cases: list[tuple[dict, dict]]) -> tuple[dict, dict]:
    """Return ({case_id: source_group_id}, {case_id: [same_source_case_id]}).

    Union-find over shared bibliographic identifiers, excluding aggregates.
    Group ids are derived from the smallest member CASE_ID so they stay stable
    when new, different studies are added.
    """
    ids = {}
    aggregate = {}
    for record, meta in cases:
        cid = record.get("case_id")
        found = case_identifiers(record, meta)
        ids[cid] = found
        aggregate[cid] = is_aggregate_source(record, meta)

    parent = {cid: cid for cid in ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            if rb < ra:
                ra, rb = rb, ra
            parent[rb] = ra

    owner: dict[str, str] = {}
    for cid in sorted(ids):
        if aggregate[cid]:
            continue
        for ident in ids[cid]:
            if ident in owner:
                union(owner[ident], cid)
            else:
                owner[ident] = cid

    groups: dict[str, str] = {}
    for cid in sorted(ids):
        if aggregate[cid]:
            groups[cid] = "SRC-AGG-" + cid
        else:
            groups[cid] = "SRC-" + find(cid)

    same = {}
    for cid in sorted(ids):
        mine = set(ids[cid])
        same[cid] = sorted(other for other in ids
                           if other != cid and mine & set(ids[other]))
    return groups, same


# --- 2. Stage routing (retrieval aid, explicitly NOT a case claim) ---------
H_STAGE_LABELS = {
    "H3": "科研问题与论文价值",
    "H4": "数据、真值与独立评价路径",
    "H6": "科研方案与论文贡献",
    "H7": "实验失败分析与机制转向",
    "H8": "核心贡献调整与再定位",
}
STAGE_ROUTING_BASIS = "MECHANISM_ROUTING_HEURISTIC_V1"
STAGE_ROUTING = {
    "COMPLEX_VS_SIMPLE_BASELINE": ["H3", "H6"],
    "BENCHMARK_SENSITIVITY": ["H3", "H4"],
    "CROSS_DOMAIN_GENERALIZATION": ["H3", "H6"],
    "IMPLEMENTATION_ATTRIBUTION": ["H3", "H6"],
    "CONTROL_DESIGN": ["H6"],
    "GROUP_INDEPENDENCE": ["H4"],
    "DISTRIBUTIONAL_CONFIDENCE": ["H4", "H6"],
    "EVALUATION_METRIC_MISMATCH": ["H4", "H6"],
    "DATA_LEAKAGE": ["H4"],
    "EXTERNAL_VALIDATION": ["H4", "H6"],
    "STATISTICAL_POWER": ["H6"],
    "MEASUREMENT_UNIT": ["H4"],
    "ILLEGITIMATE_PREDICTIVE_INFO": ["H4"],
    "SPURIOUS_NOVELTY": ["H3"],
    "DYNAMIC_POLICY_IDENTIFIABILITY": ["H6", "H7"],
    "MULTIPLE_COMPARISONS": ["H6"],
    "TRUTH_PROXY": ["H4"],
    "DATA_ADMISSION": ["H4"],
    "HOLDOUT_CONTAMINATION": ["H4"],
    "REAL_DISTRIBUTION_SHIFT": ["H4", "H8"],
    "SHORTCUT_LEARNING": ["H7", "H8"],
    "NEIGHBOR_COVERAGE": ["H4"],
    "ADAPTIVE_OVERFITTING": ["H6", "H7"],
    "CAUSAL_MISIDENTIFICATION": ["H3", "H7"],
    "SENSOR_CALIBRATION": ["H4"],
    "LABEL_LOOP": ["H4"],
    "RANDOMIZATION_CONTROL": ["H6"],
    "NEAR_DUPLICATE_LEAKAGE": ["H4"],
    "TEMPORAL_ALIGNMENT": ["H4"],
    "CUE_CONFLICT_TEST": ["H6"],
    "MODEL_CAPACITY_PRETRAINING": ["H3"],
    "INDUCTIVE_BIAS_MISMATCH": ["H3", "H6"],
    "UNDERSPECIFICATION": ["H3", "H6"],
    "OFF_POLICY_EVALUATION": ["H6", "H8"],
    "POLICY_SELECTION": ["H6"],
    "DOMAIN_RANDOMIZATION": ["H6"],
    "REPRODUCIBILITY_GATE": ["H6", "H8"],
    "MULTISENSOR_FUSION": ["H6"],
    "LABEL_ERROR": ["H4"],
    "INDEPENDENCE_DF": ["H4"],
    "ALGEBRAIC_IDENTITY": ["H6"],
    "LOGICAL_VS_PHYSICAL": ["H3", "H8"],
    "LEADERBOARD_PROBING": ["H3"],
    "HIDDEN_GROUP_STRUCTURE": ["H4"],
    "DEMONSTRATION_QUALITY": ["H4", "H6"],
    "CROSS_EMBODIMENT_TRANSFER": ["H6", "H8"],
    "DEPLOYMENT_SHIFT_DETECTION": ["H8"],
}
FAILURE_VERDICTS = {"FAILURE", "MIXED", "INCONCLUSIVE"}


def stage_routes(record: dict) -> tuple[list[str], str]:
    """Declared stage wins; otherwise derived routing labels; else UNKNOWN."""
    declared = _as_list(record.get("h_stages"))
    if declared:
        clean = [s.upper() for s in declared if s.upper() in H_STAGE_LABELS]
        return sorted(set(clean)), "DECLARED"
    stages = set()
    for mech in _as_list(record.get("mechanisms")):
        stages.update(STAGE_ROUTING.get(mech.upper(), []))
    if str(record.get("verdict") or "").upper() in FAILURE_VERDICTS:
        stages.add("H7")
    if str(record.get("evidence_class") or "").upper() == "REPAIR_PROTOCOL":
        stages.update({"H7", "H8"})
    if not stages:
        return [], "UNKNOWN"
    return sorted(stages), STAGE_ROUTING_BASIS


# --- 3. Status classification (explicit, never "upgraded") -----------------
_STATUS_CLASS_ORDER = ("ARCHIVED", "RETIRED", "CLOSED_NO_CLAIM",
                       "WEAK_EVIDENCE", "PREPRINT", "ACTIVE")
_ARCHIVE_MARKERS = ("ARCHIVE", "归档")
_DROP_MARKERS = ("DROP", "丢弃", "撤回")
_CLOSED_MARKERS = ("PROJECT_CLOSED", "TASK_REDESIGN", "NOT_IDENTIFIABLE",
                   "NO_ELIGIBLE_CANDIDATE", "M6=FAIL", "CLOSED")


def classify_status(record: dict) -> tuple[str, list[str]]:
    raw = str(record.get("status") or "").upper()
    flags = set()
    if any(m in raw for m in _ARCHIVE_MARKERS):
        flags.add("ARCHIVED")
    if any(m in raw for m in _DROP_MARKERS):
        flags.add("RETIRED")
    if not flags and any(m in raw for m in _CLOSED_MARKERS):
        flags.add("CLOSED_NO_CLAIM")
    if str(record.get("evidence_class") or "").upper() == "UNVERIFIED_REPORT":
        flags.add("WEAK_EVIDENCE")
    if "PREPRINT" in raw:
        flags.add("PREPRINT")
    if not raw.strip():
        flags.add("NO_STATUS")
    for name in _STATUS_CLASS_ORDER:
        if name in flags:
            return name, sorted(flags)
    return "ACTIVE", sorted(flags)


# --- 4. Case -> knowledge record ------------------------------------------
def _first_text(record: dict, key: str) -> str:
    values = _as_list(record.get(key))
    return values[0] if values else ""


def _clip_text(value, n: int) -> str:
    s = str(value or "").strip().replace("\r", " ").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def evidence_results(card_meta: dict | None) -> list[str]:
    """The claims actually recorded on the card, with their evidence level."""
    out = []
    for entry in (card_meta or {}).get("evidence") or []:
        if not isinstance(entry, dict):
            continue
        claim = _clip_text(entry.get("claim"), MAX_CLAIM_CHARS)
        if not claim:
            continue
        level = str(entry.get("level") or "UNKNOWN").upper()
        source = _clip_text(entry.get("source"), MAX_SOURCE_CHARS)
        out.append(f"[{level}] {claim}" + (f"（来源：{source}）" if source else ""))
    return out


def to_knowledge_record(record: dict, *, card_meta: dict | None = None,
                        card_path: str = "", card_sha256: str = "",
                        source_card_path: str = "",
                        lib_sha256: str = "", grade: str = "UNVERIFIED",
                        source_group_id: str = "",
                        same_source: list[str] | None = None,
                        publish_blockers: list[str] | None = None) -> dict:
    """Map one index record (+ its card) onto knowledge schema v1."""
    meta = card_meta or {}
    domains = sorted({d.upper() for d in _as_list(record.get("research_domains"))})
    tags = sorted({m.upper() for m in _as_list(record.get("mechanisms"))})
    stages, basis = stage_routes(record)
    status_class, status_flags = classify_status(record)
    problem = _as_list(record.get("research_problem"))
    problem_basis = "DECLARED" if problem else "TITLE"
    if not problem:
        problem = _as_list(record.get("title"))
    ident = case_identifiers(record, meta)
    blockers = sorted(set(publish_blockers or []))
    out = {
        "schema_version": KNOWLEDGE_SCHEMA_VERSION,
        "format": KNOWLEDGE_CARD_FORMAT,
        "case_id": record.get("case_id"),
        "title": record.get("title") or "UNTITLED",
        "source_type": str(record.get("origin") or "UNKNOWN").upper(),
        "source_group_id": source_group_id or ("SRC-" + str(record.get("case_id"))),
        "source_ids": ident,
        "same_source_cases": list(same_source or []),
        "domains": domains,
        "h_stages": stages,
        "h_stages_basis": basis,
        "problem_tags": tags,
        "outcome": str(record.get("verdict") or "UNKNOWN").upper(),
        "status": str(record.get("status") or ""),
        "status_class": status_class,
        "status_flags": status_flags,
        "evidence_class": str(record.get("evidence_class") or "UNKNOWN").upper(),
        "evidence_grade": grade,
        "evidence_level": sorted({x.upper() for x in _as_list(record.get("evidence_levels"))}),
        "source_refs": _as_list(record.get("source_refs")),
        "research_problem": problem[0] if problem else "UNKNOWN",
        "research_problem_basis": problem_basis,
        "premises": _as_list(record.get("premises")),
        "conditions": _as_list(meta.get("applicability", {}).get("conditions")
                               if isinstance(meta.get("applicability"), dict) else None)
        or _as_list((record.get("applicability") or {}).get("conditions")),
        "boundaries": _as_list((record.get("applicability") or {}).get("boundaries")),
        "counterexamples": _as_list(record.get("counterexamples")),
        "results": evidence_results(meta),
        "transferable_lesson": _first_text(record, "transferable_lesson"),
        "next_minimal_check": _as_list(record.get("next_minimal_check")),
        "success_notes": _first_text(record, "success_notes"),
        "related_cases": sorted(_as_list(record.get("related_cases"))),
        "scope_warning": _first_text(record, "scope_warning"),
        "updated_at": _first_text(record, "updated_at") or "UNKNOWN",
        "source_digest": "sha256:" + _sha256(_canonical(record)),
        "source_card_sha256": card_sha256 or "UNKNOWN",
        "source_card_path": source_card_path or "UNKNOWN",
        "card_path": card_path,
        "publishable": not blockers,
        "publish_blockers": blockers,
    }
    return {k: out[k] for k in KNOWLEDGE_FIELDS}


_SECTION_LABELS = (
    ("research_problem", "科研问题", "single"),
    ("premises", "前提（复用前逐条核对）", "list"),
    ("results", "有效结果（来源主张）", "list"),
    ("conditions", "适用条件", "list"),
    ("boundaries", "适用边界", "list"),
    ("counterexamples", "反例（何时本卡不成立）", "list"),
    ("transferable_lesson", "可迁移经验", "single"),
    ("next_minimal_check", "最小验证", "list"),
    ("success_notes", "成功条件", "single"),
)


def render_knowledge_card(krec: dict) -> dict:
    """Render schema-v1 card Markdown. Same record -> byte-identical output."""
    cid = krec.get("case_id")
    title = krec.get("title")
    head = [
        f"# {cid} · {title}",
        "",
        f"- 结论：`{krec.get('outcome')}`｜状态：`{krec.get('status') or 'UNKNOWN'}`"
        f"（`{krec.get('status_class')}`）｜来源：`{krec.get('source_type')}`",
        f"- 证据类别：`{krec.get('evidence_class')}`｜证据评定：`{krec.get('evidence_grade')}`"
        f"｜证据等级：{', '.join(krec.get('evidence_level') or []) or 'UNKNOWN'}",
        f"- 研究域：{', '.join(krec.get('domains') or []) or 'UNKNOWN'}",
        f"- 主题标签：{', '.join(krec.get('problem_tags') or []) or 'UNKNOWN'}",
        f"- 同源关系：`{krec.get('source_group_id')}`"
        + (f"｜同源案例：{', '.join(krec.get('same_source_cases') or [])}"
           if krec.get("same_source_cases") else "｜同源案例：无"),
    ]
    if krec.get("scope_warning"):
        head.append(f"- 适用范围警告：{krec['scope_warning']}")
    if not krec.get("publishable", True):
        head.append("- **发布阻断**：" + ", ".join(krec.get("publish_blockers") or []))

    lines = list(head)
    for key, label, kind in _SECTION_LABELS:
        values = krec.get(key)
        if isinstance(values, str):
            values = [values] if values.strip() and values != "UNKNOWN" else []
        if not values:
            continue
        lines += ["", f"## {label}"]
        if kind == "single":
            lines.append(str(values[0]))
        else:
            lines += [f"- {v}" for v in values]

    lines += ["", "## 检索路由（派生提示，不是案例本身的科学主张）",
              f"- 阶段：{', '.join(krec.get('h_stages') or []) or 'UNKNOWN'}"
              f"｜依据：`{krec.get('h_stages_basis')}`"]
    stage_links = ", ".join(f"[{s}](../indexes/stages/{s}.md)"
                            for s in (krec.get("h_stages") or []))
    if stage_links:
        lines.append(f"- 阶段入口：{stage_links}")
    tag_links = [f"[{t}](../indexes/topics/MECH-{t}.md)"
                 for t in (krec.get("problem_tags") or [])[:6]]
    dom_links = [f"[{d}](../indexes/topics/DOMAIN-{d}.md)"
                 for d in (krec.get("domains") or [])[:4]]
    if tag_links or dom_links:
        lines.append("- 主题入口：" + ", ".join(tag_links + dom_links))

    lines += ["", "## 来源与追溯"]
    for ref in (krec.get("source_refs") or [])[:8]:
        lines.append(f"- {ref}")
    if krec.get("source_ids"):
        lines.append("- 文献标识：" + ", ".join(krec["source_ids"]))
    lines += [
        f"- 源案例卡（CASE_LIBRARY 内）：`{krec.get('source_card_path')}`"
        f"（sha256 `{krec.get('source_card_sha256')}`）",
        f"- 镜像路径：`{krec.get('card_path')}`",
        f"- 源记录摘要：`{krec.get('source_digest')}`",
        f"- 更新日期：`{krec.get('updated_at')}`（原始记录未提供时为 UNKNOWN）",
        f"- Schema：`{krec.get('schema_version')}`｜格式：`{krec.get('format')}`",
    ]
    if krec.get("related_cases"):
        lines += ["", "## 相关案例", ", ".join(krec["related_cases"])]

    lines += ["", "---",
              "本卡由只读渲染器从 CASE_LIBRARY 生成：检索结果是候选证据，不是已证实结论；",
              "复用前须核对原始 Run 与本文适用边界；本文件不授予任何权限，也不代表已发布。"]
    body = "\n".join(lines) + "\n"
    markdown = ("---json\n" + json.dumps(krec, ensure_ascii=False, sort_keys=True,
                                        indent=1) + "\n---\n\n" + body)
    return {"markdown": markdown, "sha256": _sha256(markdown),
            "body_sha256": _sha256(body)}


def knowledge_card(record: dict, **kwargs) -> dict:
    """Record -> (knowledge record, rendered card)."""
    krec = to_knowledge_record(record, **kwargs)
    rendered = render_knowledge_card(krec)
    return {"record": krec, **rendered}
