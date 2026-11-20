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
version: 0.9.14
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

**No approval by declarations:** `continue`, a model recommendation, a repeated message ref, a plan SHA or an `APPROVED` JSON cannot replace specific original user choices. The trusted host must authenticate original messages and independently authorize protected tool effects; card checkers never do so. Technical changes within an approved H7 scope proceed autonomously; material core-Claim or strategy changes go through H8/relevant author boundary. For versioned H3/H4/H6 card schemas, the optional `candidate-review` check (named nearest gap, knowledge gain vs replication, independent truth/unit, discriminating prediction) and the advisory CLI, load [references/plan-selection.md](references/plan-selection.md) *only when selecting/revising a plan*. Preserve original records in `RESEARCH_RECORD.md` and `STATE`, not a third ledger.

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
4. **Choose:** use [references/research-leverage.md](references/research-leverage.md) for first meaningful Pilot, unexpected simple-method win, negative result, publication-ready result or pivot. Distinguish NOT_RUN / invalid experiment / inconclusive / valid negative / valid positive. First Pilot is diagnostic, not a final Q2/SOTA verdict; evaluate evidence-matched smaller contributions and successful precedents as well as failures. Compare candidate next DEV probe against original Task/Claim, baseline and relevant historical cases. Prefer the highest decision-relevant information per valid total cost, not automatically the cheapest probe and not repeated training under the same failed premise; the optional `science.cli decision` `declared_probe_efficiency` output only compares unverified declared pair coverage/cost and never selects science automatically. Use `search_research_memory` as a secondary index only; where original DEV Run is available use `review_evidenced_lesson` and/or `review_lesson_applicability`. At H3/H4/H6 pass the **unchanged** selection card to `project_case_bridge` so prior cases inform the choice without altering the card or its fingerprint. Keyword similarity cannot prove the same failure mechanism or justify an automatic STOP.
5. **Execute:** WorkBuddy's existing approved tools perform coding and experiments. Reuse verified Runs and current state: no mandatory full-rule reload, audit suite, extra agent call, fixed seed count or arbitrary time delay per step. One negative Pilot pauses its premise, never automatically kills the whole project. An in-scope better old/simple method may replace the original new-model proposal; re-open author choice only for material scope/primary-Claim changes. Continue related already-authorized ordinary DEV work autonomously without repetitive confirmations. Keep distinct H3/H4/H6 author choices and all H1–H10 decisions, dataset/download/SEALED/CONFIRMATION boundaries, real authorization, publishing/upload/payment, writing and figures under the original PD-RW gate. Never use a reported APPROVED field, hash or receipt as authorization.
6. **Reconcile:** never blindly restart an uncertain previous process. At major evidence/choice transitions update only existing `RESEARCH_RECORD.md` (and `PAPER_BLUEPRINT.md` if Claim/section changes); `STATE` holds pointers, not a third research ledger. No automatic manuscript text, figure/render, download, release, payment or submission. An unresolved historical job does not prohibit a *different*, independently permitted DEV task. Record significant science only in original PD-RW artifacts; operation receipts never become scientific Runs.
7. **Deliver:** return one primary artifact, precise paths, verification evidence, remaining uncertainty and the next step in the three tiers of [references/execution.md](references/execution.md) — legal now under the original grant, needing a named new authorization, or future-conditional — never one running list. Keep exploration/engineering progress distinct from a credible independent contribution, paper fit and a manuscript authorization. When a supported small finding has an actual Q2+ paper route, identify only the remaining decisive evidence; do not require a grand breakthrough or keep tuning indefinitely. When a meaningful Run changes the science, identify the fastest remaining evidence to a strong paper Claim, and whether the contribution is genuinely new and reusable, without writing an unapproved manuscript. Use `prepare_handoff` only for actual files; avoid dumping logs.

## Selective audits and tool profiles

Default MCP `research` exposes core+scientific+optional case tools (21 tools); `minimal` exposes 11, and `diagnostic` exposes all 24, including fixed-host diagnostics. Visibility does **not** confer permission. No MCP tool in this version can execute real DEV/GPU commands, authenticate author grants, write PD-RW Run/Claim, or establish SEALED filesystem isolation.

## Case-library reuse (on demand, never a new retrieval loop)

When `CASE_LIBRARY` is configured (`PDRW_CASE_LIBRARY_ROOT` or `case_library_root`), call `case_gate_check(event)` at **five triggers, priority G1 > G2 > G3 > T1 > T2**. Ordinary DEV iteration does not trigger. The earlier four on-demand points — a **new Task**, a **significant anomaly**, a **planned large resource investment**, and the **end of an effective experiment** — are covered by these five; do not re-run for every step. For unrelated general questions, do not load it.

