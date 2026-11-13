---
name: pd-rw-research
display_name: PD-RW 科研 Agent
display_name_en: PD-RW Research Agent
description: Resume and execute explicitly PD-RW-governed research tasks in WorkBuddy; locate local project evidence, load only applicable PD-RW rules, and hand off verified results.
description_zh: 在明确使用 PD-RW 的科研项目中，恢复项目状态、按需读取规则、执行已授权任务并交付可追溯证据。
description_en: Read-only project recovery and evidence-aware execution routing for PD-RW research projects.
examples_zh:
  - "按 PD-RW 继续已存在的项目 19"
  - "恢复这个科研项目的状态和下一步任务"
  - "依据 PD-RW 审查本次 DEV 实验与交付"
examples_en:
  - "Resume an existing PD-RW research project"
version: 0.1.0
author: phr-devil
---

# PD-RW research execution adapter

Use this Skill only when the user explicitly selects PD-RW or asks to continue a project already governed by PD-RW. For unrelated general research questions, do not load this Skill.

## Operating contract

- **Authority:** PD-RW's `WORKFLOW.md` is the sole scientific decision authority; PD-RW's `AGENTS.md` is its default routing entry. This Skill **does not** duplicate or override PD-RW's rules.
- **Evidence:** original project Run, protocol, data manifest, and user messages outrank summaries. A state value or checker result never authenticates a user decision or experiment.
- **Memory:** use the project's existing `STATE`, `RESEARCH_RECORD.md`, and (when relevant) `PAPER_BLUEPRINT.md`. Do not create a second project memory database.
- **Limits:** bundled scripts are read-only helpers, not a secure executor or permission enforcement. Do not claim SEALED isolation or WorkBuddy integration has been proven.

## Task lifecycle

1. **Identify the project.** Verify project ID, research line, dataset and real local directory. If ambiguous, do not choose a project by guesswork.
2. **Locate the authority.** Determine the local PD-RW checkout and current local Git HEAD. If source freshness is material, compare with the remote only through an available authorized read-only mechanism. Unchecked remote = `RULE_VERSION_UNVERIFIED`; no silent pull or overwrite.
3. **Resume minimally.** Run `scripts/bridge.py doctor` and `resume` when a local project mapping is available. Read the current `RESEARCH_RECORD` snapshot and `STATE` pointers first; examine only the relevant raw Run/protocol. Missing/contradictory evidence = `UNKNOWN` or `SOURCE_CONFLICT`, not success.
4. **Route by need.** Read PD-RW `AGENTS.md` once per verified rule version/task, then its **single relevant** scientific owner document as needed. Follow its existing H1–H10, authorization, scientific evidence, and delivery rules. Do not read the full repository by default.
5. **Execute within authority.** Continue ordinary safe DEV coding, diagnosis, and tests within **actual** granted scope; reuse valid evidence and stop redundant probes. For new download, payment, SEALED, formal confirmation, publication, external upload, writing, drawing or major strategic changes, follow PD-RW's existing independent gates. Do not infer permission from a file or this Skill.
6. **Validate and persist.** Use PD-RW's existing read-only checks when relevant, but validate science against raw artifacts. On significant research events, update the **existing** project record/blueprint only within authorized file scope; retain history and provenance.
7. **Deliver.** Give one principal result with paths, checks actually run, scientific limits, and the next legal action (or required user choice). Avoid full log dumps, repeated rule text, and unsupported PASS claims.

## Optional helpers (no network/API required)

Commands are run from the directory containing this `SKILL.md`, or use an absolute path to `scripts/bridge.py`:

```bash
python scripts/bridge.py doctor --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
python scripts/bridge.py resume --project-id "example-project" --project-map "D:/path/to/project-map.local.json" --workflow-root "D:/path/to/Problem-Data-Research-Workflow"
```

The JSON output is **a locator and partial snapshot**, never user authorization or scientific verification.

## Load additional guidance only if necessary

- PD-RW path/version/project integration → [references/integration.md](references/integration.md)
- Autonomous DEV loop or handoff mechanics → [references/execution.md](references/execution.md)
- Missing paths, contradictory state, stale checkout, other failure → [references/troubleshooting.md](references/troubleshooting.md)

Do not automatically load all three references. Fail only the affected action if evidence or authority is missing; continue separately permitted, read-only work.
