# PD-RW-Agent

**Research agent integration for WorkBuddy, powered by the existing PD-RW workflow.**

> Status: **v0.1 scaffold** — read-only project discovery and resume helpers, Skill routing, and initial tests. Not a deployed autonomous executor or a trusted permission-enforcement layer.

## Purpose

PD-RW-Agent makes an existing research project easier for an AI agent to **find, resume, route, and hand off**. It does **not** redefine scientific rules. [Problem-Data-Research-Workflow](https://github.com/phr-devil/Problem-Data-Research-Workflow) remains the sole authority for scientific workflow, review/authorization, DEV/SEALED boundaries, writing gates, and evidential standards.

## Quick start (Windows / PowerShell)

1. Clone this repository and PD-RW into separate local folders.
2. Copy `config/project-map.example.json` to **`project-map.local.json`** and replace the illustrative project paths with *verified* local paths. The local file is git-ignored.
3. Run the read-only helper:

```powershell
python skills/pd-rw-research/scripts/bridge.py doctor --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
python skills/pd-rw-research/scripts/bridge.py resume --project-id "example-project" --project-map "./project-map.local.json" --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
```

4. In WorkBuddy, install/import `skills/pd-rw-research/` as a Skill (or package it with `python tools/package_skill.py`). See [WorkBuddy Skill documentation](https://open.workbuddy.cn/docs/skill).
5. Try: **“按 PD-RW 恢复 example-project，并指出下一项已授权的工作。”** Verify the output against the original project evidence and authorization.

## Repository map

| Location | Responsibility |
| --- | --- |
| [skills/pd-rw-research/SKILL.md](skills/pd-rw-research/SKILL.md) | **Only Skill entry**: trigger, boot, recovery, rule routing, execution boundaries, handoff |
| [skills/pd-rw-research/references/](skills/pd-rw-research/references/) | Read only when needed: integration, execution, troubleshooting |
| [skills/pd-rw-research/scripts/bridge.py](skills/pd-rw-research/scripts/bridge.py) | Read-only `doctor` and `resume` JSON commands |
| [config/project-map.example.json](config/project-map.example.json) | Example only; actual project paths kept locally |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Boundaries, extension points, limitations |
| [tests/](tests/) and [evals/](evals/) | Deterministic checks and scenarios for real Agent evaluations |

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

Git HEAD is a local version marker, **not** proof the checkout matches remote. Project mapping is an operator-supplied locator, **not** scientific identity verification. The helper does not authenticate original author permissions or enforce tool access. WorkBuddy behavior and token savings require real client-side tests; they have **not yet been measured**.

For extension guidance, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
