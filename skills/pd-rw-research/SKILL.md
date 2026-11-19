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
version: 0.8.1
author: phr-devil
---

# PD-RW WorkBuddy adapter

Invoke only for explicit PD-RW projects; never assume a project identity from a number alone.
PD-RW `WORKFLOW.md` owns scientific decisions and authorization, `AGENTS.md` owns routing.
Original user grants, frozen protocols and project STATE/EVENTS/Run outrank the Skill,
MCP responses, summaries and private operational SQLite receipts. No second research ledger.

**Outcome:** efficiently deliver credible, submission-ready Q1-aspirational / Q2+-plausible papers with real scholarly reuse potential. A modest but distinct, independently supportable contribution (including a useful traditional-method improvement) can be valuable; a novel network or dramatic SOTA gain is not mandatory. Initial algorithm/Claim is an adaptable route, not the outcome. Never promise acceptance or citations. PD-RW remains the only scientific-policy authority.

**Five non-negotiable boundaries (not five extra checklists):** (1) real author choices and scoped effect permissions; (2) correct project identity and original evidence provenance; (3) legal prediction-time inputs and DEV/VAL/SEALED isolation; (4) no invented Run, novelty, citations or verified conclusions; (5) protected effects, resources, data egress and process safety. Only the trusted WorkBuddy host can enforce actual permissions/tool/filesystem access: Python/Skill declarations are advisory. Consult PD-RW `WORKFLOW.md` and the relevant original protocol for the precise rules.

## New projects: three real author decisions, then autonomous DEV

**New projects (PD-RW v1.14):** reuse original H1/H2 limits. Ask for **three distinct post-card author decisions**: H3 selects a paper-worthy question after bounded prior-art/opportunity review; H4 selects evidence/data/proof route after truth, independence, permission and cost review; H5 is an Agent draft, confirmed when H6 selects the paper contribution, concrete Task and bounded adaptive-pivot scope. H4 cites H3; H6 cites H3/H4 and the original HARD-constraint fingerprint. An old single-H6 project retains its valid original choices. Missing choices pause only dependent actions, not independent permitted read-only work.

**No approval by declarations:** `continue`, a model recommendation, a repeated message ref, a plan SHA or an `APPROVED` JSON cannot replace specific original user choices. The trusted host must authenticate original messages and independently authorize protected tool effects; card checkers never do so. Technical changes within an approved H7 scope proceed autonomously; material core-Claim or strategy changes go through H8/relevant author boundary. For versioned H3/H4/H6 card schemas and optional advisory CLI, load [references/plan-selection.md](references/plan-selection.md) *only when selecting/revising a plan*. Preserve original records in `RESEARCH_RECORD.md` and `STATE`, not a third ledger.

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
4. **Choose:** use [references/research-leverage.md](references/research-leverage.md) for first meaningful Pilot, unexpected simple-method win, negative result, publication-ready result or pivot. Distinguish NOT_RUN / invalid experiment / inconclusive / valid negative / valid positive. First Pilot is diagnostic, not a final Q2/SOTA verdict; evaluate evidence-matched smaller contributions and successful precedents as well as failures. Compare candidate next DEV probe against original Task/Claim, baseline and relevant historical cases. Prefer the highest decision-relevant information per valid total cost, not automatically the cheapest probe and not repeated training under the same failed premise; the optional `science.cli decision` `declared_probe_efficiency` output only compares unverified declared pair coverage/cost and never selects science automatically. Use `search_research_memory` as a secondary index only; where original DEV Run is available use `review_evidenced_lesson` and/or `review_lesson_applicability`. Keyword similarity cannot prove the same failure mechanism or justify an automatic STOP.
5. **Execute:** WorkBuddy's existing approved tools perform coding and experiments. Reuse verified Runs and current state: no mandatory full-rule reload, audit suite, extra agent call, fixed seed count or arbitrary time delay per step. One negative Pilot pauses its premise, never automatically kills the whole project. An in-scope better old/simple method may replace the original new-model proposal; re-open author choice only for material scope/primary-Claim changes. Continue related already-authorized ordinary DEV work autonomously without repetitive confirmations. Keep distinct H3/H4/H6 author choices and all H1–H10 decisions, dataset/download/SEALED/CONFIRMATION boundaries, real authorization, publishing/upload/payment, writing and figures under the original PD-RW gate. Never use a reported APPROVED field, hash or receipt as authorization.
6. **Reconcile:** never blindly restart an uncertain previous process. At major evidence/choice transitions update only existing `RESEARCH_RECORD.md` (and `PAPER_BLUEPRINT.md` if Claim/section changes); `STATE` holds pointers, not a third research ledger. No automatic manuscript text, figure/render, download, release, payment or submission. An unresolved historical job does not prohibit a *different*, independently permitted DEV task. Record significant science only in original PD-RW artifacts; operation receipts never become scientific Runs.
7. **Deliver:** return one primary artifact, precise paths, verification evidence, remaining uncertainty and next legal action. Keep exploration/engineering progress distinct from a credible independent contribution, paper fit and a manuscript authorization. When a supported small finding has an actual Q2+ paper route, identify only the remaining decisive evidence; do not require a grand breakthrough or keep tuning indefinitely. When a meaningful Run changes the science, identify the fastest remaining evidence to a strong paper Claim, and whether the contribution is genuinely new and reusable, without writing an unapproved manuscript. Use `prepare_handoff` only for actual files; avoid dumping logs.

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
