# Three author choices for new PD-RW research lines (on demand)

**Authoritative:** PD-RW WORKFLOW.md / AUTHOR_STRATEGY_REVIEW.md / human_review_protocol.v1.json v1.4. This adapter describes input cards only, never grants permissions or replaces science rules. All existing v1.3 single-H6 projects retain their original scope and choice records. H1/H2 from startup are not re-asked.

## Scientific outcome

Optimize time to a **credible, high-tier (Q1 preferred; defensible Q2+ floor), widely reusable/citation-potential paper result**. Proposed direction, algorithm, question, title, or expected contribution are hypotheses and methods, not immutable success criteria. Broader citation impact is never guaranteed; check actual nearest research, authentic independent evidence, audience and reuse rationale before promising a high-impact claim.

## Three staged decisions

**H3 – choose a paper-worthy scientific question.** Agent investigates a reasonably broad opportunity pool (often 6–10 preliminary candidates, adaptive to evidence), challenges direct nearest papers, checks reality/novelty and independent truth and compares usually three different questions. Show an evidence-backed recommendation and a few alternatives; user chooses one or gives clearly bounded post-card delegation. No H4 decision without an explicit H3 reply.

**H4 – choose evidence and dataset/proof path.** Bound the H4 card to H3's selected plan SHA, original message ref and selected option/delegated scope. Compare 2–3 realistic paths, truth/group independence, confounds, license and minimum external confirmation. Require a **different post-card message**. H4 selection alone is **not** download, CPU/GPU or SEALED access permission.

**H6 – choose the paper contribution and executable Task.** Agent synthesizes H5 final-question/claim-boundary draft from H3/H4. H6 card binds *both* earlier selection refs/hashes and compares evidence-worthy algorithm, meaningful traditional-algorithm improvement, mechanism, measurement, benchmark, reliability or systems routes. Each H6 v3 option declares an **adaptive_pivot_envelope**: method and limited contribution changes that H7 may pursue without further author choice. The user selects an option in a third post-card reply; H5 is confirmed by the *same H6* reply, not a fourth separate step. Core Claim change beyond envelope triggers H8; a different core question/data route reopens H3/H4 as applicable.

All cards make the shortest credible evidence-to-paper path, strongest near-neighbor counterargument, unknowns, cost/time and realistic scholarly reuse explicit. No fixed waiting time, invented bibliography, journal acceptance forecast, citation count, or automatic negative-Run STOP.

## Candidate review before H3 (optional, advisory)

A candidate card records one question the Agent is prepared to defend. Write one per retained
candidate (1–6) and run the review before showing the H3 card:

```powershell
python -m pdrw_agent.science.cli candidate-review --cards CANDIDATES.json
```

Each card declares: `question`, `failure_premise`, `contribution_form`, `success_new_knowledge`,
`refutation_consequence`, `named_nearest` (`work/covers/remaining`), `nearest_status`,
`competing_explanations` (`explanation/predicted_observation`), `falsifier`, `truth_kind`,
`truth_source`, `truth_independent_of_input`, `prediction_time_inputs`, `evaluation_unit`,
`independent_units`, `reported_n`, `confounders` (list or `NONE_AFTER_CHECK`), `evidence_path`,
`confirmation_ref`, `confirmation_shares_evaluation_data`, `resources`.

The review cross-checks eight declared relations and returns finding codes with the rule and the
library precedent, plus one blocking question and its cheapest check per finding:
`NEIGHBOR_UNVERIFIED`/`NOVELTY_FROM_ABSENCE` (a search miss is not a gap), `REPLICATION_ONLY`
(same relation in another dataset/sensor), `KNOWLEDGE_GAIN_IS_METRIC_ONLY`,
`TRUTH_NOT_INDEPENDENT`/`DECLARED_CONFLICT` (proxy or model-generated truth claimed independent),
`UNIT_NOT_INDEPENDENT`/`UNIT_COUNT_CONFLATION` (frames counted as N), `NON_DISCRIMINATING`
(both explanations predict the same observation), `CONFIRMATION_CIRCULAR`,
`CONFOUNDERS_NOT_STATED`, `ILLEGAL_PREDICTION_INPUT`. `cross_candidate` reports candidates that
share one `failure_premise`: those are one option, not a comparison.

Answer the questions in the card, or drop the candidate. The review reads no literature, Run or
project file; `score_provided`, `scientific_truth_verified`, `automatic_go` and `automatic_stop`
are always false, and the CLI exits 3. It is not an H3 approval, not a ranking and not a
substitute for reading the nearest paper. Precedent: CASE-10, CASE-11, CASE-14, CASE-21.

## Versioned read-only card contracts

The local CLI can check **declared** fields, not user authentication:

```powershell
python -m pdrw_agent.science.cli early-review --plan H3_PLAN.json
python -m pdrw_agent.science.cli early-review --plan H4_PLAN.json --choice H4_CHOICE.json
python -m pdrw_agent.science.cli h6-review --plan H6_PLAN.json --choice H6_CHOICE.json --pd-rw-checkpoint
```

- **H3/H4** `schema_version=pdrw-early-plan-v1`, `stage=H3|H4`, `research_line_ref`, `scope_ref`, `hard_constraints_sha256`, `upstream_choices` (`{}` for H3; for H4 must contain H3), `options` (1–3), `recommended_option_id`, `recommendation_rationale`. Each option: `id`, `question_or_evidence_path`, `paper_value`, `nearest_prior`, `truth_and_independence`, `discriminating_probe`, `cost_and_risk`.
- **H3/H4 choices** `schema_version=pdrw-early-choice-v1`, `plan_sha256`, `kind=USER_SELECTED|USER_DELEGATED`, `original_user_message_ref`, `selected_option_id`, `allowed_option_ids`, `delegated_scope`. Same selection/delegation conventions as historical H6. H4 cannot reuse H3 message.
- **H6 new v3** `schema_version=pdrw-h6-plan-v3`. Retains v2 plan fields and options; adds `hard_constraints_sha256` and `upstream_choices={"H3":link,"H4":link}` to plan, and `adaptive_pivot_envelope` string to every option. Each upstream `link` has exactly `plan_sha256`, `original_user_message_ref`, and `choice` (selected option ID or bounded delegated scope). The v3 material digest binds the same HARD constraints snapshot as H3/H4, the full upstream pair and option scopes. `pdrw-h6-choice-v1` is still the H6 response schema; third message must differ from both upstream messages.
- **Legacy H6 v1/v2** plans remain readable and keep existing hashes; they cannot stand in for new v1.4 H3/H4 decisions.

All these CLIs return **exit code 3** even on a structurally valid choice declaration. A declared `APPROVED`, hash or message ref does not authenticate the original author, justify DEV admission, or authorize dataset download/SEALED/writing/figures/submission. A trusted WorkBuddy host must independently bind original messages, immutable option-card digests, source lineage, project identity and all protected action paths. PD-RW `review_new_project_choices` does the independent H3/H4/H6 *structural* check; the new DEV host preflight requires `new_project_three_choices_confirmed` supplied only after authenticated review. On missing permission, continue independently legal read-only research and preserve prior legitimate records.

Store decisions in existing RESEARCH_RECORD/STATE, linking the same research-line locator, original H1/H2 scope reference and canonical SHA-256 of original HARD constraints across H3/H4/H6. These are scope-integrity declarations, not authorization tokens; the real original constraints must be checked independently. Distinguish HARD constraints, author-approved ADAPTIVE scope and EVIDENCE whose truth can change. When new results contradict an initial algorithm route, compare a stronger paper route with nearest work and validation cost; do not call ordinary model change a new project or rewrite exploratory results as preregistered.
