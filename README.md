# PD-RW-Agent

> **Current release — 0.9.8 (holdout-checked candidate paths and probe contradictions).**
> Six explicit layers (PD-RW rules · research project · Skill · Python science
> checks · service/CLI/MCP · runtime receipts), one **downgrade-only**
> projection from an evidence-linked Run to the next action, and one read-only
> **candidate review** for the question chosen at H3. No event field
> authenticates itself: `case_gate_check` reports what was claimed next to what
> it actually checked, `candidate-review` reports which declared relation is
> unstated or self-contradictory, and `decision` reports when a probe's
> reference is not a legal baseline, when its unit contradicts a declared
> independent group check, and when no candidate probe separates any hypothesis.
> Theory and simulation paths are representable (`ANALYTIC_DERIVATION`,
> `INSTANCE`/`REPLICATE`), so a form check cannot eliminate a legal direction.
> No scientific rule, H-node, permission gate or tool count changed: MCP stays
> 11/21/24, no tool was added, and the case library / Runs / frozen protocols are
> untouched.
> [Architecture](docs/ARCHITECTURE.md) · [Runtime](docs/RUNTIME_AND_MCP.md) ·
> [Preservation map](docs/DECISION_COVERAGE.md) ·
> [Feedback contract](docs/EXPERIMENT_FEEDBACK_LINK.md).
> Real research gain, Token and wall-clock savings remain `NOT_MEASURED`.

## Release notes (newest first; the release above is the current one)

> **v0.9.8 holdout and experiment-design checks:** two capabilities were tested
> on cases that were *not* used to build them (CASE-12/13/17 and
> INT-SUCCESS-03/04, EXT-N06): the candidate review hit 3/3 documented defects
> with 0 false positives on the 3 successful directions, while both
> non-experimental directions were rejected **before** the fix because the card
> could not express a proof or a simulation replicate. `assess_proposal` now
> reports `REFERENCE_NOT_LEGAL`, `PROBE_UNIT_NOT_INDEPENDENT` and
> `no_decisive_probe`; previously a probe whose reference was a test-label oracle
> sat on the "cheap" frontier, windows counted as independent units while
> `group_independence` stayed PASS, and a packet where nothing separated anything
> still named a probe to run. No score, no ranking, no new approval.

> **v0.9.7 candidate review (science capability, not new process):** at H3 the
> only checks were card *shape* and author-choice binding, and the H6 warning
> heuristic fired on the literal string `UNKNOWN` — so a confident card claiming
> "no prior work, F1 improves, 29 279 frames" passed with zero warnings, while an
> honest card was the one that got flagged. `science.cli candidate-review`
> cross-checks eight declared relations (named nearest gap, knowledge gain vs
> replication, truth independence, evaluation unit, discriminating prediction,
> confirmation independence, confounders, prediction-time inputs) and returns
> the rule, a library precedent and the cheapest check per finding. It provides
> no score, no GO/STOP, reads no literature or Run, and exits 3. On six frozen
> cards reconstructed from CASE-10/11/14/21 and INT-SUCCESS-01/05 it surfaces
> 4/4 documented defects that v0.9.6 did not flag, and leaves both historically
> successful directions clean. **Model behaviour and research value are
> `NOT_MEASURED`.**
>
> **v0.9.6 bounded-input cache key (freeze candidate):** the gate fingerprint
> hashed only the first 900 characters of `run_feedback` and the first 500 of a
> derived evidence declaration. Two *legal* declarations that differed later
> therefore shared one key, and the second call was answered from the first
> call's advisory — a declared `ENGINEERING_FAILURE` came back as
> `VALID_SCIENTIFIC_NEGATIVE`. The digest now covers the complete bounded input
> (the event validator already caps each field at 1200 characters and the event
> at 20 fields); clipping survives only in the returned, human-auditable basis.
> A T1 declaration of a valid negative that contradicts its own declared Run
> state is still echoed as `category`, but reported as
> `category_effective = UNKNOWN`. `CASE_GATES_VERSION` 1.2 → 1.3. No tool,
> rule, permission, H-node or `next_actions` shape changed: MCP stays 11/21/24.
> Scripted stdio calls confirm both fixes; **a real model session was not
> available in this round**, so model adherence, Token cost and research gain
> remain `NOT_MEASURED`.

> **v0.9.0–v0.9.3 (summary):** evidence-linked probe feedback, a judged-Run
> next action, separate pre-decision/post-Run case timing, a strict `as_of`
> historical view for replay, and the `pdrw-probe-feedback-link-v1` contract.
> Details are in the tagged commits and `docs/EXPERIMENT_FEEDBACK_LINK.md`;
> the individual notes are not duplicated here.

> **v0.8.1 lean scientific autonomy:** The WorkBuddy Skill now explicitly preserves five root boundaries while restoring first-Pilot tolerance, meaningful narrow findings, fair traditional-method improvements, positive and negative lesson reuse, selective rule loading, no automatic project STOP and evidence-first paper closure. No new hard gates or permissions. Real research gains remain **NOT_MEASURED**. [Skill](skills/pd-rw-research/SKILL.md) · [Research guidance](skills/pd-rw-research/references/research-leverage.md).

> **v0.8.0 publication-first three-choice startup (historical behavior):** New PD-RW v1.4 projects require independent author H3 question, H4 evidence, and H6 contribution/Task selections; H5 is derived and bound to H6. Research focus and contribution method may adapt to stronger evidence-backed paper opportunities within an approved pivot envelope. Optional read-only H3/H4 card checks and v3 H6 upstream binding are provided, without true user authentication, real DEV/GPU execution, SEALED rights or manuscript permission. Existing v1.3/v1/v2 selections remain readable; **real WorkBuddy improvement NOT_MEASURED**. [Card contract](skills/pd-rw-research/references/plan-selection.md).

