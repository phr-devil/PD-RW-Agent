# v0.7.6 — Scoped resume diagnostics and Run coverage

- Compact resume now preserves specific `history_status`, raw read-only recovery routes, and machine-readiness status/reason when present. Full remains backward-compatible. This is output summarization, not internal I/O reduction or grant verification.
- `audit_scientific_experiment` optionally checks a hash-linked DEV/VAL fold-by-arm matrix through existing `evaluation_plan` JSON and `evaluation_results` CSV Run artifacts. No new MCP tools, dependencies, scientific ledger or host executor. Missing and skipped cells remain reviewable, not automatic project failure; duplicates and unplanned skips are structural conflicts.
- Synthetic CI fixtures test recovery mismatches, coverage/skip/duplicate cases, and tampered hash links. Real private projects 42/43/44 remain `NOT_MEASURED`. See [WorkBuddy acceptance](WORKBUDDY_ACCEPTANCE.md).