**Knowledge mirror (optional, local only).** A mirror may be built for a reviewed
allowlist (`--scope-file <case_ids.json>`); a scoped mirror is complete at N/N and says
so in `manifest.scope`, so a partial mirror is never mistaken for the whole library.
`case-knowledge-build --out <dir>` renders the
same cases into a read-only Markdown/JSONL mirror for ChatGPT/Codex; it never syncs, uploads
or writes to `CASE_LIBRARY`, and `manifest.publishable` must be `true` before any publication
step. Reuse `case_search`/`case_gate_check` for retrieval; the mirror is not a second index.

**Three mandatory checkpoints** (each must actually retrieve AND judge applicability; a `CASE_CHECK: COMPLETED` text is not proof):

- **G1 · H2–H3 · before the core scientific question is fixed** (`milestone=QUESTION_SELECTION`): related success/failure cases and important counterexamples; check highly overlapping prior work, whether historical failure premises still hold, success key conditions, and whether a new scientific question is worth exploring. Historical failure must NOT auto-negate a new direction with different legal information conditions.
- **G2 · H4 and H6–H7 · before the evidence route and the core experimental protocol are frozen** (`milestone=PROTOCOL_FREEZE`): legal inputs at prediction time and temporal causality, labels, group independence, evaluation unit, strong simple baseline, repeated invalid algorithm premises, cheaper/more discriminative designs. H4 uses this window because choosing data/truth paths fixes those conditions. Convert only ADMISSIBLE experiences into concrete `next_minimal_check` items.
- **G3 · H8/H10 · before a major conclusion, main Claim or staged closure** (`milestone=CLAIM_OR_CLOSURE`): similar explanations for positive/negative results, evidence for innovation/mechanism/law claims, usable success conditions, failure boundaries, alternative directions and candidate experiences for `extract_case_candidates`. **PD-RW H8 author strategic choice and separate paper-writing permission are unchanged.**
- **H9 recheck** (`h_stage=H9` with `CONFIRMATION_PROTOCOL_CHANGED` / `PROTOCOL_SUBSTANTIVE_CHANGE` / `HOLDOUT_PROTOCOL_CHANGED`, or `milestone=PROTOCOL_RECHECK`): re-opens **G2** to re-check legal inputs, grouping, evaluation risk and strong baselines. It is NOT a claim checkpoint.

**Two conditional triggers:**

- **T1** important anomaly, core mechanism unsupported, severe evaluation problem, repeated ineffective attempts or consecutive valid negative results → first distinguish engineering error / invalid experiment / insufficient evidence / valid scientific negative, then suggest ONE next decisive action. Quote `anomaly_triage.category_effective`, not `category`: the second is your own declaration, and a declared negative contradicted by the same Run's declaration is reported as `UNKNOWN`.
- **T2** significant resource increase or change of core algorithm strategy, data scope, evaluation criterion or scientific question. Ordinary code changes, tuning, tests, plotting and same-scope DEV iteration do **not** trigger.

### H3/H4/H6 cards stay authoritative; the bridge only reads them

`project_case_bridge(stage_card, stage)` accepts an unchanged H3/H4 early plan (`pdrw-early-plan-v1`), an H6 plan (`pdrw-h6-plan-v1..v3`) or a plain declared card, and maps it into the same advisory gate. It **never rewrites, approves, rejects, reorders or fingerprints-over** a card: `plan_sha256`, `upstream_choices`, `hard_constraints_sha256` and the declared choice ref are echoed for traceability only, and `authorization.card_rewritten/plan_approved/execution_authorized` are always `false`.

Only same-meaning fields are mapped (`scientific_question`/`question_or_evidence_path` → `decision`, `competing_explanation` → `counterexamples`, plus any explicit `case_profile` the author declared). Every other dimension is returned in `unknown_dimensions` as **UNKNOWN** and is deliberately **not** written into the retrieval profile: a literal "UNKNOWN" would otherwise be compared as declared text and could fabricate `NO_TEXT_OVERLAP` → `CONDITIONS_DIFFER`. Early stages (`H3/H4/H6`, `early_stage_no_experiment_profile_required=true`) therefore need **no complete experiment profile** before real Run evidence exists. The result only advises; it never blocks a legal selection.

### From retrieval to a next action

