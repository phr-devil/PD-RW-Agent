---
name: pd-rw-research
display_name: PD-RW 科研 Agent
display_name_en: PD-RW Research Agent
description: Resume and execute explicitly PD-RW-governed research tasks in WorkBuddy; locate local project evidence, load only applicable PD-RW rules, and hand off verified results.
description_zh: 在明确使用 PD-RW 的科研项目中，恢复项目状态、按需读取规则、执行已授权任务并交付可追溯证据。
description_en: Read-only project recovery and evidence-aware execution routing for PD-RW research projects.
examples_zh:
  - "按 PD-RW 继续已存在的项目 19"
  - "恢复这个科研项目的状态和下一步任务"
  - "依据 PD-RW 审查本次 DEV 实验与交付"
examples_en:
  - "Resume an existing PD-RW research project"
version: 0.5.0
author: phr-devil
---

# PD-RW research execution adapter

Use this Skill only when the user explicitly selects PD-RW or asks to continue a project already governed by PD-RW. For unrelated general research questions, do not load this Skill.

## Operating contract

- **Authority:** PD-RW's `WORKFLOW.md` is the sole scientific decision authority; PD-RW's `AGENTS.md` is its default routing entry. This Skill **does not** duplicate or override PD-RW's rules.
- **Evidence:** original project Run, protocol, data manifest, and user messages outrank summaries. A state value or checker result never authenticates a user decision or experiment.
- **Memory:** use the project's existing `STATE`, `RESEARCH_RECORD.md`, and (when relevant) `PAPER_BLUEPRINT.md`. Do not create a second project memory database.
- **Limits:** bundled scripts are read-only helpers, not a secure executor or permission enforcement. Do not claim SEALED isolation or WorkBuddy integration has been proven.

## Tool access: prefer MCP v0.5 when configured

For registered projects, call the `pd-rw-research` MCP server tools, preferably in this order as needed:
`get_project_context` → `get_applicable_rules` → `find_experiment_evidence`; consult `search_research_memory` only when useful and `check_duplicate_experiment` before costly repeated runs. These five tools are **read-only** and return bounded metadata. For cross-session continuation, use `get_resume_context` and `get_execution_status` first when an interrupted operation is relevant. Only for a meaningful, already-authorized DEV operation, use `begin_operation_receipt` and at significant transitions `checkpoint_operation_receipt` to maintain **private operational metadata**, not science or permission. Before any proposed Run registration call `preview_experiment_record`; it is read-only and does NOT write PD-RW. `prepare_handoff` checks declared paths without creating files. **No MCP tool is allowed to register Run/Claim or repair STATE.** Never treat `status`, `APPROVED`, receipt state or fingerprint as authentic permission or science.

MCP is **optional**: importing this Skill does NOT install/start Python or MCP. To use receipts set private `PDRW_RUNTIME_DIR` once; absence is not a reason to block unrelated authorized DEV work. If MCP is unavailable, use the existing standalone `scripts/bridge.py`/`scripts/context.py` fallback or read the actual PD-RW project sources within verified access. Do not repeatedly retry a missing integration. Full setup: repository `docs/RUNTIME_AND_MCP.md` (maintainer/operator reference, not default task context).

## Task lifecycle

1. **Identify the project.** Verify project ID, research line, dataset and real local directory. If ambiguous, do not choose a project by guesswork.
2. **Locate the authority.** Determine the local PD-RW checkout and current local Git HEAD. If source freshness is material, compare with the remote only through an available authorized read-only mechanism. Unchecked remote = `RULE_VERSION_UNVERIFIED`; no silent pull or overwrite.
3. **Resume minimally.** Run `scripts/bridge.py doctor` and `resume` when a local project mapping is available. Supports existing Markdown `STATE.md` or machine `STATE.json`; read the current `RESEARCH_RECORD` snapshot and selected pointers, not its full event history. An ID mismatch is a stop for affected work; missing/contradictory evidence = `UNKNOWN` or `SOURCE_CONFLICT`, not success.
4. **Route by need.** Read PD-RW `AGENTS.md` once per known rule version/task. Optionally run `scripts/context.py route` to obtain rule-file hints **parsed from the current AGENTS.md**, then load the relevant owner only. Keep H1–H10, science, permissions and delivery under PD-RW's existing authority; do not read the full repository.
5. **Execute within authority.** Classify a new user message as IDEA, explicit instruction or strategic choice. Author selects/delegates H6 core Task/strategy and H8 primary Claim changes; valid H7 / approved local nonpaid DEV is autonomous without repeated approvals. Continue related diagnosis, coding and targeted tests at useful work-unit granularity; reuse valid Run, avoid repeated false premises, stop when no distinct informative probe remains. For new download, payment, SEALED, confirmation, publication, external upload, writing, drawing or strategic changes, obey PD-RW's existing separate gates. A Skill or self-written JSON never grants permission.
6. **Validate and persist.** Optional `scripts/context.py action-review` invokes PD-RW's declaration-only preflight; it is **not** a trusted tool interceptor. Verify original user authorization and actual Run/protocol independently. On significant scientific events update the **existing** research record/affected blueprint only; retain negative results and provenance. No new third ledger.
7. **Deliver.** Use `prepare_handoff` when available, or run the existing PD-RW path-only delivery checker through `scripts/context.py delivery-review` **only when real file artifacts are being handed off**. Give one principal result with paths, checks actually run, scientific limits, and the next legal action (or required user choice). Avoid large log dumps and unsupported PASS claims.

## Optional helpers (no network/API required)

Commands are run from the directory containing this `SKILL.md`, or use an absolute path to `scripts/bridge.py`:

```bash
python scripts/bridge.py doctor --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
python scripts/bridge.py resume --project-id "example-project" --project-map "D:/path/to/project-map.local.json" --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
python scripts/context.py route --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
# When an original authorization question or actual file delivery requires it:
python scripts/context.py action-review --workflow-root "D:/path/to/Problem-Data-Research-Workflow" --packet "D:/safe/ACTION.json"
python scripts/context.py delivery-review --workflow-root "D:/path/to/Problem-Data-Research-Workflow" --output-root "D:/research/output" --primary "result.md"
```

All JSON outputs are **locators, routing hints, or structural checks**, never original-user authorization or scientific verification. Trigger four kinds of targeted calibration only on evidence of need: new-session recovery, observed execution drift, restricted-effect gate, or material scientific-value change. No repetitive review prompts or new phases.

## Load additional guidance only if necessary

- PD-RW path/version/project integration → [references/integration.md](references/integration.md)
- Autonomous DEV loop or handoff mechanics → [references/execution.md](references/execution.md)
- Missing paths, contradictory state, stale checkout, other failure → [references/troubleshooting.md](references/troubleshooting.md)
- Design coverage map (maintainers only; not task context) → see repository `docs/DECISION_COVERAGE.md`

Do not automatically load all three references. Fail only the affected action if evidence or authority is missing; continue separately permitted, read-only work.
