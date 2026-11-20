# 任务：把四份真实决策包修到能通过工具（最多两轮）

你是一个独立会话，没有参与这套工具的开发。任务是**结构修复**，不是重写科研结论。

## 工具

仓库：`D:\workbuddy-agent\PD-RW-Agent`

在仓库根目录下运行（Windows, bash）：

```
PYTHONPATH=src python -m pdrw_agent.science.cli packet-check --packet <文件>
PYTHONPATH=src python -m pdrw_agent.science.cli template
PYTHONPATH=src python -m pdrw_agent.science.cli decision --packet <文件> --project-root <项目根>
```

`packet-check` 会一次性列出**所有**形状违规（带字段路径）、被忽略的字段、以及警告。
退出码 0 = 形状通过，3 = 形状违规（不是执行错误），2 = 其它错误。

## 要修的四份包

- `audit/science03d/packets/D1_independent.json`（项目根 `audit/science03d/fixture-project`）
- `audit/science03d/packets/D2_independent.json`（项目根 `D:/workbuddy-work/48`）
- `audit/science03d/packets/D3_old.json`（项目根 `D:/workbuddy-work/48`）
- `audit/science03d/packets/D3_new.json`（项目根 `D:/workbuddy-work/48`）

把修好的版本写到 `audit/science04/answers/A1_<原名>_fixed.json`（不要覆盖原文件）。

## 允许与禁止

**允许**（只能做这些）：
- 把 `prechecks` 的 list 形式改成以检查名为键的 mapping；
- 把 `predictions` 的 list 形式改成 hypothesis→outcome 的 mapping；
- 缩短过长但属于"描述"的字段（`observable`、`comparison_reference`、`conclusion`、`new_information`、`scope` 的取值），缩短时不得改变含义；
- 把被错误放到顶层的执行字段移到它所属的探针里（若只有一个探针才可以这么做；若有多个探针且无法判断归属，见下）；
- 删除工具不会读取的多余字段，但要在报告里列出你删了什么。

**禁止**：
- 不得改动任何 `predictions` 的**方向**（INCREASE/DECREASE/NO_CHANGE/UNKNOWN）；
- 不得为原先没有预测的假设**编造**方向（原包用散文写的预测，只能由原作者决定方向）；
- 不得改动 `premise_id`、`hypotheses`、`claim_type` 的**科学含义**（把自造的 claim_type 改成三个合法值之一，只有在你能从 `question` 直接读出时才允许，并要说明）；
- 不得新增证据引用、Run 引用、授权声明；
- 不得读取 `src/`、`tests/`、`docs/`；只用 CLI 的输出和包文件本身。

## 轮次

每份包最多 **2 轮** `packet-check` + 修改。第 2 轮仍不通过就停手，如实记录卡在哪里。

## 报告

写到 `audit/science04/answers/A1_report.json`：

```json
{
  "packets": [
    {"name": "D1_independent", "rounds": 1, "final_status": "SHAPE_OK|SHAPE_VIOLATIONS",
     "violations_before": 1, "violations_after": 0,
     "changed_paths": ["prechecks"],
     "science_touched": false,
     "blocked_by": null,
     "note": "一句话"}
  ],
  "invented_any_prediction": false,
  "wall_clock_minutes": 0
}
```

`science_touched` 必须诚实：只要你改动了预测方向、前提、证据或授权之一，就写 true 并在 `note` 里说明。

回复我时只写三件事：1) 四份包各自几轮通过/卡在哪；2) 有没有任何一处不得不改动科学内容；3) 粗略耗时。不要贴 JSON 全文。
