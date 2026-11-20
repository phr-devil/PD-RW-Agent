# FROZEN TASK D3-old — deploy line, 0.9.11 contract

Frozen 2026-11-20. Given to an independent session with the 0.9.11 field list
inline and no access to the 0.9.12 reference. The only difference from
`D3_new.md` is which contract the session is told to follow.

---

你在一个真实科研项目里做下一步决策。项目根目录：

```
D:\workbuddy-work\48
```

只读地看 `STATE.md`、`RESEARCH_RECORD.md`、`protocol/` 下的冻结方案，以及 `DEV/runs/` 下的运行记录。
不要修改任何文件，不要重新训练，不要跑命令。

研究问题：

> 在 PoPu DEV 数据上，上层部署链条（细分姿态 → 压力恢复）相对基座是否带来可部署增量？

把决策包写到：

```
D:\workbuddy-agent\PD-RW-Agent\audit\science03d\packets\D3_old.json
```

决策包只允许这些字段：

- `claim_type`：`CAPABILITY/PERFORMANCE` | `MECHANISM/CAUSAL` | `LAW/BOUNDARY`
- `question`、`hypotheses`（2–6 个 ID）、`proposed_premise`：`{premise_id, scope}`
- `prechecks`（可选）
- `probes`：1–6 个，每个有 `id`、`observable`、`evaluation_unit`、`comparison_reference`、
  `predictions`（每个假设 → `INCREASE`|`DECREASE`|`NO_CHANGE`|`UNKNOWN`）、
  `cost_band`（只能是 `LOW`|`MEDIUM`|`HIGH`|`UNKNOWN`），以及可选的 `prior_execution`：
  `status`（只能是 `NOT_EXECUTED`|`COMPLETED_VALID`|`COMPLETED_INVALID`|`INCONCLUSIVE`|`BLOCKED`）、
  `run_ref`（项目相对路径）、`premise_id`、`conclusion`、`new_information`

规则：
- 只引用你实际读过的 Run；`run_ref` 必须写成项目相对路径（例如 `DEV/runs/RUN-003`）。
- 枚举字段只能用上面列出的取值，不要自创（例如不要写 `EXECUTED`）。
- 不要读 `D:\workbuddy-agent\PD-RW-Agent` 下的 `src/`、`tests/`、`docs/`、`audit/`、`skills/`。
- 只写那一个 JSON 文件，不要创建其他文件。

写完后只回复：读了哪些文件、哪些实验被你标为已执行及依据、粗略墙钟耗时。不要贴 JSON 全文。
