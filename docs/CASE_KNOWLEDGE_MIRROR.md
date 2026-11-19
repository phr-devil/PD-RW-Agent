# 知识镜像：结构、导出、校验与发布范围

本文件记录 `src/pdrw_agent/case_knowledge.py` 的实现约定。WP6-A 只做本地只读派生镜像；
WP6-B 增加**发布范围（scope）**与「发布工作树 = git 仓库」的运行方式（见 §11）。

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
├── manifest.json          版本 / 数量 / 分布 / 文件清单 / 内容哈希 / 发布闸门 / scope
├── .gitattributes         `* -text`，保证克隆后字节不变（哈希才可比）
├── INDEX.md               紧凑总索引（表格）
├── cases/<CASE_ID>.md     稳定路径，不按学科或成败移动
├── indexes/cases.jsonl    程序化筛选（每行一案例，含 sha256）
├── indexes/lifecycle.jsonl 撤回与状态变化事件（不静默丢失历史）
├── indexes/stages/H3|H4|H6|H7|H8.md
├── indexes/topics/MECH-*.md, DOMAIN-*.md
├── insights/README.md     预留；不自动生成跨案例规律
└── docs/SCHEMA.md, docs/RETRIEVAL.md
```

全库导出实测：65 张案例、140 个内容文件（主题入口 61 个），加 `manifest.json` 共 141 个文件。

计数口径必须说清楚，否则会被误判为缺陷：

| 字段 | 含义 |
|---|---|
| `manifest.files` / `file_count` | 内容文件数（**不含** `manifest.json` 自己） |
| `manifest.file_count_including_manifest` | 目录内实际文件数 = `file_count + 1` |
| `file_count_semantics` | 固定为 `MANIFEST_EXCLUDED` |

原因是 manifest 无法列出（也无法哈希）自身。`case-knowledge-verify` 会同时报告
`file_count_including_manifest` 与磁盘实际文件数 `files_on_disk`，二者不等或存在
未受管文件时判为问题。

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
（该卡 + `INDEX.md` + `README.md` + `cases.jsonl` + `manifest.json`），其余 136 个文件
inode 不变；无改动重建时写入 0 个文件。

## 6.1 发布工作树的 `.git/`

镜像一旦同时是 git 工作树，原子替换就有个副作用：`out.rename(retiring)` 会把 `.git/`
一起带走，随后清理旧目录就等于删库。所以替换成功后必须把 `retiring/.git` 移回 `out/.git`
再清理；移动失败时保留旧目录并报 `VCS_PRESERVE_FAILED`，宁可留下可恢复的副本，也不静默丢仓库。

`.gitattributes`（`* -text`）由生成器写出并纳入 manifest，原因同上：Windows 上若发生
CRLF 转换，克隆后每个文件的 sha256 都会变，`verify` 会把一份完好的镜像判成被篡改。

## 7. 发布闸门

构建期（写入 `manifest.publishable` / `publish_state` / `publish_blockers`）：

| 阻断码 | 触发条件 |
|---|---|
| `INDEX_STALE_REBUILD_REQUIRED` | 案例卡比 `index.json` 新（索引过期） |
| `EXPORT_INCOMPLETE` | 实际导出数 ≠ 本次请求导出的范围大小（全库或 allowlist） |
| `CARD_COUNT_MISMATCH` | 范围内有卡片的源卡文件未能定位或哈希未知 |
| `PRIVACY_OR_CONTENT_BLOCKER` | 渲染内容命中隐私/凭据模式 |

校验期（`case-knowledge-verify --dir`，带 settings 时）：

| 阻断码 | 触发条件 |
|---|---|
| `SOURCE_LIBRARY_CHANGED_SINCE_EXPORT` | 当前 `index.json` 与 manifest 记录的哈希不同 |
| `FILES_MISSING` / `FILE_HASH_MISMATCH` / `CONTENT_SHA_MISMATCH` | 文件被删改 |
| `CASE_FILE_COUNT_MISMATCH` | `cases/` 文件数与 manifest 不符 |
| `UNMANAGED_FILES_PRESENT` | 目录里有 manifest 未登记的文件（`.git/`、`.gitignore` 等 VCS 元数据除外） |
| `SCOPE_COUNT_MISMATCH` | `scope.included` 与 `case_count` 不一致 |

`UNMANAGED_FILES_PRESENT` 是发布安全闸门，不是洁癖：任何未登记文件都会绕过哈希、
隐私扫描与人工审查被一起推送出去（例如误放的原始数据、`.env`、SQLite 库）。

隐私模式：Windows/Unix 绝对路径、邮箱、`sk-`/`ghp_`/`AKIA`/私钥块、
`password/secret/api_key/token` 赋值、11 位手机号。命中即整份镜像不可发布，
但卡片仍被写出并打上"发布阻断"标记——不静默丢弃，也不静默放行。

私有仓库不是隐私豁免：闸门对所有目标一致生效，`publishable=false` 的镜像不得推送。

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
pdrw-agent ... case-knowledge-build --out <目录> \
  --scope-file <allowlist.json>                 # 定向子集（发布白名单）
pdrw-agent ... case-knowledge-verify --dir <目录>            # 校验并给发布判定
```

