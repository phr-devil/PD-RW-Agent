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
version: 0.6.2
author: phr-devil
---

# PD-RW research execution adapter

Use this Skill only when the user explicitly selects PD-RW or asks to continue a project already governed by PD-RW. For unrelated general research questions, do not load this Skill.

## Operating contract

- **Authority:** PD-RW's `WORKFLOW.md` is the sole scientific decision authority; PD-RW's `AGENTS.md` is its default routing entry. This Skill **does not** duplicate or override PD-RW's rules.
- **Evidence:** original project Run, protocol, data manifest, and user messages outrank summaries. A state value or checker result never authenticates a user decision or experiment.
- **Memory:** use the project's existing `STATE`, `RESEARCH_RECORD.md`, and (when relevant) `PAPER_BLUEPRINT.md`. Do not create a second project memory database.
- **Limits:** bundled scripts are read-only helpers, not a secure executor or permission enforcement. Do not claim SEALED isolation or WorkBuddy integration has been proven.

## Tool access: MCP-first for a registered, permitted project

For a **fresh WorkBuddy task** with an explicit project ID, an operator-registered project mapping, and enabled `pd-rw-research` MCP tools, **actually call `get_project_context(project_id)` once before bulk project-file reading**. Do not merely list the tool or cite this Skill as evidence that it ran. After that scope check, use `audit_project_state(project_id)` when source
completeness or rule drift affects the decision. When relevant, use
`reconstruct_project_history(project_id)` to diagnose STATE/EVENTS conflicts,
`verify_run_evidence(project_id, run_id)` to check original DEV/VAL Run bytes,
and `review_lesson_applicability(proposal, lessons)` to compare declared
negative-premise scope. For a registered DEV/VAL Run with real row-level
artifacts, `audit_scientific_experiment(project_id, run_id)` checks hashed
train/evaluation IDs, recomputed metrics, declared input scope and baseline
comparability. Inspect only when the scientific decision needs these checks;
a missing sidecar yields UNKNOWN, never an automatic STOP or scientific PASS. Never treat any of these as scientific verification,
original approval, permission to run, or a reason to auto-STOP. It is optional for a quick
informational lookup: avoid redundant scans and treat `PARTIAL_RECOVERY` only
as a diagnostic, not permission to run.

The MCP call executes the shared `pdrw_agent` Python service; WorkBuddy's own terminal Python is not evidence of that integration. Avoid additional preflight calls when the same verified tool result is already in this task's context.

**Scope gate:** when the user restricts sources to a frozen snapshot, use this MCP only if the registered mapping has been explicitly permitted for that snapshot. Compare its reported `project_root` with the user-approved snapshot before using any returned project state; a mismatch means **do not continue project MCP access or read a different project root**. A matching string is a locator check, *not* independent proof of project identity, authorization, provenance, or SEALED isolation.

- If the user requests cross-session recovery or an interrupted-task diagnosis, use `get_resume_context` only when informative. `INCOMPLETE_CONTEXT` / `BLOCKED_INCOMPLETE_CONTEXT` prohibit unsupported resumption, **not** independent permitted read-only evidence review. Never synthesize STATE/EVENTS.
- Use `get_applicable_rules(topic)` for relevant rule-file routing, then read the applicable **original PD-RW rule files**; `ROUTE_FOUND` is navigation, not policy attestation. Use `find_experiment_evidence` only for indexed evidence that matters; use `search_research_memory` only when useful and `check_duplicate_experiment` before a costly repeated Run.
- If MCP is absent, disconnected, explicitly prohibited, unregistered or fails, record `MCP_NOT_USED` with the factual reason **once**, then use permitted original sources or the existing standalone `scripts/bridge.py` / `scripts/context.py` fallback. Do not invent an MCP call, repeatedly retry, or let a tool failure block unrelated legal read-only review.
- In evaluation/hand-off reports, state the **actual MCP tool names and statuses**, or `MCP_NOT_USED`; distinguish MCP invocation from Skill loading, Python package installation, and WorkBuddy terminal commands. An MCP-connected status alone is not an actual call.

Only for a meaningful, already-authorized DEV operation, use `begin_operation_receipt` and at significant transitions `checkpoint_operation_receipt` to maintain **private operational metadata**, not science or permission. Before a proposed Run registration call `preview_experiment_record` (read-only). Use `prepare_handoff` when meaningful real file artifacts are delivered. **No MCP tool can register Run/Claim, repair STATE or authenticate original user permission.** Never treat `status`, `APPROVED`, receipt state, fingerprint, or hash match as scientific validity.

