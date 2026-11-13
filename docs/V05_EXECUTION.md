# v0.5 autonomous continuation + governed registration — single implementation contract

> **Runtime is ready for synthetic tests; WorkBuddy on-device behavior and
> independently enforced original-user authorization are NOT validated.**

This is an execution adapter, **not** a new PD-RW scientific phase or a second evidence database. PD-RW `AGENTS.md` / `WORKFLOW.md`, existing `STATE.json`, `EVENTS.jsonl`, `RESEARCH_RECORD.md`, raw Runs and original author messages remain authoritative.

## AI-readable call order

1. On fresh chat/project switch, call `get_resume_context(project_id)`. A conflicting or incomplete project context returns `BLOCKED_PROJECT_IDENTITY` or `BLOCKED_INCOMPLETE_CONTEXT`; use source recovery only, no execution hint. Confirm actual project ID, user scope and original evidence; do not trust a receipt as science.
2. When a previous receipt indicates `RUNNING_DECLARED` or `ARTIFACT_REPORTED`, query `get_execution_status`, check the *real* process/log/Run through the already-allowed local tools, and reconcile before repeating a GPU job. No automatic restart.
3. For a meaningful, already-authorized non-paid DEV work unit, call `begin_operation_receipt(project_id, operation_id, task_id, action)` **once**. Receipt writes reject missing project context and a declared Task that conflicts with the indexed active Task. A receipt records intent only; does not authorize, execute, or freeze scientific strategy.
4. At a meaningful state change, call `checkpoint_operation_receipt(..., expected_revision, phase, artifact_ref?)`. Never checkpoint every line or every test. `ARTIFACT_REPORTED` needs a small existing non-protected evidence file; it is a source claim, not independently verified science.
5. Before scientific Run registration, call `preview_experiment_record(project_id, artifact_ref)`; only returns structural/source-integrity hints. **No MCP or CLI tool can modify original PD-RW research ledger.**
6. When delivering real files, call `prepare_handoff(project_id, primary_ref, supporting_refs?)`. The result validates paths only. Follow current PD-RW `NEXT_ACTION_POLICY.md` for scientific meaning, next legal action, and authorized updating of existing record/blueprint.

## Tool table

| Tool | Effect | Output contract |
| --- | --- | --- |
| `get_resume_context` | Read | Existing snapshot + at most six unresolved operation receipts |
| `get_execution_status` | Read | Small SQLite receipt index, artifact integrity, process liveliness **not verified** |
| `begin_operation_receipt` | Private metadata write | `RECEIPT_CREATED`, `ALREADY_RECEIPTED`, `OPERATION_ID_CONFLICT`; never permission |
| `checkpoint_operation_receipt` | Private metadata write | Versioned CAS state transition; retries idempotent; technical failure ≠ scientific negative |
| `preview_experiment_record` | Read | Authoritative Run schema/status check when safe; dedup candidate, explicit blocks |
| `prepare_handoff` | Read | Original PD-RW path-only checker, no output artifact generated |

Only four supported receipt actions: `DEV_CODE`, `DEV_TRAIN`, `DEV_EVALUATE`, `DEV_FIX`. States are `PLANNED`, `RUNNING_DECLARED`, `ARTIFACT_REPORTED`, `TECHNICAL_FAILED`. These are **operation receipts** and never H1–H10 research stages.

## Setup and file ownership

- Install Python 3.11+, pinned `mcp==2.3.0`, and import the existing `skills/pd-rw-research/` Skill.
- Supply `PDRW_AGENT_CONFIG` (private explicit project paths), `PDRW_WORKFLOW_ROOT` (local PD-RW checkout), and `PDRW_RUNTIME_DIR` (absolute **private directory outside any project/Git repository**). Runtime path is not passed by the model.
- The private SQLite database stores only operation IDs, task/action, declared phase/revision, relative metadata artifact ref/SHA and timestamps. It is **not** a replacement scientific ledger.
- Do not commit `project-map.local.json`, local receipts, user chats, project files, SEALED paths or tokens.
- Rules stay in PD-RW; general Skill routing stays in `SKILL.md`; Python service stays in `src/pdrw_agent`; CLI and MCP call **the same service**.

## Registration semantics / crash reconciliation

The **internal** `register_run_in_trusted_host` compatibility interface is **fail-closed**: it returns `TRUSTED_HOST_NOT_CONNECTED` and NEVER writes original PD-RW files, even if the caller supplies `lambda: True`. Actual write behavior belongs in a future independently secured OS/tool host that must authenticate original user permissions before invoking PD-RW's native writer. This interface is not exposed to MCP/CLI. Running WorkBuddy with broad write access still allows its terminal to bypass any Python-level boundary, so real isolation requires independent OS ACLs and permissions.

Integration design tests only use a synthetic host. Actual protected writes require a separate OS permission domain that can authenticate original author scope and enforce filesystem/tool ACLs.

Preview is deliberately conservative. It blocks projects with SEALED history before running PD-RW's hash-verifying status checker, refuses protected paths, rejects missing machine ledger, and never auto-calls `recover()`. It checks original PD-RW `validate_run`, existing `STATE/EVENTS` consistency, run ID + file hash conflict. Final `record_event` still validates actual linked Run artifacts and protocol. A preview success is **not** permission, scientific validity or guarantee the later write succeeds.

If a write crashes after `EVENTS.jsonl` append but before `STATE.json` update, the next status check returns `RECONCILIATION_REQUIRED`: inspect the original event and evidence, then explicitly reconcile with the authoritative PD-RW process. Never blindly re-run, append again or `recover()` automatically. A repeated same Run ID + same hash returns `ALREADY_RECORDED`, not a second event, after consistent original files are independently verified.

## Validation gates

- Windows/Linux: unit, MCP handshake, concurrent private receipt, CLI parity, actual pinned PD-RW ledger integration, duplicate retry, crash fault injection, data-boundary negatives.
- WorkBuddy: cross-session recovery and prompt/tool accuracy must be recorded from real client (pending).
- Real OS ACL / trusted authorization host: **not yet installed or tested**. Do not claim SEALED hard isolation or actual autonomous execution unless independently demonstrated.

## Extend in v0.6

Add a secure operator host and explicit original-author grant channel before enabling protected writes. Benchmark actual WorkBuddy event traces, human interruptions, false repeated experiment avoidance and total Task/Token cost using PD-RW `REPLAY_PROTOCOL.md`. Do not prematurely add LangGraph, vector databases, unrestricted shell tools, or duplicate scientific state machines.
