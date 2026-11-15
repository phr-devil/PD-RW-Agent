# Execution and handoff adapter

Load only when a resumed task actually needs multiple tool actions, DEV iteration, or project handoff. Scientific semantics stay in PD-RW.

## Trigger-aware calibrations (not four new stages)

- **Restore** on new chat / compaction / project switch: recover exact project, rule version, record snapshot and primary evidence.
- **Execution calibration** when WorkBuddy drifts, repeats work, or misses a rule: check only the affected fact and route, then continue.
- **Gate calibration** immediately before an actual restricted effect: check original permission and tool boundary, not just a state tag.
- **Science calibration** only when a key new Run, negative result or Claim shift could change the next experiment or contribution.

## The autonomous loop

1. Verify the chosen task, legal input information, original operation scope and best valid evidence.
2. Select the next **meaningful cluster** of related safe DEV actions, with a scientific discriminator and bounded cost; reuse valid runs. Do not create artificial micro-approvals or fixed batch counts. A user idea is a hypothesis to assess, not automatically a decision.
3. Use the WorkBuddy-provided tools to implement within existing approved DEV scope, preserving protected artifacts and original evidence.
4. Read actual tool exit status and targeted tests/results; distinguish engineering failure, INVALID evaluation and a meaningful scientific negative. Preserve original failed runs and source paths; do not repeatedly falsify unchanged assumptions.
5. Decide whether another different probe is informative. Stop an unchanged/low-information loop rather than producing repetitive experiments.
6. Record only important scientific events in the existing `RESEARCH_RECORD.md`, checking the associated `PAPER_BLUEPRINT.md` when affected. Do not add a parallel approval table or new research phase.
7. Deliver one principal result, exact artifacts, performed validations, scientific limitations, and one next legal action.

## Authorizations

Scientific strategy and operational permissions are separate. Use the current PD-RW `AGENTS.md`, `WORKFLOW.md`, `NEXT_ACTION_POLICY.md`, and relevant owner when those boundaries matter. Existing permissible safe, non-paid DEV technical work can proceed autonomously; do not request new approval for every ordinary run.

Reading `approved` in `STATE`, a self-written JSON packet, or a successful static preflight **does not** prove original user authorization. Current bundled scripts are **read-only**. There is **no** trusted hook preventing an unrestricted WorkBuddy shell from opening SEALED files: hard enforcement requires independent filesystem access controls or a separately trusted tool host.

## Checks and evidence

When warranted, invoke PD-RW's existing tools from its root, e.g. `python -m core.cli status --root RESEARCH_PROJECT`, `python -m core.execution_preflight action PACKET.json`, or targeted regression tests, using actual compatible inputs from PD-RW documentation. A structural ALLOW declaration is not proof of authorization, isolation, or scientific success. Never invent a run, hash, metric, or test result.

v0.5 adds private SQLite operational receipts, read-only recovery, PD-RW Run registration preview and handoff preview. A reported artifact with a matching SHA is `ARTIFACT_REVIEW_PENDING`, NOT `NEEDS_RECONCILIATION`: inspect original Run/protocol and continue separately authorized work, without automatically rerunning or treating its checksum as science. Unknown/changed artifact or uncertain process remains `NEEDS_RECONCILIATION`. Reported `RUNNING_DECLARED` is NOT a verified live process; an uncertain job must be reconciled before restarting. The original PD-RW event writer has a separately callable host-only adapter, but **no MCP/CLI path grants Run registration**; a real independently secured authorization host and OS ACL are still absent. No background scheduler, independent model loop, automatic GPT API bridge, or WorkBuddy runtime enforcement is installed. WorkBuddy's own continuation mechanisms, if available, control execution lifetime.

## Optional scientific discriminability helper

Only at a consequential research fork, assemble a small local DEV proposal with exact premise/scope, at least two competing hypotheses, qualitative probe predictions and original source refs. Use `python -m pdrw_agent.science.cli decision --packet FILE.json` to compare stated distinctions. A matched prior negative is an **advisory candidate**, not automatic STOP. Missing evidence is UNKNOWN; no new approval step or research authority.

## Case-library decision reuse (v0.5.4 local increment)

At a **new Task**, a **significant anomaly**, a **planned large resource investment**, or the **end of an effective experiment**, call `search_research_memory` once with the mechanism filters and a declared `task_profile` (mechanisms, legal_inputs, labels, grouping, evaluation_unit, baseline, boundaries, counterexamples, decision). Read `decision_experiences` (≤5, both negative warnings and success transfers) and `case_review`; for an explicit second opinion use `review_case_transfer`.

