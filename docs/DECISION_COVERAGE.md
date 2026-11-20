# Proven design decisions and ownership map — NOT a second PD-RW policy

This index preserves the **effective design decisions** from prior WorkBuddy + ChatGPT + PD-RW discussions, while referring to the **current** authoritative sources instead of copying their rules. If a rule changes, its PD-RW owner wins; this index may need its *reference* updated, not its own competing interpretation.

| Agreed principle / pain point | Sole source of scientific/permission meaning | What PD-RW-Agent actually does or must test |
| --- | --- | --- |
| **Agent ≠ newly trained LLM**: leverage WorkBuddy model/tools and local Windows + RTX 4080; avoid mandatory API/fine-tuning | Platform configuration outside PD-RW; user tool choice | Skill-based tool adapter, no model API/fees required; optional integrations later |
| **Single Skill first**, no speculative multi-agent architecture | PD-RW `AGENTS.md` / `docs/STRUCTURE.md` | One `SKILL.md` and on-demand references; no duplicate agents or approval phases |
| **Memory loss after restarts/compaction** | Project `STATE` + `RESEARCH_RECORD.md` + optional `PAPER_BLUEPRINT.md` and original Run | `bridge.py resume` reads bounded snapshot, locates files, flags missing/conflicting identity; no third project ledger |
| **Number/name collisions across projects** | PD-RW `DUAL_DOCUMENT_WORKFLOW.md`; `LESSONS/CASE_REGISTRY.md` only as index | Explicit operator mapping and original project ID / dataset cross-check; no guesses |
| **Rule drift and stale versions** | PD-RW `AGENTS.md`, `WORKFLOW.md` | Local HEAD in `doctor`; remote unverified until independently checked; no silent pull/rebase |
| **Scattered/duplicate rule loading** | PD-RW `AGENTS.md` section 2 | `context.py route` derives current owner-file hints from the live checkout; progressive disclosure |
| **Separate author strategy from technical autonomy** | PD-RW `WORKFLOW.md`, `AUTHOR_STRATEGY_REVIEW.md`, `NEXT_ACTION_POLICY.md` | Respect H1–H6, H8 and applicable H9/H10 author choices; H7 and already authorized DEV can progress without repetitive sign-off |
| **New-project H6 plan selection only once** | PD-RW WORKFLOW + AUTHOR_STRATEGY_REVIEW (H1/H2 launch, H3-H5 drafts, H6 one author choice) | Skill shows current option card and waits for specific author reply; local science H6 checker binds hash/declared option but always reports unauthenticated. No real WorkBuddy host enforcement yet. |
| **User suggestions are not automatic scientific verdicts** | PD-RW `AGENTS.md` entry and `NEXT_ACTION_POLICY.md` | Classify IDEA / EXPLICIT_INSTRUCTION / STRATEGIC_CHOICE at task start; require original message evidence for strategy change |
| **Operational authorization separate from chosen Task/Claim** | PD-RW `WORKFLOW.md` and relevant SEALED/writing/figure owners | `context.py action-review` wraps existing advisory checker; never grants permission. Host-level enforcement still absent |
| **SEALED, confirmations, writing, drawing, payments, uploads/submission are independent gates** | PD-RW `CONFIRMATION.md`, `WRITING_GATE.md`, `FIGURE_POLICY.md`, `EXECUTION_ASSURANCE.md` | No automatic sealed access, model fitting beyond scope, manuscript, chart, upload, payment or submission based on Skill/STATE text |
| **Scientific evidence must be traceable** | PD-RW `EXPERIMENT_LOOP.md` and `core/` | Compare original versioned Run, group split, label provenance, legal prediction-time inputs, evaluator; INVALID/NOT_RUN is not a scientific negative |
| **Stay scientifically open but avoid fake innovation** | PD-RW `HIGH_VALUE_RESEARCH_DESIGN.md`, `PAPER_FIRST.md`, `CONTRIBUTION_TAXONOMY.md` | Preserve strong simple baselines, named nearest work, independent evidence and competing hypotheses; no automatic Q2 prediction |
| **Excessive narrow falsification / endless parameter tuning** | PD-RW `EXPERIMENT_LOOP.md`, `ALGORITHM_ENGINEERING.md`, `core.probes`, `core.failure_triage` | Before a new probe check changed prediction, legal leverage, reusable Run, cost and termination premise; distinguish crash vs valid negative |
| **Important positive / negative results remain useful** | PD-RW `SCIENCE_RESULT_HARVEST.md`, `POST_ALGORITHM_SCIENCE_AUDIT.md` | Route to existing result-harvest tooling as appropriate; do not discard a valid baseline because one mechanism failed |
| **Incremental research memory and paper blueprint** | PD-RW `DUAL_DOCUMENT_WORKFLOW.md` | Update existing record only for meaningful event; re-check affected blueprint SEC_ID without writing manuscript |
| **Small, consistent delivery instead of a pile of files** | PD-RW `NEXT_ACTION_POLICY.md`, `core.delivery_check` | `context.py delivery-review` delegates path check; output main entry, actual tests/evidence, limits, one next action |
| **Token and time efficiency as a whole-task objective** | PD-RW `NEXT_ACTION_POLICY.md`, `REPLAY_PROTOCOL.md` | Minimal snapshots, no default full read, avoid repeated experiments; compare real tokens/DEV hours/human interventions, do not invent savings |
| **Four optional calibration triggers, not repeated prompt spam** | PD-RW `AGENTS.md` entry/hand-off, `NEXT_ACTION_POLICY.md`, `REPLAY_PROTOCOL.md` | On new session: recovery; observed drift: execution calibration; restricted action: gate check; changed evidence/claim: scientific-value check. Not four new mandatory phases |
| **Keep completed old project decisions valid unless a dependency actually changes** | PD-RW `WORKFLOW.md`, `AUTHOR_STRATEGY_REVIEW.md` | Local reopen only affected decision; don't silently re-approve downstream H nodes |
| **Test actual WorkBuddy behavior** | PD-RW `REPLAY_PROTOCOL.md` / `evals/` | This repo: offline unit/CI plus manually captured, same-budget WorkBuddy A/B traces; until then `NOT_MEASURED` |
| **Future flexibility** | Adapter architecture in this repo | WorkBuddy-first, API/MCP optional later; no duplicate science rules, migrate via narrow interfaces |

