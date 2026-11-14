# PD-RW-Agent

> v0.7.1: Legacy/machine state diagnostics, advisory independent SHA manifests,
> protected lexical paths, private DB migrations, bounded immutable DEV
> proposal contracts, fail-closed host admission and read-only PID/start-token
> observation. Real DEV/GPU execution is still disabled.
> See docs/V071_HOST_READINESS.md for limitations and acceptance criteria.

> **v0.7.0 host execution foundation (synthetic CPU only):** strict execution
> plans, source-bound preflight, private SQLite job checkpoints, idempotent
> fixed-code synthetic subprocess and fail-closed recovery. MCP/CLI expose
> **only read-only planning/status**, never arbitrary command execution.
> Scientific DEV/GPU execution still requires a separately secured host.
> See [v0.7 contract](docs/V070_HOST_EXECUTION.md).

> **v0.6.3 source-lineage and evidenced-lessons increment:** bounded,
> non-executing Python AST feature/split-fit risk detection and optional
> linked content-hash overlap checks; original Run + science-audit + baseline
> grounded negative metric lesson matching (never an automatic STOP).
> See [docs/V063_LINEAGE_LESSONS.md](docs/V063_LINEAGE_LESSONS.md).

> **v0.6.2 scientific-evaluation checks:** bounded, hash-bound DEV/VAL
> train/evaluation sample and group overlap; real metric recomputation;
> declared-input scope and matched baseline evaluation. The new tool is
> `audit_scientific_experiment` via Python CLI/MCP. It detects specific
> falsifiable faults without attesting truth, trained-code lineage, author
> approval or official confirmation. [Contract](docs/V062_SCIENCE_VALIDITY.md).

> **v0.6.1 research integrity increment:** read-only reconstruction of machine
> STATE/EVENTS metadata, original-PD-RW-contract Run evidence checks, and
> declared negative-lesson scope comparisons, exposed via CLI/MCP. None
> authenticates approvals, validates scientific truth, or permits execution.
> See [v0.6.1 contract](docs/V061_HISTORY_RUN_LESSONS.md).

> **v0.6.0 Python state/evidence increment:** The shared CLI/MCP service
> now provides bounded, read-only `audit_project_state` diagnostics:
> registered source availability, SHA-256 manifest coverage, historical
> snapshot excerpts and local declared rule-version mismatch. This does not
> verify scientific truth or original user authorization.
> See [v0.6 contract](docs/V06_STATE_EVIDENCE.md).

**Research agent integration for WorkBuddy, powered by the existing PD-RW workflow.**

> **v0.5.3 routing adjustment:** For an explicitly registered and permitted project, an MCP-enabled WorkBuddy Skill now requests an actual bounded MCP project-context call before broad file reads; the server uses the same Python service as the CLI. This is an instruction-level routing change, **not** a guaranteed host enforcement mechanism. See [WorkBuddy MCP-first acceptance](docs/RUNTIME_AND_MCP.md#v053-workbuddy-mcp-first-routing-acceptance).

> Status: **v0.5 controlled-continuation foundation** — original 5 read-only MCP tools plus 6 scoped resume/receipt/preview/handoff tools. Only private operational receipts may be written; real PD-RW Run registration is disabled in the Agent adapter (including caller-supplied callback) pending independently secured host authorization. Actual WorkBuddy end-to-end performance remains NOT_MEASURED.

## v0.5.2 evidence-binding and negative lesson preview (optional local Python only)

Local `src/pdrw_agent/science/` helpers review **declared** competing hypotheses, classify failure types, compare exact premise/scope identities, bind cited IDs to hash-checked frozen sources, and validate/blind A/B/C replay packets. Byte matches do not prove science or historical authenticity.
**No additional MCP tools, permissions, research data writes or automatic scientific judgments.** Refer to [docs/V06_EVAL_PREVIEW.md](docs/V06_EVAL_PREVIEW.md).

```powershell
python -m pdrw_agent.science.cli decision --packet evals/examples/synthetic_decision.json
python -m pdrw_agent.science.cli lessons --packet evals/examples/synthetic_lessons.json
python -m pdrw_agent.science.cli decision --packet evals/examples/synthetic_decision.json --evidence-root evals/examples --evidence-manifest evals/examples/synthetic_case.json
python -m pdrw_agent.science.cli replay-check --root evals/examples --manifest evals/examples/synthetic_case.json
```

These examples are synthetic. Actual WorkBuddy performance, Token savings, and publishing impact remain `NOT_MEASURED`.

## Purpose

PD-RW-Agent makes an existing research project easier for an AI agent to **find, resume, route, and hand off**. It does **not** redefine scientific rules. [Problem-Data-Research-Workflow](https://github.com/phr-devil/Problem-Data-Research-Workflow) remains the sole authority for scientific workflow, review/authorization, DEV/SEALED boundaries, writing gates, and evidential standards.

## v0.5 continuation and controlled registration

See [docs/V05_EXECUTION.md](docs/V05_EXECUTION.md) for a minimal AI-oriented contract, operator setup, safe write boundary, receipt lifecycle and crash recovery.

Add `PDRW_RUNTIME_DIR` as a **private path outside the project and Git repositories** to allow non-scientific execution receipts. This is not an authorization token. It does not execute training.

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
| [src/pdrw_agent/integrations/mcp_server.py](src/pdrw_agent/integrations/mcp_server.py) | Eleven bounded MCP tools: nine read-only and two private-receipt metadata writes; no scientific record writer |
| [docs/RUNTIME_AND_MCP.md](docs/RUNTIME_AND_MCP.md) | Windows setup, CLI usage and WorkBuddy stdio configuration |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Delivery stages, acceptance criteria and explicit non-goals |
| [docs/V05_EXECUTION.md](docs/V05_EXECUTION.md) | v0.5 operator/AI contract, receipt recovery and trusted write limitations |
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