`event` declares `h_stage`, `milestone`, `signals`, `task_id`, `decision`, `hypothesis`, `protocol`, `task_profile`, `query`, `filters`, optional `known_h_stage` and optional `execution_evidence_refs`. Stage, milestone and known project state are cross-validated: contradictions or a stale index return an **UNKNOWN advisory**, never `RETRIEVAL_VERIFIED`, and never block unrelated legal DEV. No matching cases may pass normally, but the tool records retrieval scope/result and marks `UNKNOWN`. An inaccessible library reports the reason, never fakes a completed check.

`next_actions` implements `RETRIEVE → GRADE_EVIDENCE → COMPARE_PREMISES → EXTRACT_RISK_OR_SUCCESS_CONDITIONS → PROPOSE_NEXT_ACTION → EXECUTION_EVIDENCE_RECHECK`. It returns **1–3** proposals of type `CONCRETE_CHECK`, `DECISIVE_EXPERIMENT`, `SUCCESS_CONDITION_TO_PRESERVE` or (only for G3/T2 risk) `AUTHOR_STRATEGY_OPTION`; each cites a case, evidence path/tier, the declared current-task premises and an applicability basis. Evidence insufficient ⇒ `UNKNOWN`, never a fabricated confident conclusion. `status=PROPOSED_NOT_EXECUTED`; `verify_execution_evidence` only rechecks references in existing Task/Run/receipt records. **Generating advice is not executing it**; no second research-state database.

**Success/failure balance:** `DECISION_GRADE` cases may drive advice. Preprint / internal-report / abstract-only cases appear as explicitly labelled `EXPLORATORY_LEAD` (`exploratory_lead_only=true`, `independent_confirmation=NOT_ESTABLISHED`) and never as independently confirmed conclusions; success leads also carry key conditions, matching/differing conditions, transferable mechanism and a minimal validation experiment. `SECONDARY_ONLY`, `NOT_ACCESSED`, speculation and unverified cards stay `CANDIDATE_ONLY`. `CONDITIONS_DIFFER` is never transferred as an active negative warning against a new direction with different legal information conditions.

**Reuse & token control:** `gate_fingerprint` covers Task, decision, hypothesis, protocol, stage, milestone, known project stage, `task_profile`, query/filters, evidence + execution declarations, `index_stale` and case-library `index.json` sha256; unchanged conditions return the verified cached record (`cache_hit: true`) with **zero new retrieval**. A stale index or declaration conflict never reuses a "verified" conclusion. The reused record carries the same `query_fingerprint`, so a `cache_hit: true` result is the same evidence, not new evidence. Default `detail=compact` is slimmed (no duplicated nested warnings, no raw 8-dim dumps); full evidence via `detail=full` or `review_case_transfer`. `payload_chars` reports the ACTUAL returned payload. General `search_research_memory` lookups use `case_scope=auto` and skip the full case library; `case_scope=force` retrieves it.

**Other tools:** `search_research_memory(query, ..., task_profile)` keeps the legacy PD-RW `CASE_REGISTRY.md` matches and adds one `case_library` object plus `case_learning_summary`; the old `(query, limit)` shape is unchanged. `review_case_transfer` compares all 8 dimensions and returns `APPLICABILITY_RISK` / `CONDITIONS_DIFFER` / `USEFUL_ANALOGY` / `EVIDENCE_INSUFFICIENT` per case; declared-text triage, **not** scientific equivalence. `extract_case_candidates(project_id, observations, ...)` derives **CANDIDATE_ONLY** items from original Run evidence + existing `science.lessons` / `science.provenance` audit; never promoted, never writes STATE/Run/EVENTS.

**Enforcement level (honest):** these are **Skill/tool-level advisory requests**, NOT a WorkBuddy host state-transition hard gate (`enforcement_level.hard_gate=false`). `verify_gate_record` rejects a bare `CASE_CHECK: COMPLETED`; check `retrieval_record` and `applicability_judgments`. A `cache_hit: true` result is the same evidence, not new information. No case tool grants permission, requires extra human approval, or auto-approves/rejects/terminates a project.

**Hard limits:** keyword similarity != scientific premise equivalence; compare `premises`, `applicability.conditions/boundaries` and `counterexamples` line by line. Check `evidence_grade`, `evidence_tier` and `index_stale`; `SECONDARY_ONLY` / `NOT_ACCESSED` / speculation stay candidates and must NOT support decision-grade claims, while labelled exploratory leads are clues only. `APPLICABILITY_DIVERGENCE` forbids merging two cases into one conclusion. Missing cases, insufficient sources and `CONDITIONS_DIFFER` are `UNKNOWN`. Archived/dropped cards stay visible but carry their status and never become positive success precedents. These tools never output GO/STOP, never grant permission, never modify PD-RW rules, SEALED, STATE, Run or CASE_LIBRARY, and never fetch external URLs. Candidate extraction is not a scientific conclusion. See `references/execution.md`.

