# FROZEN TASK D1 — PRESS-26 cross-premise decision point

Frozen 2026-11-20, before the patch under test was documented. Given verbatim to
an independent WorkBuddy session that had not seen this round's changes.

---

你在一个已有的实验项目里做科研决策。项目根目录是：

```
D:\workbuddy-agent\PD-RW-Agent\audit\science03d\fixture-project
```

请先读 `STATE.md`、`protocol/` 下的冻结方案，以及 `DEV/runs/` 下的每个运行记录（不要修改任何文件），
然后回答这个研究问题：

> 在 PRESS DEV 26 上，接触力重构的残差主要由传感器漂移解释，还是由梁刚度解释？

请把结论写成一份决策包 JSON，保存到：

```
D:\workbuddy-agent\PD-RW-Agent\audit\science03d\packets\D1_independent.json
```

决策包字段（只允许这些）：

- `claim_type`：`CAPABILITY/PERFORMANCE`、`MECHANISM/CAUSAL`、`LAW/BOUNDARY` 之一
- `question`：上面的研究问题
- `hypotheses`：2–6 个互不相同的假设 ID
- `proposed_premise`：`{premise_id, scope}`，scope 是小的键值字典（数据集、输入、单位等）
- `prechecks`：可选，`group_independence` 等检查项，状态为 `PASS`/`FAIL`/`UNKNOWN`/`NOT_CHECKED`
- `probes`：1–6 个候选实验，每个包含
  - `id`、`observable`、`evaluation_unit`、`comparison_reference`
  - `predictions`：每个假设 → `INCREASE`/`DECREASE`/`NO_CHANGE`/`UNKNOWN`
  - `cost_band`：`LOW`/`MEDIUM`/`HIGH`/`UNKNOWN`
  - `prior_execution`（可选，只有当你认为该实验已经跑过时才写）：
    `status`（`NOT_EXECUTED`/`COMPLETED_VALID`/`COMPLETED_INVALID`/`INCONCLUSIVE`/`BLOCKED`）、
    `run_ref`（项目相对路径）、`premise_id`，以及可选的 `conclusion`/`new_information`

规则：
- 只用你在文件里看到的证据；引用运行时 `run_ref` 必须是项目相对路径。
- 不要运行任何命令、不要调用 PD-RW 工具、不要修改仓库里的其他文件。
- 如果你的判断依赖某个你没有证据的东西，在包里如实留空或标 UNKNOWN，不要编造。
- 写完后只回复三件事：你读了哪些文件、你为什么这样填 `prior_execution`、以及你的墙钟耗时（粗略即可）。
