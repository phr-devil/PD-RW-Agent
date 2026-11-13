# Implementation roadmap (not a second research workflow)

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
