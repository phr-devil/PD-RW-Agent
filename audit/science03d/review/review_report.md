# Blind review — the two arm pairs, as returned

Reviewer: a fresh WorkBuddy session that had not seen the patch. It was given
`review_bundle.json` (arm labels A/B shuffled) and the fixture project, told to
verify the Runs against the files itself, and not told which arm was which.
Unblinding key: `review_key.json` (pair 1: A = 0.9.11, B = 0.9.12; pair 2:
A = 0.9.12, B = 0.9.11).

## What it verified in the fixture before judging

- `RUN-101`: record `run_id` = directory, plan `PROTO-PRESS-BEAM-26` with a
  `protocol_sha256` matching the plan file byte for byte, `status` COMPLETED,
  anchor PASS, base 9.171 / beam 9.204 with a paired delta CI of [-0.09, 0.16]
  (contains 0) — a negative under the frozen rule.
- `RUN-102`: record still says `RUN-101`, no aggregate block — a copy, not an
  independent replication.
- `RUN-103`: no `run_id`, no `protocol_id`, no `status`, no CI, self-described
  scratch copy.
- `STATE.md`: "the sensor line's question was not answered by any Run".
- The only substantive input difference between the two packets: the
  `premise_id` of the probe citing `RUN-101` (`BEAM_STIFFNESS_MECHANISM` in
  pair 1, `SENSOR_DRIFT_MECHANISM` in pair 2).

## Verdicts (verbatim, trimmed to the decisive sentences)

Pair 1 (`D1_fixed`), chose **B**:

> "B 明确给出 `run_id_consistency: MISMATCH`、`EXECUTION_STATUS_CONFLICT`、
> `applicability: STATUS_CONFLICT` … A 在 P2（乃至全部探针）的
> `run_id_consistency / record_structure / premise_binding_basis` 全为 null，
> 等于对目录名与记录 run_id 不一致**完全未核对、未指出**."
> "两者都不构成『没做过的实验被判无需再做』的风险" (identical on that axis).

Pair 2 (`D1_misattributed`), chose **A**:

> "**B**，在 P1：`premise_binding: MATCH`、`status_verified: true`、
> `HISTORICAL_EVIDENCE_ONLY` … 原始文件不支持这一说法 … 一个 beam 臂对基线的
> 负结果不能算传感器漂移前提的历史证据。A 没有这样断言——它给的是
> `CLOSURE_PREMISE_CONTRADICTED`（basis: FROZEN_PLAN），方向正确。"
> "这正是把『从不存在的实验』读成『已有结论、无需再做』的路径。"

## Criticisms taken into the code

1. "A 自身缺陷：P1 同时出现在 frontier 与 premise_contradicted 中，自相矛盾；
   `status_verified: false` 却做出闭合级别的判断." — The action label was indeed
   `RUN_IF_LEGAL_AND_DISCRIMINATING`; it is now
   `CONFIRM_WHICH_EXPERIMENT_THE_RUN_ANSWERED`, and the finding's question asks
   which experiment the Run answered.
2. "把复现降级为『先解冲突』" — accepted as intended: a conflict is resolved
   before compute, not instead of it.

## Criticism accepted but not engineered away

A contradicted probe remains in the frontier. Removing it would re-close a live
experiment on the strength of a label, which is the error this round fixes. The
reviewer's own note — "若后续没有复现动作" — is the real risk, and it is a
researcher decision, not a checker one.

## Limits the reviewer stated

- It did not open `review_key.json` or `eval_packets.json`, so it could not know
  which implementation each arm was, nor whether MATCH/MISMATCH is defined
  against the probe premise or the packet premise.
- It could not tell whether the 0.9.11 arm read RUN-101 or RUN-102 for the
  copied-record probe, only that the arm did not distinguish them.
- It did not run experiments or recompute metrics; its only computation was the
  `protocol_sha256` check against the plan file.
