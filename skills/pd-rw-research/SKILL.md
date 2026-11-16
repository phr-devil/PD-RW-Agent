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
version: 0.6.0
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

For a **fresh WorkBuddy task** with an explicit project ID, an operator-registered project mapping, and enabled `pd-rw-research` MCP tools, **actually call `get_project_context(project_id)` once before bulk project-file reading**. Do not merely list the tool or cite this Skill as evidence that it ran. The MCP call executes the shared `pdrw_agent` Python service; WorkBuddy's own terminal Python is not evidence of that integration. Avoid additional preflight calls when the same verified tool result is already in this task's context.

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

## Case-library decision reuse (on demand, not a new retrieval loop)

When `CASE_LIBRARY` is configured (`PDRW_CASE_LIBRARY_ROOT` or `case_library_root`), call `case_gate_check(event)` at **five triggers, priority G1 > G2 > G3 > T1 > T2**. Ordinary DEV iteration does not trigger. The earlier four on-demand points — a **new Task**, a **significant anomaly**, a **planned large resource investment**, and the **end of an effective experiment** — are now covered by these five; do not re-run for every step. For unrelated general questions, do not load it.

**Three mandatory checkpoints** (each must actually retrieve AND judge applicability; a `CASE_CHECK: COMPLETED` text is not proof):

- **G1 · H2–H3 · before the core scientific question is fixed** (`milestone=QUESTION_SELECTION`): related success/failure cases and important counterexamples; check highly overlapping prior work, whether historical failure premises still hold, success key conditions, and whether a new scientific question is worth exploring. Historical failure must NOT auto-negate a new direction with different legal information conditions.
- **G2 · H6–H7 · before the core experimental protocol is frozen** (`milestone=PROTOCOL_FREEZE`): legal inputs at prediction time and temporal causality, labels, group independence, evaluation unit, strong simple baseline, repeated invalid algorithm premises, cheaper/more discriminative designs. Convert only ADMISSIBLE experiences into concrete `next_minimal_check` items.
- **G3 · H8–H10（H9 除外）· before a major conclusion, main Claim or staged closure** (`milestone=CLAIM_OR_CLOSURE`, `h_stage=H8/H10`): similar explanations for positive/negative results, evidence for innovation/mechanism/law claims, usable success conditions, failure boundaries, alternative directions and candidate experiences for `extract_case_candidates`. **PD-RW H8 author strategic choice and separate paper-writing permission are unchanged.**
- **H9 recheck** (`h_stage=H9` + `CONFIRMATION_PROTOCOL_CHANGED` / `PROTOCOL_SUBSTANTIVE_CHANGE` / `HOLDOUT_PROTOCOL_CHANGED`, or `milestone=PROTOCOL_RECHECK`): re-opens **G2** to re-check legal inputs, grouping, evaluation risk and strong baselines. It is NOT a claim checkpoint.

**Two conditional triggers:**

- **T1** important anomaly, core mechanism unsupported, severe evaluation problem, repeated ineffective attempts or consecutive valid negative results → first distinguish engineering error / invalid experiment / insufficient evidence / valid scientific negative, then suggest ONE next decisive action.
- **T2** significant resource increase or change of core algorithm strategy, data scope, evaluation criterion or scientific question. Ordinary code changes, tuning, tests, plotting and same-scope DEV iteration do **not** trigger.

`event` declares `h_stage`, `milestone`, `signals`, `task_id`, `decision`, `hypothesis`, `protocol`, `task_profile` (mechanisms, legal_inputs, labels, grouping, evaluation_unit, baseline, boundaries, counterexamples, decision), `query`, `filters`, optional `known_h_stage` and optional `execution_evidence_refs`. Stage, milestone and known project state are cross-validated: contradictions / a stale index return an **UNKNOWN advisory**, never `RETRIEVAL_VERIFIED`, and never block unrelated legal DEV. No matching cases may pass normally, but the tool must record retrieval scope/result and mark `UNKNOWN`. An inaccessible library reports the reason, never fakes a completed check.