**Local experience export (contract only in this version):** `case_export.export_case_markdown(case_id)` is a read-only, deterministic renderer that turns one already-indexed case (index + local card, later a local SQLite row) into a standalone Markdown experience card with a JSON front-matter block and a body sha256. It performs no GitHub sync, no upload and no write to `CASE_LIBRARY`; see `docs/CASE_EXPORT_INTERFACE.md`.

## Optional science check (only for a material research choice)

Use `audit_project_state(project_id)` and `reconstruct_project_history(project_id)` for material source conflicts;
`verify_run_evidence(project_id, run_id)` for original Run integrity;
`audit_scientific_experiment(project_id, run_id)` for bounded DEV/VAL leakage, metric and baseline checks;
`review_evidenced_lesson(project_id, run_id, proposal)` for hash-linked prior negative evidence.
Missing information => UNKNOWN, not PASS/FAIL or a new approval. If original hash-linked DEV/VAL Run artifacts include an evaluation matrix, the scientific audit reports coverage; absence is not complete coverage. Do not run every audit for every task.
Host CPU synthetic checks and `preflight_execution_plan(plan)` are diagnostic only and require the `diagnostic` profile; never interpret them as true research execution.

## Optional experiment feedback (only for a meaningful hypothesis-judging Run)

Only when a real Run judged a pre-declared hypothesis and the original pre-result
proposal still exists, run `python -m pdrw_agent.science.cli feedback-link --link
<link.json> --project-root <project>`. It verifies files/hashes, compares declared
categorical predictions, and attaches at most three case candidates. Rules:

- Report three states separately: `DECLARED_PREDICTION_COMPARED` (contrast
  computed, advisory), `PRE_RESULT_PROVENANCE_VERIFIED` (project-file record binds
  the proposal digest, its own time precedes the Run, no conflict),
  `PRE_RESULT_RECORD_UNVERIFIED` (anything less — never call it verified). A
  self-declared time, an inline proposal or equal hashes prove no order.
- `INVALID`/`INCONCLUSIVE`/`NOT_RUN` never become scientific negatives; a changed
  observable, unit or comparison reference is `NOT_COMPARABLE`. A positive keeps
  its conditions and boundaries; a negative challenges only the tested premise.
- Cases are candidates: `REVIEW_REQUIRED`, preprint and internal-report cards stay
  exploratory; same-paper/same-Run cards count once; a miss is
  `NOT_FOUND_WITHIN_SCOPE`, never "no evidence".
- Timing is explicit: retrieval now is `post_run_related_case_ids`, never
  pre-decision use. Pre-decision IDs need a `pdrw-case-usage-receipt-v1` receipt
  in the project dated before the frozen decision; otherwise UNKNOWN.
- After a judged Run, project the link with `to_run_feedback` (or
  `feedback-link --as-run-feedback`) and pass it as `run_feedback` to
  `case_gate_check`. Every event field is a declaration: the gate never reports
  a verified provenance and names the four checks it did not run, so say
  "declared" unless `feedback_link` reported that check itself. The first next
  action follows the Run situation, not keywords (conflict, missing evidence, changed axes, repair, rerun, reassess premise).
- Write the contrast and the changed next step in the existing
  `RESEARCH_RECORD.md`; `PAPER_BLUEPRINT.md` only when a Claim changes. No second
  ledger, no approval step.

Ordinary code changes, debugging and routine DEV must not invoke it. No MCP
tool is registered for it. See `docs/EXPERIMENT_FEEDBACK_LINK.md`.

## Optional references (load only when triggered)

- [references/plan-selection.md](references/plan-selection.md): new-project H3/H4/H6 stage card, lineage and choice boundary
- [references/research-leverage.md](references/research-leverage.md): high-impact scientific opportunity, H6 decision or significant negative/pivot only
- [references/integration.md](references/integration.md): installation, mapping, version or project-switch issues
- [references/execution.md](references/execution.md): authorized DEV continuation, evidence handoff, interruption; [references/packet.md](references/packet.md) to write and check a decision packet
- [references/troubleshooting.md](references/troubleshooting.md): missing sources, identity or permission conflicts
- [references/INDEX.json](references/INDEX.json): optional routing metadata, never policy authority

WorkBuddy imports the Skill separately from the Python/MCP installation. See `docs/RUNTIME_AND_MCP.md` for setup. Never pre-read all references.
