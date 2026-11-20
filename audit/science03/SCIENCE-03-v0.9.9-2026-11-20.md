# SCIENCE-03 — 前沿合法性修复与一次真实会话轨迹（v0.9.9）

基线 `a94805c`（PR #21 / v0.9.8），分支 `science/02-experiment-design`，未合 main。
A 段是确定性修复；B 段是**一次真实 WorkBuddy 会话**的轨迹记录，两段证据分开陈述。

## A. 两个前沿缺陷：先复现，再修

复现脚本 `audit/science03/probe_frontier_prefix.py`，原始输出 `probe_frontier_prefix.json`。
包体取自既有卡片形状（CASE-08 的“廉价但盲”、CASE-02/12 的“oracle 参照”），不是新造的假问题。

| # | 修复前 | 修复后 |
| --- | --- | --- |
| 1 | `CHEAP-BUT-BLIND`（LOW，区分 0 对）与 `MEDIUM-BUT-DECIDES`（区分 1 对）同时进入前沿：`frontier=[CHEAP-BUT-BLIND, MEDIUM-BUT-DECIDES]` | `frontier=[MEDIUM-BUT-DECIDES]`；盲探针进 `exploratory_probe_ids` |
| 2 | `ORACLE-UPPER-BOUND`（LOW，oracle 参照）**支配**了合法的 `LEGAL-SPECIMEN-PROBE`（同区分对、更贵）：`frontier=[ORACLE-UPPER-BOUND]`，`dominated=[LEGAL-SPECIMEN-PROBE]` | `frontier=[LEGAL-SPECIMEN-PROBE]`；oracle 探针进 `diagnostic_upper_bound_ids` |

第 2 条比报告里描述的更严重：不是“非法探针也在前沿里”，而是“非法探针把唯一合法探针挤掉了”。

### 改了什么（最小）

| 文件 | 改动 |
| --- | --- |
| `science/probe_frontier.py` | 支配关系只在 eligible 集合内计算；eligible＝区分 ≥1 对 且 无 `REFERENCE_NOT_LEGAL`。新增 `exploratory_probe_ids`、`diagnostic_upper_bound_ids`、`needs_unit_verification_ids`、`no_legal_decisive_probe` |
| `science/decision.py` | finding 增加 `usage`（`DIAGNOSTIC_UPPER_BOUND_ONLY` / `VERIFY_INDEPENDENT_UNITS_FIRST`）与 `blocks_decisive_frontier`；顶层增加 `no_legal_decisive_probe(_question)` |
| `tests/test_science03_probe_frontier_boundary.py` | 10 条边界测试 |
| `skills/.../execution.md`、`docs/RUNTIME_AND_MCP.md`、`README.md`、`docs/DECISION_COVERAGE.md` | 三个列表与一句话边界 |

刻意没做：不删探针、不加必填字段、不加审批、不加 STOP、不建评分器、不动 `assess_proposal` 既有键。
`PROBE_UNIT_NOT_INDEPENDENT` 仍留在前沿里，只追加“先数独立单位”的提示——未禁止任何 window/frame 指标。

### 工程与成本

- 全量：**534 通过 / 8 跳过 / 151 subtests**（同一 checkout 改前基线 523 通过 / 8 跳过，1 条与本改动无关的 PID 复用偶发失败；新增 10 条）。
- `case_decision_eval` 10/10，V1/V2/V3 载荷 15 512 / 12 824 / 15 787 逐字未变；`case_gate_eval` 17/17；MCP 仍 24 工具、profile 11/21/24。
- 声明载荷（紧凑 JSON，字符代理非 token）：干净双探针 2 858 → 3 054（+6.9%）；三张缺陷包合计 8 211 → 9 124（+11.1%）。`audit/science03/payload_probe_{before,after}.json`。

## B. 真实会话：宿主检查与降级路径

| 检查 | 结果 |
| --- | --- |
| `~/.workbuddy/mcp.json` | 声明 stdio `pd-rw-research`（`.venv\Scripts\python.exe`，指向本 checkout） |
| 该解释器 | 存在，`import pdrw_agent` 返回 `0.9.9` |
| 本会话工具列表 | **无** `pd-rw-research` 工具（ToolSearch 查 `pd-rw-research` / `pdrw science` 均未命中） |
| 连接器 | 只有 `agent-mail` |

阻碍记录一次，未重装、未改 MCP 配置，改用既有合法 CLI：`python -m pdrw_agent.science.cli decision --packet FILE`。
`REAL_LLM_END_TO_END = PARTIAL`：模型行为在真实会话中发生并被记录，但**不经过 MCP**，因此 MCP 集成效果仍 `NOT_MEASURED`。

