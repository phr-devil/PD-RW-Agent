# SCIENCE-03B｜真实科研执行闭环与历史实验复用（v0.9.10）

- 基线：PR #21 HEAD `c6e045e`（v0.9.9）｜分支 `science/03b-dev-loop`（独立，不合并 main）
- 时间：2026-11-20（GMT+9）
- 环境：Windows / Python 3（`PYTHONPATH=src`），CPU；仓库 `D:/workbuddy-agent/PD-RW-Agent`
- 一句话：把"已关闭的实验不再被推荐为下一实验"做成可执行字段，用三个冻结历史决策点验证，再在一个真实 DEV 项目里跑完一次完整闭环（结果是否定的，但闭环成立）。

---

## A. 修复：已关闭探针的重复推荐

### A.1 先复现（v0.9.9 原样）

`audit/science03b/probe_reuse_prefix.py`，三个包全部来自 RCT-CONTACT-26 的真实记录：

| 包 | 修复前 frontier | 修复前 dominated |
| --- | --- | --- |
| REUSE-A（已按用户决定关闭的 DEV 斜率探针，LOW） | `[R1-DEV-SLOPE]` | `R2-CONTROLLED-PRESS`、`R3-SENSOR-SWAP` 都被它支配 |
| REUSE-B（INVALID 的符号变换探针） | `[R1-INVALID-TRANSFORM]` | 合法探针全被支配 |
| REUSE-C（调用方声称"已完成"但无 Run 引用） | `[R1-DECLARED-CLOSED]` | `R2-CONTROLLED-PRESS` |

修复后：

| 包 | frontier | 归类 |
| --- | --- | --- |
| REUSE-A | `[R3-SENSOR-SWAP]` | `R1` → `historical_evidence_ids` |
| REUSE-B | `[R3-SENSOR-SWAP]` | `R1` → `repair_required_ids` |
| REUSE-C | `[R2-CONTROLLED-PRESS]` | `R1` → `unverified_closure_ids` + finding `EXECUTION_DECLARED_NOT_VERIFIED` |

原始输出：`probe_reuse_prefix.json`（前）、`probe_reuse_after.json`（后）。

### A.2 改法

- `probe_frontier.py`：支配关系只在 **runnable** 集合内计算。runnable = 区分 ≥1 对 ∧ 无 `REFERENCE_NOT_LEGAL` ∧ `applicability == NOT_YET_RUN`。
- `decision.py`：新增可选字段 `prior_execution`（`status/run_ref/premise_id/conclusion/new_information/requires_new_authorization`），逐探针输出 `applicability` 与 `next_action`；新增 finding `EXECUTION_DECLARED_NOT_VERIFIED`（规则 `SCIENCE_RESULT_HARVEST §RUN_EVIDENCE`，先例 CASE-20/CASE-21）。
- 分类：`HISTORICAL_EVIDENCE_ONLY`、`TARGETED_REPAIR`、`REVISIT_ON_NEW_INFORMATION`、`AWAIT_NEW_INFORMATION`、`NEEDS_AUTHORIZATION`、`BLOCKER_UNRESOLVED`、`CLOSURE_DECLARED_NOT_VERIFIED`、`NOT_YET_RUN`。
- 新标志 `no_executable_next_probe` 与既有 `no_legal_decisive_probe` 分开：前者=合法且可区分但没有现在能做的；后者=所有能区分的都用了非法参照。
- 无删除、无 STOP、无新审批、无必填字段；旧包（不带该字段）行为逐字不变。

### A.3 真实项目上的效果

`audit/science03b/session2/popu_next_action.json`（项目 48，按 RUN-004/005 的实际状态）：

| | frontier | dominated | 结论 |
| --- | --- | --- | --- |
| 修复前 | `[P-POSTURE-VARIANTS-RERUN, P-RELIABILITY-GATE]` | `P-SECOND-LIBRARY` ← 被已关闭的 P1 支配 | 建议重跑已关闭分支 |
| 修复后 | `[]` | `[]` | 两个已完成=历史证据，第二库=需授权，`no_executable_next_probe=true` |

---

## B. 真实 DEV 闭环（项目 48 / PoPu，RUN-005）

### B.1 恢复与授权核对

- 状态：`ACTIVE`，`REVIEW:H7 delegated`（2026-11-17 原消息："普通编码/调参/消融/修复 Agent 自主"），`H8` 未裁定。
- 数据：`PoPu_data_no_segments.zip`（77,189,574 B，SHA-256 `c0788650…dc91`），只读；派生缓存 `DEV/cache/`。
- 已有 Run：RUN-001（60 折）、RUN-002/003/004（固定 12 人 DEV 子集）；`SEALED` 未访问。
- 判断：本轮问题落在作者已选 H6-A「可恢复性**与可靠感知**」的可靠感知一半，不新增数据、不改 Claim、不碰 SEALED/写作 → H7 授权内；H8 贡献判断仍交作者。

