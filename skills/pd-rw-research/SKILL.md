---
name: pd-rw-research
display_name: PD-RW 科研 Agent
display_name_en: PD-RW Research Agent
description: Start high-impact PD-RW research with H3/H4/H6 author choices, or resume evidence-aware authorized DEV for a fast credible publication path.
description_zh: 以尽快形成高水平、高引用潜力且证据可靠的科研成果为目标，筛选科研方案、完成H3/H4/H6三次关键选择并续做已授权项目。
description_en: Bounded PD-RW project recovery and evidence-aware execution routing.
examples_zh:
  - "按 PD-RW 启动新科研项目，分三步选择问题、证据与方案"
  - "按 PD-RW 继续已存在的项目 19"
  - "恢复项目状态并继续已授权 DEV 工作"
  - "依据 PD-RW 检查实验并交付"
  - "按 PD-RW 研究高影响力问题并提出最快可靠证据路径"
examples_en:
  - "Resume an existing PD-RW research project"
version: 0.8.0
author: phr-devil
---

# PD-RW WorkBuddy adapter

Invoke only for explicit PD-RW projects; never assume a project identity from a number alone.
PD-RW `WORKFLOW.md` owns scientific decisions and authorization, `AGENTS.md` owns routing.
Original user grants, frozen protocols and project STATE/EVENTS/Run outrank the Skill,
MCP responses, summaries and private operational SQLite receipts. No second research ledger.

**Research outcome:** optimize the user's stated goal of timely, scientifically credible **high-tier and high-citation-potential papers**, not task count, benchmark score alone or speedy prose. Prioritize important reusable scientific knowledge, named-neighbor novelty and the shortest valid evidence route (Q1 preferred, credible Q2+ minimum per PD-RW); neither impact nor citations nor acceptance can be guaranteed. Do not replace original PD-RW policy, user scope, independent confirmation or writing authorization. Read [references/research-leverage.md](references/research-leverage.md) only at new H6 strategy choice, material scientific pivot or stalled evidence path.

## New projects: three real author decisions, then autonomous DEV

The goal is **fast, credible publication in high-tier, high-reuse/citation-potential venues**, not completing a fixed research algorithm or generating research plans. Preserve genuine measurement, fair comparison, independent evidence and journal fit (Q1 preferred; credible Q2+ minimum per PD-RW). Initial hypotheses, algorithms, contribution types and task framing are *adaptable*, not permanent restrictions. Discover a supported, stronger paper contribution when valid DEV results expose one; never invent novelty, pre-registration or citations. See [references/research-leverage.md](references/research-leverage.md) at first topic selection or a substantial scientific pivot.

Read the original startup prompt as H1/H2 and HARD constraints; do not request already-supplied information. For new v1.4 projects use these three separate **post-card** author interactions:

1. **H3 / paper-worthy question:** conduct bounded broad opportunity search, deep named-neighbor falsification, realistic high-tier publication precedents, audience/reuse value and data/measurement plausibility. Compare usually three genuinely distinct problems after sufficient search; recommend one, show the **H3 card**, and require a specific original author response before H4 is selected.
2. **H4 / evidence path:** for the selected H3 question, investigate 2–3 plausible dataset/proof pathways, independent ground truth/groups, confounds, legal inputs, license and fastest credible confirmation. Show the **H4 card bound to H3**, wait for a **different** original author response. H4 is not a download, training or SEALED grant.
3. **H6 / paper contribution and Task:** Agent prepares the derived H5 question/evidence boundary, then compares new methods, meaningful improvements to older/simpler methods, mechanisms, measurements, evaluation or system contributions. Show the **H6 card bound to H3/H4** with recommended paper claim, nearest neighbor, decisive probe, timeline/cost, and **authorized adaptive-pivot envelope**. Require a third, different original author reply; H5 is confirmed with H6, not a fourth questionnaire.

These are substantive scientific choices, not fixed waiting periods or repeated constraints questionnaires. Unknown truth is an explicit probe target, not automatic failure. After selected, allow continuous in-scope H7 DEV. H8 applies to freezing/changing the core Claim or a material strategy/pivot outside the chosen envelope, not every model or seed. Preserve original old v1.3 single-H6 projects without retroactive new choices.

**Guardrails:** Never treat "continue", a recommendation, arbitrary `APPROVED`, old blanket delegation or three copies of one user message as three specific decisions. Record each displayed card digest, original message reference, selected/delegated scope and upstream dependencies in existing `RESEARCH_RECORD.md` (no third ledger). If a source changes, invalidate only affected downstream choices. Distinguish HARD (author scope, cost, protected data, actions), ADAPTIVE (technique/contribution within selected envelope), EVIDENCE (revisable scientific hypotheses). Critical original-message authentication and effect enforcement remain trusted WorkBuddy-host responsibilities, **not** this Skill or its Python helpers.

**Optional local declarations checker:** `python -m pdrw_agent.science.cli early-review --plan H3.json [--choice H3_CHOICE.json]` (and H4); `python -m pdrw_agent.science.cli h6-review --plan H6.json [--choice H6_CHOICE.json] --pd-rw-checkpoint`. New H6 uses `pdrw-h6-plan-v3`; H4/H6 cards must bind actual declared H3/H4 source/digest/choice. All return nonzero 3 for pending or untrusted selection, **including a structurally valid one**: this is not a crash or permission signal. New project scientific review uses PD-RW `review_new_project_choices` and activity03 handoff with `new_project=True`. Historic v1/v2 H6 plans and PD-RW v1.3 records remain readable but cannot fake new v1.4 decisions. For card contracts, load [references/plan-selection.md](references/plan-selection.md) only during staged startup or pivot.

