# Implementation roadmap (not a second research workflow)

## v0.7.4 first-pass runtime integration and resume correction

- The current fixed host mirrors a new attempt into the existing
  versioned `operation_attempts` table transactionally with `host_jobs`.
  Old host rows remain read-only and explicitly `LEGACY_UNLINKED`; no
  blanket DB migration or synthetic history rewriting.
- Project/operation IDs cannot be reused across *new* host fixed CPU
  jobs and logical DEV operational receipts. Existing records remain intact.
- Resume detects host STARTING/RUNNING uncertainty, completed diagnostic
  output tamper, and new host/attempt mismatch. `scientific_resume_status`
  remains separate and never promotes a diagnostic to scientific evidence.
- Keep old synthetic selftest reports; no automatic job adoption or restart.
- Next: original Run read-only end-to-end test and real WorkBuddy A/B/C;
  actual DEV runner authorization and Windows ACL remains device-gated.
- [Integration contract](V074_RUNTIME_INTEGRATION.md).


## v0.7.3 host reliability, fixture ACL gate and remaining work

- Distinguish Windows PID/birth-token identity from observed active process.
- Record interrupted fixed diagnostic attempts explicitly; never auto-retry.
- Operator-only synthetic DEV-read / denied-fixture probe with exit-code
  failure for readable protected fixture. No actual SEALED files opened.
- Still pending and **not claimed as complete**: independent restricted
  Windows principal, authenticated original user grants, real OS filesystem
  ACL enforcement, host IPC, registered DEV CPU runner and scientific Run
  registration, GPU limits, and real WorkBuddy acceptance.
- See [the bounded host acceptance contract](V073_HOST_RELIABILITY.md).


## v0.7.2 OS-supervised fixed CPU host pilot

- The host-only `python -m pdrw_agent.host.cli` is a separate operator-
  launched process, not a socket or MCP command executor. Only package-fixed
  CPU selftests are runnable, without project data, custom scripts or GPU.
- Windows child is created suspended, assigned to a kill-on-close Job
  Object, then resumed; Linux child uses its own session and parent-death
  signal. Supports cancellation, timeout, recovery diagnosis and no blind
  replay after uncertain status. Output and source hashes are scoped only.
- New read-only `get_host_diagnostic_status` MCP/CLI tool and host
  resume summaries. Independent catalog source integrity and OS identity
  probes are **not security attestations**.
- Next release must provision distinct restricted Windows host account,
  enforce DEV/SEALED ACL and network isolation, validate original author
  grants, bind a trusted catalog to the host and test real permitted
  DEV CPU execution. No such authority is inferred in v0.7.2.

## v0.7.1 source compatibility and trusted host admission foundation

- No implicit legacy state migration; complete original STATE.json/EVENTS
  consistency required for machine-ready diagnostics.
- Optional standalone SHA256 manifests do not determine scientific validity.
- Versioned private SQLite migration adds separate operation attempt table.
- Bounded DEV plan contains only pre-registered runner ID and original source
  fingerprints; not an execution grant. Default host denies ALL real DEV.
- PID+birth token observed on Linux/Windows, but OS identity ownership,
  liveness supervision, ACL/SEALED enforcement, real GPU limits, DEV run
  registration and user-grant authenticity are NOT implemented.
- Next: v0.7.2 separate OS-restricted trusted host process, ACL/Job Objects
  on Windows, unforgeable source of user consent, real process containment,
  and host-owned process/resource supervision. See V071_HOST_READINESS.md.

## v0.7.0 execution foundation: fixed synthetic CPU only

- Strict versioned plan schema, bounded CPU/timeout limits, explicit project
  registry and STATE/EVENTS metadata preflight. No model-supplied approval.
- Private SQLite checkpoint for one fixed synthetic subprocess; unique
  project/operation/plan identity, no duplicate execution or blind retry.
- RUNNING retained as UNKNOWN after interruption; private result hash
  recorded only on verified synthetic completion, not a scientific Run.
- MCP/CLI expose planning and checkpoint status only; internal self-test
  executor accepts no commands, script paths, datasets, GPU or network.
- Next gate: independent trusted host permission enforcement, real DEV
  scheduler, OS-level process sandbox, liveness/heartbeat and integration
  with original PD-RW Run recording. None are implemented by this stage.

## v0.6.3 source lineage and evidenced negative lessons

- Parse only hash-bound linked Python source with bounded AST; identify
  explicit forbidden feature selection in feature sinks and probable eval
  fit calls. No code execution and never claim complete dynamic provenance.
- Optional original Run-linked canonical input feature hashes identify exact
  reported content collisions across train/eval even with different IDs;
  missing/unauthenticated fingerprints remain UNKNOWN.
- New `review_evidenced_lesson`: require original DEV/VAL Run contract,
  STATE/EVENTS consistency, Run/hash-linked lesson context, independently
  recomputed challenger/baseline metrics, verified group disjointness and
  structural fairness before comparing an old negative metric observation
  to a proposed new premise. Neither the prior outcome's scientific truth
  nor the new proposal's provenance is certified.
- CLI/MCP share one service; synthetic original-contract and boundary CI
  tests. No research ledger mutations, automatic GO/STOP or SEALED access.

## v0.6.2 scientific evaluation checking engine

- A Run-linked `science_audit` spec and DEV/VAL artifacts are hash-attested
  via PD-RW before bounded row-level checking.
- Exact train/eval sample/group overlap, evaluation-unit-specific numeric
  scores, declared feature allowlist, and matched baseline rows/metrics.
