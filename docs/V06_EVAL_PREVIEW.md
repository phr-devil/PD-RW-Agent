# v0.6 evaluation-preview: local operator instructions (v0.5.1)

**Status:** Synthetic engineering contract implemented. Actual WorkBuddy, independent expert scientific quality and efficiency remain `NOT_MEASURED`. PD-RW is the only scientific rule authority; no new stage, permissions, or MCP tools.

## 1. Decision and negative-premise preview

```powershell
python -m pdrw_agent.science.cli decision --packet evals/examples/synthetic_decision.json
```

A proposal JSON contains `question`, `claim_type` (`CAPABILITY`, `MECHANISM`, `LAW`), `proposed_premise` (`premise_id` plus nonempty `scope`), 2–6 `hypotheses`, 1–6 `probes` and optionally `prior_negative_lessons`, `claim_evidence_refs`, `prechecks`. Each probe also requires an explicit `observable`, `evaluation_unit` and `comparison_reference` shared across the hypotheses; missing measurement context is an input error, not an information-value signal. Claim types are normalized to the existing PD-RW `CAPABILITY/PERFORMANCE`, `MECHANISM/CAUSAL`, `LAW/BOUNDARY` categories. Probes declare predictions per hypothesis (`INCREASE`, `DECREASE`, `NO_CHANGE`, `UNKNOWN`) and a cost band (`LOW`, `MEDIUM`, `HIGH`, `UNKNOWN`).

Output `ADVISORY_REVIEW_ONLY` shows *declared* hypothesis pairs with distinct predictions. Its count is not calibrated information gain, expected effect size or paper-value ranking. A matching negative premise and exactly matching scope **never authorizes STOP or proves scientific equivalence**. If a past result is invalid/unknown, the tool refuses to treat it as valid negative evidence.

Six optional prechecks are `label_provenance`, `group_independence`, `legal_inputs`, `evaluation_integrity`, `metric_appropriateness`, `effect_size`. Their declared statuses are `PASS`, `FAIL`, `UNKNOWN`, `NOT_CHECKED`. Missing checks default to `NOT_CHECKED`; declared `PASS` without source becomes `SOURCE_REQUIRED`, not independently verified. Scientific interpretation follows PD-RW `HIGH_VALUE_RESEARCH_DESIGN.md` and `SCIENCE_RESULT_HARVEST.md`. No references, article originality or Run provenance are fetched or fabricated.

## 2. Prepare real A/B/C frozen replay (manual, not executed by this tool)

Follow authoritative PD-RW `REPLAY_PROTOCOL.md`: reconstruct the actual history at decision time, then freeze **legally available** records, original user scope, version, tools, budget and referenced documents. Exclude future outcomes and SEALED/holdout. If original sources are unavailable, set the case `NOT_REPLAYABLE` rather than inventing a substitute.

Each local manifest has `schema_version: 1`, `case_id`, a timezone-aware `frozen_at`, 1–20 `sources` with relative path and SHA256, and `allowed_evidence_refs` drawn from those sources. Only local files up to 2 MB are checked; no network access or protected paths.

```powershell
python -m pdrw_agent.science.cli replay-check --root evals/examples --manifest evals/examples/synthetic_case.json
```

`STRUCTURAL_SNAPSHOT_VERIFIED` means only that listed files have matching bytes. **Not proven:** historical completeness, source authenticity, valid approvals or absence of leaked future knowledge in text. Read-only check does not open sealed content. The example is synthetic and must not be presented as a historical research case.

Use three equal-budget conditions: A direct WorkBuddy + PD-RW, B plus Skill, C plus Skill+Python/MCP. All responses must contain exactly PD-RW's `ROUTE`, `EVIDENCE_USED` (list of allowed frozen refs), `NEXT_ACTION`, `AUTH`, `DECISION_SCOPE`, `CLAIM_BOUNDARY`, `COST_CAP`, `EXPECTED_DECISION_CHANGE`. Never claim an unexecuted recommendation was a completed experiment.

To make blind packets after **independently collecting** real A/B/C replies, run:

```powershell
python -m pdrw_agent.science.cli replay-blind --root D:\private\replay-case --manifest D:\private\replay-case\case.json --a D:\private\A.json --b D:\private\B.json --c D:\private\C.json --seed 20261113 --private-key D:\private\unblind.json
```

The CLI prints only randomized X/Y/Z reviewer responses and **writes** the unblinding map to the specified NEW file outside the frozen case folder. Keep that file private, outside Git, with Windows ACL configured appropriately. A human must check identity and future knowledge embedded in free text before using the packet; machine-checked evidence IDs alone cannot detect that contamination.

Before unblinding, independently review unauthorized operations, leakage, citation grounding, baselines, negative results, unfair splits, next-probe discriminability and premature GO/STOP. After unblinding compare paired outcome quality and actual model/GPU/human cost. See `evals/AB_C_CAPTURE_TEMPLATE.md`.

**Next gate:** Run actual WorkBuddy scenarios and record traces; use failures to justify any new MCP or memory feature. Never infer increased publication probability from synthetic tests.
