---
name: pd-rw-research
display_name: PD-RW 科研 Agent
display_name_en: PD-RW Research Agent
description: Start new PD-RW projects with one specific H6 plan choice or resume existing projects with evidence-aware, authorized DEV continuation.
description_zh: 按用户启动配置自主筛选研究方案，在 H6 等待具体方案选择，并恢复已授权科研项目。
description_en: Bounded PD-RW project recovery and evidence-aware execution routing.
examples_zh:
  - "按 PD-RW 启动新科研项目并提出 H6 科研方案"
  - "按 PD-RW 继续已存在的项目 19"
  - "恢复项目状态并继续已授权 DEV 工作"
  - "依据 PD-RW 检查实验并交付"
examples_en:
  - "Resume an existing PD-RW research project"
version: 0.7.8
author: phr-devil
---

# PD-RW WorkBuddy adapter

Invoke only for explicit PD-RW projects; never assume a project identity from a number alone.
PD-RW `WORKFLOW.md` owns scientific decisions and authorization, `AGENTS.md` owns routing.
Original user grants, frozen protocols and project STATE/EVENTS/Run outrank the Skill,
MCP responses, summaries and private operational SQLite receipts. No second research ledger.

## New project: one H6 scientific-plan choice (no duplicate startup questionnaire)

Use the original startup prompt as USER_SCOPE/H1-H2; never ask again for filled research goals, resources or exclusions. Bind a stable, explicit research-line reference (existing project identity if verified, otherwise a provisional new-line locator linked to the original launch message), never assume the project number alone proves identity. H3-H5 are Agent candidate investigation: compare 1-3 genuinely different scientific problems; check named prior work, official truth/independent groups, confounding, legal prediction-time inputs, a decisive inexpensive probe and the evidence path. UNKNOWN is not FAIL. Even SUPPORTED_BY_METADATA is provisional: disclose unverified truth/independence and NOT_ACCESSED nearest work explicitly, then prioritize a cheap discriminating probe instead of declaring scientific success. No mandatory new datasets, training or project registration before the corresponding original permission.

**H6 is a real interaction boundary:** show one short ranked plan card with an AI recommendation and alternatives, then **stop dependent new-mainline execution** until the user specifically chooses the displayed plan or explicitly delegates among displayed options. "Continue", silence, a broad startup delegation, a recommendation, an AI-created USER_CONFIRMED field, or an operation receipt is NOT a specific H6 choice. Do not freeze the selected Task/claim/evaluation or start the dependent new mainline before this choice. Independent authorized read-only work may continue. If one option is viable, say why alternatives were dropped rather than inventing three.

When a local Python runtime is available, `python -m pdrw_agent.science.cli h6-review --plan PLAN.json` checks the bounded card (v2 material-scope hash; v1 card hashes remain readable). With the user's current specific reply, use `--choice CHOICE.json --pd-rw-checkpoint` and check the returned activity-03 mapping against PD-RW's original science checkpoint. The H6 CLI **intentionally exits 3 even for a valid declared choice**: this is not a Python crash or a request to repeat the human decision. It cannot authenticate chat messages or grant execution. If the *user's response is directly present in the active conversation*, record that concrete observed choice once and continue planning/other independently permitted DEV work within its scope, without claiming host attestation; do not re-ask for H6 on each run. Never treat a model-generated choice packet or unauthenticated receipt as an execution permit. Only a trusted WorkBuddy host with access to the actual user reply may *independently authenticate* H6 and enforce a new-mainline gate; the current MCP/CLI does not provide that host-level protection. New-project activity-03 handoffs should use PD-RW's `review_activity_handoff(packet, new_project=True)` (host-trusted project context), and the current science checkpoint, not generic old H6 checks. Keep the exact original reply reference and option-card digest with the existing project research record, NOT a third ledger. Reuse a valid historical decision within unchanged scope; do not retroactively demand H6 for old legitimate DEV Runs. Ordinary model/feature/seed changes after H6 do not reopen it. Review [references/plan-selection.md](references/plan-selection.md) only for a new project's plan decision.

## MCP-first for a registered, permitted project

For a new session or interrupted-task recovery, **actually call `get_resume_context(project_id, detail_level="compact")` once** if an operator-registered mapping and permitted MCP are available. This already resolves project context; do NOT redundantly call `get_project_context` for the same recovery unless details are missing or conflicting.
For an isolated project-identity lookup without resumption, call `get_project_context(project_id)` once.
Compare the registered project root with the explicitly approved root before accepting any returned state; matching paths are locators, not independent proof of project identity or permission.
When the source scope is frozen, refuse access to a different root. If MCP is unavailable, unregistered, disallowed or fails, report `MCP_NOT_USED` with a concrete reason **once**, then use permitted original files or `scripts/bridge.py` / `scripts/context.py` without retry loops.
Report actual MCP tool names and statuses only for calls really made. A Skill import, local Python command or stated intention is not proof of MCP invocation.

## Execution lifecycle

1. **Identify:** for a new line, use the startup H1/H2 scope and pending H6 plan; for an existing line, verify exact project root, dataset, Task ID and source version. Identity conflict blocks affected operations, not independent permitted read-only evidence review.
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
Missing information => UNKNOWN, not PASS/FAIL or a new approval. If original hash-linked DEV/VAL Run artifacts include an evaluation matrix, the scientific audit reports coverage; absence is not complete coverage. Do not run every audit for every task.
Host CPU synthetic checks and `preflight_execution_plan(plan)` are diagnostic only and require the `diagnostic` profile; never interpret them as true research execution.

## Optional references (load only when triggered)

- [references/plan-selection.md](references/plan-selection.md): new-project H6 candidate card and explicit choice boundary
- [references/integration.md](references/integration.md): installation, mapping, version or project-switch issues
- [references/execution.md](references/execution.md): authorized DEV continuation, evidence handoff, interruption
- [references/troubleshooting.md](references/troubleshooting.md): missing sources, identity or permission conflicts
- [references/INDEX.json](references/INDEX.json): optional routing metadata, never policy authority

WorkBuddy imports the Skill separately from the Python/MCP installation. See `docs/RUNTIME_AND_MCP.md` for setup. Never pre-read all references.