## Out of scope and unresolved

1. **No authenticated user-message source** is supplied to a trusted executor in v0.2. A self-written JSON or `APPROVED` marker is not consent.
2. **No OS-level SEALED isolation or WorkBuddy tool interception** has been installed or tested.
3. **No supervised autonomous scheduler/model orchestration** is bundled. WorkBuddy continues tasks under its own supported runtime.
4. **No credible empirical token savings or research-success claim** exists until real paired WorkBuddy tasks are recorded.
5. **No full reproduction of private local project evidence** is possible from this public adapter repository.

Whenever a gap is fixed, update the implementation + focused tests, and mark evidence scope precisely.

## Constraint preservation map — 0.9.4 convergence review (2026-11-19)

This is an audit index, not a second policy. "Authority" names the owner of the
meaning; where the local rule checkout cannot show that text, the row says so
instead of assuming it away.

Baseline: `83b6360` (v0.9.3) on `wp9/v0.9.3-trusted-feedback`; review branch
`arch/convergence-0.9.4`. Local PD-RW checkout: `68e29c3` = `pd-rw-human-review-v1.3`.
The v1.4 protocol text (`d4056fc`) was read from the remote raw file, not from
the local checkout.

### Scientific goal

| Requirement | Authority | Implementation | Test | This round | Verification |
| --- | --- | --- | --- | --- | --- |
| Q1 first, credible Q2+ as the floor | PD-RW `Q2_PUBLICATION_GOAL.md`, `HIGH_VALUE_RESEARCH_DESIGN.md` | `SKILL.md` Outcome paragraph | `test_skill_contract` (text) | unchanged | text assertion + manual read |
| Importance, named nearest-neighbor delta, falsifiability | H3/H4 card schema | `science/staged_selection.py` | `test_staged_selection` | unchanged | card-field contract |
| Simple methods, valid negatives, mechanism/law/evaluation contributions allowed | `CONTRIBUTION_TAXONOMY.md` | `SKILL.md`, `references/research-leverage.md` | `test_skill_contract` | unchanged | text contract |
| No auto-certification of novelty via DEV gains, model complexity or zero retrieval hits | `NEXT_ACTION_POLICY.md` | `case_gates` (no GO/STOP), `science/decision.py` | `test_case_gates`, `test_science_decision` | unchanged; new "no upgrade" assertions | `test_arch_convergence` |

### Scientific workflow

| Requirement | Authority | Implementation | Test | This round | Verification |
| --- | --- | --- | --- | --- | --- |
| PD-RW is the only rule source | `WORKFLOW.md` | Skill header, service docstring | `test_skill_contract` | `ARCHITECTURE.md` makes the layer order explicit | doc assertions |
| Three loops, six activities, H1–H10 version compatibility | `contracts/research_activity_protocol.v1.json`, `human_review_protocol.v1.json` | no re-implementation in this repo | CI matrix (v1.13 + v1.14 fixture) | unchanged | CI + review |
| v1.4: H3/H4/H6 are three distinct author decisions, H5 derived and bound to H6 | `pd-rw-human-review-v1.4` (`d4056fc`, read remotely) | `staged_selection.py` (H3/H4), `plan_selection.py` v3 upstream | `test_staged_selection`, `test_h6_plan_selection` | unchanged; stale "v1.4 chain" docstring corrected to v1.14 | targeted tests |
| Old projects keep valid historical choices (no retroactive re-selection) | `WORKFLOW.md` local rollback; `legacy_protocol_versions` | `LEGACY_PLAN_VERSION` v1 path | `test_h6_plan_selection` | unchanged | legacy-card test |
| H7: authorized DEV continues autonomously | protocol H7 `decision_owner=AGENT` | `SKILL.md` step 5; ordinary DEV → `NO_TRIGGER` | `test_science_autonomy_regressions`, `test_case_gates` | unchanged | regression |
| H8 only for a material Claim/strategy change | H8 `reopen_when` | `_strategy_scope_change` | `test_case_gates`, `test_wp9_next_action` | unchanged | regression |
| No new H node, approval step or state machine | `WORKFLOW.md` header | nothing added | `test_arch_convergence` (tool surface) | none added | test |

### Scientific truthfulness

