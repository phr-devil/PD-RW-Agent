# SCIENCE-03C — 可信 Run 绑定与自主科研决策（v0.9.11）

- 仓库：`D:/workbuddy-agent/PD-RW-Agent`
- 基线：`1318732`（v0.9.10，PR #22 的 HEAD）
- 分支：`science/03c-run-binding`（独立分支，不触 `main`）
- 日期：2026-11-20
- 版本：0.9.10 → 0.9.11

本轮不新增数据库、多 Agent 调度器、评分器或第二套科研流程；改动集中在 `science/decision.py`、
`science/probe_frontier.py`、`science/feedback_link.py`、`science/cli.py`、Skill 参考文档与 21 条边界测试。

## 1. 实际修复的缺陷（先复现）

`audit/science03c/binding_prefix.py` 的输出（`binding_prefix_before.json` → `binding_prefix_after.json`），
用项目 48（PoPu）的真实 Run 目录：

| 声明 | 修复前 | 修复后（带 `--project-root`） |
| --- | --- | --- |
| `DEV/runs/RUN-999`（不存在） | `status_verified: true` → `HISTORICAL_EVIDENCE_ONLY` | `false` → `CLOSURE_DECLARED_NOT_VERIFIED`，`file_binding: UNRESOLVED` |
| `../MCS-HEMO-26/...`（跨项目） | `true` → `HISTORICAL_EVIDENCE_ONLY` | `false` → `CLOSURE_DECLARED_NOT_VERIFIED`，绑定被拒 |
| `RUN-005/attempt-1-invalid-anchor`（记录自称 INVALID） | `true` → `HISTORICAL_EVIDENCE_ONLY` | `false` → `STATUS_CONFLICT`，`status_consistency: CONFLICT` |
| `DEV/runs/RUN-005`（真实且一致） | `true` | `true` → `HISTORICAL_EVIDENCE_ONLY`（唯一被验证的路径） |
| 真实 Run，但**没有** `premise_id` | `true` → 当作本前提已关闭 | `false` → `CLOSURE_PREMISE_UNBOUND`，进入 `premise_unbound_ids` |
| 真实 Run，`premise_id` 指向别的前提 | `NOT_YET_RUN`（原本正确） | 不变 |

根因是 `verified = status != "NOT_EXECUTED" and bool(texts["run_ref"])`——只检查字符串非空。

修法是五个**分开**的轴，只有最后一个才是推断：

```
reference_present → file_binding → status_consistency → premise_binding → status_verified
```

`file_binding` 由 `feedback_link.bind_run_reference()` 完成：复用该模块既有的 `_resolve`
（拒绝 `..`、拒绝 SEALED/holdout/confirmation）、`_read_json` 与 `_sha256`，只读一个 ≤128 KiB 的记录文件，
回报 `run_id/status/verdict/anchor_pass`。没有新增验证器，也没有新账本。

两处新增的判定，都不关闭前提、也不淘汰候选：

- `STATUS_CONFLICT`：Run 记录与声明矛盾（例如把 INVALID 的尝试声明为有效关闭）；
- `CLOSURE_PREMISE_UNBOUND`：关闭声明从未写出前提。既不能当作已关闭（会错误淘汰在用探针），也不能直接重跑（会浪费）。

`status_verified` 保留原名，语义收紧为"绑定 + 一致 + 同前提"；没有项目根时一律 `file_binding: NOT_CHECKED`，
`run_binding_checked: false`。载荷另加 `authorization_basis: CALLER_DECLARED_ONLY_NEVER_A_PERMIT`——
包里的授权布尔值是调用方陈述，不是执行许可。

第三条（C 段暴露）：`REFERENCE_NOT_LEGAL` 会把"oracle upper bound and deployable arm"这类**并列诊断臂**判成非法参照，
使一个合法决定性探针被从"合法"里剔除（`no_legal_decisive_probe` 变 true）。改为匹配前先剥掉明确命名的
`oracle/diagnostic upper bound`；把 oracle **当作**参照（"oracle labels at test time"）仍然判非法。

## 2. 真实回放：四种有效性状态，四种不同下一行动

四个决策点都用项目 48 的既有 Run 文件，一条命令一次，`--project-root D:/workbuddy-work/48`。
工件：`audit/science03c/session3/{d1..d4}*.json|out.json`。

| 决策点 | 声明 | `applicability` | `next_action` | 前沿 |
| --- | --- | --- | --- | --- |
| RUN-005 已回答可靠性前提 | COMPLETED_VALID | `HISTORICAL_EVIDENCE_ONLY` | `KEEP_AS_RECORDED_EVIDENCE_DO_NOT_RERUN` | 空 |
| `attempt-1-invalid-anchor` | COMPLETED_INVALID | `TARGETED_REPAIR` | `REPAIR_NAMED_DEFECT_FIRST` | 空 |
| RUN-003（偏 oracle） | INCONCLUSIVE | `AWAIT_NEW_INFORMATION` | `HOLD_UNTIL_NEW_INFORMATION_EXISTS` | 空 |
| 同上 + 指名新信息 | INCONCLUSIVE | `REVISIT_ON_NEW_INFORMATION` | `REVISIT_ONLY_IF_NEW_INFORMATION_CHANGES_JUDGMENT` | 空 |
| 几何配准（新实验） | NOT_EXECUTED | `NEEDS_AUTHORIZATION` | `OBTAIN_AUTHORIZATION_FIRST` | 空 |

