# v0.6.2 — Bounded Scientific Evaluation Audit (DEV/VAL only)

**Authority:** PD-RW WORKFLOW/core.contracts/STATE/EVENTS remain the only
scientific authority. This engine checks *specific original-file predicates*
rather than certifying scientific truth, user permission, originality or Q2 potential.

## Entry points

- MCP: audit_scientific_experiment(project_id, run_id, baseline_run_id="")
- CLI: python -m pdrw_agent.cli science-audit --project-id 37 --run-id <id>

Before opening row-level data, the engine calls v0.6.1 verify_run_evidence:
registered STATE/EVENTS consistent; original Run PD-RW contract VALID;
Run JSON and all linked artifacts hash matched; split DEV or VAL; no SEALED.
The optional audit config **must** be an original Run artifact:
artifact_refs.science_audit -> hashed JSON with linked_sha256 coverage.

## Example sidecar, linked from Run artifact_refs

    {
      "schema_version": "pdrw-science-audit-v1",
      "run_id": "r-main",
      "metric": "MAE",
      "evaluation_unit": "sample",
      "independence_unit": "group",
      "baseline_run_id": "r-base",
      "used_inputs_declared": ["sensor"]
    }

Original Run must declare \`evaluation_unit\` to obtain a positive unit
consistency check. A sample/group unit mismatch is a hard FAIL. The Run's
\`metrics\` must contain the exact named key. Supported \`metric\` values:
\`MAE\`, \`RMSE\`, \`accuracy\`, \`macro_f1\`. Macro-F1 requires
\`class_labels\` (fixed complete class universe including absent classes);
classification group aggregation is unsupported (UNKNOWN). For group
regression, group-macro MAE = mean(per-group MAE) and group-macro RMSE =
mean(per-group RMSE); these are **not** equivalent to pooled RMSE.

Predictions must be hashed, bounded UTF-8 CSV at original
\`artifact_refs.predictions\`, with
\`sample_id,group_id,y_true,y_pred\`. At most 100k rows and 8 MiB/file.
\`artifact_refs.train_index\` is a hashed optional CSV containing
\`sample_id,group_id\`; missing source -> leakage UNKNOWN, never PASS.
Malformed or duplicate training membership rows are FAIL. An optional `sample_ids_hash_rule: "sha256_sorted_ids_v1"` binds the Run's sample_ids_hash to SHA-256 of sorted exact UTF-8 sample IDs, each terminated by LF. Legacy IDs without a defined convention remain UNKNOWN.
Group-disjoint checks exact IDs and all group IDs. Sample-disjoint checks
exact sample IDs, reports group overlap but does not reject it.
**Exact group absence is not proof of no duplicates, causality, unobserved
identifier aliasing, subject leakage or dataset identity correctness.**

Inputs: \`used_inputs_declared\` from the hashed sidecar is compared against
original Run \`legal_inputs\`. Declared illegal features cause FAIL; matching
declarations yield UNKNOWN because the code's actual feature accesses,
prediction-time availability and preprocessing have not been traced.

Baseline (optional): a separate verified Run must match exact
task/protocol/dataset/evaluator/split/group-split/sample-ID hash, evaluation
unit, metric, legal inputs, declared label definition, metric direction and budget basis. Missing budget, label definition or metric direction yields UNKNOWN instead of fairness PASS. Both Runs must also have matching training membership (when hash-bound); missing training membership yields UNKNOWN. Sample-level group/label
identity and recomputed baseline metric must match. Positive baseline PASS
only means structural comparability under these recorded conditions; it
does not prove tuning-budget parity or a causal ablation.

## Result interpretation

- \`SCIENTIFIC_AUDIT_CONFLICT\`: at least one independently detectable
  mismatch (e.g. exact ID leakage, metric discrepancy, unfair cohort).
- \`SCIENTIFIC_AUDIT_INCOMPLETE\`: some checks cannot be independently resolved.
- \`SCOPED_NUMERIC_CHECKS_MATCHED_ONLY\`: all selected tests matched;
  does NOT mean scientific evidence, model deployment, or user authority pass.
- \`AUDIT_PREREQUISITE_UNVERIFIED\`: blocked at immutable record / hash
  / scope / source requirements, before reading prediction rows.

Each check has PASS/FAIL/UNKNOWN and small counts; no raw IDs, prediction rows,
individual group labels or private file contents are returned. Never fixes
STATE/EVENTS, downloads, trains, accesses SEALED or auto-approves H8/H9.
Outputs are for investigation; if a scientific blocker is found, its root
cause and correct experiment protocol still require independent review.

## Validation

Synthetic original-contract-checked test fixtures exercise nonoverlapping
cohorts, exact sample+group reuse, score drift, immutable hash changes,
baseline evaluation mismatch, budget mismatch, missing source, protected
references and grouped metric behavior. GitHub CI runs on Windows+Ubuntu.
End-to-end user WorkBuddy behavior and Token/effect gains are NOT_MEASURED.