| Requirement | Authority | Implementation | Test | This round | Verification |
| --- | --- | --- | --- | --- | --- |
| Legal prediction-time inputs, label truth, group independence, strong baseline, fair evaluation, leakage | `EXPERIMENT_LOOP.md` | `science/validity.py` | `test_v062_validity` | unchanged | regression |
| DEV/VAL/SEALED separation and frozen evidence | `CONFIRMATION.md`, `EXECUTION_ASSURANCE.md` | path refusal in `feedback_link` | `test_science_feedback_link` | unchanged | regression |
| Distinguish NOT_RUN / INVALID / INCONCLUSIVE / UNKNOWN / valid positive / valid negative | `RUN_RECORD_STATUS` mapping (v0.9.3) | `feedback_link`, `case_gates._run_situation` | `test_wp9_feedback_timing`, `test_wp9_next_action` | three record-level situations added (conflict / missing evidence / changed axes) | `test_arch_convergence` |
| One negative Pilot, UNKNOWN evidence or an engineering failure never ends the project | `NEXT_ACTION_POLICY.md` | `_SITUATION_TEXT` | `test_wp9_next_action` | unchanged | regression |
| Retrieval, declaration, hash, CI PASS or self-assessment never become proof | original user instructions (**PRESERVATION_UNVERIFIED**: no rule file in this repo) | `declared_only`, `declared` vs `effective` | new | strengthened: hand-written provenance is capped, projection is downgrade-only | `test_arch_convergence` |
| Proposal → evidence → feedback → next action stays one chain | this review (B) | `feedback_link.to_run_feedback`, gate `decision_basis` | new (18 tests) | added | targeted tests |

### Permissions

| Requirement | Authority | Implementation | Test | This round | Verification |
| --- | --- | --- | --- | --- | --- |
| Original authorization separate from the scientific plan choice | `human_review_protocol.v1.json` | every checker returns `*_authorized=false` | `test_science_feedback_link`, `test_wp9_*` | unchanged | regression |
| Already-authorized ordinary DEV is not blocked again | `NEXT_ACTION_POLICY.md` | ordinary DEV triggers nothing | `test_case_gates` | unchanged | regression |
| Download, extra resources, cost, egress, SEALED, figures, writing, submission keep separate gates | `CONFIRMATION.md`, `WRITING_GATE.md`, `FIGURE_POLICY.md` | no tool can perform them | `test_mcp` (no execution tool) | unchanged | regression |
| Skill/Python/MCP declarations are not host authorization or OS isolation | same | `hard_gate=false`, `permission_to_execute=false` | `test_case_gates` | `ARCHITECTURE.md` states it per layer | regression + doc |

### State and memory

| Requirement | Authority | Implementation | Test | This round | Verification |
| --- | --- | --- | --- | --- | --- |
| Real project identity and root/STATE/RESEARCH_RECORD/Run binding | `DUAL_DOCUMENT_WORKFLOW.md` | `projects.py`, `runtime/recovery.py` | `test_runtime`, `test_v05_pd_rw_integration` | unchanged | regression |
| An unregistered project is never pretended to be registered | PD-RW identity rules | `service` returns `PROJECT_NOT_REGISTERED` | `test_mcp`, `test_runtime` | unchanged | regression |
| No second scientific ledger | `WORKFLOW.md` | no new store | `test_arch_convergence` | none added | test |
| Original Runs, frozen protocols, historical choices, card fingerprints and CASE_LIBRARY are not migrated or rewritten | original user instructions | this round writes to no project | `git diff` + directory audit | untouched | change audit |
| Cross-session recovery, rule-version check, MCP fallback, context-confusion guard | `AGENTS.md` | `runtime/recovery.py`, `MCP_NOT_USED` | `test_wp2_reliability`, `test_skill_contract` | unchanged | regression |
| Pre/post-Run case timing and strict `as_of` do not regress | this repo (v0.9.3 contract) | `feedback_link.case_timing`, `case_learning.search(as_of=...)` | `test_wp9_feedback_timing`, `test_wp9_case_as_of` | unchanged; legacy comparator now states its timing is unverified | regression + new test |

### Efficiency and compatibility

| Requirement | Authority | Implementation | Test | This round | Verification |
| --- | --- | --- | --- | --- | --- |
| On-demand Skill loading, compact/full recovery, MCP profiles, CLI/MCP contract | `RUNTIME_AND_MCP.md` | Skill <160 lines; profiles | `test_skill_contract`, `test_mcp` | docs converged on one current entry; counts unchanged | tests |
| No mandatory full-rule read, repeated review, extra agent call or fixed useless test | `NEXT_ACTION_POLICY.md` | none added | — | none added | manual |
| Trimming prompts must not drop behavior | original user instructions | marker-based Skill contract | `test_skill_contract` | one bullet rewritten, no marker removed | regression |
| Research-Prompt-Library stays a read-only compatibility reference | original user instructions | no edits | — | not modified | `git status` per repo |

### Explicitly unverified in this round

1. **`PRESERVATION_UNVERIFIED`** — "retrieval, declaration, hash, CI or self-assessment is not proof" is only stated in original user messages; no repository rule file carries that sentence. Behavior was preserved and tightened, but the *source text* could not be re-read.
2. **v1.4 protocol text is remote-only here.** The local PD-RW checkout is `pd-rw-human-review-v1.3` (`68e29c3`); the v1.4 wording was read from `d4056fc` on GitHub. The adapter implements the v1.4 shape, but this machine cannot diff the two rule trees offline.
3. **No measured research, Token or wall-clock benefit.** `NOT_MEASURED`; no paired WorkBuddy replay was recorded.
4. **Whether a real model will call `to_run_feedback` instead of hand-writing `run_feedback`** is unmeasured; only the code-level cap is tested.

## WP10 — declared feedback cannot certify itself (2026-11-19)