### 模型实际读到的文件（全部只读，未开 SEALED）

| 文件 | 用途 |
| --- | --- |
| `MCS-HEMO-26/research/STATE.md` | H 节点、O1–O13 事实、`NEXT`、授权边界 |
| `MCS-HEMO-26/research/dev_audit/beat_level_associations.csv` | 逐搏偏相关（`partial_r_PAT_foot__SBP_given_HR` 等） |
| `MCS-HEMO-26/research/dev_audit/subject_level_deltas.csv` | 受试者级配对差值（n=47） |
| `MCS-HEMO-26/research/dev_audit/competing_explanations.json` | 跨 session rho、运动伪迹 rho |
| `MCS-HEMO-26/research/dev_audit/ob_reference_recheck.json`（引用） | NIBP＝CNAP 同源，无独立第二血压参考 |
| `RCT-CONTACT-26/research/STATE.md` | `NO_USEFUL_NEXT_PROBE`、R1 收束、V2 唯一出路 |
| `RCT-CONTACT-26/research/dev_audit/contrast_table.json` | Q_R1A/B/C 三问的判决与独立单位数 |
| `RCT-CONTACT-26/research/dev_audit/dev_projection/`（列目录） | 派生 stiffness 标签的来源 |
| `CRIA_A1A3_20261111/RESEARCH_RECORD.md` | 作为候选被**排除**：活动 02 只有数据验收，无 Run |

### 工具与迭代成本

- `decision` CLI 执行 **9 次**：5 次产出结果，4 次因字段长度被同一规则拒绝（`observable`/`comparison_reference` > 80 字符），修正后通过。
- 另有 4 次 shell 计时工具缺失（CLI 未执行），未计入。
- 批准请求 **0** 次；拟合/训练 **0** 次；下载 **0** 次；SEALED 读取 **0** 次；新建 Run **0** 次。
- B 段墙钟约 10 分钟（11:55–12:05），CLI 合计约 0.9 s；Token `NOT_MEASURED`。

## C. 两个案例：原始方案 vs 模型修订方案

### 案例 1 — MCS-HEMO-26（参考层不可独立）

**记录里的原始方案**：`STATE.md` NEXT＝“需 CPU/GPU 拟合授权（公平基线对照）”，配合“向官方核实袖带读数是否曾记录”的只读文档核查。
**真实阻碍（从 Run 读出，不是从摘要抄）**：① `NIBP` 是 CNAP 同源连续动脉压，数据集内无独立第二血压参考；② C 层独立信息证据为负（偏相关 −0.095、HR 分箱 −0.072）；③ `Ear_sync` 跨 session ICC −0.222，而 `PAT_foot` 静息基线 rho +0.823；④ 队列不可识别（19/22 服 β 阻滞剂）。

包：`session1/case1_original.json` / `case1_revised.json`，输出 `*.out.json`。

| | 原始 | 修订 |
| --- | --- | --- |
| 探针 | 融合增益（RECORD 单位，参照 CNAP 派生 SBP）+ 文档核查（LOW，区分 0 对） | 跨 session ICC（SUBJECT，参照同一受试者第二次会话）+ 运动伪迹控制（SUBJECT） |
| 检查器判定 | 两个探针都命中 `PROBE_UNIT_NOT_INDEPENDENT`（RECORD 单位 vs 声明 PASS）；文档核查进 `exploratory` | 无 finding；两个探针都在前沿 |
| 成本 | 高（拟合）＋需新授权 | 零拟合，低 |
| 是否可区分 | 名义上区分 1 对，但参照同源，“增益”不可归因 | 两个探针以不同失效模式区分同一对假设 |

**方案是否改变：是。** 从“申请拟合做公平基线”改为“参考层是阻碍，拟合不能解决；先用零拟合的跨 session 重复性与运动控制判定载体 vs 伪迹”。依据是 O6/O8/O12 的既有数字，未产生新数据。

### 案例 2 — RCT-CONTACT-26（机制不可辨识）

**记录里的原始方案**：V1（DEV-only、材料级 force–Z 斜率不变性）已执行并判 `NO_USEFUL_NEXT_PROBE`；V2（独立材料力学真值 + 标定/零点/时序的受控按压）需新授权。
**真实阻碍**：15 687 帧 vs 98 材料 / 979 序列（帧不独立）；深度与帧序共线；派生 stiffness 标签由同一力数据拟合（伪标签循环）；无外部模量真值 → `UNIDENTIFIABLE_WITH_CURRENT_DATA`。

