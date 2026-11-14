# v0.7.5 — WorkBuddy convergence contract

## Decision

Refactor only existing behavior with demonstrated agent utility; do not copy entire high-star agent platforms or add a new memory/Run database.

| Upstream examined (source) | Borrowed boundary | Our exact implementation |
| --- | --- | --- |
| [LangGraph checkpoint](https://github.com/langchain-ai/langgraph/tree/main/libs/checkpoint) | Separate resumable execution checkpoints from persistent scientific state | `runtime/recovery.py`: `scientific_context`, `operation_context`, `next_action_hint` views of existing sources |
| [Agent Skills specification](https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx) | Lightweight Skill entry and opt-in references | `skills/pd-rw-research/SKILL.md` and existing `references/` |
| [Aider repo map](https://github.com/Aider-AI/aider/blob/main/aider/repomap.py) | Bounded, relevant context instead of whole repository | Compact recovery, one project lookup and on-demand rule/audit routing; do not clone Aider's parser/cache |
| [Deep Agents](https://github.com/langchain-ai/deepagents) | Reuse the external execution harness, pluggable tools/context | WorkBuddy remains execution owner; this adapter only reports/scopes |
| [SWE-agent](https://github.com/SWE-agent/SWE-agent) and [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) | Configurable, minimal tool surface and reproducible task traces | Startup `PDRW_MCP_PROFILE`; no new executor |
| [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) | Register only callable, intentional tools | Profile-selected decorators on existing MCPServer |
| [MLflow](https://github.com/mlflow/mlflow) | Link metrics and artifacts to a declared original Run | Retain original PD-RW Run/EVENTS, no parallel tracking database |

Star counts are not a correctness guarantee. Upstreams are design comparisons, **not added package dependencies**.

## Changed behavior

1. `get_resume_context` supports `detail_level="compact"|"full"`. Python legacy default remains `full`; MCP defaults to compact. The concise response preserves status, blockers, declared state and permission uncertainty. `next_action_hint` is not an execution grant.
2. Tools are registered by `minimal`, `research` (default) or `diagnostic` selection. Sets are nested (11/17/20). A profile cannot constrain separate WorkBuddy terminal/file permissions or authenticate original grants.
3. Skill prefers a single compact resume for fresh-session continuation. Project-only lookups still use `get_project_context`; deeper audits, Run checks and original PD-RW rule reads are selective.
4. Case index matches include matched terms, `scientific_applicability=UNKNOWN` and a source-review prompt. Do not promote an index card, semantic resemblance or a summary into a validated negative/STOP.

## Validation

- Python/MCP unit tests: profile counts and diagnostic visibility; compact/full resume compatibility, incomplete-project blockers and no newly conferred authority; historical MCP wire tests explicitly use diagnostic profile.
- Manual WorkBuddy acceptance: compare three configurations on 12 representative, **time-frozen** original-source tasks (success, valid negative, invalid experiment, interrupted/identity-conflict). Match model, original source scope, author permissions and resource budget.
- Preserve full evidence provenance, prohibited SEALED access and user strategic gates. Each benchmark must record actual calls, source identifiers, result correctness, human interventions, wall time and observed token/GPU usage.
- Without the operator's client and original evidence, this repo cannot truthfully report real WorkBuddy quality/Token savings. Mark `NOT_MEASURED`, not PASS.

## Exit conditions and non-goals

Stop adding new features when source identity, safe scope routing, evidence-aware negative-case reuse and authorized DEV continuation work on real frozen tasks without unauthorized effects or quality regression. Report comparative costs, including null results.
Do **not** develop a second local GPU runner, permissions authority, vector store, training scheduler, autonomous Run writer or new subprocess host. Preserve the experimental v0.7.4 Host for diagnostics; real DEV/SEALED/authorization remains a separately gated future project only if measured need justifies it.