Baseline `995406c` (v0.9.4, PR #19). Only the two confirmed defects were
touched; the 0.9.4 constraint map above still applies unchanged.

| # | Defect | Evidence it was real | Fix | Test |
| --- | --- | --- | --- | --- |
| 1 | `case_gates._declared_run_feedback` treated a caller-typed `link_status` as proof, so `provenance=PRE_RESULT_PROVENANCE_VERIFIED` + `link_status=ADVISORY_FEEDBACK_ONLY` stayed "effective verified" | `VERIFIED_PROVENANCE_STATUSES` literally contained `ADVISORY_FEEDBACK_ONLY`; the old test `test_binder_status_keeps_a_verified_provenance` asserted the upgrade | every field is declared; `provenance_effective` is pinned to `PRE_RESULT_RECORD_UNVERIFIED` with `provenance_basis = DECLARED_INPUT_ONLY_GATE_PERFORMS_NO_BINDING`; `link_status`/digest are echoed as `*_declared`; `checks_by_gate` names the four unrun checks | `test_wp10_declared_trust` (19) |
| 2 | the gate cache key ignored `run_feedback`, so a second call with a different judged Run was answered from the first call's payload | real MCP stdio trial: scenarios C and C2 returned `COMPETING_EXPLANATIONS_SPLIT` (A's answer) instead of the record-level situations | `gate_fingerprint` includes a canonical, bounded `run_feedback`; `CASE_GATES_VERSION` 1.1 → 1.2 | `GateCacheKeyTests`, `GateCacheBehaviourTests`, `audit/wp10/mcp_trial.py` |

### Result naming (no scientific claim from a declared list)

| Before | After | Advice |
| --- | --- | --- |
| `VALID_NEGATIVE_RESULT` | `DECLARED_NEGATIVE_RESULT_UNVERIFIED` | same action (`REASSESS_FAILED_PREMISE_AND_ALTERNATIVES`), now prefixed with "verify the Run record first" |
| `situation` had no scope | `kind_scope=DECLARED_ONLY`, `verification=NOT_VERIFIABLE_AT_GATE`, `prediction_verification_performed=false` | unchanged action set, `author_decision_required=false` |
| `prediction_verification_reported_by_binder` (derived from caller JSON) | removed | — |

### v1.14 rule check (offline, read-only worktree at `d4056fc`)

| Item | v1.13 → v1.14 | Adapter status |
| --- | --- | --- |
| H3/H4 decision style | added `AUTHOR_QUESTION_SELECTION` / `AUTHOR_EVIDENCE_PATH_SELECTION` | already author selections in `staged_selection`; no change |
| H5 | renamed "final question" → draft confirmed with H6 | adapter never asks H5 separately; H6 plan carries it |
| H6 `reopen_when` | now says original-vs-simple algorithm selection and in-scope DEV stay autonomous | **real conflict fixed**: `CORE_ALGORITHM_CHANGE` removed from the H6/H8-triggering signal set; `DATA_SCOPE_CHANGE` and `SCIENTIFIC_QUESTION_CHANGE` still trigger |
| H3/H4/H6 binding | `requires_distinct_post_card_user_messages`, H6 binds H3+H4 | `validate_upstream_choices` already rejects duplicate message refs and H6 requires `("H3","H4")` |
| H8, SEALED, writing, figures, confirmation | unchanged text in both versions | untouched |

### Unverified in this round

1. `PRESERVATION_UNVERIFIED` for the "retrieval/declaration/hash/CI is not proof"
   sentence: it exists only in original user messages, not in a rule file.
2. The P1 A/B/C trial used a **scripted MCP client**, not a language model. It
   proves the interface; whether a model follows the Skill and calls
   `to_run_feedback` instead of hand-writing the object is `NOT_MEASURED`.
3. Token and wall-clock cost: characters are recorded, tokens are `NOT_MEASURED`.
4. Research gain from the clarified boundary: `NOT_MEASURED`.

## ARCH-CLOSEOUT — a cache key may not be shorter than its input (2026-11-20)

