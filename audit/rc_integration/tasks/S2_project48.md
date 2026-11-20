# S2 — 项目 48 的有效负结果、历史 Run 归属与下一合法行动

你是一个**没有参与开发**的独立科研会话。工作仓库根：`D:\workbuddy-agent\PD-RW-Agent`。
项目：`D:\workbuddy-work\48`（PoPu 可靠性 / 姿态先验）。

## 只能读什么

- `D:\workbuddy-work\48` 下的 **Markdown / JSON** 工件（`STATE.md`、`RESEARCH_RECORD.md`、`protocol/`、`DEV/runs/`），只读。
- 仓库里的 `skills/pd-rw-research/SKILL.md`、`references/packet.md`、`references/execution.md`。
- **不要**读 `src/`、`tests/`、`audit/science0*`、`audit/rc_*`、`docs/`。
- 不要训练、不要下载、不要改项目里任何文件，不要读 `data/PoPu/*.zip`。

CLI 前缀：`cd D:\workbuddy-agent\PD-RW-Agent && PYTHONPATH=src python -m pdrw_agent.science.cli ...`

## 必须完成的三件事

1. **有效负结果**：项目当前有效的负结果是什么，来自哪个 Run，它的适用边界（数据集、受试者数、指标、量程）是什么。**特别注意**：`RUN-001` 的某个比较结论已被判为无效——说明是哪一条、被什么取代、引用时有什么强制要求。
2. **历史 Run 归属**：`RUN-005` 是否真的执行了"你现在要提的这个实验"？用 packet 的 `prior_execution` 引用 `DEV/runs/RUN-005`，并用 `premise_ref` 点名你认为它执行的冻结协议。
   - 如果工具给出 `attribution_basis`，把值抄下来（`RUN_RECORD` / `FROZEN_PLAN` / `CALLER_PREMISE_PLAN` / `NONE`）；
   - 然后**再写一个包**，引用 `RUN-005` 但换一个 `premise_ref`（指向另一份协议），看结果是否变。
   - 两次的 `applicability`、`next_action`、以及探针是否还留在前沿，都要记下来。
3. **下一合法行动**：在当前原始授权（`STATE.md` 的 `AUTH/BUDGET`）下，**今天就能做**的一步是什么？哪一步需要新授权（`VAL` / `SEALED` / 全 60 人 / 第二库）？用 packet 里一个 `requires_new_authorization: true` 的探针表达后者，确认它没有变成"下一行动"。

## 必须真正调用

```
PYTHONPATH=src python -m pdrw_agent.science.cli template
PYTHONPATH=src python -m pdrw_agent.cli context --project-id 48
PYTHONPATH=src python -m pdrw_agent.cli verify-run --project-id 48 --run-id RUN-005
PYTHONPATH=src python -m pdrw_agent.cli audit --project-id 48
```

然后 `packet-check`（最多两轮）+ `decision --project-root D:\workbuddy-work\48`，两个包各跑一次。

## 交付

只写：

- `D:\workbuddy-agent\PD-RW-Agent\audit\rc_integration\answers\S2_packet_same.json`
- `D:\workbuddy-agent\PD-RW-Agent\audit\rc_integration\answers\S2_packet_other.json`
- `D:\workbuddy-agent\PD-RW-Agent\audit\rc_integration\answers\S2_report.json`，键：
  `valid_negative`、`run001_invalidation`、`attribution_same`、`attribution_other`、`next_legal_action`、`needs_new_authorization`、`decision_same`（四个键）、`decision_other`（四个键）、`packet_rounds`、`calls`、`errors_and_retries`、`wall_clock_minutes`、`tokens`、`uncertainties`。

最后回复 5 条以内要点，不要贴 JSON 全文。