> **v0.7.9 research outcome alignment:** For the user's explicit goal, optimize **time to credible high-tier, high-citation-potential scientific results** (Q1 preferred; credible Q2+ minimum as defined by PD-RW). The WorkBuddy Skill now compares scientific importance, named nearest-neighbor delta, reusable knowledge and the shortest legitimate evidence path at H6 / meaningful pivots. Optional `science.cli decision` adds conservative declared probe-cost Pareto hints. This is **advisory**: no citation/acceptance forecast, no extra H6 gate, no new research executor or permissions, and **real WorkBuddy research gains remain NOT_MEASURED**. [Scope](skills/pd-rw-research/references/research-leverage.md).

> **v0.7.8 H6 decision closure preview (historical, superseded for new v1.4 projects):** New projects reuse user startup scope, AI researches H3-H5, and the Skill requires one specific H6 author choice. A hash-bound **read-only** Python checker rejects stale or malformed *declared* choices but cannot authenticate a user or enforce WorkBuddy actions. No new MCP tools. [Audit and limits](docs/V077_H6_PLAN_CHOICE.md).

> **v0.7.6 targeted science/runtime patch:** Compact resume keeps specific blocker reasons and source-reported read-only recovery routes. Optional hash-bound DEV/VAL Run matrix coverage is checked within existing `audit_scientific_experiment`; it never certifies metric validity or a preregistered plan. No new MCP tools or execution permissions. **Real 42/43/44 WorkBuddy comparisons remain NOT_MEASURED.** [Scope and limitations](docs/V076_TARGETED_AUDIT.md).

> **v0.7.5 WorkBuddy convergence (candidate):** compact, evidence-bounded resume hints coexist with the v0.7.4 full schema; the Skill prefers one resume call rather than repeating context reads. MCP profiles now expose `minimal` (11), `research` (17, default) or `diagnostic` (20) tools, without changing scientific authorization. Case-index search identifies review candidates but does not promote similarity to a scientifically validated lesson. Existing v0.7.4 host experiments remain intact and diagnostic-only. **Actual WorkBuddy A/B/C is still NOT_MEASURED.** [Design and acceptance](docs/V075_CONVERGENCE.md).

> **v0.7.4 first-pass runtime integration:** fixed CPU host records now
> mirror into the existing versioned operation-attempt ledger; duplicate
> logical IDs between host jobs and operational receipts are rejected.
> Resume summaries surface unresolved host attempts, output tampering and
> attempt-record conflicts, independently of scientific status. Existing
> standalone synthetic selftests and prior host records remain readable.
> No real DEV/GPU execution or original Run registration is enabled.
> [Read the runtime integration scope](docs/V074_RUNTIME_INTEGRATION.md).

> **v0.7.3 fixed-host reliability:** Windows process-exit observation,
> explicit INTERRUPTED checkpoints and an operator-only synthetic ACL
> fixture probe. This is diagnostic code, **not** a trusted production
> DEV/GPU executor. See [v0.7.3 scope and backlog](docs/V073_HOST_RELIABILITY.md).

> **v0.7.2 supervised CPU pilot:** separate operator-launched host CLI,
> Windows suspended child + Job Object kill-on-close (Linux session +
> parent-death safeguard), persistent fixed CPU diagnostic, live
> cancellation/timeout, plan-idempotent checkpoints and hash-verified
> read-only MCP status. Operator runner-catalog source SHA checks and
> OS-identity probes are diagnostic only. **No real DEV/GPU execution or
> authenticated WorkBuddy permission is enabled.**
> [Host contract](docs/V072_HOST_PILOT.md).

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

> **v0.5.3 routing adjustment:** For an explicitly registered and permitted project, an MCP-enabled WorkBuddy Skill now requests an actual bounded MCP project-context call before broad file reads; the server uses the same Python service as the CLI. This is an instruction-level routing change, **not** a guaranteed host enforcement mechanism. See [WorkBuddy MCP-first acceptance](docs/RUNTIME_AND_MCP.md#historical-v053-workbuddy-mcp-first-routing-acceptance-replay-only).

> Status: **v0.5 controlled-continuation foundation** — original 5 read-only MCP tools plus 6 scoped resume/receipt/preview/handoff tools. Only private operational receipts may be written; real PD-RW Run registration is disabled in the Agent adapter (including caller-supplied callback) pending independently secured host authorization. Actual WorkBuddy end-to-end performance remains NOT_MEASURED.

> **v0.5.4 local increment:** read-only, advisory reuse of `CASE_LIBRARY` (`review_case_transfer`, `extract_case_candidates`, and an additive `case_library` field on `search_research_memory`). No writes to CASE_LIBRARY / STATE / Run / SEALED and no GO/STOP. Setup, restart steps and the ON/OFF ablation are in [RUNTIME_AND_MCP.md](docs/RUNTIME_AND_MCP.md#v054-local-increment-case_library-advisory-reuse) and `evals/case_learning_ablation.py`.

> **v0.5.5 local increment:** `case_gate_check` adds 3 advisory mandatory checkpoints (G1 H2–H3, G2 H6–H7, G3 H8–H10) and 2 conditional triggers (T1 anomalies/negatives, T2 material decision changes), with fingerprint-based cache reuse, real-retrieval + applicability verification and UNKNOWN marking. It reuses the existing retriever; no second database, no GO/STOP, and **no WorkBuddy host state-transition hard gate** (`enforcement_level.hard_gate=false`). See [RUNTIME_AND_MCP.md](docs/RUNTIME_AND_MCP.md#v055-local-increment-five-case-application-gates) and `evals/case_gate_eval.py`.

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
