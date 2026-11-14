---
name: pd-rw-research
display_name: PD-RW 科研 Agent
display_name_en: PD-RW Research Agent
description: Resume an existing PD-RW research project with original state and Run evidence, route authorized WorkBuddy DEV work, and deliver scoped results. Use only for explicitly PD-RW-governed tasks.
description_zh: 恢复明确采用 PD-RW 的科研项目，按需读取规则、核对原始证据、连续推进已授权 DEV 工作。
description_en: Bounded PD-RW project recovery and evidence-aware execution routing.
examples_zh:
  - "按 PD-RW 继续已存在的项目 19"
  - "恢复项目状态并继续已授权 DEV 工作"
  - "依据 PD-RW 检查实验并交付"
examples_en:
  - "Resume an existing PD-RW research project"
version: 0.7.5
author: phr-devil
---

# PD-RW WorkBuddy adapter

Invoke only for explicit PD-RW projects; never assume a project identity from a number alone.
PD-RW `WORKFLOW.md` owns scientific decisions and authorization, `AGENTS.md` owns routing.
Original user grants, frozen protocols and project STATE/EVENTS/Run outrank the Skill,
MCP responses, summaries and private operational SQLite receipts. No second research ledger.

## MCP-first for a registered, permitted project

For a new session or interrupted-task recovery, **actually call `get_resume_context(project_id, detail_level="compact")` once** if an operator-registered mapping and permitted MCP are available. This already resolves project context; do NOT redundantly call `get_project_context` for the same recovery unless details are missing or conflicting.
For an isolated project-identity lookup without resumption, call `get_project_context(project_id)` once.
Compare the registered project root with the explicitly approved root before accepting any returned state; matching paths are locators, not independent proof of project identity or permission.
When the source scope is frozen, refuse access to a different root. If MCP is unavailable, unregistered, disallowed or fails, report `MCP_NOT_USED` with a concrete reason **once**, then use permitted original files or `scripts/bridge.py` / `scripts/context.py` without retry loops.
Report actual MCP tool names and statuses only for calls really made. A Skill import, local Python command or stated intention is not proof of MCP invocation.

## Execution lifecycle

1. **Identify:** verify exact project root, dataset, Task ID and source version. Identity conflict blocks affected operations, not independent permitted read-only evidence review.
2. **Recover:** use compact resume and load only the current `STATE` snapshot, `RESEARCH_RECORD` pointer and relevant original Run. `next_action_hint` is advisory; `execution_authorized=false` never means all independent legitimate tasks are forbidden.
3. **Route:** consult original PD-RW `AGENTS.md` and the one relevant scientific authority file; avoid loading all rules or this Skill's historical releases.
4. **Choose:** compare candidate next DEV probe against original Task/Claim, baseline and relevant historical cases. Use `search_research_memory` as a secondary index only; where original DEV Run is available use `review_evidenced_lesson` and/or `review_lesson_applicability`. Keyword similarity cannot prove the same failure mechanism or justify an automatic STOP.
5. **Execute:** WorkBuddy's existing approved tools perform coding and experiments. Continue related already-authorized ordinary DEV work autonomously without repetitive confirmations. Keep H1–H10 decisions, dataset/download/SEALED/CONFIRMATION boundaries, real authorization, publishing/upload/payment, writing and figures under the original PD-RW gate. Never use a reported APPROVED field, hash or receipt as authorization.
6. **Reconcile:** never blindly restart an uncertain previous process. An unresolved historical job does not prohibit a *different*, independently permitted DEV task. Record significant science only in original PD-RW artifacts; operation receipts never become scientific Runs.
7. **Deliver:** return one primary artifact, precise paths, verification evidence, remaining uncertainty and next legal action. Use `prepare_handoff` only for actual files; avoid dumping logs.

## Selective audits and tool profiles

Default MCP `research` exposes core+scientific checks (17 tools); `minimal` exposes 11, and `diagnostic` exposes all 20, including fixed-host diagnostics. Visibility does **not** confer permission. No MCP tool in this version can execute real DEV/GPU commands, authenticate author grants, write PD-RW Run/Claim, or establish SEALED filesystem isolation.

Use `audit_project_state(project_id)` and `reconstruct_project_history(project_id)` for material source conflicts;
`verify_run_evidence(project_id, run_id)` for original Run integrity;
`audit_scientific_experiment(project_id, run_id)` for bounded DEV/VAL leakage, metric and baseline checks;
`review_evidenced_lesson(project_id, run_id, proposal)` for hash-linked prior negative evidence.
Missing information => UNKNOWN, not PASS/FAIL or a new approval. Do not run every audit for every task.
Host CPU synthetic checks and `preflight_execution_plan(plan)` are diagnostic only and require the `diagnostic` profile; never interpret them as true research execution.

## Optional references (load only when triggered)

- [references/integration.md](references/integration.md): installation, mapping, version or project-switch issues
- [references/execution.md](references/execution.md): authorized DEV continuation, evidence handoff, interruption
- [references/troubleshooting.md](references/troubleshooting.md): missing sources, identity or permission conflicts
- [references/INDEX.json](references/INDEX.json): optional routing metadata, never policy authority

WorkBuddy imports the Skill separately from the Python/MCP installation. See `docs/RUNTIME_AND_MCP.md` for setup. Never pre-read all references.