Baseline `cca068f` (v0.9.5, PR #19). This round touched two functions'
inputs in `case_gates.py`; no rule, tool, permission, H-node, payload shape or
`next_actions` type changed.

| # | Defect | Evidence it was real | Fix | Test |
| --- | --- | --- | --- | --- |
| 1 | `gate_fingerprint` hashed `run_feedback` clipped to 900 chars and a derived `evidence_declaration` string clipped to 500, so two **legal** declarations (`MAX_TEXT_CHARS` = 1200) that differed past the clip shared one key and the second call was served the first call's cached advisory | reproduced before any change: a 1033-char `run_feedback` differing only in its last field produced the same digest; an 8-ref declaration differing in `outcome_class` produced the same digest. Over stdio, a declared `ENGINEERING_FAILURE` was answered with `VALID_SCIENTIFIC_NEGATIVE` and `cache_hit=true` | digest built from `_fingerprint_inputs` (every field, plus a structured declaration); `FINGERPRINT_DISPLAY_CLIP` + `_fingerprint_display` produce the returned basis only; `CASE_GATES_VERSION` 1.2 → 1.3 | `test_closeout_fingerprint` (7), `test_a_changed_declaration_tail_is_not_answered_from_cache` |
| 2 | `triage_anomaly` echoed a declared `VALID_SCIENTIFIC_NEGATIVE` even when the same call declared a Run state that cannot support it, so one payload said "valid scientific negative" while its first next action said "find the real Run record first" | reproduced over stdio with `validity=INVALID`: `category=VALID_SCIENTIFIC_NEGATIVE`, `situation=EXECUTION_UNVERIFIED` | `_declared_category_conflict` is a pure declaration cross-check (no file read, no approval): `category` stays declared, `category_effective` becomes `UNKNOWN`, `status` becomes `UNKNOWN`, and the reason is listed. The other three classes are untouched | `test_closeout_t1_triage` (6) |

### Preservation in this round

| Requirement | Status | Evidence |
| --- | --- | --- |
| H3/H4/H6/H8 + H7 in-scope DEV autonomy | unchanged | full suite 488/488 under the v1.13 root (`68e29c3`) **and** the v1.14 read-only worktree (`d4056fc`); `V114BoundaryTests`, `test_h6_plan_selection`, `test_v061_history` |
| SEALED, source tiers, `as_of`, DEV/VAL isolation | unchanged | `test_wp9_*`, `test_science_feedback_link`, `SealedBoundaryUnchangedTests` |
| CLI / MCP surfaces | unchanged: 24 tools, profiles 11/21/24, no tool added | `test_mcp`, stdio trial reports 21 tools under `research` |
| `next_actions` / `status` names | unchanged for every non-contradictory input | `case_decision_eval` 10/10, `case_gate_eval` 17/17 |
| Original research data, Runs, STATE, `CASE_LIBRARY`, frozen A/B/C | untouched | `case_gate_eval` library digest before = after; `git status` |

### Unverified in this round

1. **A real model session was not run.** `~/.workbuddy/mcp.json` still declares
   the stdio server, but this session exposes no `pd-rw-research` tools and the
   connector list is empty, so no LLM tool call could be made. The three
   scenarios were driven by a scripted stdio client (`audit/closeout/mcp_trial.py`);
   that proves the interface, not that a model calls the tool or follows the
   Skill. `REAL_LLM_END_TO_END = NOT_MEASURED (BLOCKED_BY_HOST_TOOL_MOUNT)`.
2. Token and wall-clock cost in a real conversation: `NOT_MEASURED` (character
   counts are recorded; the cache hit is 5.8 ms vs 11.4 ms server-side only).
3. Research value of the two fixes: `NOT_MEASURED`. Fix 1 removes a wrong
   advisory; it does not by itself improve a research decision.
4. `PRESERVATION_UNVERIFIED` is unchanged: "retrieval / hash / CI is not proof"
   still exists only in original user messages.

## SCIENCE-01 — candidate value, novelty and identifiability (2026-11-20)

Baseline `d1ca67f` (v0.9.6). One new read-only module (`science/candidate_review.py`) and one
CLI subcommand. No rule, H-node, permission, MCP tool, profile count, `next_actions` shape or
existing payload changed. The authoritative science rules stay in PD-RW
`HIGH_VALUE_RESEARCH_DESIGN.md` / `SEARCH_DISCOVERY.md`; this round adds a check on the
*candidate card*, not another process.

### Measured defect

| # | Defect | Evidence it was real | Fix | Test |
| --- | --- | --- | --- | --- |
| 1 | At H3 the only checks were card *shape* and author-choice binding (`staged_selection.review_early_choice` has no science check), and the H6 heuristic (`_declared_evidence_warnings`) fires on the literal string `UNKNOWN`. A confident card therefore passed untouched, while an honest card was the one penalised | six frozen cards reconstructed from CASE-10/11/14/21 and INT-SUCCESS-01/05: H3 science findings **0/6**; H6 with `SUPPORTED_BY_METADATA` **0/6**; H6 with `UNKNOWN_NEEDS_PROBE` **6/6** and one identical warning set (zero discrimination) | `candidate-review` cross-checks eight declared relations (named nearest gap, knowledge gain vs replication, truth independence, evaluation unit, discriminating prediction, confirmation independence, confounders, prediction-time inputs); findings carry the rule, the library precedent and the cheapest check | `test_science01_candidate_review` (25); `evals/science_value_eval.py` |
| 2 | The four defect types had no machine-checkable statement, only prose in the rules: novelty from a search miss (CASE-14), replication reframed as knowledge (CASE-21), proxy/model-generated truth declared independent (CASE-10), rows counted as N (CASE-11) | the frozen cards pass `early-review` structurally while a human reads them as the same historical failures | each becomes a finding code with a declared-vs-declared contradiction (`DECLARED_CONFLICT`) rather than a score | `HistoricalDefectTests` (7), `RevisionLoopTests` (2) |

### Measured comparison (same six cards, no model)

| | v0.9.6 checks | candidate review |
| --- | --- | --- |
| Historically defective cards flagged | 0 / 4 | 4 / 4 |
| Defect localised to the right relation | 0 / 4 | 4 / 4 |
| Historically successful cards left clean | n/a (no signal) | 2 / 2 |
| Payload for the six cards | 6 152 chars | 8 559 chars |

### Preservation in this round

| Requirement | Status | Evidence |
| --- | --- | --- |
| H3/H4/H6/H8 + H5-with-H6 + H7 in-scope DEV autonomy | unchanged; no new author node | full suite 513/513 under the v1.13 root (`68e29c3`) **and** the v1.14 worktree (`d4056fc`); `V114BoundaryTests`, `test_h6_plan_selection` |
| SEALED, source tiers, `as_of`, DEV/VAL isolation | unchanged | `test_wp9_*`, `test_science_feedback_link`, `SealedBoundaryUnchangedTests` |
| MCP surface | 24 tools, profiles 11/21/24, no tool added; the new check is CLI-only | `PROFILE_TOOLS`, `test_mcp`, `case_decision_eval` V9 live stdio |
| Existing payloads | unchanged: `case_decision_eval` V1/V2/V3 stay 15 512 / 12 824 / 15 787 chars | `case_decision_eval` 10/10 |
| Case gate behaviour | unchanged | `case_gate_eval` 17/17 guardrails |
| Original research data, Runs, STATE, `CASE_LIBRARY`, frozen protocols | untouched; cases were read only, no Run re-executed | `git status`, library digest before = after |

### Unverified in this round

1. **No real model session.** The Skill is installed (`0.9.7`, byte-identical) and the stdio
   server starts, but this session exposes no `pd-rw-research` tool and the connector list is
   empty. `REAL_LLM_END_TO_END = NOT_MEASURED (BLOCKED_BY_HOST_TOOL_MOUNT)`. The protocol is in
   `audit/science01/REAL_SESSION_PROTOCOL.md`.
2. **The six cards are reconstructions**, written from CASE_LIBRARY premises. They are not
   verbatim model output and not an expert-labelled benchmark; they test whether a documented
   defect is surfaced.
3. **Research value is `NOT_MEASURED`.** A surfaced question is not a better question. The
   v0.9.7 → 0.9.6 difference measured here is instrumentation, not scientific output.
4. **Passing the review is not validity.** A card can be written to satisfy all eight relations;
   `score_provided`, `scientific_truth_verified`, `automatic_go` and `automatic_stop` are always
   false, and the CLI exits 3.
5. Token/wall-clock cost in a real session: `NOT_MEASURED` (character counts only).

## SCIENCE-02 — holdout candidate paths and probe contradictions (2026-11-20)

Baseline `0d2cd63` (v0.9.7). Three additive changes: two vocabulary entries in
`candidate_review`, three declaration-level outputs in `decision.assess_proposal`, and an
empty frontier in `probe_frontier` when no probe discriminates. No rule, H-node, permission,
MCP tool, profile count or `next_actions` shape changed; `assess_proposal` and
`candidate_review` keep every existing key.

### Measured defects

| # | Defect | Evidence it was real | Fix | Test |
| --- | --- | --- | --- | --- |
| 1 | The candidate card could not represent a theory or a simulation: `evaluation_unit` was a closed experimental set and `truth_kind` had no analytic option, so both legal PD-RW paths failed **validation** (`CANDIDATE_CARD_INVALID`, exit 2) before any review | two cards written from legal directions (`INSTANCE` over problem instances, `REPLICATE` over simulation runs): represented 0/2 before, 2/2 after | `ANALYTIC_DERIVATION` truth kind; `INSTANCE`/`REPLICATE` independent units; a null count stays `NOT_DECLARED` | `test_science02_candidate_paths` (8) |
| 2 | A probe whose `comparison_reference` was a test-label oracle sat on the declared frontier as the cheap option | `PA-01` (`ORACLE_OFFSET_REMOVAL_DEV_VAL_LABELS`) returned no finding, `frontier=[PA-01]` | `REFERENCE_NOT_LEGAL` with CASE-02/CASE-12 precedent | `test_science02_probe_design` (11) |
| 3 | A probe could count `WINDOW` as its evaluation unit while `group_independence` was declared PASS, and the precheck kept a clean `review` | `PB-01` returned `SOURCE_NOT_VERIFIED`, no finding, `pair_count=1` | `PROBE_UNIT_NOT_INDEPENDENT`, and the precheck's `review` becomes `DECLARED_CONFLICT` (never verified) | same file |
| 4 | When no probe separated any hypothesis pair, the frontier still named the cheapest one — i.e. it recommended an experiment that could not change the judgment | `PC-01` (two probes, all predictions `UNKNOWN`) returned `frontier=[PC-01-A]`, no `no_decisive_probe` field | `no_decisive_probe` + empty frontier + the question to answer | same file |

### Holdout, not the development cards

Six cards reconstructed from cases **not** used to build the review (CASE-12/13/17,
INT-SUCCESS-03/04, EXT-N06); labels are the library's documented verdict.

| | 0.9.6 checks | 0.9.7 candidate review |
| --- | --- | --- |
| Documented defect surfaced | 0 / 3 | 3 / 3 (primary flag in all three) |
| Historically successful direction kept clean | no signal | 3 / 3 |
| Non-experimental direction representable | n/a | 2 / 2 after, 0 / 2 before |

### Preservation in this round

| Requirement | Status | Evidence |
| --- | --- | --- |
| H3/H4/H6/H8 + H5-with-H6 + H7 in-scope DEV autonomy | unchanged; no new author node | full suite 532/532 under the v1.13 root (`68e29c3`) **and** the v1.14 worktree (`d4056fc`) |
| SEALED, source tiers, `as_of`, DEV/VAL isolation | unchanged | `test_wp9_*`, `test_science_feedback_link` |
| MCP surface | 24 tools, profiles 11/21/24, no tool added | `PROFILE_TOOLS`, `case_decision_eval` V9 live stdio |
| Existing payloads | unchanged: V1/V2/V3 stay 15 512 / 12 824 / 15 787 chars | `case_decision_eval` 10/10; `case_gate_eval` 17/17 |
| A legal direction must not be eliminated by a form check | theory/simulation now representable; a finding stays a question | `test_the_unit_vocabulary_is_extended_not_opened` |
| Original research data, Runs, STATE, `CASE_LIBRARY`, frozen protocols | untouched | `git status`; library digest unchanged |

### Unverified in this round

1. **No real model session.** The host check was run once: `~/.workbuddy/mcp.json` declares the
   stdio server and the installed Skill is `0.9.8`, but this session exposes no
   `pd-rw-research` tool and `list_installed_plugins` returns no connectors. No reinstall was
   attempted. `REAL_LLM_END_TO_END = NOT_MEASURED (BLOCKED_BY_HOST_TOOL_MOUNT)`. Everything
   above is deterministic checker output.
2. **Model behaviour is not compared.** 0.9.6 vs 0.9.7 differs by 34 lines of H3 guidance and
   one CLI; whether a model then states a named gap, a two-sided gain and an independent unit
   is `NOT_MEASURED`.
3. **The holdout cards are reconstructions** from case premises, not model output and not an
   expert-labelled benchmark. Three defective + three clean cards cannot establish a false
   positive rate.
4. **Research value is `NOT_MEASURED`.** Removing a wrong probe recommendation does not by
   itself improve a research decision.
5. Token/wall-clock cost: `NOT_MEASURED`. Character counts: clean packet 2 813 → 2 965,
   three defective packets 7 400 → 8 640.

## SCIENCE-03 — a cheap probe is not automatically decisive (2026-11-20)

Baseline `a94805c` (v0.9.8). One behavioural change in `probe_frontier` (dominance only among
eligible candidates), two additive fields in `decision.assess_proposal` (`usage`,
`blocks_decisive_frontier`) and one top-level flag (`no_legal_decisive_probe`). No required field,
no rule, no H-node, no permission, no MCP tool, no profile count, no `next_actions` shape.

### Measured defects

| # | Defect | Reproduction (before) | Fix | Test |
| --- | --- | --- | --- | --- |
| 5 | A LOW-cost probe that separated no hypothesis pair was still named as a frontier candidate, next to the MEDIUM-cost probe that did separate them | `frontier=[CHEAP-BUT-BLIND, MEDIUM-BUT-DECIDES]` | frontier contains only probes with ≥1 declared pair; the blind one becomes `exploratory_probe_ids` | `test_science03_probe_frontier_boundary` (10) |
| 6 | An oracle-referenced LOW-cost probe **dominated** the legal probe with the same pair set, so the only remaining candidate was the illegal comparison | `frontier=[ORACLE-UPPER-BOUND]`, `dominated=[LEGAL-SPECIMEN-PROBE]` | `REFERENCE_NOT_LEGAL` disqualifies from dominance and from the frontier; the probe stays as `diagnostic_upper_bound_ids` | same file |

`PROBE_UNIT_NOT_INDEPENDENT` deliberately does **not** disqualify: a `WINDOW`/`FRAME` unit adds
`needs_unit_verification_ids` and `usage: VERIFY_INDEPENDENT_UNITS_FIRST`, and stays a candidate.

### Real-session evidence (not a benchmark)

One real WorkBuddy session, two existing DEV projects, no download, no fitting, no SEALED read.
MCP `pd-rw-research` was still not mounted (recorded once, not reinstalled); the model used the
existing `science.cli decision` path. Full trace: `audit/science03/SCIENCE-03-v0.9.9-2026-11-20.md`.

| Case | Original plan (from the record) | Model-revised plan | Checker contribution |
| --- | --- | --- | --- |
| MCS-HEMO-26 | request fitting authorisation for a "fair baseline" against CNAP-derived SBP | zero-fit subject-level cross-session ICC + motion control, because the reference layer is same-source | blind doc check moved to `exploratory`; `RECORD` unit flagged against declared group independence |
| RCT-CONTACT-26 | DEV-only frame-level slope invariance (already closed) + controlled press needing new truth | split: sensor-swap contrast now, external-modulus press only for the material claim; third explanation (pseudo-label circularity) added | the cheap DEV-only probe dominated the decisive press — a limit, reported below |

### Preservation in this round

| Requirement | Status | Evidence |
| --- | --- | --- |
| H1–H10, H5-with-H6, H7 in-scope DEV autonomy, SEALED, source tiers, `as_of`, DEV/VAL | unchanged; no new author node, no new stop | full suite **534 passed / 8 skipped**; `case_gate_eval` 17/17 |
| Existing payloads | V1/V2/V3 unchanged: 15 512 / 12 824 / 15 787 chars | `case_decision_eval` 10/10 |
| MCP surface | 24 tools, profiles 11/21/24, none added | `PROFILE_TOOLS` |
| Probe is never deleted, only re-labelled | `exploratory` / `diagnostic_upper_bound` / `unit_verification` keep the candidate visible | `test_a_pilot_is_still_available_but_not_called_decisive` |
| Research data, Runs, STATE, `CASE_LIBRARY`, frozen protocols | read-only | `git status`; no file written under any project root |

### Unverified in this round

1. **A cheap but already-executed probe can still dominate a decisive expensive one.** Measured on
   a real packet: the packet has no "already closed" field, so the frontier compares declared pairs
   and cost only. Fixing it needs a new field; not done under "minimal necessary".
2. **A same-source reference is not caught.** `REFERENCE_NOT_LEGAL` matches test-time truth/oracle,
   not "NIBP is the same device's waveform" and not pseudo-label circularity. Both stayed model
   judgments, as in v0.9.8 risk 4.
3. **No baseline field.** A strong simple baseline (`PAT_foot` 0.823, depth-only) can only be stated
   in prose; it is not machine-checked (the CASE-13 layer).
4. **Single session, not blind.** The model had just written the patch and knew the new fields; no
   second arm, no independent packet author. "The model designs better experiments" is
   `NOT_MEASURED`; what is measured is one trace with its artifacts.
5. Token, real experiment cost, scientific value, MCP integration: `NOT_MEASURED`.

## SCIENCE-03B — an experiment that already ran is not a next action (2026-11-20)

Baseline `c6e045e` (v0.9.9), branch `science/03b-dev-loop`. One optional per-probe field
(`prior_execution`), two per-probe codes (`applicability`, `next_action`), eight additive ID lists
and one new flag (`no_executable_next_probe`). No required field, no rule, no H-node, no permission,
no MCP tool, no profile count, no `next_actions` shape, no new ledger.

### Measured defect

| # | Defect | Reproduction (before) | Fix | Test |
| --- | --- | --- | --- | --- |
| 7 | A LOW-cost probe that had already answered the premise stayed on the frontier **and dominated** both live probes | `frontier=[R1-DEV-SLOPE]`, `dominated=[R2-CONTROLLED-PRESS, R3-SENSOR-SWAP]` | `HISTORICAL_EVIDENCE_ONLY` — excluded from dominance and from the frontier | `test_science03b_probe_applicability` (12) |
| 8 | An INVALID run was still recommended as the next experiment | `frontier=[R1-INVALID-TRANSFORM]` | `TARGETED_REPAIR`, with `REPAIR_NAMED_DEFECT_FIRST` | same file |
| 9 | A caller-declared closure with no Run reference was silently treated as fresh | `frontier=[R1-DECLARED-CLOSED]` | `CLOSURE_DECLARED_NOT_VERIFIED` + `EXECUTION_DECLARED_NOT_VERIFIED` finding: verify, do not accept, do not rerun | same file |

`INCONCLUSIVE` continues only with named `new_information`; `requires_new_authorization` keeps the
probe as a candidate without claiming it is executable; a closure under another `premise_id` does not
close this one.

### Three-way comparison on frozen historical decisions

Same packet, same evidence, three checkers. Reviewer was a separate session, labels A/B/C shuffled
per task, told that more fields ≠ more correct.

| Task (decision time) | v0.9.6 | v0.9.9 | 0.9.10 | Blind pick |
| --- | --- | --- | --- | --- |
| MCS-HEMO-26 (02c) | `MCS-P1-CROSS-SESSION-ICC` | same | none: P1 historical, P3 needs authorization | 0.9.10 |
| RCT-CONTACT-26 (V1-R) | `RCT-P1-DEV-SLOPE-RERUN` | same | none: P1+P2 historical, P3 needs authorization | 0.9.10 |
| PoPu-48 (after RUN-004) | `POPU-P1-POSTURE-VARIANTS` + P2 | same | `POPU-P2-RELIABILITY-GATE` only | 0.9.10 |

The reviewer's own reasons: P1 in MCS "cannot be estimated at n=3/4 and the reference is same-source";
P1 in RCT "already done, frame unit violates independence, 0/979 determinable, exceeds zero-fit
authorization"; P1 in PoPu "already negated by RUN-004, pure repetition". It also flagged that the
0.9.10 arm was the *least* verbose in T3 yet the most correct — i.e. field count is not the signal.

### Real DEV loop (project 48 PoPu)

Protocol frozen before fitting: `PROTO-POPU-RELIABILITY-v5-DEV005` + two amendments (training-set
alignment; seeding and a measured jitter baseline). `RUN-005`: **NEG**, failure is not predictable
beyond predicted magnitude (AUC R1−R0 = −0.088 raw / −0.102 dropall, CIs excluding 0; selective MAE
worse by 0.60; oracle ceiling 5.44 vs 8.63 MAE at 70 % coverage). 123.5 s CPU, no download, no
SEALED, no new truth.

Defect found by the pre-registered anchor rule, not by inspection: RUN-001–004 never seeded HGB, and
with ~49.5 k training rows sklearn enables early stopping on a random 10 % validation split, so the
same fold re-runs to a MAE that differs by 0.27 on average (0.48 on one fold). RUN-004's recorded
numbers therefore cannot be reproduced bit-exactly, and its decisive effect (M3−M1 = −0.059 raw) is
smaller than that jitter. Its verdict stands (that CI already spanned zero); its precision does not.
Recorded as `PROJECT-48-DEFECT-005`; historical files untouched.

### Preservation in this round

| Requirement | Status | Evidence |
| --- | --- | --- |
| H1–H10, H5-with-H6, H7 in-scope DEV, SEALED, source tiers, DEV/VAL/SEALED | unchanged; no new author node, no new stop | full suite **546 passed / 8 skipped**; `case_gate_eval` 17/17 |
| Existing payloads | V1/V2/V3 unchanged: 15 512 / 12 824 / 15 787 chars | `case_decision_eval` 9/10 (V9 skipped: `mcp` SDK absent in this checkout, same on baseline) |
| MCP surface | 24 tools, profiles 11/21/24, none added | `PROFILE_TOOLS` |
| Old packets | no `prior_execution` → byte-compatible behaviour | `test_a_packet_without_execution_fields_behaves_as_before` |
| Historical Run files, raw archive, STATE of other projects | read-only | `verification.json` hashes before/after; MCS/RCT mtimes unchanged |

### Unverified in this round

1. **One loop, one project, negative.** The DEV loop proves the machinery works end to end; it does
   not prove the agent picks *good* experiments. The reliability probe was a defensible open question
   and it came back negative.
2. **The three-way comparison is deterministic-only.** No historical LLM session was re-run; the
   "arms" are checker outputs on frozen packets. Model behaviour is measured once, in the single
   unblinded session of Part 2 — `NOT_MEASURED` as a general claim.
3. **Blinding is imperfect.** Labels were shuffled, but a richer output can be guessed as newer.
4. **`run_ref` is a string, not a verified link.** `status_verified` means "a reference was cited",
   not "the Run was read". Cross-checking it against `feedback_link`/Run integrity is not wired.
5. Token, paid compute, real experiment cost, MCP integration: `NOT_MEASURED`.