### B.2 尚未解决的阻碍（不是重复实验）

RUN-001/002/003 已回答"下层 72 通道是否有可部署增量"（否），RUN-004 已回答"细分姿态中间表示是否有独立价值"（否）。两者对该前提均已关闭。
未回答的是：**恢复失败的那些帧能否在预测时被识别**（把目标从强度换成误差）。这是不同目标、不同标签、不同判据，不是把旧实验再跑一遍——这一点用 A 的功能在决策包里显式登记，避免误判为"新问题"。

### B.3 设计与成本

- 协议 `PROTO-POPU-RELIABILITY-v5-DEV005`（拟合前冻结）+ `AMENDMENT-001`（训练集对齐）+ `AMENDMENT-002`（seed 与抖动基线）。
- B0：RUN-004 已冻结的直接 HGB（不重新调参）；分数 `R0`=预测强度（强简单基线）、`R1`=结构+预测（inner-OOF 误差上训练的 HGB）、`R2`=随机；Oracle 排序仅作**诊断上界**。
- 双层交叉拟合：外层 12 折留一受试者，训练集=其余 59 人（与 RUN-004 一致）；内层 6 组受试者不相交；阈值取自训练集 inner-OOF 误差 75 分位（不用测试统计）。
- 成本：CPU 123.5 s（另加两次被锚点拦下的运行 152 s / 101 s），0 付费，0 下载，0 SEALED，0 新真值。

### B.4 执行中真实发生的两件事（都被规则拦下，没被"顺手放过"）

1. **第一次运行锚点失败**：dev005 base MAE 10.4825 vs RUN-004 M1 9.1395。原因是 runner 把训练集限制在 12 人，而 RUN-004 每折用其余 59 人。按冻结 stop rule 停手，归档为 `attempt-1-invalid-anchor/`（状态 `INVALID_HARNESS_TRAINING_SET_RESTRICTED`），不当作结果。
2. **第二次仍差 0.044，查出更深的问题**：RUN-001–004 的 HGB **没设 `random_state`**。训练 49,556 行触发 sklearn 1.9.1 自动 early stopping，验证集是随机的 → 同折同配置重跑不同值（`subj 9` raw：11.766 / 11.528 / 12.008；设 seed 后三次同为 12.188）。
   - 影响：RUN-004 记录的数字不可能被任何 harness 逐字复现；单条件抖动均值 0.271（单折 0.48）**大于**它据以判定的 `M3−M1` raw −0.059。
   - 结论不翻（该 CI 本就跨 0），但**数字精度不成立**；记为 `PROJECT-48-DEFECT-005`，历史文件不改，本轮起一律设 seed。
   - 新锚点规则在测量前写明：`|seeded − RUN-004| ≤ 2×未设 seed 的实测抖动`，并要求两次 seeded 拟合逐位一致。两者均通过。

### B.5 结果（`DEV/runs/RUN-005/`）

| 指标 | raw | dropallGT100 |
| --- | --- | --- |
| AUC `R0` 预测强度 | 0.5785 | 0.5927 |
| AUC `R1` 结构+预测 | 0.4905 | 0.4909 |
| AUC `R2` 随机 | 0.4986 | 0.4994 |
| `R1−R0` AUC Δ [CI95] | −0.0881 [−0.164, −0.018] | −0.1017 [−0.178, −0.034] |
| 选择性 MAE@0.70：R0 / R1 / 随机 / Oracle | 8.633 / 9.237 / 9.163 / **5.436** | 7.896 / 8.488 / 8.301 / **4.979** |

判定（按冻结规则）：`NEG_NOT_PREDICTABLE_BEYOND_MAGNITUDE`。
读法：幅值信号弱但真实（AUC≈0.58）；结构特征跨受试者不迁移（受试者 12 的 AUC 0.27），比随机还差；Oracle 上界显示 70% 覆盖率下还有 −37% 空间，但当前可部署输入抓不到。

### B.6 记录更新与决定

- 新增 `RESEARCH_RECORD.md` EXP-007、`STATE.md §增量`（只追加，上文历史值不改）、`RUN-005_RESULT.md`。
- 决定：**HOLD**。不在同一 12 人子集上加可靠性变体（否则即 CASE-20 的反复消耗）；贡献问题交 H8 作者决定。
- 保留：RUN-001–004 哈希前后一致；原始 ZIP SHA-256 前后一致；SEALED 未访问。

---

## C. 只读复核：上轮两个方案是否还有新信息价值

`audit/science03b/recheck_plans.py` → `plan_recheck.json`（只读，两项目 `research/` mtime 未变：2026-11-05 / 2026-11-07）。

