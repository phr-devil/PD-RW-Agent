# v0.6.3 — Bounded source-risk and Run-grounded negative lessons

**Scope.** PD-RW remains the only scientific authority. Python/MCP perform
read-only diagnostic checks on explicitly registered, hash-verified DEV/VAL
original Runs. They do not grant authorization, certify the scientific
validity of a negative hypothesis, or perform autonomous STOP.

## 1. Source-code lineage candidates

After \`verify_run_evidence\` succeeds, \`audit_scientific_experiment\`
reads the Run-linked \`artifact_refs.code\` as source text **without execution**.
Only UTF-8 Python files <=256 KiB and ASTs <=25,000 nodes are inspected.

Recognized patterns:
- Literal feature-column lists in assignments to \`X\`, \`X_train\`,
  \`features\`, \`feature_matrix\`, etc., including unambiguous single-assignment
  constant list aliases and direct \`df.loc[:, [...]]\` selections.
- Feature names outside the original Run's \`legal_inputs\` are reported as
  \`STATIC_FEATURE_ALLOWLIST_CONFLICT\`, with only counts and code line numbers
  returned, not raw columns or data.
- \`fit\` / \`fit_transform\` / \`partial_fit\` calls whose first positional
  argument is explicitly named like \`X_test\`, \`X_eval\`, or \`X_val\` are
  reported as \`POSSIBLE_EVALUATION_FIT_OR_PREPROCESSING_LEAK\`.
- Multiple assignments, dynamic pipelines, feature generators, other languages,
  imports, closures and unrecognized sinks are **UNKNOWN**.

A finding is \`REVIEW\`, not proof that a particular code path was executed.
A script containing none of these patterns is **UNKNOWN**, not PASS.
These checks do not prove prediction-time feature availability, label absence,
no indirect leakage, causal independence, or computational reproducibility.

## 2. Exact content-fingerprint collisions

Optional **Run-linked and hash-verified** CSV artifacts:
\`artifact_refs.train_content_hashes\` and
\`artifact_refs.eval_content_hashes\`, with columns
\`sample_id,group_id,feature_sha256\`. The hash should be generated from
canonically serialized prediction-time input content by the producing
pipeline, *not* from ID, target, future label, or metadata.

The engine verifies sidecar sample/group membership matches the existing
Run-linked \`train_index\` and prediction rows exactly, then compares
64-hex SHA-256 digests across the splits.

- Overlap: \`FAIL\` (declared exact-content collision), not proof of true raw
  duplication unless fingerprint provenance has been audited separately.
- No overlap: \`UNKNOWN\` for general near-duplicates, arbitrary transforms
  and fingerprint source authenticity.
- Missing/malformed manifests: \`UNKNOWN\` or specific membership/format FAIL.
- Content hashes and private sample IDs are **not** returned.

## 3. Original Run-grounded negative lesson reuse

MCP: \`review_evidenced_lesson(project_id, run_id, proposal)\`

CLI: \`python -m pdrw_agent.cli lesson-evidence --project-id 19 --run-id r12 --proposal-file proposed.json\`

The *original DEV/VAL* Run must have a hash-bound
\`artifact_refs.lesson_context\` JSON artifact:

    {
      "schema_version": "pdrw-run-lesson-v1",
      "run_id": "r12",
      "premise_id": "premise-A",
      "outcome": "DECLARED_NEGATIVE",
      "minimum_important_improvement": 0.01,
      "scope": {
        "dataset_version": "v1", "label_definition": "target-v1",
        "evaluation_unit": "sample", "group_split": "LOSO",
        "legal_inputs": "sensor1,sensor2",
        "metric": "MAE", "comparison_reference": "baseline-run-id"
      }
    }

\`legal_inputs\` is a comma-joined sorted list derived from the original
Run. Every critical scope field must match the Run's declared metadata or
its registered audit baseline. The prospective proposal uses the same
\`premise_id\` + \`scope\` schema.

Before producing a candidate, the engine requires:
1. STATE/EVENTS consistency; original Run + all link SHA-256 matches;
   original PD-RW Run structural contract; DEV/VAL + declared VALID.
2. Hash-bound sidecar, sidecar ID/metadata consistency.
3. Independently recomputed challenger metric, structurally comparable
   baseline metric, declared evaluation/independence units and no exact
   train/evaluation membership overlap.
4. No science-audit FAIL or static code REVIEW.
5. An improvement no greater than the sidecar's explicitly declared
   minimum important improvement threshold.
6. A literal compatible declared premise scope for the prospective plan.

\`RUN_LINKED_NEGATIVE_METRIC_CANDIDATE\` means the original files show a
limited negative *metric observation*, not that an algorithm hypothesis is
false. Preregistration and authenticity of the threshold, label semantics,
training-code behavior, independent validation, science/causal effect,
prospective proposal facts, and generalization remain **NOT VERIFIED**.
Never auto-STOP a new project, copy a failure claim across datasets, or
treat a historic INVALID Run as a valid negative.

## Safety and engineering limits

- Original Run and sidecars are read only after hash/contract verification.
- Only registered roots; no disk search, SEALED, external downloads or writes.
- Bounded files/rows and explicit UNKNOWN rather than speculative PASS.
- No new scientific ledger, claim/Run writer or permissions bypass.
- Verified CI using synthetic original-PD-RW-contract fixtures does not prove
  genuine WorkBuddy scientific benefit; evaluate separately on complete
  historical DEV projects with accessible original Runs.
