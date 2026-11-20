# 任务：一个冻结的真实决策点

你是一个独立的科研决策会话，没有参与任何工具开发。下面是**冻结的**证据快照，只包含该决策点当时可见的材料。证据之外的东西（原始数据、SEALED、后续结论）你看不到，也不要去猜。

## 证据

```
D:\workbuddy-agent\PD-RW-Agent\audit\science04\frozen\DP1-POPU-HOLD\
```

先读 `MANIFEST.json`（它列出了每个文件的 sha256，以及**被有意排除**了什么），再按需读其他文件。这些文件只读，不要修改，不要训练，不要下载，不要运行实验。

## 研究问题

> 在 PoPu DEV 数据上，可靠性机制相对基座是否带来可部署的增量？

## 你要做的四件事

1. **机会**：基于可见证据与你的领域判断，指出一个仍有信息价值的科研机会。必须说明它为什么**不是**已经做过的实验（点名你已经看到的 Run）。
2. **假设**：2–4 个具有**不同科学机制**的竞争假设。每个都要写：机制、它对应的最强基线、以及在下一步实验里可观察的定性预测（INCREASE/DECREASE/NO_CHANGE/UNKNOWN）。
3. **实验**：一个**最小**的、**合法**（参考条件在预测时可得）的、能**区分**上述假设的实验。写清观察量、评估单位（独立单位是什么）、参考条件、成本带，并说明：它为什么合法、为什么最小、以及它是否已经跑过（若跑过，指认是哪个 Run 与哪个记录字段支持你的判断）。
4. **贡献**：如果现在就要把这些证据写成论文，最可信的贡献是什么？现有证据支持到什么程度（STRONG / PARTIAL / ABSENT）？还缺什么证据？补齐的**最短路径**（按顺序 1–3 步，每步说明它排除什么替代解释）。

## 约束

- 只使用证据快照里的文件；引用时写文件名与字段名。
- 不得编造数字、Run、引用或结论。看不到的就写 UNKNOWN。
- 若某个判断依赖你的领域先验而非文件证据，明确标注 `PRIOR`。
- 不要读 `D:\workbuddy-agent\PD-RW-Agent` 下的 `src/`、`tests/`、`docs/`、`skills/`、`audit/science03*`。

## 输出

写到 `D:\workbuddy-agent\PD-RW-Agent\audit\science04\answers\B1_DP1.json`：

```json
{
  "decision_point": "DP1-POPU-HOLD",
  "opportunity": {"claim": "...", "why_not_already_done": "...", "evidence_refs": ["文件:字段"]},
  "hypotheses": [{"id": "...", "mechanism": "...", "strongest_baseline": "...",
                  "prediction": "INCREASE|DECREASE|NO_CHANGE|UNKNOWN"}],
  "experiment": {"id": "...", "observable": "...", "evaluation_unit": "...",
                 "comparison_reference": "...", "predictions": {"假设ID": "方向"},
                 "cost_band": "LOW|MEDIUM|HIGH|UNKNOWN",
                 "why_legal": "...", "why_minimal": "...",
                 "already_run": false, "which_run_if_so": null},
  "contribution": {"claim": "...", "evidence_support": "STRONG|PARTIAL|ABSENT",
                   "missing_evidence": ["..."], "shortest_path": ["1) ...", "2) ..."]},
  "read_files": ["..."],
  "uncertainties": ["..."],
  "wall_clock_minutes": 0
}
```

回复我时**只写**：1) 你提的机会与实验各一句；2) 你判断"已经跑过/没跑过"的依据是哪几条文件字段；3) 粗略耗时。不要贴 JSON 全文。