`--scope-file` 接受 `{"case_ids": [...]}` 或裸数组；清单里的任一 `CASE_ID` 不在库中即
报 `SCOPE_CASE_NOT_FOUND`（防止笔误变成静默的空发布）。

## 10. 未做与边界

- 不生成 `insights/` 的跨案例规律：自动归纳会把标签相似当作科学等价。
- 不做网络请求、不上传、不 push；镜像构建与发布是两个动作。
- 不改 `CASE_LIBRARY`、科研 Run、`STATE/EVENTS`、`SEALED`。
- `evidence_grade=REVIEW_REQUIRED`（内部卡缺少 `evidence_role` 时）保持原样，
  与 MCP 检索的判定完全一致，不在此处"补齐"。

## 11. 发布范围与发布工作树（WP6-B）

### 11.1 为什么需要 scope

"这张卡在库里"与"这张卡可以离开本机"是两个判断。后者取决于未公开数据、内部文件引用、
合作者授权等与证据强度无关的因素，所以不能靠手工删卡实现——那会让索引与卡片互相矛盾，
下一次导出又会把删掉的卡长回来。

`--scope-file` 给出一个 `CASE_ID` 白名单，**所有索引、JSONL、manifest 都只由这份子集生成**，
因此子集内部依然自洽。manifest 记录：

```json
"scope": {"mode": "ALLOWLIST", "included": 5, "library_total": 65, "excluded": 60,
          "excluded_case_ids": ["..."], "scope_sha256": "...", "note": "..."}
```

全库导出时为 `{"mode": "FULL", "included": 65, "library_total": 65, "excluded": 0}`。
`INDEX.md` / `README.md` / `AGENTS.md` 都会写明"定向子集 N/M 张，检索不到 ≠ 该经验不存在"，
避免读者把子集当成全库。

### 11.2 发布工作树

发布工作树就是镜像目录本身，里面额外有 `.git/`：

```text
PD-RW-Case-Knowledge          全库镜像（65 张，本地权威知识的完整视图，无 VCS）
PD-RW-Case-Knowledge-remote   发布工作树（按 scope 生成，含 .git/，推送到 GitHub）
```

两者都由同一个生成器产出，不存在"GitHub 上手工维护的第二套正文"。

原子替换必须显式保住 `.git/`：它在目录级 `rename` 中会随旧目录一起被删除。实现上在
`building → out` 成功后把 `retiring/.git` 移回 `out/.git` 再清理旧目录；移动失败则
保留旧目录并报 `VCS_PRESERVE_FAILED`（可恢复），不静默丢仓库。

`<name>.state.json` 仍写在镜像外层，不进入任何被推送的内容。

### 11.3 发布流程（单向）

```text
本地 CASE_LIBRARY（权威）
  → case-knowledge-build --out <发布工作树> --scope-file <白名单>
  → case-knowledge-verify --dir <发布工作树>        # 必须 publishable=true
  → git -C <发布工作树> status/diff                 # 变更预览（人看这一步）
  → git commit -m "..." && git push                 # 只有在明确授权后
  → GitHub 私有仓库 → ChatGPT / Codex 只读检索
```

反向永远不成立：ChatGPT 或镜像都不能回写本地案例、Run、`STATE/EVENTS` 或 `SEALED`。

### 11.4 生命周期事件与 scope

被 scope 排除的卡片会记为 `CASE_RETIRED` 且 `reason=SCOPE_EXCLUDED`，
与源记录真被删除（`SOURCE_RECORD_REMOVED`）区分开——缩小发布范围不等于删除历史依据。
