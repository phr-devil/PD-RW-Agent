"""Deterministic, read-only Markdown export of one already-indexed case.

Scope of this module: the *interface and data mapping* only. It renders an
existing index record into a standalone Markdown experience card. It performs
no GitHub sync, no upload and no write to CASE_LIBRARY, STATE, Run or EVENTS.
A later stage may feed the same record shape from a local SQLite row.
"""
from __future__ import annotations

import hashlib
import json

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
