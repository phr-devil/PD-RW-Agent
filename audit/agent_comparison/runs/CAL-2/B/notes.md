# notes — CAL-2 / 项目 44 冻结快照（2026-11-16）

**核实到的（可直接引原文）**
- 身份：STATE.md 第 4 行把 PROJECT_ID=44 / PROJECT_ROOT=D:/workbuddy-work/44 记为 2026-11-15 自检「通过」，并称原 map 只有 example-project/37；EXP-001 复述同一事件。这是**申报之间的自洽**，没有任何登记表、签名或根目录内容在本 bundle 内。
- 规则提交：STATE.md 把 RULE_COMMIT=68e29c3… 标为「本地=远端」，核验手段写的是 2026-11-15 `git ls-remote origin HEAD`。这只查远端 HEAD。
- Run：两 Run 的 metrics.json 都存在；RUN-002 的 468 组 / 18 臂 / 26 折齐全，per_fold 均值与该记录宣称的 0.9846/0.9342、0.7937/0.7179 完全一致（我自己重算，不是引用）。
- 协议哈希：protocol v1 = 35239fa4…、v2 = b1b3557d…，与 STATE/EXP-003/EXP-004 里写的摘要一致；v2 自带 protocol_status=FROZEN_BEFORE_ANY_FITTING、frozen_at=2026-11-15T23:57:46+09:00（**文件内自述时间，不能证明先后顺序**）。
- 授权原文（STATE.md AUTH/BUDGET）：未授权＝新数据下载、付费、外传、READ_SEALED、正式绘图、论文正文、投稿、项目 STOP/PIVOT；2026-11-16 H8 消息再收紧为停止当前 D1 上的新增算法开发。

**组件实际贡献了什么**
- `context --project-id 44` → identity=UNKNOWN、identity_basis=EXPLICIT_PROJECT_ID、identity_verified=false、original_user_authorization=UNVERIFIED、workflow_commit_local_only=null、rule_freshness=REMOTE_NOT_CHECKED。这一条**有用**：它把「同一套文件」里能自动判为未验证的部分明确判成 UNKNOWN，而不是顺着 Markdown 说「已通过」。
- `verify-run RUN-002 / RUN-001` → 都是 RUN_HISTORY_NOT_ATTESTABLE / HISTORY_SOURCES_MISSING。这一条也有用，但原因在 bundle 缺件，不在 Run 本身。
- 其余基本没加东西：state_index 与 snapshot_excerpt 是 STATE/RESEARCH_RECORD 原文的截断回声（Skill 自己也说「tool echo of a Markdown line is not stronger evidence than the line itself」——正适用于此）。`rules` 直接 RULE_ROUTE_MISSING，没有任何规则被真正路由。

**没能核实的**
- 本地规则库检出与该提交是否一致（bundle 内无规则库；我也没有读 D:/workbuddy-agent/Problem-Data-Research-Workflow——不在允许读的范围内）。
- 身份是否为真：D:/workbuddy-work/44 不在 bundle 内，`project-map.local.json` 也不在，无法比对根。
- RUN-002 声明的 183,600 条预测与「独立复算 max|Δ|=0.0」：predictions.jsonl / verification.json / run_manifest.json / artifact_index.json 全部不在 bundle，metrics.json 内部也没有引用它们的摘要 ⇒ **无法绑定**，故 run.bindable=false。
- 作者原消息本身：只能看到 STATE/EXP-007 的转述，原消息不可得，故 grant_date 是「记录所称的日期」，不是已认证的日期。

**边界与授权问题（我看到的两处）**
1. STATE.md 的「PROJECT_IDENTITY_CHECK 通过」是项目**自检自记**，同一文件末尾自己写着「本文件不授权、不认证 SEALED 隔离」，但 §项目身份 的语气比这强得多——这是本 bundle 里最容易被误读为「已验证」的一行。
2. STATE.md 同时写 `SEALED = NOT_ACCESSED`（仅锁声明、无数据副本）与 `VAL = RESERVED_NOT_ACCESSED`；bundle 里确实没有 VAL/SEALED 目录，我也没有去找。所以「未访问」在这里是**结构上必然**，不是行为上的功劳——不能当合规证据用。

**我做的配置改动（必须披露）**
- 在工作区写了 `project-map.json`（schema_version=1，root 指向本工作区 inputs/）与 `wf_stub/{AGENTS.md,WORKFLOW.md}` 两张**标注为 STUB 的占位文件**，仅为让 CLI 载入 Settings。它们**不是** PD-RW 规则文本，`rules` 因此报 RULE_ROUTE_MISSING——即本次没有任何规则权威被实际行使，结论全部来自原始文件。
