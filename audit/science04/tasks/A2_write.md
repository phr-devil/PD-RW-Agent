# 任务：把一个已经决定的实验编码成合法决策包（最多三轮）

你是一个独立会话，没有参与这套工具的开发。**实验已经由作者决定**，你的工作只是把它编码成工具能读的输入；不要改进实验设计，也不要增加假设。

## 工具

仓库：`D:\workbuddy-agent\PD-RW-Agent`，在该目录下运行（Windows, bash）：

```
PYTHONPATH=src python -m pdrw_agent.science.cli template
PYTHONPATH=src python -m pdrw_agent.science.cli packet-check --packet <文件>
```

`template` 会打印一份能通过检查的最小包；`packet-check` 一次列出所有形状违规（含字段路径与可接受取值），退出码 0 = 通过，3 = 形状违规。

背景证据（只读，可选）：`audit/science04/frozen/DP1-POPU-HOLD/`
不要读取 `src/`、`tests/`、`docs/`、`audit/science03d/`。

## 作者已经决定的实验（照抄，不要改写）

- 研究问题：在 PoPu DEV 数据上，可靠性门控相对幅值基线是否带来可部署的选择性强度误差下降？
- 前提 `premise_id`：`REL-GATE-DEPLOYABLE-INCREMENT`
- 作用域 `scope`（键值都必须短）：dataset=PoPu DEV 12-subject fixed subset；unit=SUBJECT；outcome=Tactilus top-1% intensity MAE at selectivity 0.70
- 假设与作者给定的预测方向（**不得改动，也不得给没列的假设加预测**）：
  - `H_RELIABILITY_ADDS` → `DECREASE`
  - `H_MAGNITUDE_ONLY` → `NO_CHANGE`
  - `H_SCOPE_12SUBJ` → `UNKNOWN`
- 一个探针，id `P-RUN005-REPLICATION`：
  - observable：subject-level paired ΔMAE (C2 − C0) at selectivity 0.70
  - evaluation_unit：`SUBJECT`
  - comparison_reference：same 12-fold LOSO folds, magnitude-only baseline C0
  - cost_band：`MEDIUM`
  - 不给 `prior_execution`（这一步是复现，作者未声明它已在这些折上跑过）
- prechecks：`group_independence` = PASS；`legal_inputs` = PASS；其余留空/不写

## 轮次

最多 **3 轮** `packet-check` + 修改。目标是 `SHAPE_OK`，并且 `decision` 子命令能跑通：

```
PYTHONPATH=src python -m pdrw_agent.science.cli decision --packet <文件> --project-root "D:/workbuddy-work/48"
```

## 禁止

- 不得新增假设、探针、证据引用、Run 引用、授权声明；
- 不得改动作者给定的预测方向、premise_id、评估单位、成本带；
- 不得把 `precheck` 的 PASS 改成 FAIL/UNKNOWN 来绕过检查；如果你认为某个 precheck 缺证据，照原样写 PASS 并在报告里注明。

写出：`audit/science04/answers/A2_run005_packet.json`

## 报告

另外写 `audit/science04/answers/A2_report.json`：

```json
{"rounds": 0, "final_shape": "SHAPE_OK|SHAPE_VIOLATIONS",
 "decision_ran": true, "decision_status": "...",
 "frontier": [], "no_executable_next_probe": true,
 "changed_paths": [], "author_values_changed": false,
 "wall_clock_minutes": 0, "notes": "一句话"}
```

回复我时只写三件事：1) 几轮通过，最终 `decision` 的 frontier 与 `no_executable_next_probe` 是什么；2) 有没有改动作者给定的任何取值；3) 粗略耗时。不要贴 JSON 全文。