| | 原始 | 修订 |
| --- | --- | --- |
| 探针 | DEV-only 斜率不变性（FRAME，LOW）＋受控按压（MATERIAL，HIGH，参照外部模量） | 传感器互换（MATERIAL，MEDIUM，489 对同材料同位置）＋受控按压（MATERIAL，HIGH） |
| 检查器判定 | `frontier=[ORIG-DEV-SLOPE-INVARIANCE]`；**受控按压被便宜的已关闭探针支配** | 两个探针都在前沿；按压区分 2 对（含伪标签循环） |
| 竞争解释 | 2 个（材料 / 传感器-轨迹） | 3 个（＋标签循环）；按压探针对伪标签给出 NO_CHANGE |
| 成本 | LOW（但已知无信息）＋HIGH | MEDIUM（现有 DEV 即可）＋HIGH（需新授权） |

**方案是否改变：是，且是“拆分”而不是“发明”。** 把“传感器实例 vs 接触物理”这一段拆成现在就能做的互换对照，把“材料力学性质”留给唯一需要新真值的受控按压；同时保留 `NO_USEFUL_NEXT_PROBE`，不重跑已关闭的 DEV 探针。

### 六项对照（两案例合并）

| 维度 | 原始 | 修订 | 依据 |
| --- | --- | --- | --- |
| 问题与实验匹配 | 低：用同源参照回答“信息”，用伪标签回答“材料性质” | 中：参照改为同一受试者第二次会话 / 另一传感器实例 | O6、Q_R1C |
| 强基线与竞争解释 | 不足：无强简单基线；解释各 2 个 | 较好：`PAT_foot` 0.823 与深度-only 作为门槛；解释 3 个 | `competing_explanations.json`、Q_R1A |
| 能否真正区分 | 名义区分，实际不可归因 | 每个探针对应一种失效模式，按压另测标签循环 | `pair_count` 1→1/1，2 |
| 输入与预测时合法性 | RECORD 单位（已声明 PASS 冲突）；CNAP 同源 | SUBJECT / MATERIAL；无 finding | `probe_findings`、`needs_unit_verification_ids` |
| 成本 | 高（拟合）／低但无信息 | 低（零拟合）／中＋高（分阶段） | 声明成本带 |
| 无意义重复/审批 | 会申请一次不可辨识的拟合；会重跑已关闭探针 | 0 批准；0 重复执行 | 本轮 9 次 CLI，0 授权请求 |

**保留负结果与不确定性**：两案例的 `prior_negative_lessons` 都判为 `DECLARED_SAME_PREMISE_SCOPE_CANDIDATE` 且 `automatic_stop=false`；RCT 的 `NO_USEFUL_NEXT_PROBE`、MCS 的 O-A/O-B `DEMOTED` 原样保留；`PRESERVATION_UNVERIFIED` 未变。

## D. 检查器与模型各做了什么

| 结论 | 来源 |
| --- | --- |
| 盲探针不是前沿候选（真实包上也成立） | 确定性检查器（`ORIG-DOC-CHECK` → `exploratory`） |
| RECORD 单位与声明 PASS 冲突 | 确定性检查器（`PROBE_UNIT_NOT_INDEPENDENT`，未阻断前沿） |
| CNAP 同源、伪标签循环、队列不可识别 | **模型**（检查器看不到：无关键字、无“已执行”字段） |
| 拆分问题、选零拟合探针、拒绝重跑 | **模型** |
| 受控按压需要新授权 | 记录原文 + 模型判断 |

## E. 仍未解决

1. **便宜的已关闭探针仍能支配昂贵的决定性探针**（`case2_original` 实测）。包内没有“该探针已执行且已关闭”的字段，前沿只能按声明对集＋成本比较。这是包表达力问题，不是支配逻辑错误；修它需要新字段，本轮按“最小必要”未做。
2. **同源参照（CNAP）不被 `REFERENCE_NOT_LEGAL` 捕获**：该规则只认测试期真值/oracle。同源与伪标签仍是模型判断，与 SCIENCE-02 风险 4 同源。
3. **强基线没有字段**：`PAT_foot` 0.823、深度-only 只能写在方案文本里，无法机检（CASE-13 层）。
4. **单会话、非盲**：本次模型刚写完该补丁，知道新字段含义，存在启动偏置；没有第二臂对照，不能据此声称“模型变强”。
5. **MCP 集成**：仍 `NOT_MEASURED`；本次全部经 CLI。
6. Token / 真实实验成本 / 科研价值：`NOT_MEASURED`。

## F. 下一步建议

不再加检查器。下一步应把 MCP 挂载修好（`pd-rw-research` 在本会话不可见是唯一阻塞），在同一批案例上做**双模型/双版本**对照，且由未参与补丁的人写包，才能回答“模型是否更会设计实验”。若宿主仍不挂载，则保留 CLI 通道并明确其边界。