| 上轮方案 | 是否已被历史证据回答 | 证据 |
| --- | --- | --- |
| MCS-HEMO-26：零拟合受试者级跨 session ICC + 运动控制 | **是** | O8（02b `Ear_sync` 跨 session ICC −0.222）、O12（02c 设备 mask 敏感性 ICC 0.332→0.334、CI 跨 0）、O22（02e 主分析 LOW n=3 / HIGH n=4 → rho/ICC 不可估计；无 mask 敏感性 CI 跨 0）；`n1r_verification.json` G1 覆盖 n=13 < 30 → FAIL |
| RCT-CONTACT-26：先做传感器互换斜率对比 | **是** | `contrast_table.json` Q_R1B："sensor_1 vs sensor_2 on the same material AND position"，489 对，`PARTIAL_OR_CONFOUNDED`；不可解混淆=传感器实例与自身胶层/照明/背景完全共线，部分力日志跨传感器字节相同；Q_R1C=`UNIDENTIFIABLE_WITH_CURRENT_DATA` |

**负结论**：上轮我给出的两个"修订方案"都没有新增信息价值——一个是已执行三次且样本量根本不足以估计统计量，另一个是已做过的对比且混淆无法通过去偏移解决。不改写理由，直接撤回：
- MCS：下一行动只能是 (a) 文档核实 U9/U10（非决定性、无新数据），或 (b) 通道级群延迟/独立标定/新数据集（需新授权）。
- RCT：`NO_USEFUL_NEXT_PROBE = TRUE` 对同类 DEV 探针继续有效；唯一决定性对比是外部模量（需新真值与授权）。

---

## D. 三臂对照（确定性检查器）

`audit/science03b/tasks/`：三个冻结决策点，同一包分别喂给 v0.9.6（worktree `d1ca67f`）、v0.9.9（stash 前三轮代码）、0.9.10。

| 任务 | v0.9.6 | v0.9.9 | 0.9.10 |
| --- | --- | --- | --- |
| MCS-HEMO-26 | `MCS-P1-CROSS-SESSION-ICC` | 同 | 无（P1 历史、P3 需授权） |
| RCT-CONTACT-26 | `RCT-P1-DEV-SLOPE-RERUN` | 同 | 无（P1+P2 历史、P3 需授权） |
| PoPu-48 | `POPU-P1-POSTURE-VARIANTS` + P2 | 同 | 仅 `POPU-P2-RELIABILITY-GATE` |

盲评：另开会话，A/B/C 每任务独立打乱，明确告知"字段多≠更正确"，按六项标准打分。结果三个任务都选中 0.9.10，且给出的理由与项目记录一致（ICC 在 n=3/4 不可估计、帧级单位违反独立性、RUN-004 已否定姿态变体）。评审还主动指出 T3 里"字段最少的那个反而最对"，说明它不是被字段数量带偏。

**限制**：三臂是**检查器输出**，不是三次独立 LLM 会话；历史 LLM 行为无法回放，故"模型能力是否变强"仍是 `NOT_MEASURED`；盲评在富字段差异下只能算半盲。

---

## E. 保留约束

| 项 | 状态 | 证据 |
| --- | --- | --- |
| H1–H10 / H5 随 H6 / H7 授权内 DEV / H8 作者决定 | 未变，无新节点、无新 STOP | 全套 546 通过 / 8 跳过 |
| SEALED / DEV‑VAL‑SEALED 隔离 | 未触碰 | `verification.json`：`sealed_accessed=false` |
| RUN-001–004、原始 ZIP、其他项目 STATE | 只读、哈希一致 | `protected_runs_unchanged=true`、`raw_zip_unchanged=true` |
| 既有载荷 | V1/V2/V3 仍 15 512 / 12 824 / 15 787 字符 | `case_decision_eval`（V9 因本机缺 `mcp` SDK 跳过，基线同样跳过） |
| MCP 面 | 24 工具 / 11‑21‑24 profile，未新增 | `PROFILE_TOOLS` |
| 旧包兼容 | 无新字段 → 行为不变 | 边界测试 12 条含兼容用例 |

## F. 未证实 / 未测量

1. "模型更会设计实验"：`NOT_MEASURED`（单臂、非盲、且本轮实验是负结果）。
2. 三臂对照只覆盖确定性检查器；真实 LLM 会话未回放。
3. `run_ref` 只是字符串，`status_verified` 只表示"引用了 Run"，不表示"读过 Run"；与 `feedback_link`/Run 完整性未打通。
4. Token、付费算力、真实实验成本、MCP 集成：`NOT_MEASURED`。
5. 项目 48 的 12 人子集已被 RUN-002–005 反复使用，任何结论都只是探索性。
