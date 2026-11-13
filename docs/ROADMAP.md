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
