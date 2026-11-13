# PD-RW-Agent

**Research agent integration for WorkBuddy, powered by the existing PD-RW workflow.**

> Status: **v0.4 read-only runtime + MCP foundation** — installable shared Python library, 5 read-only MCP v2 tools, CLI parity, the original Skill and legacy standalone helpers. WorkBuddy on-device behavior and trusted enforcement are NOT yet validated.

## Purpose

PD-RW-Agent makes an existing research project easier for an AI agent to **find, resume, route, and hand off**. It does **not** redefine scientific rules. [Problem-Data-Research-Workflow](https://github.com/phr-devil/Problem-Data-Research-Workflow) remains the sole authority for scientific workflow, review/authorization, DEV/SEALED boundaries, writing gates, and evidential standards.

## v0.4 Python Runtime + MCP

The **primary** installation and WorkBuddy MCP configuration are documented in [docs/RUNTIME_AND_MCP.md](docs/RUNTIME_AND_MCP.md). The shared service is `src/pdrw_agent/service.py`, called by the Python CLI and MCP server. No API subscription is required for these local tools.

```powershell
py -3.11 -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -e ".[mcp]"
```

Use a private `project-map.local.json` and set `PDRW_AGENT_CONFIG` and `PDRW_WORKFLOW_ROOT`; never commit local data.

## Original v0.2 helpers (compatibility)

1. Clone this repository and PD-RW into separate local folders.
2. Copy `config/project-map.example.json` to **`project-map.local.json`** and replace the illustrative project paths with *verified* local paths. The local file is git-ignored.
3. Run the read-only helper:

```powershell
python skills/pd-rw-research/scripts/bridge.py doctor --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
python skills/pd-rw-research/scripts/bridge.py resume --project-id "example-project" --project-map "./project-map.local.json" --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
python skills/pd-rw-research/scripts/context.py route --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
```

4. In WorkBuddy, install/import `skills/pd-rw-research/` as a Skill (or package it with `python tools/package_skill.py`). See [WorkBuddy Skill documentation](https://open.workbuddy.cn/docs/skill).
5. Try: **“按 PD-RW 恢复 example-project，并指出下一项已授权的工作。”** Verify the output against the original project evidence and authorization.

## Repository map

| Location | Responsibility |
| --- | --- |
| [skills/pd-rw-research/SKILL.md](skills/pd-rw-research/SKILL.md) | **Only Skill entry**: trigger, boot, recovery, rule routing, execution boundaries, handoff |
| [skills/pd-rw-research/references/](skills/pd-rw-research/references/) | Read only when needed: integration, execution, troubleshooting |
| [skills/pd-rw-research/scripts/bridge.py](skills/pd-rw-research/scripts/bridge.py) | Read-only `doctor` and `resume` JSON commands |
| [skills/pd-rw-research/scripts/context.py](skills/pd-rw-research/scripts/context.py) | Legacy live rule routing and advisory/delivery checker wrappers |
| [src/pdrw_agent/](src/pdrw_agent/) | Shared Python runtime: explicit registered projects, rules, evidence, memory, dedup |
| [src/pdrw_agent/integrations/mcp_server.py](src/pdrw_agent/integrations/mcp_server.py) | Five bounded read-only MCP v2 tools |
| [docs/RUNTIME_AND_MCP.md](docs/RUNTIME_AND_MCP.md) | Windows setup, CLI usage and WorkBuddy stdio configuration |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Delivery stages, acceptance criteria and explicit non-goals |
| [config/project-map.example.json](config/project-map.example.json) | Example only; actual project paths kept locally |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Boundaries, extension points, limitations |
| [tests/](tests/) and [evals/](evals/) | Deterministic checks and scenarios for real Agent evaluations |
| [docs/DECISION_COVERAGE.md](docs/DECISION_COVERAGE.md) | Prior effective design decisions, mapped to their single existing owner |
| [docs/WORKBUDDY_ACCEPTANCE.md](docs/WORKBUDDY_ACCEPTANCE.md) | On-device acceptance protocol (not yet measured) |

## Design invariants

- **Single source of truth:** scientific policy lives in PD-RW; scientific evidence lives in actual project artifacts.
- **Progressive disclosure:** read `SKILL.md`, then the relevant project's snapshot and PD-RW `AGENTS.md`; fetch other material only for the current task.
- **No phantom memory/authorization:** a summary, status file, static validator, or Skill text cannot prove real user permission or scientific validity.
- **No hidden side effects:** the shipped bridge only reads paths, local files, and Git HEAD; it never downloads data, trains, edits research files, or accesses SEALED.
- **Small changes:** update one owner, one caller, and focused tests. No new approvals, research phases, duplicate records, or multi-agent orchestration just for architecture.

## Tests

```powershell
python -m unittest discover -s tests -v
python tools/package_skill.py
```

Packaging creates `dist/pd-rw-research.zip` for import; **do not commit project data, user conversations, credentials, or authorization logs**.

## Current limits

Git HEAD is a local version marker, **not** proof the checkout matches remote. Project mapping is an operator-supplied locator, **not** scientific identity verification. The helper does not authenticate original author permissions or enforce tool access. **`context.py action-review` may report structural ALLOW on public read-only requests, but never grants protected effects.** WorkBuddy behavior and token savings require real client-side tests; they have **not yet been measured**.

For extension guidance, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).


### Runtime status and caveats

The new `src/` runtime is canonical for **new MCP/CLI tools**; `skills/.../scripts/` remain backwards-compatible standalone read-only adapters and are not another scientific authority. Real WorkBuddy Skill selection, stdio connection, safe OS-level SEALED isolation, and any memory or token benefit remain **NOT_MEASURED** until tested on the user's own client. Local Git commit != remote freshness. A duplicate-run candidate != a reproducible/identical scientific experiment. 