Importing this Skill does NOT install/start Python or MCP. An enabled MCP server is configured independently by the operator; private `PDRW_RUNTIME_DIR` is needed only for receipt operations. See repository `docs/RUNTIME_AND_MCP.md` for setup. Scientific authority remains solely with PD-RW.

## Task lifecycle

1. **Identify the project.** Verify project ID, research line, dataset and real local directory. If ambiguous, do not choose a project by guesswork.
2. **Locate the authority.** Determine the local PD-RW checkout and current local Git HEAD. If source freshness is material, compare with the remote only through an available authorized read-only mechanism. Unchecked remote = `RULE_VERSION_UNVERIFIED`; no silent pull or overwrite.
3. **Resume minimally.** Apply the registered-project MCP-first route above when enabled and permitted. Otherwise run `scripts/bridge.py doctor` and `resume` when a local project mapping is available. Supports existing Markdown `STATE.md` or machine `STATE.json`; read the current `RESEARCH_RECORD` snapshot and selected pointers, not its full event history. An ID mismatch is a stop for affected work; missing/contradictory evidence = `UNKNOWN` or `SOURCE_CONFLICT`, not success.
4. **Route by need.** Read PD-RW `AGENTS.md` once per known rule version/task. Optionally run `scripts/context.py route` to obtain rule-file hints **parsed from the current AGENTS.md**, then load the relevant owner only. Keep H1–H10, science, permissions and delivery under PD-RW's existing authority; do not read the full repository.
5. **Execute within authority.** Classify a new user message as IDEA, explicit instruction or strategic choice. Author selects/delegates H6 core Task/strategy and H8 primary Claim changes; valid H7 / approved local nonpaid DEV is autonomous without repeated approvals. Continue related diagnosis, coding and targeted tests at useful work-unit granularity; reuse valid Run, avoid repeated false premises, stop when no distinct informative probe remains. For new download, payment, SEALED, confirmation, publication, external upload, writing, drawing or strategic changes, obey PD-RW's existing separate gates. A Skill or self-written JSON never grants permission.
6. **Validate and persist.** Optional `scripts/context.py action-review` invokes PD-RW's declaration-only preflight; it is **not** a trusted tool interceptor. Verify original user authorization and actual Run/protocol independently. On significant scientific events update the **existing** research record/affected blueprint only; retain negative results and provenance. No new third ledger.
7. **Deliver.** Use `prepare_handoff` when available, or run the existing PD-RW path-only delivery checker through `scripts/context.py delivery-review` **only when real file artifacts are being handed off**. Give one principal result with paths, checks actually run, scientific limits, and the next legal action (or required user choice). Avoid large log dumps and unsupported PASS claims.

## Optional science check (only for a material research choice)

When competing hypotheses or a repeated negative premise may change an already-authorized DEV choice, optionally run `python -m pdrw_agent.science.cli decision --packet LOCAL_PROPOSAL.json` using permitted local metadata. The result compares **declared** predictions and scope, never independently verified scientific evidence, novelty or user approval. Do not run on every experiment; original PD-RW `HIGH_VALUE_RESEARCH_DESIGN.md` and `SCIENCE_RESULT_HARVEST.md` remain authoritative. Freeze-time A/B/C review is operator-only; see repository `docs/V06_EVAL_PREVIEW.md` on demand.

For a meaningful, evidence-backed negative Run, optional `python -m pdrw_agent.science.cli lessons --packet DEV_OBSERVATIONS.json` separates technical/invalid failures from *declared* negative evidence. If a legitimately frozen historical source manifest is available, optionally add `--evidence-root DIR --evidence-manifest CASE.json` to either science command to check that cited IDs resolve to hash-checked, allowlisted frozen source bytes. No semantic science, permission or literature novelty is attested; do not perform this on every Run. See `docs/V06_EVAL_PREVIEW.md` only when needed.

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
- Optional machine-readable trigger index → [references/INDEX.json](references/INDEX.json) (metadata only; **never** replaces current PD-RW rule router)
- Design coverage map (maintainers only; not task context) → see repository `docs/DECISION_COVERAGE.md`

Do not automatically load all three references. Fail only the affected action if evidence or authority is missing; continue separately permitted, read-only work.
