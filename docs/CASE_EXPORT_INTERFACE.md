# CASE_LIBRARY → Markdown 经验卡导出接口（v1 契约，v0.8.2 引入，v0.9.0 起为批量导出的内层）

本文件只定义**接口与数据映射**。本轮不创建 GitHub 私有仓库、不上传任何案例、
不修改 `CASE_LIBRARY` 的 65 张原始案例，也不引入新的数据库框架。

## 1. 定位

- 源码：`src/pdrw_agent/case_export.py`
- 服务入口：`ResearchService.call("export_case_markdown", case_id=...)`
- 读取依赖：`case_learning.resolve_root()` + `case_learning.load_index()`（只读，
  复用现有 `index.json` 与 `cases/*.md`；后续可由本地 SQLite 行提供同一 record 形状）
- 不注册为 MCP 工具：本轮不新增工具面，避免扩大可见工具与权限边界

## 2. 输入

| 项 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `settings` | `Settings` | 是 | 仅用于解析案例库根目录（`PDRW_CASE_LIBRARY_ROOT` 或 `case_library_root`） |
| `case_id` | `str` | 是 | 必须已存在于 `index.json`；不存在返回 `CASE_NOT_FOUND` |

不接受的输入：任意文件路径、URL、远端仓库地址、待写入目录。该接口不读取
`CASE_LIBRARY` 之外的路径，也不发起网络请求。

## 3. 输出

```json
{
  "status": "MARKDOWN_CARD_RENDERED_NOT_WRITTEN",
  "export_version": "1.0",
  "case_id": "EXT-C02",
  "markdown": "---json\n{...}\n---\n\n# ...",
  "sha256": "<整卡 sha256>",
  "body_sha256": "<正文 sha256>",
  "front_matter": {"case_id": "...", "verdict": "...", "status": "...",
                   "origin": "...", "evidence_class": "...",
                   "evidence_levels": ["..."], "research_domains": ["..."],
                   "mechanisms": ["..."], "related_cases": ["..."],
                   "evidence_paths": ["cases/..."], "source_refs": ["..."],
                   "query_fingerprint_sha256": "...",
                   "library_index_sha256": "...", "export_version": "1.0",
                   "scientific_equivalence_verified": false,
                   "authorization_granted": false},
  "source": {"library_root": "...", "library_index_sha256": "...",
             "index_stale": false, "evidence_paths": ["..."]},
  "no_writes": true, "sync_performed": false, "authorization_granted": false
}
```

`status` 永不表示“已发布/已同步”。`sha256` 可用于后续增量同步的幂等键；
`library_index_sha256` 用于判断案例库版本是否变化。

## 4. 字段映射（索引字段 → Markdown）

| Markdown 位置 | 索引字段 | 缺失时 |
|---|---|---|
| JSON front matter | `case_id/title/verdict/status/origin/evidence_class/evidence_levels/research_domains/mechanisms/related_cases` | 保留空值，不推断 |
| `## 前提` | `premises` | 省略该节 |
| `## 适用条件` | `applicability.conditions` | 省略该节 |
| `## 适用边界` | `applicability.boundaries` | 省略该节 |
| `## 反例` | `counterexamples` | 省略该节 |
| `## 可迁移经验` | `transferable_lesson` | 省略该节 |
| `## 最小验证` | `next_minimal_check` | 省略该节 |
| `## 成功条件` | `success_notes` | 省略该节 |
| 标题行补充 | `scope_warning` | 省略该行 |

不进入卡片的字段：`search_blob`（派生检索文本，体积大且可重建）、
`legacy_refs`、`source_paths`（改为 front matter 的 `evidence_paths`/`source_refs`）。

## 5. 不变量

1. 同一 record + 同一 `library_index_sha256` ⇒ 字节级相同的 `markdown`。
2. 渲染器不写入任何文件；落盘由后续阶段在独立目录完成。
3. 卡片固定声明 `scientific_equivalence_verified=false`、
   `authorization_granted=false`：导出不等于证据升级或授权。
4. `index_stale=true` 时仍可渲染，但必须在同步阶段拒绝把旧卡当新证据推送。
5. 弱证据（`UNVERIFIED_REPORT` 等）与 `ARCHIVE/DROP` 状态原样保留在
   `evidence_class`/`status` 中，不做“升级”或隐藏。

## 6. 下一阶段（不在本轮）

从本地 SQLite 行构造同一 record 形状 → 调用 `render_markdown_card()` →
写入仓库外的导出目录 → 人工确认后才允许提交到私有 Markdown 仓库。

## 7. v0.9.0 起的分层（WP6-A）

本文件的 v1 契约（`render_markdown_card`，单卡即时渲染、不落盘）**保持不变**，
作为最小可用接口继续存在。批量导出走另一层：

| 层 | 入口 | 输出 |
|---|---|---|
| v1 单卡即时渲染 | `case_export.export_case_markdown(settings, case_id)` | 内存中的 Markdown，`no_writes=true` |
| v2 知识 Schema | `case_export.to_knowledge_record` + `render_knowledge_card` | Schema 1.0 卡（证据等级、同源簇、阶段路由、源摘要） |
| 镜像构建 | `case_knowledge.build(settings, out_dir)` | `manifest.json` / `INDEX.md` / `cases/` / `indexes/` / `docs/` |

v2 与 v1 共享同一条读取路径（`case_learning.resolve_root` + `load_index` + 卡 front matter），
因此不会出现两套"案例记录"。完整字段表与闸门见
[`docs/CASE_KNOWLEDGE_MIRROR.md`](CASE_KNOWLEDGE_MIRROR.md)。
