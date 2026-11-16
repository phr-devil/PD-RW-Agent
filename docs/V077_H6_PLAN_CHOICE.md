# v0.7.7 — H6 plan-choice audit and implementation

## Audited root causes

- Existing H1-H6 were represented as several author decisions; the filled startup prompt already covers H1/H2, but cannot approve an undisclosed H6 plan. A machine declaration of USER_CONFIRMED is not authentic user approval.
- Existing Skill emphasized registered-project resume; new-project scientific-plan choice was not an explicit path.
- PD-RW Python checkers and current Agent MCP do not independently authenticate the user's messages or guard all WorkBuddy effects. Their checks are advisory.

## Implemented here

- New read-only hash-bound H6 plan/choice checker and opt-in local science CLI. Options carry PD-RW C/R/P classifications for compatibility with the existing H6 Task/strategy check.
- Stale plan, wrong option, unbounded delegation and malformed records fail structural checks; even well-formed declared choices remain UNAUTHENTICATED.
- Skill routes new-project user startup scope (H1/H2), Agent-led candidate assessment (H3-H5), and exactly one required specific H6 choice before dependent new-mainline work.
- No new MCP tool, experimental Run writer, autonomous GPU executor or persistent decision ledger. Existing DEV continuation and separate effect authorizations are unchanged.

## Scientific quality expectations

Before H6 compare data/claim fit, independent truth/groups, predicted confounds, known prior work, smallest discriminating probe and alternative failure premises. UNKNOWN is a cue for low-cost checking, not automatic STOP. During permitted H7 DEV start with relevant simple baselines/shortcut controls; classify invalid evidence, undertraining, comparable negatives or incompatible truth before turning or holding.

## Remaining enforcement boundary

A trusted WorkBuddy host must obtain/authenticate the actual author reply, prove it refers to the exact displayed plan, bind the real project/task scope and make all dependent execution paths call that check. Neither a digest, original_user_message_ref string, local CLI result, MCP receipt nor model text is proof of authorization. Until that integration is built and tested, this is a Skill behavioral stop plus Python diagnostic, **not** an unbypassable execution ACL.

## Verification

Run python -m unittest discover -s tests -v and python tools/package_skill.py; new H6 tests cover missing response, generic continue, changed cards, wrong options, bounded delegation, UNKNOWN and read-only CLI. Real WorkBuddy H6 bypass testing, 42/43/44 historical replay and comparative token/scientific success improvements are NOT_MEASURED.
