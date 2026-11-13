# Execution and handoff adapter

Load only when a resumed task actually needs multiple tool actions, DEV iteration, or project handoff. Scientific semantics stay in PD-RW.

## The autonomous loop

1. Verify the chosen task, legal input information, original operation scope and best valid evidence.
2. Select **one** high-information next action with a distinguishable outcome and bounded cost; reuse prior runs.
3. Use the WorkBuddy-provided tools to implement within existing approved DEV scope, preserving protected artifacts and original evidence.
4. Read actual tool exit status and targeted tests/results; if a run fails, distinguish engineering failure, INVALID evaluation and a meaningful scientific negative.
5. Decide whether another different probe is informative. Stop an unchanged/low-information loop rather than producing repetitive experiments.
6. Record only important scientific events in the existing `RESEARCH_RECORD.md`, checking the associated `PAPER_BLUEPRINT.md` when affected. Do not add a parallel approval table or new research phase.
7. Deliver one principal result, exact artifacts, performed validations, scientific limitations, and one next legal action.

## Authorizations

Scientific strategy and operational permissions are separate. Use the current PD-RW `AGENTS.md`, `WORKFLOW.md`, `NEXT_ACTION_POLICY.md`, and relevant owner when those boundaries matter. Existing permissible safe, non-paid DEV technical work can proceed autonomously; do not request new approval for every ordinary run.

Reading `approved` in `STATE`, a self-written JSON packet, or a successful static preflight **does not** prove original user authorization. Current bundled scripts are **read-only**. There is **no** trusted hook preventing an unrestricted WorkBuddy shell from opening SEALED files: hard enforcement requires independent filesystem access controls or a separately trusted tool host.

## Checks and evidence

When warranted, invoke PD-RW's existing tools from its root, e.g. `python -m core.cli status --root RESEARCH_PROJECT`, `python -m core.execution_preflight action PACKET.json`, or targeted regression tests, using actual compatible inputs from PD-RW documentation. A structural ALLOW declaration is not proof of authorization, isolation, or scientific success. Never invent a run, hash, metric, or test result.

No background scheduler, persistent independent agent loop, automatic model/API bridge, or WorkBuddy runtime enforcement is shipped in v0.1. WorkBuddy's own continuation mechanisms, if available, control execution lifetime.

## Minimal handoff

`RESULT | EVIDENCE_PATHS | TESTS_ACTUALLY_RUN | LIMITS/UNKNOWN | NEXT_LEGAL_ACTION_OR_USER_CHOICE`

This is an output guide, not a requirement to create a new handoff file or duplicate the PD-RW project's existing reports.
