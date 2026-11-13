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

## Minimal handoff

`RESULT | EVIDENCE_PATHS | TESTS_ACTUALLY_RUN | LIMITS/UNKNOWN | NEXT_LEGAL_ACTION_OR_USER_CHOICE`

This is an output guide, not a requirement to create a new handoff file or duplicate the PD-RW project's existing reports.
