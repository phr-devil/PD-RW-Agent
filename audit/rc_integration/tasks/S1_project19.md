# S1 — 项目 19 的正向结果、最强基线与贡献边界

你是一个**没有参与开发**的独立科研会话。工作仓库根：`D:\workbuddy-agent\PD-RW-Agent`。
项目：`D:\workbuddy-work\19`（CRFW / CRPS，动作条件化帧分类）。

## 只能读什么

- `D:\workbuddy-work\19` 下的 **Markdown / JSON / CSV** 工件（只读）。
- 仓库里的 `skills/pd-rw-research/SKILL.md`、`references/packet.md`、`references/execution.md`。
- **不要**读 `src/`、`tests/`、`audit/science0*`、`audit/rc_*`、`docs/`。不要读任何别的会话的答案。
- **绝对不要**打开 `D:\workbuddy-work\19\REASSEMBLE\`（原始数据目录，含 37 条封存录制）。不要训练、不要下载、不要改项目里任何文件。

调用 CLI 一律：`cd D:\workbuddy-agent\PD-RW-Agent && PYTHONPATH=src python -m pdrw_agent.science.cli ...`

## 必须完成的四件事

1. **正向结果**：项目 19 的当前主结果是哪一个已经跑完的评测，冠军方案与最强对照分别是哪个，差值多少。**必须从 JSON 自己复算**（至少均值、逐对象胜场、按录制分组的胜场），不要抄 Markdown 报告里的数字。列出你复算出的数字与报告数字不一致的地方。
2. **最强基线**：报告把哪个方案称为“公平基线”？**按数字**最强的可部署基线是哪个？两者是同一个吗？如果不同，这对论文主张意味着什么（一句话）。
3. **覆盖度争议**：报告里的 `17/17`、`96/111`（或类似表述）能否从 `episode_paired` 复算出来？分别在哪些文件里成立、哪些不成立？"独立单位"到底是什么（对象？情节？录制？），这会让哪些说法失效？
4. **贡献边界**：用不超过 5 句话写清——这个结果能支持什么主张、不能支持什么、最短还需要哪一条证据才能升级为可投稿的 Claim。必须点名证据文件。

## 必须真正调用的工具

按顺序，**真的执行**并把原样输出记下来（不要臆造）：

```
PYTHONPATH=src python -m pdrw_agent.science.cli template
PYTHONPATH=src python -m pdrw_agent.cli context --project-id 19
PYTHONPATH=src python -m pdrw_agent.cli audit --project-id 19
PYTHONPATH=src python -m pdrw_agent.cli history --project-id 19
```

这四条里，后三条可能因为"19 没有在本地 project-map 注册"而失败——**把错误原文抄下来**（错误码 + 一句话），不要自己去改任何配置文件，也不要因为失败就跳过。失败本身就是这次验收要记录的事实。

然后**自己写一个 packet**（基于 `template` 的输出，最多两轮 `packet-check`），针对项目 19 的下一个合法科研问题，其中至少包含：

- 一个**在 DEV 内**就能跑的探针；
- 一个**需要封存录制（37 条）**才能跑的探针，按 `references/packet.md` 的方式声明它需要新授权。

跑：

```
PYTHONPATH=src python -m pdrw_agent.science.cli packet-check --packet <你的包>.json
PYTHONPATH=src python -m pdrw_agent.science.cli decision --packet <你的包>.json --project-root D:\workbuddy-work\19
```

把 `declared_probe_efficiency` 里的 `frontier_candidate_ids_as_declared`、`needs_authorization_ids`、`historical_evidence_ids`、`no_executable_next_probe` **四个键原样抄下来**。封存探针是否出现在前沿里？如果没有，它去了哪里？

## 交付

只写两个文件，不要改别的：

- `D:\workbuddy-agent\PD-RW-Agent\audit\rc_integration\answers\S1_packet.json`
- `D:\workbuddy-agent\PD-RW-Agent\audit\rc_integration\answers\S1_report.json`，键：
  `positive_result`、`strongest_baseline`、`coverage_dispute`、`contribution_boundary`、`decision`（四个键原样）、`packet_rounds`（整数）、`calls`（你实际跑过的命令）、`errors_and_retries`、`wall_clock_minutes`、`tokens`（无法测量就写 `NOT_MEASURED`）、`uncertainties`。

最后回复我 5 条以内的要点，不要贴 JSON 全文。
