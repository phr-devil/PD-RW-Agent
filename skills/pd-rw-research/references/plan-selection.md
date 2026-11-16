# New-project H6 plan choice (on demand)

This is adapter guidance, not a second PD-RW scientific policy. Existing projects reuse legitimate original selections.

1. Read the completed launch prompt as H1/H2 scope; never repeat already-specified direction, goals, budget or exclusions.
2. AI researches H3-H5 internally. Compare at most 3 genuinely different scientific plans: precise question and Task, named nearest work or NOT_ACCESSED, official data/proof path, label truth, independent group, confounding, legal inputs, decisive inexpensive probe, risk and cost. UNKNOWN is not FAIL.
3. Show one compact H6 recommendation card and STOP dependent new-mainline work until the user *specifically* selects its displayed option or expressly delegates among shown options. A generic 'continue', old broad delegation, silence or an AI-declared APPROVED never constitutes H6 choice.
4. Bind the actual user's reply to the exact option card version. The local helper computes a SHA and checks *declarations* only. Substantive Task/question/evidence changes invalidate a prior plan choice; ordinary H7 algorithm improvements do not.
5. Record selected option, original user-message reference, card SHA, scope and allowed fallback in the existing research record when legitimately writable. No third project ledger. Do not infer new dataset downloads, SEALED, paid tools, writing or submission permission.
6. Legitimate legacy projects continue without retroactive author sign-off when their original scope is unchanged.

Optional **read-only**, installed local Python CLI:

    python -m pdrw_agent.science.cli h6-review --plan PLAN.json
    python -m pdrw_agent.science.cli h6-review --plan PLAN.json --choice CHOICE.json

PLAN.json fields: schema_version=pdrw-h6-plan-v1, scope_ref, recommended_option_id, recommendation_rationale, options (1-3); each option: id, scientific_question, core_task, dataset_or_proof_path, nearest_work_or_unknown, truth_and_independence, competing_explanation, decisive_probe, cost_and_risk, science_fit (SUPPORTED_BY_METADATA / UNKNOWN_NEEDS_PROBE / CONTRADICTED_FOR_CLAIM).

CHOICE.json fields: schema_version=pdrw-h6-choice-v1, plan_sha256, kind, original_user_message_ref, selected_option_id, allowed_option_ids, delegated_scope. USER_SELECTED requires one offered selected_option_id, allowed_option_ids=[] and delegated_scope=null. USER_DELEGATED requires selected_option_id=null, a nonempty subset of offered options, and bounded delegated_scope.

A structurally valid choice still returns DECLARED_CHOICE_UNAUTHENTICATED. Only a trusted WorkBuddy host able to independently access the user's original reply and enforce *all* dependent execution paths can make this a hard authorization boundary. Current MCP/CLI does not do so.
