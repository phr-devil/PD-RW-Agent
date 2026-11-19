"""Build a deterministic, incrementally maintainable case-knowledge mirror.

Architecture (WP6-A):

    CASE_LIBRARY (authoritative, read-only)
        -> Markdown / JSONL mirror in a directory outside the repository
        -> future GitHub private repository
        -> ChatGPT / Codex / WorkBuddy on-demand retrieval

This module only *writes to the mirror directory*. It never writes to
CASE_LIBRARY, never fetches a URL, never uploads anything and never pushes a
remote. Publication is a separate, explicitly-confirmed step (WP6-B); the
mirror therefore carries `publishable` plus `publish_blockers`, and a mirror
that fails any gate is rendered as "not ready to publish", never as "ready".

Determinism: a mirror rendered from the same library bytes with the same
schema version is byte-identical. No wall-clock value and no machine-specific
absolute path enters any rendered file; the run state that requires them is
kept in a dot-file *next to* the mirror, never inside it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from pathlib import Path

from . import __version__
from .schemas import AgentError
from . import case_export, case_learning

MIRROR_VERSION = "1.1"
MANIFEST_NAME = "manifest.json"
STATE_VERSION = "1"

CARD_DIR = "cases"
INDEX_DIR = "indexes"
TOPIC_DIR = "indexes/topics"
STAGE_DIR = "indexes/stages"
INSIGHT_DIR = "insights"
DOC_DIR = "docs"
JSONL_NAME = "indexes/cases.jsonl"
LIFECYCLE_NAME = "indexes/lifecycle.jsonl"
STAGES = ("H3", "H4", "H6", "H7", "H8")

# --- privacy / publish gates ----------------------------------------------
_PRIVACY_PATTERNS = (
    ("ABSOLUTE_LOCAL_PATH", re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]")),
    ("POSIX_HOME_PATH", re.compile(r"/(?:home|Users)/[A-Za-z0-9._-]+")),
    ("EMAIL_ADDRESS", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("CREDENTIAL_PATTERN", re.compile(
        r"(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}"
        r"|-----BEGIN [A-Z ]*PRIVATE KEY-----"
        r"|(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S{6,})", re.I)),
    ("PERSONAL_PHONE_NUMBER", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
)
_SAFE_URL_PREFIXES = ("http://", "https://")


def scan_publish_blockers(text: str) -> list[str]:
    """Return stable blocker codes found in rendered content (never guesses)."""
    found = set()
    for code, pattern in _PRIVACY_PATTERNS:
        for match in pattern.finditer(text or ""):
            token = match.group(0)
            # A URL such as https://host/path is not a local absolute path.
            if code == "ABSOLUTE_LOCAL_PATH":
                start = match.start()
                prefix = text[max(0, start - 8):start].lower()
                if any(prefix.endswith(p) for p in _SAFE_URL_PREFIXES):
                    continue
            if code == "EMAIL_ADDRESS" and token.lower().endswith(("@example.com",
                                                                   "@example.invalid")):
                continue
            found.add(code)
            break
    return sorted(found)


def _canonical(obj) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------
# Reading the authoritative library
# --------------------------------------------------------------------------
def load_cases(settings) -> dict:
    """Read every indexed case plus its card. Read-only by construction."""
    root = case_learning.resolve_root(settings)
    if not root:
        raise AgentError("CASE_LIBRARY_NOT_CONFIGURED",
                         "Set PDRW_CASE_LIBRARY_ROOT or case_library_root")
    bundle = case_learning.load_index(root)
    records = bundle["data"]["cases"]
    metas, cards = {}, {}
    for record in records:
        cid = record.get("case_id")
        resolved, rel = None, ""
        for candidate in record.get("evidence_paths") or []:
            target = case_learning._card_path(root, candidate)
            if target is not None:
                resolved = target
                rel = str(target.relative_to(root)).replace("\\", "/")
                break
        metas[cid] = case_learning._card_meta(resolved) if resolved else {}
        cards[cid] = {"card_path": rel,
                      "card_sha256": (_sha_bytes(resolved.read_bytes())
                                      if resolved else "UNKNOWN")}
    verification = case_learning.verify_sources(
        bundle, [{"case_id": r["case_id"]} for r in records])
    return {"root": root, "bundle": bundle, "records": records,
            "metas": metas, "cards": cards, "verification": verification,
            "library_sha": bundle["sha256"],
            "index_stale": bundle["index_stale"]}


# --------------------------------------------------------------------------
# Rendering the mirror plan
# --------------------------------------------------------------------------
def _clip(value, n: int) -> str:
    s = str(value or "").replace("\n", " ").replace("|", "/").strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def _cell(value) -> str:
    return _clip(value, 400).replace("`", "'")


def _card_table_rows(cases: list[dict]) -> list[str]:
    rows = ["| CASE_ID | 标题 | 结论 | 证据类别 | 评定 | 阶段 | 状态 |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    for krec in cases:
        rows.append("| [{cid}]({path}) | {title} | {outcome} | {eclass} | {grade} "
                    "| {stages} | {status} |".format(
                        cid=krec["case_id"], path=krec["card_path"],
                        title=_clip(krec["title"], 46),
                        outcome=krec["outcome"], eclass=krec["evidence_class"],
                        grade=krec["evidence_grade"],
                        stages=",".join(krec["h_stages"]) or "UNKNOWN",
                        status=krec["status_class"]))
    return rows


def _stage_index(stage: str, cases: list[dict]) -> str:
    label = case_export.H_STAGE_LABELS.get(stage, stage)
    hits = [c for c in cases if stage in c["h_stages"]]
    lines = [f"# {stage} · {label}", "",
             f"本阶段可参考的候选案例 {len(hits)} 张。阶段归属由机制标签路由派生"
             f"（`{case_export.STAGE_ROUTING_BASIS}`），是检索入口，不是案例的科学主张。",
             "", "读取顺序：本页 → `cases/<CASE_ID>.md` 的 `前提` / `适用条件` / `反例` "
             "→ 必要时回到原始来源。", ""]
    if hits:
        lines += ["| CASE_ID | 标题 | 结论 | 评定 | 主题标签 |", "| --- | --- | --- | --- | --- |"]
        for c in hits:
            lines.append(f"| [{c['case_id']}](../../{c['card_path']}) | {_clip(c['title'], 44)} "
                         f"| {c['outcome']} | {c['evidence_grade']} "
                         f"| {_clip(', '.join(c['problem_tags']), 60)} |")
    else:
        lines.append("（无匹配案例）")
    return "\n".join(lines) + "\n"


def _topic_index(title: str, key: str, cases: list[dict]) -> str:
    lines = [f"# {title}", "",
             f"按标签 `{key}` 收录 {len(cases)} 张案例。", "",
             "| CASE_ID | 标题 | 结论 | 评定 | 阶段 |", "| --- | --- | --- | --- | --- |"]
    for c in cases:
        lines.append(f"| [{c['case_id']}](../../{c['card_path']}) | {_clip(c['title'], 44)} "
                     f"| {c['outcome']} | {c['evidence_grade']} "
                     f"| {','.join(c['h_stages']) or 'UNKNOWN'} |")
    return "\n".join(lines) + "\n"


def _index_md(cases: list[dict], library: dict, publish: dict) -> str:
    by_outcome, by_grade, by_status = {}, {}, {}
    for c in cases:
        by_outcome[c["outcome"]] = by_outcome.get(c["outcome"], 0) + 1
        by_grade[c["evidence_grade"]] = by_grade.get(c["evidence_grade"], 0) + 1
        by_status[c["status_class"]] = by_status.get(c["status_class"], 0) + 1
    internal = sum(1 for c in cases if c["source_type"] == "INTERNAL")
    lines = ["# PD-RW 案例知识索引", "",
             "> 由 `pdrw-agent case-knowledge-build` 从 CASE_LIBRARY 只读生成。",
             f"> Schema `{case_export.KNOWLEDGE_SCHEMA_VERSION}`｜导出 `{MIRROR_VERSION}`"
             f"｜案例库索引 `{library['library_sha']}`",
             f"> 可发布状态：**{'YES' if publish['publishable'] else 'NO'}**"
             + ("｜阻断：" + ", ".join(publish["blockers"]) if publish["blockers"] else ""),
             "",
             "## 汇总", "",
             f"- 案例：{len(cases)}（内部 {internal} / 外部 {len(cases) - internal}）",
             f"- 结论分布：{', '.join(f'{k} {v}' for k, v in sorted(by_outcome.items()))}",
             f"- 证据评定：{', '.join(f'{k} {v}' for k, v in sorted(by_grade.items()))}",
             f"- 状态分布：{', '.join(f'{k} {v}' for k, v in sorted(by_status.items()))}",
             "- 同源簇：`indexes/cases.jsonl` 的 `source_group_id`；同源案例不是独立证据。",
             "",
             "## 快速入口", ""]
    for stage in STAGES:
        n = sum(1 for c in cases if stage in c["h_stages"])
        lines.append(f"- [{stage} {case_export.H_STAGE_LABELS[stage]}]"
                     f"(indexes/stages/{stage}.md) — {n} 张")
    lines += ["- 主题入口：`indexes/topics/`（机制 `MECH-*.md`、领域 `DOMAIN-*.md`）",
              "- 结构化索引：`indexes/cases.jsonl`（程序筛选用）",
              "- 字段定义：`docs/SCHEMA.md`｜读取规范：`docs/RETRIEVAL.md`",
              "", "## 全部案例", ""]
    lines += _card_table_rows(cases)
    return "\n".join(lines) + "\n"


def _jsonl(cases: list[dict]) -> str:
    lines = []
    for c in cases:
        row = {
            "case_id": c["case_id"],
            "title": _clip(c["title"], 90),
            "path": c["card_path"],
            "outcome": c["outcome"],
            "status_class": c["status_class"],
            "evidence_class": c["evidence_class"],
            "evidence_grade": c["evidence_grade"],
            "evidence_level": c["evidence_level"],
            "source_type": c["source_type"],
            "source_group_id": c["source_group_id"],
            "same_source_cases": c["same_source_cases"],
            "domains": c["domains"],
            "h_stages": c["h_stages"],
            "problem_tags": c["problem_tags"],
            "publishable": c["publishable"],
            "sha256": "",
        }
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":")))
    return "\n".join(lines) + ("\n" if lines else "")


def _jsonl_with_hashes(cases: list[dict], card_sha: dict) -> str:
    lines = []
    for line in _jsonl(cases).splitlines():
        row = json.loads(line)
        row["sha256"] = card_sha.get(row["case_id"], "")
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                separators=(",", ":")))
    return "\n".join(lines) + ("\n" if lines else "")


def _readme(cases: list[dict], library: dict, publish: dict) -> str:
    return "\n".join([
        "# PD-RW Case Knowledge（科研经验知识镜像）",
        "",
        "本目录是 `CASE_LIBRARY` 的**只读派生镜像**，用于让 ChatGPT / Codex / WorkBuddy",
        "按需检索同一组案例。权威来源永远是原始案例库与对应科研 Run；本镜像不是新的事实来源。",
        "",
        f"- Schema：`{case_export.KNOWLEDGE_SCHEMA_VERSION}`（`docs/SCHEMA.md`）",
        f"- 导出版本：`{MIRROR_VERSION}`",
        f"- 案例数：{len(cases)}",
        f"- 源库索引 sha256：`{library['library_sha']}`",
        f"- 可发布：**{'YES' if publish['publishable'] else 'NO'}**"
        + ("（阻断：" + ", ".join(publish["blockers"]) + "）" if publish["blockers"] else ""),
        "",
        "## 目录",
        "",
        "| 路径 | 用途 |", "| --- | --- |",
        "| `manifest.json` | 版本、数量、哈希与文件清单；发布前校验入口 |",
        "| `INDEX.md` | 紧凑总索引（先读这个） |",
        "| `cases/<CASE_ID>.md` | 单案例稳定路径卡片 |",
        "| `indexes/cases.jsonl` | 程序筛选用结构化索引 |",
        "| `indexes/stages/` | H3 / H4 / H6 / H7 / H8 阶段入口 |",
        "| `indexes/topics/` | 按真实标签生成的主题入口 |",
        "| `indexes/lifecycle.jsonl` | 案例撤回 / 状态变化记录（不静默丢失） |",
        "| `insights/` | 预留：未经验证的跨案例规律不自动生成 |",
        "| `docs/` | Schema 与读取规范 |",
        "",
        "## 不要做的事",
        "",
        "- 不要手工编辑 `cases/`、`indexes/`、`INDEX.md`：下次导出会覆盖。",
        "- 不要把本镜像当作证据等级升级：相似度不等于科学可信度。",
        "- 不要把同源案例（同一论文拆成两卡）当作两个独立证据。",
        "- 不要在普通代码修复或无关任务中强制调用本知识库。",
        "",
        "## 重新生成",
        "",
        "```bash",
        "pdrw-agent case-knowledge-build --out <目录> --incremental",
        "pdrw-agent case-knowledge-verify --dir <目录>",
        "```",
        "",
        "生成过程不修改 `CASE_LIBRARY`、科研 Run、STATE/EVENTS 或 SEALED；",
        "也不发起任何网络请求、上传或远端推送。",
        "",
    ])


def _agents_md(cases: list[dict]) -> str:
    return "\n".join([
        "# AGENTS.md — 三个 Agent 的统一读取约定",
        "",
        "本仓库是 PD-RW 科研经验镜像，**只读使用**。任何 Agent 都不得在此写入或改动案例。",
        "",
        "## 统一读取顺序（不要跳步）",
        "",
        "1. `manifest.json` — 确认 `schema_version`、`case_count`、`publishable`、",
        "   `library_index_sha256`。若 `publishable=false`，只能当草稿参考。",
        "2. `INDEX.md` 或 `indexes/` — 用阶段（H3/H4/H6/H7/H8）或主题标签缩小范围。",
        "3. 3–5 张候选卡 `cases/<CASE_ID>.md` — 读 `前提` / `适用条件` / `适用边界` / `反例`。",
        "4. 仅在需要判定证据强度时回到 `source_refs` 指向的原始来源。",
        "",
        "## 三条硬规则",
        "",
        "- **证据等级与来源独立性参与解释**：`evidence_grade` 为",
        "  `DECISION_GRADE` / `ABSTRACT_OR_LIMITATION_ONLY` / `NON_DECISION_GRADE`。",
        "  相似度只决定“值不值得读”，不决定“能不能用”。",
        "- **同源案例是一个证据**：`source_group_id` 相同或出现在 `same_source_cases` 中的卡，",
        "  即使结论不同，也不构成独立重复验证。",
        "- **阶段归属是路由提示**：`h_stages_basis=MECHANISM_ROUTING_HEURISTIC_V1` 表示",
        "  阶段由机制标签派生，不是案例自身的声明。",
        "",
        "## 何时不要检索",
        "",
        "普通 DEV、代码修复、格式调整、无关问答不强制调用经验库；不要为了“完整性”重复检索",
        "同一问题。检索只在选题、数据/真值路径、方案与贡献、失败分析与转向这些决策点发生。",
        "",
        f"当前收录 {len(cases)} 张案例；以 `manifest.json` 的实际计数为准。",
        "",
    ])


def _schema_md(cases: list[dict]) -> str:
    rows = []
    for field in case_export.KNOWLEDGE_FIELDS:
        rows.append(f"| `{field}` | {_clip(_field_note(field), 200)} |")
    return "\n".join([
        "# SCHEMA.md — 知识镜像字段定义",
        "",
        f"Schema 版本：`{case_export.KNOWLEDGE_SCHEMA_VERSION}`；卡格式："
        f"`{case_export.KNOWLEDGE_CARD_FORMAT}`。",
        "",
        "字段分三类，必须严格区分：",
        "",
        "1. **直映射**：原记录已有同义字段，逐字保留语义。",
        "2. **显式映射**：名称不同但有确定对应（如 `outcome` ← `verdict`），映射关系写在下表。",
        "3. **派生/未知**：`h_stages` 为路由启发式并带 `h_stages_basis`；源记录没有的字段一律",
        "   `UNKNOWN`，不推测科学事实。",
        "",
        "## 字段表",
        "",
        "| 字段 | 来源 / 语义 |",
        "| --- | --- |",
    ] + rows + [
        "",
        "## 不变量",
        "",
        "1. 同一记录 + 同一 Schema 版本 + 同一案例库索引 ⇒ 字节一致的卡片。",
        "2. `case_id` 与 `cases/<CASE_ID>.md` 路径稳定，不因学科或成败移动。",
        "3. `publishable=false` 的卡保留在镜像中但被标记，不会被静默删除或升级。",
        "4. `updated_at` 缺失时为 `UNKNOWN`；变化检测用 `source_digest` 与 `source_card_sha256`。",
        "5. 导出不复制第三方论文全文，只保留结构化字段与引用标识。",
        "",
        f"当前案例数：{len(cases)}。",
        "",
    ])


def _field_note(field: str) -> str:
    return {
        "schema_version": "Schema 版本，本镜像为 1.0",
        "format": "卡格式标识 pdrw-case-card-v2",
        "case_id": "原始 CASE_ID，永不改写",
        "title": "案例标题",
        "source_type": "`origin`：INTERNAL / EXTERNAL",
        "source_group_id": "同源簇 ID；聚合卡为 SRC-AGG-<CASE_ID>，不与单篇论文合并",
        "source_ids": "从 source_refs / evidence 提取的 DOI、arXiv、PMID、PMCID、OpenReview 标识",
        "same_source_cases": "直接共享至少一个文献标识的其他 CASE_ID（同源≠独立证据）",
        "domains": "`research_domains` 归一为大写",
        "h_stages": "阶段路由标签；依据见 h_stages_basis",
        "h_stages_basis": "DECLARED / MECHANISM_ROUTING_HEURISTIC_V1 / UNKNOWN",
        "problem_tags": "`mechanisms` 归一为大写（真实标签，非新造）",
        "outcome": "`verdict`：FAILURE / SUCCESS / MIXED / INCONCLUSIVE",
        "status": "原始 status 文本，原样保留",
        "status_class": "ARCHIVED / RETIRED / CLOSED_NO_CLAIM / WEAK_EVIDENCE / PREPRINT / ACTIVE",
        "status_flags": "全部命中标记，可多值",
        "evidence_class": "VERIFIED_FAILURE / VERIFIED_SUCCESS / VERIFIED_MIXED / REPAIR_PROTOCOL / UNVERIFIED_REPORT",
        "evidence_grade": "case_learning.verify_sources 的证据评定，与 MCP 检索一致",
        "evidence_level": "`evidence_levels`（ORIGINAL_VERIFIED / PARTIAL_TEXT_VERIFIED / ABSTRACT_VERIFIED / ...）",
        "source_refs": "原始来源引用，不抓取、不展开全文",
        "research_problem": "记录未声明时回退为 title（basis=TITLE）",
        "research_problem_basis": "DECLARED / TITLE",
        "premises": "前提，复用前逐条核对",
        "conditions": "`applicability.conditions`",
        "boundaries": "`applicability.boundaries`",
        "counterexamples": "反例：满足这些条件时本卡不成立",
        "results": "卡上 evidence[].claim 与等级；长文本按 800 字符截断",
        "transferable_lesson": "可迁移经验",
        "next_minimal_check": "最小验证动作",
        "success_notes": "成功条件（存在时）",
        "related_cases": "原记录声明的相关案例",
        "scope_warning": "适用范围警告（存在时）",
        "updated_at": "原记录未提供则为 UNKNOWN，不使用文件时间",
        "source_digest": "源记录规范化 JSON 的 sha256",
        "source_card_sha256": "源案例卡文件 sha256",
        "source_card_path": "源案例卡在 CASE_LIBRARY 内的相对路径",
        "library_index_sha256": "CASE_LIBRARY/index.json 的 sha256",
        "card_path": "镜像内稳定路径 cases/<CASE_ID>.md",
        "publishable": "本卡是否通过隐私/完整性闸门",
        "publish_blockers": "阻断码列表",
    }.get(field, "")


def _retrieval_md(cases: list[dict]) -> str:
    return "\n".join([
        "# RETRIEVAL.md — 检索与解释规范",
        "",
        "## 三个 Agent 的等价入口",
        "",
        "| Agent | 入口 | 说明 |", "| --- | --- | --- |",
        "| ChatGPT | GitHub 文件读取：`manifest.json` → `INDEX.md` → `cases/*.md` | 无本地运行环境 |",
        "| Codex | `indexes/cases.jsonl`、文本搜索、本地 git clone | 结构化筛选 |",
        "| WorkBuddy | `case_search` / `case_gate_check`（MCP，读 CASE_LIBRARY） | 同一批案例、同一证据评定 |",
        "",
        "三者必须定位到**同一组 CASE_ID**；不一致时以 CASE_LIBRARY 侧为准。",
        "",
        "## 长自然语言查询",
        "",
        "不要用整句做严格 AND 关键词匹配——会系统性漏检。做法：",
        "",
        "1. 抽取 2–5 个核心概念（机制词、数据类型、评价单位、失败模式）。",
        "2. 用宽松召回（任一概念命中即进入候选池）。",
        "3. 用适用性重排：`前提`、`适用条件`、`适用边界`、`反例` 是否冲突。",
        "4. 冲突时输出 `CONDITIONS_DIFFER`，而不是把案例结论搬过来。",
        "",
        "## 解释规则",
        "",
        "- `evidence_grade` 决定这张卡能支持多强的结论；相似度只用于排序。",
        "- `status_class` 为 `ARCHIVED` / `RETIRED` / `WEAK_EVIDENCE` 的卡，只能作为历史依据或",
        "  反例线索，不得作为当前决策的主要支撑。",
        "- 同一 `source_group_id` 或 `same_source_cases` 内的多张卡，只算一份独立证据。",
        "- 检索结果永远是候选，不产生 GO/STOP，也不产生额外人工审批要求。",
        "",
        "## 禁止",
        "",
        "- 不得把镜像内容回写成新的科学事实，或据此修改原始案例。",
        "- 不得因为检索不到就推断“该风险不存在”；应标记 `UNKNOWN` 并说明检索范围。",
        "",
    ])


def _insights_readme() -> str:
    return "\n".join([
        "# insights/ — 预留目录",
        "",
        "本目录用于将来存放**经复核的**跨案例规律（例如同一机制在多个独立来源上重复出现）。",
        "",
        "当前导出**不自动生成**任何跨案例分析：",
        "",
        "- 自动归纳会把“标签相似”误当成“科学等价”；",
        "- 同源案例（同一论文拆卡）会造成重复计数的假象；",
        "- 弱证据与归档案例尚未剔除时，任何统计都不成立。",
        "",
        "因此在有人逐条核对 `source_group_id`、`evidence_grade` 与适用边界之前，这里保持为空。",
        "",
    ])


def _lifecycle(entries: list[dict]) -> str:
    lines = [json.dumps(e, ensure_ascii=False, sort_keys=True,
                        separators=(",", ":")) for e in entries]
    return "\n".join(lines) + ("\n" if lines else "")


# --------------------------------------------------------------------------
# Plan
# --------------------------------------------------------------------------
def build_plan(settings, *, state: dict | None = None) -> dict:
    """Render every mirror file in memory. No filesystem write happens here."""
    library = load_cases(settings)
    records = sorted(library["records"], key=lambda r: str(r.get("case_id")))
    pairs = [(r, library["metas"].get(r.get("case_id"), {})) for r in records]
    groups, same = case_export.cluster_sources(pairs)

    cases, blockers = [], {}
    for record in records:
        cid = record.get("case_id")
        grade = library["verification"]["per_case"].get(cid, {}).get(
            "evidence_grade", "UNVERIFIED")
        card = library["cards"].get(cid, {})
        rendered = case_export.knowledge_card(
            record, card_meta=library["metas"].get(cid, {}),
            card_path=f"{CARD_DIR}/{cid}.md",
            card_sha256=card.get("card_sha256", "UNKNOWN"),
            source_card_path=card.get("card_path", "UNKNOWN"),
            lib_sha256=library["library_sha"], grade=grade,
            source_group_id=groups.get(cid, ""),
            same_source=same.get(cid, []))
        hits = scan_publish_blockers(rendered["markdown"])
        if hits:
            blockers[cid] = hits
            rendered = case_export.knowledge_card(
                record, card_meta=library["metas"].get(cid, {}),
                card_path=f"{CARD_DIR}/{cid}.md",
                card_sha256=card.get("card_sha256", "UNKNOWN"),
                source_card_path=card.get("card_path", "UNKNOWN"),
                lib_sha256=library["library_sha"], grade=grade,
                source_group_id=groups.get(cid, ""),
                same_source=same.get(cid, []), publish_blockers=hits)
        cases.append({**rendered["record"], "card_path": f"{CARD_DIR}/{cid}.md",
                      "_markdown": rendered["markdown"],
                      "_sha256": rendered["sha256"]})

    card_sha = {c["case_id"]: c["_sha256"] for c in cases}
    files: dict[str, str] = {}
    for c in cases:
        files[c["card_path"]] = c["_markdown"]
    files[JSONL_NAME] = _jsonl_with_hashes(cases, card_sha)
    files["INDEX.md"] = _index_md(cases, library, _publish_state(library, cases, blockers, state))
    for stage in STAGES:
        files[f"{STAGE_DIR}/{stage}.md"] = _stage_index(stage, cases)
    topic_groups: dict[str, list[dict]] = {}
    for c in cases:
        for tag in c["problem_tags"]:
            topic_groups.setdefault(f"MECH-{tag}", []).append(c)
        for dom in c["domains"]:
            topic_groups.setdefault(f"DOMAIN-{dom}", []).append(c)
    for key in sorted(topic_groups):
        title = ("机制 · " if key.startswith("MECH-") else "领域 · ") + key.split("-", 1)[1]
        files[f"{TOPIC_DIR}/{key}.md"] = _topic_index(title, key, topic_groups[key])
    files["README.md"] = _readme(cases, library, _publish_state(library, cases, blockers, state))
    files["AGENTS.md"] = _agents_md(cases)
    files[f"{DOC_DIR}/SCHEMA.md"] = _schema_md(cases)
    files[f"{DOC_DIR}/RETRIEVAL.md"] = _retrieval_md(cases)
    files[f"{INSIGHT_DIR}/README.md"] = _insights_readme()
    files[LIFECYCLE_NAME] = _lifecycle(_lifecycle_entries(state, cases))

    publish = _publish_state(library, cases, blockers, state)
    # INDEX.md/README.md embed the publish verdict: re-render once so the gate
    # string cannot go stale against the manifest.
    files["INDEX.md"] = _index_md(cases, library, publish)
    files["README.md"] = _readme(cases, library, publish)

    hashes = {path: _sha(text) for path, text in files.items()}
    content_sha = _sha("\n".join(f"{p}\n{hashes[p]}" for p in sorted(hashes)))
    manifest = {
        "schema_version": case_export.KNOWLEDGE_SCHEMA_VERSION,
        "mirror_version": MIRROR_VERSION,
        "agent_version": __version__,
        "card_format": case_export.KNOWLEDGE_CARD_FORMAT,
        "case_count": len(cases),
        "source": {
            "library_index_sha256": library["library_sha"],
            "index_schema_version": library["bundle"]["data"].get("schema_version"),
            "taxonomy_version": library["bundle"]["data"].get("taxonomy_version"),
            "source_of_truth": library["bundle"]["data"].get("source_of_truth"),
            "cases_in_index": library["bundle"]["data"].get("case_count"),
            "cards_on_disk": library["bundle"]["card_count"],
            "index_stale": library["index_stale"],
        },
        "counts": {
            "by_outcome": _count(cases, "outcome"),
            "by_status_class": _count(cases, "status_class"),
            "by_evidence_class": _count(cases, "evidence_class"),
            "by_evidence_grade": _count(cases, "evidence_grade"),
            "by_source_type": _count(cases, "source_type"),
            "same_source_groups": len({c["source_group_id"] for c in cases}),
            "cases_sharing_a_source": sum(1 for c in cases if c["same_source_cases"]),
            "cases_without_stage_route": sum(1 for c in cases if not c["h_stages"]),
            "unmapped_mechanisms": sorted({t for c in cases for t in c["problem_tags"]
                                           if t not in case_export.STAGE_ROUTING}),
        },
        "publishable": publish["publishable"],
        "publish_state": _publish_state_label(publish["publishable"]),
        "publish_blockers": publish["blockers"],
        "privacy_blocked_cases": blockers,
        "files": [{"path": p, "sha256": hashes[p], "bytes": len(files[p].encode("utf-8"))}
                  for p in sorted(files)],
        "file_count": len(files),
        "content_sha256": content_sha,
    }
    files[MANIFEST_NAME] = json.dumps(manifest, ensure_ascii=False,
                                      sort_keys=True, indent=1) + "\n"
    return {"files": files, "manifest": manifest, "cases": cases,
            "library": library, "publish": publish, "privacy_blockers": blockers}


def _publish_state_label(publishable: bool) -> str:
    """Explicit preview/publish distinction: a build never publishes anything."""
    return ("READY_FOR_CONFIRMED_PUBLICATION" if publishable
            else "BLOCKED_NOT_PUBLISHABLE")


def _count(cases: list[dict], key: str) -> dict:
    out: dict[str, int] = {}
    for c in cases:
        out[str(c.get(key))] = out.get(str(c.get(key)), 0) + 1
    return dict(sorted(out.items()))


def _case_state(cases: list[dict]) -> dict:
    return {c["case_id"]: {"path": c["card_path"],
                           "sha256": c["_sha256"],
                           "status_class": c["status_class"],
                           "evidence_grade": c["evidence_grade"]}
            for c in cases}


def _diff_state(previous: dict, cases: list[dict]) -> dict:
    """Retirement / status-change events implied by this plan. Deterministic."""
    old = previous.get("cases") or {}
    new = _case_state(cases)
    generation = int(previous.get("generation") or 0) + 1
    retired, events = [], []
    for cid in sorted(set(old) - set(new)):
        retired.append({"event": "CASE_RETIRED", "case_id": cid,
                        "path": old[cid].get("path"),
                        "last_sha256": old[cid].get("sha256"),
                        "reason": "SOURCE_RECORD_REMOVED",
                        "generation": generation})
    for cid in sorted(set(old) & set(new)):
        before, after = old[cid], new[cid]
        if before.get("status_class") != after["status_class"]:
            events.append({"event": "STATUS_CLASS_CHANGED", "case_id": cid,
                           "from": before.get("status_class"),
                           "to": after["status_class"], "generation": generation})
        if before.get("evidence_grade") != after["evidence_grade"]:
            events.append({"event": "EVIDENCE_GRADE_CHANGED", "case_id": cid,
                           "from": before.get("evidence_grade"),
                           "to": after["evidence_grade"], "generation": generation})
    return {"generation": generation, "retired": retired, "events": events}


def _lifecycle_entries(state: dict | None, cases: list[dict]) -> list[dict]:
    """History carried from the state file plus this run's delta.

    Computed before the state file is written, so a case removed in this run is
    already recorded in the mirror it produced - never only on the next run.
    """
    if not state:
        return []
    delta = _diff_state(state, cases)
    return (list(state.get("retired") or []) + delta["retired"]
            + list(state.get("status_events") or []) + delta["events"])


def _publish_state(library: dict, cases: list[dict], blockers: dict,
                   state: dict | None) -> dict:
    """Gates decided at BUILD time.

    A mirror just rendered from the current library is consistent with it by
    construction, so "the library moved on" is not a build-time blocker; it is
    a verify-time blocker (see `verify(..., settings=...)`), which is exactly
    where a stale mirror would otherwise be published.
    """
    reasons = []
    if library["index_stale"]:
        reasons.append("INDEX_STALE_REBUILD_REQUIRED")
    expected = library["bundle"]["data"].get("case_count")
    if expected != len(cases):
        reasons.append("EXPORT_INCOMPLETE")
    if library["bundle"]["card_count"] != len(cases):
        reasons.append("CARD_COUNT_MISMATCH")
    if blockers:
        reasons.append("PRIVACY_OR_CONTENT_BLOCKER")
    return {"publishable": not reasons, "blockers": reasons}


# --------------------------------------------------------------------------
# State (non-deterministic parts live outside the mirror)
# --------------------------------------------------------------------------
def state_path(out_dir: Path) -> Path:
    out_dir = Path(out_dir)
    return out_dir.parent / f".{out_dir.name}.state.json"


def load_state(out_dir: Path) -> dict:
    path = state_path(out_dir)
    if not path.is_file():
        return {"state_version": STATE_VERSION, "generation": 0,
                "library_index_sha256": None, "cases": {}, "retired": [],
                "status_events": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"state_version": STATE_VERSION, "generation": 0,
                "library_index_sha256": None, "cases": {}, "retired": [],
                "status_events": []}
    if not isinstance(data, dict) or data.get("state_version") != STATE_VERSION:
        return {"state_version": STATE_VERSION, "generation": 0,
                "library_index_sha256": None, "cases": {}, "retired": [],
                "status_events": []}
    return data


def next_state(previous: dict, plan: dict) -> dict:
    """Carry retirement/status history forward; never silently drop a case."""
    delta = _diff_state(previous, plan["cases"])
    return {"state_version": STATE_VERSION, "generation": delta["generation"],
            "library_index_sha256": plan["library"]["library_sha"],
            "cases": _case_state(plan["cases"]),
            "retired": list(previous.get("retired") or []) + delta["retired"],
            "status_events": (list(previous.get("status_events") or [])
                              + delta["events"])}


# --------------------------------------------------------------------------
# Writing
# --------------------------------------------------------------------------
def _write_tree(target: Path, files: dict[str, str]) -> list[str]:
    written = []
    for rel in sorted(files):
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = files[rel].encode("utf-8")
        if path.is_file() and _sha_bytes(path.read_bytes()) == _sha_bytes(data):
            continue
        path.write_bytes(data)
        written.append(rel)
    return written


def _stage_tree(target: Path, files: dict[str, str],
                previous_dir: Path | None) -> tuple[list[str], list[str]]:
    """Stage a full tree. Unchanged files are hard-linked, never rewritten."""
    changed, reused = [], []
    for rel in sorted(files):
        path = target / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        data = files[rel].encode("utf-8")
        digest = _sha_bytes(data)
        old = (previous_dir / rel) if previous_dir else None
        if old is not None and old.is_file() and _sha_bytes(old.read_bytes()) == digest:
            try:
                os.link(old, path)
                reused.append(rel)
                continue
            except OSError:
                shutil.copyfile(old, path)
                reused.append(rel)
                continue
        path.write_bytes(data)
        changed.append(rel)
    return changed, reused


def build(settings, out_dir, *, incremental: bool = True,
          dry_run: bool = False) -> dict:
    """Render (and optionally write) the knowledge mirror atomically."""
    out = Path(out_dir).expanduser().resolve()
    previous = load_state(out)
    plan = build_plan(settings, state=previous if incremental else None)
    manifest = plan["manifest"]

    # Never delete a case file that the new plan still contains; only files the
    # previous *manifest* owned can disappear, and the swap removes them.
    stale_files: list[str] = []
    if incremental and (out / MANIFEST_NAME).is_file():
        try:
            old_manifest = json.loads((out / MANIFEST_NAME).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            old_manifest = {}
        owned = {f.get("path") for f in old_manifest.get("files") or []
                 if isinstance(f, dict)}
        stale_files = sorted(p for p in owned if p and p not in plan["files"])

    if dry_run:
        existing = {p for p in plan["files"] if (out / p).is_file()}
        return {"status": "DRY_RUN_PLAN_ONLY", "target": str(out),
                "case_count": len(plan["cases"]),
                "file_count": len(plan["files"]),
                "would_write": len(plan["files"]) - len(existing),
                "would_delete": stale_files,
                "publishable": manifest["publishable"],
                "publish_blockers": manifest["publish_blockers"],
                "content_sha256": manifest["content_sha256"],
                "incremental": incremental, "no_writes": True}

    builder = out.parent / f".{out.name}.building-{os.getpid()}"
    retiring = out.parent / f".{out.name}.retiring-{os.getpid()}"
    if builder.exists():
        shutil.rmtree(builder)
    if retiring.exists():
        shutil.rmtree(retiring)
    builder.mkdir(parents=True)
    previous_dir = out if (incremental and out.is_dir()) else None
    try:
        changed, reused = _stage_tree(builder, plan["files"], previous_dir)
        # Validate the staged tree before touching a previously good mirror.
        for rel in plan["files"]:
            target = builder / rel
            if not target.is_file():
                raise AgentError("EXPORT_STAGING_INCOMPLETE",
                                 f"staged file missing: {rel}")
        if out.exists():
            out.rename(retiring)
            try:
                builder.rename(out)
            except OSError:
                retiring.rename(out)  # restore the last good mirror, unchanged
                raise
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            builder.rename(out)
    finally:
        if builder.exists():
            shutil.rmtree(builder, ignore_errors=True)
        if retiring.exists():
            shutil.rmtree(retiring, ignore_errors=True)

    state = next_state(previous, plan)
    state_path(out).write_text(json.dumps(state, ensure_ascii=False,
                                          sort_keys=True, indent=1) + "\n",
                               encoding="utf-8")
    return {"status": "MIRROR_WRITTEN", "target": str(out),
            "case_count": len(plan["cases"]),
            "file_count": len(plan["files"]),
            "written": changed, "reused": len(reused),
            "deleted": stale_files,
            "publishable": manifest["publishable"],
            "publish_state": manifest["publish_state"],
            "publish_blockers": manifest["publish_blockers"],
            "content_sha256": manifest["content_sha256"],
            "generation": state["generation"],
            "sync_performed": False, "upload_performed": False,
            "library_modified": False}


def verify(out_dir, settings=None) -> dict:
    """Re-verify a mirror against its manifest, and against the live library.

    `settings` is optional so the check stays usable on a copied mirror; when
    it is supplied, a library whose index.json changed after the export makes
    the mirror non-publishable.
    """
    out = Path(out_dir).expanduser().resolve()
    manifest_path = out / MANIFEST_NAME
    if not manifest_path.is_file():
        raise AgentError("MIRROR_MISSING", "manifest.json not found in target directory")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise AgentError("MIRROR_MANIFEST_INVALID", "manifest.json is not valid JSON") from exc
    problems, missing, mismatched = [], [], []
    hashes = {}
    for entry in manifest.get("files") or []:
        rel = entry.get("path")
        target = out / str(rel)
        if not target.is_file():
            missing.append(rel)
            continue
        digest = _sha_bytes(target.read_bytes())
        hashes[rel] = digest
        if digest != entry.get("sha256"):
            mismatched.append(rel)
    if missing:
        problems.append("FILES_MISSING")
    if mismatched:
        problems.append("FILE_HASH_MISMATCH")
    content_sha = _sha("\n".join(f"{p}\n{hashes[p]}" for p in sorted(hashes))) \
        if hashes else ""
    if content_sha != manifest.get("content_sha256"):
        problems.append("CONTENT_SHA_MISMATCH")
    card_files = sorted(p for p in hashes if p.startswith(f"{CARD_DIR}/"))
    if len(card_files) != manifest.get("case_count"):
        problems.append("CASE_FILE_COUNT_MISMATCH")
    if not manifest.get("publishable"):
        problems.append("MANIFEST_NOT_PUBLISHABLE")
    for code in manifest.get("publish_blockers") or []:
        problems.append(code)
    library_sha = None
    if settings is not None:
        try:
            root = case_learning.resolve_root(settings)
            library_sha = case_learning.load_index(root)["sha256"] if root else None
        except AgentError:
            library_sha = None
        exported = (manifest.get("source") or {}).get("library_index_sha256")
        if library_sha and exported and library_sha != exported:
            problems.append("SOURCE_LIBRARY_CHANGED_SINCE_EXPORT")
    return {"status": "MIRROR_VERIFIED" if not problems else "MIRROR_PROBLEMS",
            "target": str(out), "case_count": manifest.get("case_count"),
            "file_count": manifest.get("file_count"),
            "content_sha256": content_sha,
            "expected_content_sha256": manifest.get("content_sha256"),
            "missing": missing, "mismatched": mismatched,
            "problems": sorted(set(problems)),
            "publishable": not problems,
            "library_index_sha256": (manifest.get("source") or {}).get(
                "library_index_sha256"),
            "current_library_index_sha256": library_sha,
            "library_checked": settings is not None,
            "no_writes": True}