- Explicit FAIL vs UNKNOWN vs scoped PASS. Not a trained-code tracer,
  near-duplicate detector, label truth auditor, metric fairness proof, or
  automatic permission/claim authority. Full details:
  [docs/V062_SCIENCE_VALIDITY.md](V062_SCIENCE_VALIDITY.md).
- Synthetic and original-PD-RW-backed tests on Windows and Linux.

## v0.6.1 history/Run/lesson applicability increment

- New read-only `reconstruct_project_history` checks the original
  STATE.json/EVENTS.jsonl metadata chain without opening SEALED artifacts;
  blocked reconciliation is separate from optional source diagnostics.
- `verify_run_evidence` checks original PD-RW Run structural contract,
  indexed source SHA-256, metadata and bounded declared linked hashes.
- `review_lesson_applicability` compares literal negative premise and
  declared scope with conservative UNKNOWN/conflict categories. Exact
  declared scope is not proof of scientific equivalence or automatic STOP.
- CLI/MCP expose these selective tools, with synthetic fixture tests.
- Future: immutable authorized Run archival, stronger scientific data quality
  checks, semantic premise review with independently grounded evidence, and
  actual WorkBuddy cost/quality measurement.

## v0.6.0 state/evidence increment

- Bounded read-only `audit_project_state` is shared by Python CLI and MCP.
- Markdown `PROJECT_ID` identity checks and historical snapshot heading
  support; rule navigation accepts longer unambiguous queries or lists
  available topics instead of inventing a match.
- Missing EVENTS is distinguishable from a present but empty Run index;
  SQLite receipt-status queries use an actual read-only connection.
- Synthetic regression tests target byte integrity, missing evidence, rule
  versions and no project writes. WorkBuddy quality/Token benefit is not
  yet measured.
- Future increments: structured lesson retrieval, trace-backed durable
  checkpoints, trusted executor host and end-to-end WorkBuddy tests.

## Current delivery: v0.3/v0.4 foundations

- Shared installable Python package under `src/pdrw_agent/`.
- Five bounded, **read-only** tools available through both Python CLI and optional MCP v2.
- Explicit project registry, selective PD-RW rule lookup, historical case-index search, non-SEALED run index, conservative fingerprint checking.
- Existing `skills/pd-rw-research/scripts/bridge.py` and `context.py` retained temporarily as standalone compatibility tools. In a later version, either package the shared runtime for Skill use or retire legacy scripts after a measured WorkBuddy migration.
- CI validates existing plus new unit tests across Windows and Linux, including the MCP SDK where installed.

## v0.5 completed engineering foundation (not yet WorkBuddy validated)

- `get_resume_context`, `get_execution_status`: bounded project + private operational resume receipts.
- `begin_operation_receipt`, `checkpoint_operation_receipt`: local SQLite operational-only event breadcrumbs with optimistic concurrency and idempotent retries. No GPU execution and no permission grant.
- `preview_experiment_record`: original PD-RW `validate_run` and `core.cli status` via subprocess, with protected-history fail-closed and conflict handling.
- `prepare_handoff`: reuses PD-RW `core.delivery_check`, creates no research files.
- `register_run_in_trusted_host`: **always-fail-closed compatibility interface**; writing is disabled even with a caller-provided callback. A separate secured host must implement the future authorized path.
- Original 5 tools remain compatible; real WorkBuddy adoption and performance benefit are NOT_MEASURED.

## v0.5.1 scientific evaluation preview (no new MCP capabilities)

- Optional `science/decision.py` compares only declared negative-premise scope and qualitative probe predictions; cannot prove equivalence, novelty or scientific value.
- Optional `science/replay.py` verifies local frozen file SHA-256, rejects unlisted evidence refs and creates blind X/Y/Z reviewer packets with a separate mapping.
- No execution, automatic STOP, scientific ledger writes or WorkBuddy results. Real A/B/C is still `NOT_MEASURED`.

## v0.5.2 evidence-bound decision and failure classification

- Optional `science/lessons.py`: bounded, read-only compilation of declared `ENGINEERING_FAILURE`, `INVALID_EXPERIMENT`, `INCONCLUSIVE`, `VALID_POSITIVE` and `VALID_NEGATIVE`; only declared valid negatives become advisory premise candidates.
- Optional `science/provenance.py`: bind decision/lesson citation IDs to existing **time-frozen** allowlisted files with checked SHA-256; does not validate scientific truth or original historical provenance.
- CLI remains local and opt-in. Source-binding failures return a nonzero exit, no output Run/claim is written, and the 11 MCP tools are unchanged.

## Next: WorkBuddy client integration gate

- Validate startup/handshake and each of five tools from the real WorkBuddy UI.
- Verify automatic Skill selection, correct on-device source root, no fabricated Run, no SEALED read, fresh-session recovery and minimal tool outputs.
- Compare against direct PD-RW-document baseline on the same frozen task, model and input budget. **NOT_MEASURED** until real traces collected.

## Later: true governed writes and durable job execution

- Add a *trusted* tool host to authenticate original user actions independently; test protected paths at OS/tool level.
- Reuse PD-RW `core.state` event writer; idempotent record registration and crash-safe recovery with conflict tests.
- Optional bounded external execution receipt/checkpoint for an already authorized local task; never a parallel scientific record.
- Preserve user choices H1–H6/H8, autonomous authorized H7 DEV, and separate SEALED/confirm/writing/figure/upload/pay/submit gates.
- Add real historical blind A/B tests using PD-RW `REPLAY_PROTOCOL.md`; no fake measures or token-saving claims.

## Non-goals

No new scientific policy, unbounded shell/file tools, cloud service, vector database, speculative multi-agent planner, training scheduler or new GPT API billing by default.
