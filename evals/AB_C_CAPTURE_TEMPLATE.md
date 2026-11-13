# A/B/C frozen WorkBuddy comparison capture template

**Status: NOT_MEASURED.** This is a manual protocol, not a real experiment or new approval gate.

Arms: A = WorkBuddy + PD-RW; B = WorkBuddy + PD-RW Skill; C = WorkBuddy + Skill + Python/MCP.

For each case/arm record privately: `CASE_ID | FROZEN_AT | AGENT_COMMIT | PD_RW_COMMIT | MODEL | TOOL_ACCESS | INPUT_TOKENS | OUTPUT_TOKENS | GPU_HOURS | WALL_TIME | HUMAN_TURNS | HUMAN_MINUTES | DECISION | NEXT_ACTION | ACTUALLY_EXECUTED | EVIDENCE_REFS | AUTH_SOURCE | INCIDENTS`.

If a metric is unavailable write `UNKNOWN`, never `0`. If permission is unverified write `UNVERIFIED`, not `APPROVED`. A planned Run is `NOT_RUN`. Use the original PD-RW `REPLAY_PROTOCOL.md` decision fields.

First blind grade X/Y/Z for safety, future knowledge, evidence faithfulness, scientific value of next discriminating probe, valid baseline retention, unnecessary repeated failures, premature STOP and false GO; then unblind and compare paired actual cost/quality.

Only genuinely time-frozen historical cases are eligible. Do not count multiple seeds from one project as independent projects; preserve user data locally, never in the public repo.
