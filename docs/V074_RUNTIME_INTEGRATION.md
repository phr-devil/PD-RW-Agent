# v0.7.4 — First-pass runtime linkage and conservative resume

## Changes

The existing fixed CPU host (\`host/supervisor.py\`) now writes each NEW
engineering attempt to the v0.7.1 \`operation_attempts\` table *in the same
SQLite transaction* as its corresponding \`host_jobs\` row and state updates.

- Logical identity: \`(project_id, operation_id)\`.
- Attempt identity: \`(project_id, operation_id, attempt_id)\`.
- Immutable plan fingerprint, PID and creation token, final exit code and
  output digest are mirrored between the existing host and attempt records.
- Read-only status reports \`attempt_link = MATCHED | CONFLICT |
  LEGACY_UNLINKED\`. Older host records are never silently upgraded or
  given invented attempts; they remain readable.
- New fixed host jobs and \`operations\` receipts cannot claim the same
  project/operation key. Existing records are left unchanged.
- The project resume adapter now reports an independent
  \`scientific_resume_status\` and \`host_reconciliation_required\`.
  Unfinished fixed host attempts, conflicting mirror records and tampered
  output are surfaced as \`NEEDS_OPERATIONAL_RECONCILIATION\` if the
  scientific receipt was otherwise neutral.
- Existing v0.7.0 \`synthetic_jobs\` are read-only legacy-compatible.
  Their unresolved state is reported but does not change the previous
  science resume code; it never authorizes a restart.

## Limits / unchanged authority

This is a **first-pass integration**, not a schema replacement or a
database clean-up. Older host rows may not have an attempt mirror.
The last ten host rows can be summarized without rewriting historical
source files. Optional older synthetic jobs and host diagnostics remain
separate from original PD-RW scientific evidence.

Original PD-RW v1.13 remains authoritative for Rule/STATE/EVENTS/Run.
The private operational SQLite never certifies model performance or
author intent. No arbitrary shell, real DEV/GPU execution, protected
SEALED read, signed consent, authenticated IPC, scientific Run writer or
automatic retry is newly introduced.

## Validation

Test exactly one child for concurrent duplicate attempts, mirror
consistency after completion/timeout, legacy host row compatibility,
cross-table operation-ID collisions, tamper/concurrent failure and
resume outcome. Test both OS CI, with the original PD-RW rule checkout.

Do not claim actual WorkBuddy token savings or Windows account ACL
isolation until measured on a live workstation.

## Remaining work

1. Read-only WorkBuddy evaluation with original frozen valid/negative/invalid
   DEV source materials; classify missing source as NOT_REPLAYABLE.
2. Independently restricted Windows host SID and real ACL DEV/SEALED test.
3. Authentic original grant store and restricted real DEV CPU runner,
   secure IPC and original PD-RW \`core.state\` Run registration.
4. GPU budget enforcement and matched WorkBuddy token/quality A/B/C.
