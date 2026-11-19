# WP6-A 知识镜像：结构、导出与校验

本文件记录 `src/pdrw_agent/case_knowledge.py` 的实现约定。它只描述**本地只读派生镜像**，
不涉及 GitHub 私有仓库发布（那是 WP6-B）。

## 1. 架构位置

```text
CASE_LIBRARY（权威，只读）
  -> PD-RW-Case-Knowledge/（本模块生成，确定性、可增量）
  -> 未来 GitHub 私有仓库
  -> ChatGPT（文件读取）/ Codex（JSONL+搜索）/ WorkBuddy（SQLite+MCP）
```

权威来源永远是 `CASE_LIBRARY` 与对应科研 Run。镜像不产生新的科学事实，
不改写 `CASE_ID`，不复制论文全文，不抓取 URL，不上传、不推送。

## 2. 核心模块

| 文件 | 职责 |
|---|---|
| `src/pdrw_agent/case_export.py` | 单卡渲染。`render_markdown_card`（v1，WP5 契约不变）+ `to_knowledge_record` / `render_knowledge_card`（v2 知识 Schema） |
| `src/pdrw_agent/case_knowledge.py` | 批量导出、索引生成、增量维护、原子替换、发布闸门、`verify` |
| `src/pdrw_agent/case_learning.py` | 检索（复用 `search_cases.py`）+ 长查询宽松召回回退 |
| `src/pdrw_agent/service.py` | `build_case_knowledge` / `verify_case_knowledge` 处理器（不注册为 MCP 工具） |
| `src/pdrw_agent/cli.py` | `case-knowledge-build` / `case-knowledge-verify` |

不新增 MCP 工具：可见工具面仍是 minimal 11 / research 21 / diagnostic 24。

## 3. 目录与文件

```text
PD-RW-Case-Knowledge/
├── README.md              只读说明与目录表
├── AGENTS.md              三个 Agent 的统一读取约定
├── manifest.json          版本 / 数量 / 分布 / 文件清单 / 内容哈希 / 发布闸门
├── INDEX.md               紧凑总索引（表格，65 行）
├── cases/<CASE_ID>.md     稳定路径，不按学科或成败移动
├── indexes/cases.jsonl    程序化筛选（每行一案例，含 sha256）
├── indexes/lifecycle.jsonl 撤回与状态变化事件（不静默丢失历史）
├── indexes/stages/H3|H4|H6|H7|H8.md
├── indexes/topics/MECH-*.md, DOMAIN-*.md
├── insights/README.md     预留；不自动生成跨案例规律
└── docs/SCHEMA.md, docs/RETRIEVAL.md
```

当前实测：65 张案例、140 个文件（其中主题入口 61 个）。

## 4. Schema v1 的三类字段

1. **直映射**：`case_id/title/source_refs/premises/counterexamples/...` 原义保留。
2. **显式映射**：`source_type`←`origin`、`outcome`←`verdict`、`problem_tags`←`mechanisms`、
   `domains`←`research_domains`、`conditions`←`applicability.conditions`、`results`←卡上
   `evidence[].claim`、`research_problem`←`title`（`research_problem_basis=TITLE`）。
3. **派生或未知**：`h_stages` 由机制标签路由派生（`h_stages_basis` 说明依据）；
   `status_class` 由状态文本分类；`source_group_id` 由文献标识聚类得到；
   源记录没有的字段一律 `UNKNOWN`（例如 `updated_at`）。

变化检测不用文件时间：用 `source_digest`（源记录规范化 JSON 的 sha256）与
`source_card_sha256`。案例库级哈希只写进 `manifest.json`，**不写进每张卡**，
否则任一案例改动都会导致全库重写，增量维护失效。

## 5. 同源判定

- 标识来源：`source_refs`、`evidence_paths`、卡上 `evidence[].source` 中的
  DOI / arXiv / PMID / PMCID / OpenReview。
- `source_ids`：该卡声明的全部标识。
- `source_group_id`：共享任一标识的卡片用并查集聚为一簇，簇 ID 取最小 `CASE_ID`
  （`SRC-<CASE_ID>`）。
- 聚合卡（`evidence_class=REPAIR_PROTOCOL`，或引用 ≥5 个独立来源）不参与聚类，
  单独记为 `SRC-AGG-<CASE_ID>`，避免一个修复索引吞掉三篇不同论文。
