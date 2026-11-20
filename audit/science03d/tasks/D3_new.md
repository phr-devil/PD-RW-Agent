# FROZEN TASK D3-new — deploy line, 0.9.12 contract

Frozen 2026-11-20. Same project and question as `D3_old.md`; the session is told
to follow the updated reference, which documents `premise_ref` and the premise
evidence axes.

---

你在一个真实科研项目里做下一步决策。项目根目录：

```
D:\workbuddy-work\48
```

先读这份当前版本的执行约定（这是你要遵守的契约）：
`D:\workbuddy-agent\PD-RW-Agent\skills\pd-rw-research\references\execution.md`

再只读地看项目里的 `STATE.md`、`RESEARCH_RECORD.md`、`protocol/` 下的冻结方案、`DEV/runs/` 下的运行记录。
不要修改项目文件，不要重新训练，不要跑命令。

研究问题：

> 在 PoPu DEV 数据上，上层部署链条（细分姿态 → 压力恢复）相对基座是否带来可部署增量？

把决策包写到：

```
D:\workbuddy-agent\PD-RW-Agent\audit\science03d\packets\D3_new.json
```

字段按执行约定里的 `prior_execution` 定义来（`status`、`run_ref`、`record_ref`、`premise_ref`、`premise_id`、`conclusion`、`new_information`），
其余顶层字段为 `claim_type`、`question`、`hypotheses`（2–6）、`proposed_premise`（`premise_id` + `scope`）、
`prechecks`（可选）、`probes`（1–6，含 `id`、`observable`、`evaluation_unit`、`comparison_reference`、
`predictions`、`cost_band`）。

规则：
- 只引用你实际读过的 Run；`run_ref` 必须是项目相对路径。
- `status` 只能是 `NOT_EXECUTED`|`COMPLETED_VALID`|`COMPLETED_INVALID`|`INCONCLUSIVE`|`BLOCKED`；
  `cost_band` 只能是 `LOW`|`MEDIUM`|`HIGH`|`UNKNOWN`。
- 如果你声称某个实验已回答本研究问题，按约定把前提证据交代清楚（`premise_id`，以及在你知道对应冻结方案时给 `premise_ref`）。
- 不要读 `D:\workbuddy-agent\PD-RW-Agent` 下的 `src/`、`tests/`、`audit/`（那份 reference 除外）。
- 只写那一个 JSON 文件。

写完后只回复：读了哪些文件、哪些实验被你标为已执行及依据（包括是否用了 `premise_ref`）、粗略墙钟耗时。不要贴 JSON 全文。
