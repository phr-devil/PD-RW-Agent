# v0.7.1 — source compatibility, plan contracts and host admission

## Contract

PD-RW is still the sole authority for scientific decisions, STATE/EVENTS,
original Run, H6/H8 author strategy and actual user permission. There is
no second science ledger, no extra user confirmation stage, and **no real
DEV/GPU executor** in this version. v0.7.1 keeps 19 MCP tools; no new
arbitrary-command, training or Run-writer tool is exposed.

## Project sources

Readiness has separate outcomes for:

- LEGACY_READ_ONLY: historical Markdown STATE only. Original sources
  can be read within their original allowed scope; no implicit conversion.
- MACHINE_METADATA_READY: original STATE.json + EVENTS.jsonl reconstruct
  to the same metadata, with no contradictory identity declaration.
- MACHINE_LEDGER_INCOMPLETE / MACHINE_LEDGER_CONFLICT /
  MACHINE_STATE_INVALID / STATE_IDENTITY_CONFLICT: diagnose without repair.

A matching machine ledger is not scientific truth or permission. If original
PD-RW has event and linked hashes, absence of an additional standalone
.sha256 manifest is only an advisory. Actual missing/mismatched original Run
hashes still prevent positive evidence attestation. Protected path lexical
segments are rejected before symlink/path resolution, too.

## Private operation schema

Migration occurs ONLY on a write-mode SQLite connection. Schema version 2
adds operation_attempts separate from logical operations. Older operation
rows are preserved. Read-only status does not mutate or upgrade the DB, and
a DB with a higher version than the installed agent refuses writer access.

Runtime, evidence, science and authorization states are separate:
UNSTARTED/RUNNING/EXITED/INTERRUPTED/UNKNOWN for runtime,
NOT_REVIEWED/VERIFIED_SCOPED/INCOMPLETE/CONFLICT for evidence,
NOT_REVIEWED/VALID/INVALID/INCONCLUSIVE for science, and
UNVERIFIED/IN_SCOPE/OUT_OF_SCOPE for authorization.

No operational state, hash or model-declared status upgrades science.

## Host contracts

The host proposal schema pdrw-dev-plan-v1 contains only project/task/
operation identity, action DEV_CODE/DEV_TRAIN/DEV_EVALUATE/DEV_FIX,
a registered runner ID, TaskSpec/code/dataset fingerprints, requested
seconds/CPU/GPU and an explicit DEV-only, no-network scope.

No commands, paths, environment, model-approved flag, SEALED operations
or authorization strings are accepted. Plan fingerprint is canonical SHA256.
The internal preview_dev_admission always refuses to authorize real
execution. The internal submit_dev_in_trusted_host remains a non-executing,
non-MCP stub. Adding an OS supervisor or running training is NOT included
in this release.

Process observation reads Linux procfs start ticks or Windows creation
FILETIME with PID, so a simple reused PID does not falsely match. This
is a diagnostic and not host ownership, process-tree supervision, actual
Windows liveness, ACL containment, heartbeat or execution permission.

## Acceptance and next gate

GitHub Actions on Ubuntu and Windows must pass original PD-RW integration,
synthetic process termination, legacy DB upgrade, conflicting dual states,
forged plan, protected paths and non-mutating status.

For actual Windows WorkBuddy DEV/GPU launch, a **separate OS-restricted
host** still needs native identity/ACL verification, DEV/SEALED path
separation, original user grant authentication, a trusted runner registry,
Windows Job Object containment, child process identity, cancellation,
restart reconciliation, resource monitoring and original PD-RW Run
registration. None can be inferred from a JSON plan or these CI results.

Real WorkBuddy task quality, token savings, unattended DEV execution and
scientific validity remain NOT_MEASURED until controlled on-device trials.
