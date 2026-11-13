# PD-RW-Agent architecture and change contract

## Boundary: one Skill, two kinds of source

- **PD-RW** owns H1–H10 semantics, task/claim strategy, authorized DEV work, data/SEALED segregation, scientific evidence, paper/figure/writing permissions, and its own preflight/checker implementations.
- **Existing project folders** own STATE, RESEARCH_RECORD, PAPER_BLUEPRINT, immutable run evidence, scripts and data.
- **This repository** owns the WorkBuddy Skill, the shared read-only Python Runtime under `src/pdrw_agent`, CLI/MCP tool adapters, optional legacy standalone helpers, packaging and integration tests. It contains no second scientific workflow.
- A traceable inventory of prior design rationale is in [DECISION_COVERAGE.md](DECISION_COVERAGE.md); maintainers may consult it, but agents do **not** preload it.

## AI context budget

1. WorkBuddy discovers the Skill through YAML `description`.
2. When triggered, read the short `SKILL.md`.
3. Resolve a single project; inspect only its current snapshot and state index.
4. Read PD-RW `AGENTS.md` and the **one relevant authority document**; follow references on demand.
5. Read original evidence and permission only to the depth needed for the next action.
6. Preserve existing state and provide a concise output; do not echo the full context.

## Stable interfaces

| Interface | Producer | Consumer | Guarantee |
| --- | --- | --- | --- |
| Skill YAML + `SKILL.md` | This repository | WorkBuddy Skill loader | Trigger and documented workflow, not automatic compliance |
| `bridge.py doctor` | This repository | WorkBuddy terminal | Local rule-file existence and local HEAD only |
| `bridge.py resume` | This repository | WorkBuddy terminal | Explicit project paths, bounded snapshot, machine/Markdown STATE index, no edits |
| `context.py route` | Current PD-RW AGENTS.md | WorkBuddy terminal | Existing routing labels/file pointers; **not** duplicate science policy |
| `context.py action-review` | PD-RW `core.execution_preflight` | WorkBuddy terminal | Advisory declaration check; no real authorization |
| `context.py delivery-review` | PD-RW `core.delivery_check` | WorkBuddy terminal | Existence/path-only verification; no content/SEALED clearance |
| `project-map.local.json` | Operator's local machine | `bridge.py` | Locator only, not identity/auth verification |
| `AGENTS.md` / `WORKFLOW.md` | PD-RW | Research Agent | Scientific routing and decision authority |
| Run/protocol and original messages | Research project/user | Research Agent | Primary evidence and real authorization, independently checked |

## What is not implemented in v0.4

- No automatic syncing of PD-RW Git checkout, shell/task orchestration, or independent API model calls.
- No writing of project state or claims by the supplied bridge.
- No tool interceptor, sandbox, OS ACL or authentic original-user authorization service.
- No real WorkBuddy end-to-end acceptance tests or measured Token/quality improvement. See [WORKBUDDY_ACCEPTANCE.md](WORKBUDDY_ACCEPTANCE.md) and [RUNTIME_AND_MCP.md](RUNTIME_AND_MCP.md).

## Adding a capability without increasing confusion

1. Decide if it is scientific policy (edit **PD-RW**), tool integration (add a script here), or operational guidance (add a narrow reference here).
2. Reuse existing state/logs and PD-RW checks; do not copy the original files.
3. Change `SKILL.md` only to add a short reference or trigger when genuinely necessary.
4. Add one focused automated test and, if model behavior matters, a real WorkBuddy replay scenario.
5. Report measured outcomes and remaining limitations; never equate passing CI with scientific correctness or a secure gate.

References: https://agentskills.io/ ; https://github.com/openai/skills ; https://github.com/anthropics/skills ; https://open.workbuddy.cn/docs/skill
