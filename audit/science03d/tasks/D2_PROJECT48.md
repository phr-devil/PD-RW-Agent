# FROZEN TASK D2 — a real project's next experiment

Frozen 2026-11-20, before the patch under test was documented. Given verbatim to
an independent WorkBuddy session that had not seen this round's changes.

---

你在一个真实的科研项目里做下一步决策。项目根目录是：

```
D:\workbuddy-work\48
```

请先读 `STATE.md`、`RESEARCH_RECORD.md` 的关键段落、`protocol/` 下的冻结方案，以及
`DEV/runs/RUN-001` … `RUN-005` 的记录（只读，不要修改任何文件，不要重新训练任何模型），
然后回答：

> 在 PoPu DEV 数据上，可靠性机制相对基座是否带来可部署的增量？

把结论写成一份决策包 JSON，保存到：

```
D:\workbuddy-agent\PD-RW-Agent\audit\science03d\packets\D2_independent.json
```

决策包字段（只允许这些）：

- `claim_type`：`CAPABILITY/PERFORMANCE`、`MECHANISM/CAUSAL`、`LAW/BOUNDARY` 之一
- `question`：上面的研究问题
- `hypotheses`：2–6 个互不相同的假设 ID
- `proposed_premise`：`{premise_id, scope}`，scope 是小的键值字典
- `prechecks`：可选
- `probes`：1–6 个候选实验，每个包含 `id`、`observable`、`evaluation_unit`、
  `comparison_reference`、`predictions`、`cost_band`，以及可选的 `prior_execution`
  （`status`、`run_ref`（项目相对路径）、`premise_id`、`conclusion`、`new_information`）

规则：
- 只引用你实际读过的 Run；`run_ref` 用项目相对路径（例如 `DEV/runs/RUN-005`）。
- 不要运行训练、不要调用 PD-RW 工具、不要修改仓库文件。
- 已经跑过的实验如果确实回答了同一个科学前提，请标成已执行并说明依据；不确定就不要标。
- 写完后只回复三件事：你读了哪些文件、你如何判断哪些实验已经跑过、以及你的墙钟耗时（粗略即可）。