## MCP-first for a registered, permitted project

For a new session or interrupted-task recovery, **actually call `get_resume_context(project_id, detail_level="compact")` once** if an operator-registered mapping and permitted MCP are available. This already resolves project context; do NOT redundantly call `get_project_context` for the same recovery unless details are missing or conflicting.
For an isolated project-identity lookup without resumption, call `get_project_context(project_id)` once.
Compare the registered project root with the explicitly approved root before accepting any returned state; matching paths are locators, not independent proof of project identity or permission.
When the source scope is frozen, refuse access to a different root. If MCP is unavailable, unregistered, disallowed or fails, report `MCP_NOT_USED` with a concrete reason **once**, then use permitted original files or `scripts/bridge.py` / `scripts/context.py` without retry loops.
Report actual MCP tool names and statuses only for calls really made. A Skill import, local Python command or stated intention is not proof of MCP invocation.

## Execution lifecycle

1. **Identify:** for a new line, use startup H1/H2 and the current H3/H4/H6 choice boundary; for an existing line, verify exact project root, dataset, Task ID and source version. Identity conflict blocks affected operations, not independent permitted read-only evidence review.
2. **Recover:** use compact resume and load only the current `STATE` snapshot, `RESEARCH_RECORD` pointer and relevant original Run. `next_action_hint` is advisory; `execution_authorized=false` never means all independent legitimate tasks are forbidden.
3. **Route:** consult original PD-RW `AGENTS.md` and the one relevant scientific authority file; avoid loading all rules or this Skill's historical releases.
4. **Choose:** compare candidate next DEV probe against original Task/Claim, baseline and relevant historical cases. Prefer a hypothesis-distinguishing result per valid research cost, not repeated training under the same failed premise; the optional `science.cli decision` `declared_probe_efficiency` output only compares unverified declared pair coverage/cost and never selects science automatically. Use `search_research_memory` as a secondary index only; where original DEV Run is available use `review_evidenced_lesson` and/or `review_lesson_applicability`. Keyword similarity cannot prove the same failure mechanism or justify an automatic STOP.
5. **Execute:** WorkBuddy's existing approved tools perform coding and experiments. Continue related already-authorized ordinary DEV work autonomously without repetitive confirmations. Keep distinct H3/H4/H6 author choices and all H1–H10 decisions, dataset/download/SEALED/CONFIRMATION boundaries, real authorization, publishing/upload/payment, writing and figures under the original PD-RW gate. Never use a reported APPROVED field, hash or receipt as authorization.
6. **Reconcile:** never blindly restart an uncertain previous process. An unresolved historical job does not prohibit a *different*, independently permitted DEV task. Record significant science only in original PD-RW artifacts; operation receipts never become scientific Runs.
7. **Deliver:** return one primary artifact, precise paths, verification evidence, remaining uncertainty and next legal action. When a meaningful Run changes the science, identify the fastest remaining evidence to a strong paper Claim, and whether the contribution is genuinely new and reusable, without writing an unapproved manuscript. Use `prepare_handoff` only for actual files; avoid dumping logs.

## Selective audits and tool profiles

Default MCP `research` exposes core+scientific checks (17 tools); `minimal` exposes 11, and `diagnostic` exposes all 20, including fixed-host diagnostics. Visibility does **not** confer permission. No MCP tool in this version can execute real DEV/GPU commands, authenticate author grants, write PD-RW Run/Claim, or establish SEALED filesystem isolation.

Use `audit_project_state(project_id)` and `reconstruct_project_history(project_id)` for material source conflicts;
`verify_run_evidence(project_id, run_id)` for original Run integrity;
`audit_scientific_experiment(project_id, run_id)` for bounded DEV/VAL leakage, metric and baseline checks;
`review_evidenced_lesson(project_id, run_id, proposal)` for hash-linked prior negative evidence.
Missing information => UNKNOWN, not PASS/FAIL or a new approval. If original hash-linked DEV/VAL Run artifacts include an evaluation matrix, the scientific audit reports coverage; absence is not complete coverage. Do not run every audit for every task.
Host CPU synthetic checks and `preflight_execution_plan(plan)` are diagnostic only and require the `diagnostic` profile; never interpret them as true research execution.

## Optional references (load only when triggered)

- [references/plan-selection.md](references/plan-selection.md): new-project H3/H4/H6 stage card, lineage and choice boundary
- [references/research-leverage.md](references/research-leverage.md): high-impact scientific opportunity, H6 decision or significant negative/pivot only
- [references/integration.md](references/integration.md): installation, mapping, version or project-switch issues
- [references/execution.md](references/execution.md): authorized DEV continuation, evidence handoff, interruption
- [references/troubleshooting.md](references/troubleshooting.md): missing sources, identity or permission conflicts
- [references/INDEX.json](references/INDEX.json): optional routing metadata, never policy authority

WorkBuddy imports the Skill separately from the Python/MCP installation. See `docs/RUNTIME_AND_MCP.md` for setup. Never pre-read all references.