**从检索到下一行动:** `next_actions` implements `RETRIEVE → GRADE_EVIDENCE → COMPARE_PREMISES → EXTRACT_RISK_OR_SUCCESS_CONDITIONS → PROPOSE_NEXT_ACTION → EXECUTION_EVIDENCE_RECHECK`. It returns **1–3** proposals of type `CONCRETE_CHECK`, `DECISIVE_EXPERIMENT`, `SUCCESS_CONDITION_TO_PRESERVE` or (only for G3/T2 risk) `AUTHOR_STRATEGY_OPTION`; each cites a case, evidence path/tier, the declared current-task premises and an applicability basis. Evidence insufficient ⇒ `UNKNOWN`, never a fabricated confident conclusion. `status=PROPOSED_NOT_EXECUTED`; `verify_execution_evidence` only rechecks references in existing Task/Run/receipt records. **Generating advice is not executing it**; no second research-state database.

**成功/失败平衡:** `DECISION_GRADE` cases may drive advice. Preprint / internal-report / abstract-only cases appear as explicitly labelled `EXPLORATORY_LEAD` (`exploratory_lead_only=true`, `independent_confirmation=NOT_ESTABLISHED`) and never as independently confirmed conclusions; success leads also carry key conditions, matching/differing conditions, transferable mechanism and a minimal validation experiment. `SECONDARY_ONLY`, `NOT_ACCESSED`, speculation and unverified cards stay `CANDIDATE_ONLY`. `CONDITIONS_DIFFER` is never transferred as an active negative warning against a new direction with different legal information conditions.

**Reuse & Token control:** `gate_fingerprint` covers Task, decision, hypothesis, protocol, stage, milestone, known project stage, `task_profile`, query/filters, evidence + execution declarations, `index_stale` and case-library `index.json` sha256; unchanged conditions return the verified cached record (`cache_hit: true`) with **zero new retrieval**. A stale index or declaration conflict never reuses a "verified" conclusion. The unchanged verified record carries the same `query_fingerprint`; a `cache_hit: true` result is the same evidence, not new evidence. Default `detail=compact` is slimmed (no duplicated nested warnings, no raw 8-dim dumps); full evidence via `detail=full` or `review_case_transfer`. `payload_chars` reports the ACTUAL returned payload. General `search_research_memory` lookups use `case_scope=auto` and skip the full case library; `case_scope=force` retrieves it. No second science-state database.

**Other tools:** `search_research_memory(query, ..., mechanism, domain, task_profile)` keeps the legacy PD-RW `CASE_REGISTRY.md` matches and adds one `case_library` object (`cases.results`, `case_review.comparisons`, `decision_experiences.experiences`, at most 3–5 impacts, both negative warnings and success transfers) plus `case_learning_summary`; old `(query, limit)` shape unchanged. `review_case_transfer` compares all 8 dimensions and returns `APPLICABILITY_RISK` / `CONDITIONS_DIFFER` / `USEFUL_ANALOGY` / `EVIDENCE_INSUFFICIENT` per case; declared-text triage, **not** scientific equivalence. `extract_case_candidates(project_id, observations, ...)` derives **CANDIDATE_ONLY** items from original Run evidence + existing `science.lessons` / `science.provenance` audit; never promoted, never writes STATE/Run/EVENTS.

**Enforcement level (honest):** these are **Skill/tool-level advisory requests**, NOT a WorkBuddy host state-transition hard gate (`enforcement_level.hard_gate=false`). `verify_gate_record` rejects a bare `CASE_CHECK: COMPLETED`; check `retrieval_record` and `applicability_judgments`. A `cache_hit: true` result is the same evidence, not new information.

**Hard limits:** keyword similarity != scientific premise equivalence; compare `premises`, `applicability.conditions/boundaries` and `counterexamples` line by line. Check `evidence_grade`, `evidence_tier` and `index_stale`; `SECONDARY_ONLY` / `NOT_ACCESSED` / speculation stay candidates and must NOT support decision-grade claims, while labelled exploratory leads are clues only. `APPLICABILITY_DIVERGENCE` forbids merging two cases into one conclusion. Missing cases, insufficient sources and `CONDITIONS_DIFFER` are `UNKNOWN`. These tools never output GO/STOP, never grant permission, never modify PD-RW rules, SEALED, STATE, Run or CASE_LIBRARY, and never fetch external URLs. Candidate extraction is not a scientific conclusion. See `references/execution.md`.

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
