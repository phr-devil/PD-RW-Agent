# notes（CAL-2 / 项目 44 冻结快照 2026-11-16）

## 已核实（可直接复算）
- bundle 仅 8 个文件；无 `VAL/`、`SEALED/` 目录，故 prompt 的禁令未被触发，也未推断其内容。
- 协议哈希：v1 sha256 `35239fa4…`（11667 B）、v2 `b1b3557d…`（22055 B），与记录中的 `35239fa4…`/`b1b3557d…` 前缀一致；v2 `frozen_at` 2026-11-15T23:57:46+09:00。
- RUN-002 `metrics.json`：411,202 B，sha256 `da112269…`；468 组 = 26 折 × 18 臂，Σn = 183,600，与协议 v2 `n_arms/n_fold_arm_combinations/expected_prediction_records` 逐项相符（10200×18 亦为 183,600）。
- 关键数值复算一致：RAW 0.9846/0.9342、DEMEAN 0.7621/0.7233、NORM 0.9992/0.9183、BOTH 0.7937/0.7179、SHORTCUT 0.7604/0.7238；DC 效应 +0.2225、幅值效应 −0.0146、BOTH−SHORTCUT +0.0333。
- RUN-001 `metrics.json`：207,982 B，169 组、7 臂、Σn=66,600，与其记录一致。

## 未能核实
- 规则 commit `68e29c3…`：规则库 `D:/workbuddy-agent/Problem-Data-Research-Workflow` 在 bundle 外、无网络 ⇒ 只记录为「文件中的断言」，不当作已验证事实。
- `project-map.local.json`、`PAPER_BLUEPRINT.md`、`run_manifest.json`、`verification.json`、`predictions.jsonl`、`V2_RESULT.md`、`paired/` 均不在 bundle ⇒ 「协议先于拟合」「468 组最大绝对差 0.0」「627 项检查」都无法在我这里复算。
- `metrics.json` 内部无 `sha256`/`manifest`/`commit`/`status` 字段；`VALID / METRIC_VERIFIED_DEV_ONLY` 是 Markdown 判断，不是工件字段（JSON 中 `status` 只作为普通词出现）。
- 记录中的 MCP 事实（`get_project_context(44)`→`SOURCE_REVIEW_REQUIRED`、`preview_experiment_record`→`INVALID_RUN_CONTRACT`）未复跑：本会话无该工具，且禁止调用 pdrw/PD-RW 组件。按 prompt：工具回显一行 Markdown 并不比那行本身更强。
- 作者原消息不在 bundle，只有转述引用 ⇒ 授权是二手引证（第二手证据），非原件。

## 边界与授权问题
- 身份是自指闭环：`PROJECT_ID=44` 由 STATE.md 声明，映射 `44` 由同一 agent 在 EXP-001 写入；2026-11-14 报告 §6.7 当时仍写 `NOT_REGISTERED`。故 DECLARED_ID_MATCH 而非 VERIFIED。
- STATE.md 自述「本文件不授权」；授权来源是 2026-11-15 原消息（转述）。2026-11-16 H8 方案 A 进一步收紧：停止 D1 上新算法开发、`NEXT_ACTION = NONE`、`ASSET_FREEZE` 只读。
- 项目自认无 OS 级 SEALED 隔离（EXECUTION_ASSURANCE §1 转述），`SEALED=NOT_ACCESSED` 仅为流程声明 + 哈希可复核。
- ERRATUM-001 显示定义级错误（条件比率分母互换）未被 627 项复算拦截 ⇒ 该项目「verified」只等于算术/分区一致，不等于定义正确。
- 未读到任何允许「新下载 / SEALED / 绘图 / 写作 / 外传」的语句；也不存在允许把负结果写成「等价」或「已证实为采集伪影」的语句。