- Compare each case's `premises`, `applicability.conditions/boundaries` and `counterexamples` with the **actual** protocol. `USEFUL_ANALOGY` is a prompt to check, not a licence to transfer a conclusion. `APPLICABILITY_RISK` or `CONDITIONS_DIFFER` means do not reuse that result directly; `EVIDENCE_INSUFFICIENT` means mark it a candidate.
- Check `source_verification.per_case.<id>.evidence_grade`; a `DECISION_GRADE` case is original/partial-text verified with a matching local card. `ABSTRACT_VERIFIED_ONLY`, `NON_DECISION_GRADE`, `+PREPRINT_NOT_PEER_REVIEWED`, `UNVERIFIED_CARD_MISSING_OR_ID_MISMATCH` and `INDEX_STALE_REBUILD_REQUIRED` stay `candidates_only`. `role_classes` separates original empirical work, independent replication/external validation, author/internal reports, opinion/review and unverified secondary claims.
- Never emit GO/STOP from these tools; decisions stay with PD-RW and the author. Never write to CASE_LIBRARY, STATE, RESEARCH_RECORD, Run, EVENTS or SEALED. No second memory file or research-rule copy.
- **Dedup:** keep `query_fingerprint`; do not repeat the same query+profile+index in one task. `cache_hit: true` is the same evidence, not new evidence. Re-query only when the declared conditions or the index fingerprint change.
- At the end of an effective experiment, `extract_case_candidates` may produce `CANDIDATE_ONLY` items from original Run evidence plus the existing science audit. They are **not** verified scientific conclusions and are never auto-promoted; a later, separately authorized, independently verified review would be required to add a case card.

## Case-application gates (v0.5.5 local increment)

`case_gate_check(event, detail="compact")` is the **single** new MCP tool. It is an orchestrator only: it decides WHEN to retrieve, reuses the verified result, and verifies that a real retrieval happened. All retrieval/ranking/8-dimension review come from the existing `case_learning.case_search` -> `CASE_LIBRARY/scripts/search_cases.py`. No second retriever, no new science-state database.

**Five triggers, priority G1 > G2 > G3 > T1 > T2**

| Trigger | When | Declared event fields | Main output |
| --- | --- | --- | --- |
| G1 | H2–H3, before the core scientific question is fixed | `h_stage=H2/H3`, `milestone=QUESTION_SELECTION` | `selection_impact` |
| G2 | H6–H7, before the core experimental protocol is frozen | `h_stage=H6/H7`, `milestone=PROTOCOL_FREEZE` | `concrete_checks`, `protocol_design_review` |
| G3 | H8–H10, before a major conclusion / main Claim / staged closure | `h_stage=H8/H9/H10`, `milestone=CLAIM_OR_CLOSURE` | `contribution_review`, candidate hint |
| T1 | anomaly, unsupported core mechanism, severe evaluation problem, repeated ineffective attempts, consecutive valid negatives | `signals` with a T1 code; `outcome_class`, `evidence_refs` | `anomaly_triage`, failure/repair experiences |
| T2 | significant resource increase or change of core algorithm, data scope, evaluation criterion or scientific question | `signals` with a T2 code | `decision_change_review` |

`CODE_CHANGE`, `HYPERPARAMETER_TUNING`, `TEST_ONLY`, `PLOTTING`, `SAME_SCOPE_DEV`, `BUG_FIX`, `DOCUMENTATION`, `REFACTOR` are DEV noise: with `milestone=NONE` they return `NO_CASE_RETRIEVAL_REQUIRED` and **zero retrieval**. Unknown declared signals/stages are recorded as `UNKNOWN`, never silently invented.

**Mandatory checkpoints are evidence-checked.** The result carries `retrieval_record` (`retrieval_tool=case_learning.case_search`, `index_sha256`, `retrieval_scope`, `retrieved_case_ids`, `applicability_judgments`, `source_verification_present`) and `verification.status`. A bare `CASE_CHECK: COMPLETED` string is rejected by `verify_gate_record`. No-match still passes with `gate_status=UNKNOWN`, an explicit retrieval scope and result, and `may_proceed=true`. An inaccessible library returns `CASE_LIBRARY_UNAVAILABLE` with the reason, no fake completion and no blocking of unrelated legal work.

**Fingerprint reuse.** `gate_fingerprint` hashes Task, hypothesis, protocol, `h_stage`, `milestone`, `task_profile`, `query`, `filters`, evidence declaration and the CASE_LIBRARY `index.json` sha256. Unchanged conditions return the **same verified record** with `cache_hit=true` and zero new retrieval; changing any key premise/evidence/protocol or rebuilding the index produces a new fingerprint and a fresh retrieval. The cache is a bounded in-process `OrderedDict`, not a project STATE/EVENTS store. `detail="compact"` defaults to ≤5 one-line cases; `detail="full"` or the existing `search_research_memory` / `review_case_transfer` tools supply full evidence.

**Enforcement level.** `enforcement_level.actual = ADVISORY_SKILL_AND_TOOL_LEVEL`, `hard_gate=false`, `host_state_transition_interception=false`. WorkBuddy on this host has no trusted state-transition hook: the Skill requests the check, the tool executes it when actually called, but it cannot block a transition. Never report it as a hard gate. `automatic_go_stop=false` always; PD-RW H6/H8 author choices and separate writing permission are unchanged. T1 triage separates engineering error / invalid experiment / insufficient evidence / valid scientific negative before any suggested action. `evals/case_gate_eval.py` records actual calls, false/missed triggers and payload size; real decision quality and WorkBuddy tokens remain `NOT_MEASURED`.

## Minimal handoff

`RESULT | EVIDENCE_PATHS | TESTS_ACTUALLY_RUN | LIMITS/UNKNOWN | NEXT_LEGAL_ACTION_OR_USER_CHOICE`

This is an output guide, not a requirement to create a new handoff file or duplicate the PD-RW project's existing reports.
