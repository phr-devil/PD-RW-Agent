# A/B/C capture template — component ablation inside one system

**Status: NOT_MEASURED.** This is a manual protocol, not a real experiment and not
an approval gate. The frozen task set, budget and grading rules for the v1.0
comparison live in `audit/agent_comparison/PLAN.md` and `RUBRIC.md`.

PD-RW-Agent is a Skill/CLI/MCP component loaded by WorkBuddy, not a second system
and not an LLM. So the arms below vary one component, not one product against
another.

Two levels, both alive:

**System level** (`audit/agent_comparison/PLAN.md`)

- `A` = ChatGPT + WorkBuddy + PD-RW rules and project records
- `B` = `A` + PD-RW-Agent (Skill, CLI; MCP where the host exposes it)
- `C` = `B` + one external agent capability (read-only feasibility so far)

**Component level** — the original ablation, now a sub-axis of `B`

- `B1` = Skill only: rules, packet format, three-tier plan, no CLI calls
- `B2` = Skill + CLI/MCP: `packet-check`, `decision`, `resume`, `context`

Use `B1` vs `B2` to ask what the executable checks add over the written rules.
Use `A` vs `B2` to ask what the component adds over the workflow as practised
without it. Do not report `B` as if it were a separate agent.

For each case/arm record privately: `CASE_ID | FROZEN_AT | AGENT_COMMIT | PD_RW_COMMIT | MODEL | TOOL_ACCESS | INPUT_TOKENS | OUTPUT_TOKENS | GPU_HOURS | WALL_TIME | HUMAN_TURNS | HUMAN_MINUTES | DECISION | NEXT_ACTION | ACTUALLY_EXECUTED | EVIDENCE_REFS | AUTH_SOURCE | INCIDENTS`.

If a metric is unavailable write `UNKNOWN`, never `0`. If permission is unverified write `UNVERIFIED`, not `APPROVED`. A planned Run is `NOT_RUN`. Use the original PD-RW `REPLAY_PROTOCOL.md` decision fields.

First blind grade for safety, future knowledge, evidence faithfulness, scientific
value of next discriminating probe, valid baseline retention, unnecessary repeated
failures, premature STOP and false GO; then unblind and compare paired actual
cost/quality. `audit/agent_comparison/RUBRIC.md` holds the 0–3 anchors.

Only genuinely time-frozen historical cases are eligible — `audit/agent_comparison/tasks/*/MANIFEST.json`
records the copy, its hashes and the exclusions. Do not count multiple seeds from
one project as independent projects; preserve user data locally, never in the
public repo.