- `same_source_cases`：直接共享标识的其他卡片，用于提示"这不是独立证据"。

实测：65 张属于 63 个来源簇；`EXT-C04/EXT-C05`、`EXT-N01/EXT-N02` 各为一簇；
`EXT-REPAIR-01` 独立成簇。

## 6. 增量与原子替换

1. 在内存中渲染全部文件，计算逐文件 sha256 与 `content_sha256`。
2. 在 `.<name>.building-<pid>` 暂存目录生成：内容未变的文件用**硬链接**指向旧镜像
   （inode 不变，文件未被改写），只有变化或新增的文件才写入新内容。
3. 校验暂存树完整性后，`out → .<name>.retiring-<pid>`，`building → out` 目录级原子替换；
   替换失败则把旧镜像改回原名，暂存目录清理。
4. 清理旧目录；状态文件 `.<name>.state.json` 写在镜像**外层**，不进入镜像内容。

实测（在案例库副本上修改单张卡）：只重写 5 个文件
（该卡 + `INDEX.md` + `README.md` + `cases.jsonl` + `manifest.json`），其余 135 个文件
inode 不变。

## 7. 发布闸门

构建期（写入 `manifest.publishable` / `publish_blockers`）：

| 阻断码 | 触发条件 |
|---|---|
| `INDEX_STALE_REBUILD_REQUIRED` | 案例卡比 `index.json` 新（索引过期） |
| `EXPORT_INCOMPLETE` | 导出数与索引 `case_count` 不一致 |
| `CARD_COUNT_MISMATCH` | 导出数与磁盘卡数不一致 |
| `PRIVACY_OR_CONTENT_BLOCKER` | 渲染内容命中隐私/凭据模式 |

校验期（`case-knowledge-verify --dir`，带 settings 时）：

| 阻断码 | 触发条件 |
|---|---|
| `SOURCE_LIBRARY_CHANGED_SINCE_EXPORT` | 当前 `index.json` 与 manifest 记录的哈希不同 |
| `FILES_MISSING` / `FILE_HASH_MISMATCH` / `CONTENT_SHA_MISMATCH` | 文件被删改 |
| `CASE_FILE_COUNT_MISMATCH` | `cases/` 文件数与 manifest 不符 |

隐私模式：Windows/Unix 绝对路径、邮箱、`sk-`/`ghp_`/`AKIA`/私钥块、
`password/secret/api_key/token` 赋值、11 位手机号。命中即整份镜像不可发布，
但卡片仍被写出并打上"发布阻断"标记——不静默丢弃，也不静默放行。

## 8. 检索约定

`docs/RETRIEVAL.md`（生成在镜像内）定义顺序：`manifest → 阶段/主题索引 → 候选卡 →
必要时原始证据`。工程侧改动只有一处：

- 长自然语言查询若在原有单关键词路径上零命中，则抽取 2–5 个核心概念
  （西文词 + 中文 2–4 字 n-gram + 固定的概念别名表），做并集召回，
  再按"概念命中权重 → 覆盖数 → 适用条件/前提用词重合 → 原检索分数"重排。
- 已声明的硬过滤（mechanism/domain/verdict/...）在回退路径中依旧生效，
  所以"不存在的机制"仍是 `NO_CASE_MATCH`，不会被宽松召回掩盖。
- 输出新增 `retrieval_mode`、`recall_terms`、`source_independence`；
  同源卡片只算一份独立证据。

## 9. 命令

```bash
pdrw-agent --project-map <map> --workflow-root <rules> \
  case-knowledge-build --out <目录>              # 增量（默认）
pdrw-agent ... case-knowledge-build --out <目录> --full      # 全量重建
pdrw-agent ... case-knowledge-build --out <目录> --dry-run   # 只出计划
pdrw-agent ... case-knowledge-verify --dir <目录>            # 校验并给发布判定
```

## 10. 未做与边界

- 不生成 `insights/` 的跨案例规律：自动归纳会把标签相似当作科学等价。
- 不做 GitHub 同步、不建私有仓库、不上传、不改 `main`。
- 不改 `CASE_LIBRARY`、科研 Run、`STATE/EVENTS`、`SEALED`。
- `evidence_grade=REVIEW_REQUIRED`（内部卡缺少 `evidence_role` 时）保持原样，
  与 MCP 检索的判定完全一致，不在此处"补齐"。