`VALID_POS` 在本语料里**没有**可用的真实正性 Run（八个 Run 全是 NEG / INCONCLUSIVE / INVALID），
因此该分支只有测试夹具覆盖，行为学结论标 `NOT_MEASURED`。

## 3. 回放暴露的真实缺口：裸 Run ID 不可解析

03B 的包写的是 `"RUN-005"`，带根目录后解析不到任何文件，两个关闭声明都变成
`CLOSURE_DECLARED_NOT_VERIFIED`（`session3/bare.out.json`）。这本身诚实，但读者容易理解成
"记录坏了，重跑一次"。改成 `"DEV/runs/RUN-005"` 后两者都绑定成功并成为记录证据
（`session3/bound.out.json`）。

处理：Skill 的 `execution.md` 写明 `run_ref` 必须是项目相对路径，并给出四行状态→行动映射表；
未解析的关闭，`next_action` 恒为 `VERIFY_RUN_BEFORE_DECIDING`，从不是 `RUN`。没有为此加检查器。

## 4. B 段：项目 48 只读复核

复核 `RUN-005`、`PROJECT-48-DEFECT-005`、原协议与两项修订。结论与来源已追加为
`D:/workbuddy-work/48/STATE.md` 的 `§勘误 · SCIENCE-03C`（只追加，不改任何 Run、数字或判定）：

1. **配对效应与单条件抖动被混用**（措辞问题，判定不变）。`M3−M1` 是受试者级配对对比
   （`intensity_mae_delta = -0.05891`、`cohens_dz = -0.1913`、CI `[-0.23376, 0.10361]`、12 折），
   0.271 是单条件边际抖动（3 折平均）。两者不能直接比大小；该配对 CI 未含 seed 抖动、**偏乐观**，
   但 CI 已跨 0 且 dz 很小，结论不会翻。
2. **AMENDMENT-001 之后的中间运行没有独立工件**：被最终运行覆盖，只剩 amendment 里的数字
   （anchor 9.183602 vs 9.139519）。标 `INTERMEDIATE_ATTEMPT_ARTIFACT_ABSENT`，不重建、不补造。
3. **成本行少计一次运行**：记录 3 次，实际执行 `run_dev005.py` 4 次；缺的墙钟时长记 `NOT_RECORDED`。

未发现问题的项：RUN-005 负结果的适用范围已在 STATE 与 RUN-005_RESULT 中限定为
"本 12 人 DEV 子集 / 本模型族 / 本可部署输入"，并明写"不判物理不可恢复、非项目失败"，**没有**被推广成
"所有可部署算法均不可辨识"；`HOLD_RELIABILITY` 与 `H8_PENDING` 分开记录；两项修订都写明触发条件并声明
未因看到结果放宽判定。

## 5. 成本与执行轨迹

- 工具轨迹：读 6 个项目文件（RUN-004/005 metrics、RUN-005_RESULT、两项 amendment、STATE×2、contrast 类无）、
  写 6 个包 + 8 个 CLI 输出、12 次 CLI `decision` 调用（含 4 次带根目录）、0 次训练、0 次下载、0 次 SEALED。
- 墙钟：CLI 单次 < 0.2 s；本轮代码与测试约 30 分钟；`pytest` 全量 38.7 s。
- 测试：**568 passed / 8 skipped / 151 subtests**（基线同 checkout 546，+21 条新测试、1 条旧断言改为对抗性）。
- 评测：`case_decision_eval` 9/10（V9 因本 checkout 无 `mcp` SDK 跳过，基线同）；`case_gate_eval` 17/17；
  V1/V2/V3 载荷 15 512 / 12 824 / 15 787 逐字未变。
- 载荷（紧凑 JSON 字符代理，非 token）：干净双探针 3 541 → 3 726（+5.2%）；三个缺陷包 10 429 → 10 984（+5.3%）；
  带 3 个真实关闭声明的包 6 706 → 8 180（+22%，约 490 字符/关闭探针）。
- MCP 仍 24 工具、profiles 11/21/24，无新增。

## 6. 科研结果与不确定性

- 本轮的科研产出是**一个决策修正**与**一个证据绑定修正**，不是新实验结论：
  - RUN-004 的不确定性表述被改对（配对 CI 才是该对比的误差，且它偏乐观），结论仍是 NEG；
  - 关闭声明的可信度现在可机检，裸 ID 不再被当作已关闭证据。
- 未执行任何新 DEV：唯一有 H7 授权的项目（48）已 `HOLD`，其余项目是零拟合只读或需新授权。
  因此"Agent 能连续完成授权内技术工作"本轮只有代码与回放证据，**没有**新的实验执行证据。
- `VALID_POS` 分支未在真实数据上跑过。
- "模型更会做科研决策"仍是 `NOT_MEASURED`：单会话、单项目、且检查器与包都由同一模型撰写。

## 7. 是否具备进入 SCIENCE-04 的条件

部分具备。基础设施层面已经够用：执行状态可绑定、四种有效性状态给出不同行动、前沿不再被"便宜的已关闭探针"占据。
缺的是**独立对照**：同一批冻结任务、由未参与补丁的人写包、两个模型版本各跑一次、由第三方评阅。
建议 SCIENCE-04 只做这件事，不再加检查器。
