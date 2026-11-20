# 任务 C1：正向证据 + 从 template 写包 + 真实 CLI + 下一步

你是一个独立的科研会话，没有参与任何工具开发。工作对象是真实项目 19（CRPS/CRFW 技能分割），
它的正向结果已经在磁盘上。下面所有路径都可读，除标注为不可读的。

## 只读范围

```
D:\workbuddy-work\19\CRPS_L2_EVAL.json
D:\workbuddy-work\19\CRPS_L2_ALGO_ROUND.json
D:\workbuddy-work\19\CRPS_L2_ALGO_ROUND_AGG.json
D:\workbuddy-work\19\FINAL_ALGO_ROUND_REPORT.md
D:\workbuddy-work\19\STATE.md
D:\workbuddy-work\19\CONFIRMATION_FREEZE.md
D:\workbuddy-work\19\RUNS.md
```

**不要**打开 `REASSEMBLE/`（37 个封存 Episode 从未被读取，本轮也不读）、不要训练、不要下载、
不要运行实验、不要修改项目里的任何文件。不要读 `src/`、`tests/`、`audit/science0*`（那是工具实现，
你要用的是已经装好的 Skill 与 CLI 文档）。

允许读的产品文档（这是你这一轮要验收的东西）：

```
D:\workbuddy-agent\PD-RW-Agent\skills\pd-rw-research\SKILL.md
D:\workbuddy-agent\PD-RW-Agent\skills\pd-rw-research\references\packet.md
D:\workbuddy-agent\PD-RW-Agent\skills\pd-rw-research\references\execution.md
```

## 命令行（真的调用，不要凭空写）

仓库根目录 `D:\workbuddy-agent\PD-RW-Agent`，所有命令加 `PYTHONPATH=src`：

```
PYTHONPATH=src python -m pdrw_agent.science.cli template
PYTHONPATH=src python -m pdrw_agent.science.cli packet-check --packet <你的包.json>
PYTHONPATH=src python -m pdrw_agent.science.cli decision --packet <你的包.json> --project-root D:\workbuddy-work\19
```

## 四件事

1. **正向结果的三句话**：这条结果的可发表贡献是什么；**按数字**最强的基线是哪一个（不是报告里
   被称为"公平基线"的那个）；它的适用边界到哪里；还缺哪些证据。每条都要能指到文件与字段。
   如果报告里的某个覆盖度说法与 JSON 复算不一致，说出来（自己算，不要只抄报告）。

2. **从 template 写一个合法包**：主题是"下一个决定性实验"。包必须包含**两个**探针：
   - 一个**当前授权内**就能做的（只用已有的 DEV/冻结预测，不碰封存）；
   - 一个**需要新授权**的（封存跨录制确认）。
   用 `template` 生成骨架再改写；用 `packet-check` 检查，**最多两轮**修复；把最终包存到
   `D:\workbuddy-agent\PD-RW-Agent\audit\rc_preflight\answers\C1_packet.json`。

3. **真的跑 decision**，把 `frontier_candidate_ids_as_declared`、`historical_evidence_ids`、
   `needs_authorization_ids`、`no_executable_next_probe` 原样抄下来（不要改写键名、不要总结成
   "工具认为 X"），并说明它是否与你第 2 步的意图一致；不一致就说明差在哪。

4. **下一步计划**：按 `execution.md` 的三层格式给出（NOW / NEEDS_NEW_AUTHORIZATION /
   FUTURE_CONDITIONAL），每层一到三条，每条都要写它花的是哪一份授权。

## 输出

写到 `D:\workbuddy-agent\PD-RW-Agent\audit\rc_preflight\answers\C1_report.json`：

```json
{
  "positive_result": {"contribution": "...", "strongest_baseline_by_number": "...",
                      "boundary": "...", "missing_evidence": ["..."],
                      "recomputed": {"<说法>": {"reported": "...", "computed": "..."}},
                      "evidence_refs": ["文件:字段"]},
  "packet_rounds": [{"round": 1, "command": "...", "exit": 0, "violations": ["path: problem"]}],
  "packet_path": "...",
  "decision": {"frontier_candidate_ids_as_declared": [], "historical_evidence_ids": [],
               "needs_authorization_ids": [], "no_executable_next_probe": false,
               "probe_applicability": {"<probe id>": "<applicability>"}},
  "consistency_note": "...",
  "plan": {"now": ["..."], "needs_new_authorization": ["..."], "future_conditional": ["..."]},
  "calls": [{"cmd": "...", "exit": 0, "note": "..."}],
  "errors_and_retries": ["..."],
  "wall_clock_minutes": 0,
  "uncertainties": ["..."]
}
```

回复我时**只写**：1) 贡献与最强基线各一句；2) 报告里哪个数字你没复算出来（若有）；3) 包的轮数与
`packet-check` 的最终状态；4) `decision` 给出的 frontier 与 `needs_authorization`；5) 三层计划各一行。
不要贴 JSON 全文。
