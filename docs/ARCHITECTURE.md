# PD-RW-Agent architecture and change contract

This file describes **where each responsibility lives** in v0.9.13 and what each
layer is forbidden to do. It is an adapter map, not a scientific rule source:
PD-RW `WORKFLOW.md` / `AGENTS.md` remain the only owners of scientific meaning.

## Six layers

| Layer | Owns | Must NOT do | Implemented in |
| --- | --- | --- | --- |
| **1 · PD-RW rule checkout** | H1–H10 semantics, three decision loops, six activities, SEALED/writing/figure gates, its own preflight/checker code | Be replaced, paraphrased away or silently re-versioned by this repo | External checkout (`PDRW_WORKFLOW_ROOT`) |
| **2 · Research project** | `STATE`, `RESEARCH_RECORD`, `PAPER_BLUEPRINT`, immutable Runs, frozen protocols, data, scripts, original user messages | Be rewritten, migrated or summarised into a second ledger | Project root, resolved from the operator's private map |
| **3 · Skill (prompt adapter)** | Trigger text, routing instructions, when to call which tool, bounded reporting | Authenticate a user, authorize an effect, or stand in for a missing rule | `skills/pd-rw-research/` |
| **4 · Python science checks** | Read-only, bounded declarations: candidate review, plan cards, proposal assessment, feedback binding, Run integrity, validity audit, case admissibility | Decide science, promote a declared value to a verified one, or write project artifacts | `src/pdrw_agent/science/` |
| **5 · Service + adapters** | One dispatch table shared by CLI and MCP; stable JSON shapes; visibility profiles | Add a second implementation of a science rule; grant permission by being installed | `service.py`, `cli.py`, `integrations/mcp_server.py` |
| **6 · Runtime + host diagnostics** | Private operational receipts (SQLite), bounded resume, fixed CPU synthetic jobs, host readiness probes | Become scientific records; claim OS isolation or authenticated authorization | `runtime/`, `host/` |

**WorkBuddy host** sits outside all six: it holds the real terminal, filesystem,
network and approval capabilities. No layer here can enforce what the host
allows; every layer can only *report what it checked*.

## Authority order

1. Original user messages and grants (authenticated by the host, never by this repo).
2. PD-RW rule documents and contracts for the applicable version.
3. The project's own frozen artifacts: Run records, protocols, `STATE`, `RESEARCH_RECORD`.
4. The Skill's instructions, which may only route and constrain *this* adapter.
5. Python/MCP tool output — bounded, advisory, re-readable evidence pointers.
6. Private operation receipts — operational only, never scientific evidence.

A lower layer never overrides a higher one. Tool output that conflicts with a
project artifact is reported as `UNKNOWN` / `RULE_CONFLICT`, not resolved in
favor of the tool.

## Attestation vocabulary (used consistently)

| Term | Meaning |
| --- | --- |
| `ATTESTED_BY_ORIGINAL_SOURCE` | The trusted host has seen the original message/artifact. This repository cannot produce this state. |
| `NOT_ATTESTED` | The value is declared; nobody in this process verified its origin. |
| `UNKNOWN` | Not enough information to decide either way. Never rendered as PASS/FAIL. |

Fields named `*_verified` mean *the specific mechanical check in that module
passed* (a file exists, a hash matches). They never mean scientific truth,
authorization, or SEALED clearance. Outputs that would otherwise be misread
carry the pair `declared` / `effective` so a reader can see the cap.

An input to a public tool is **always** `NOT_ATTESTED`, including a
`link_status`, a `proposal_sha256` or a field literally named "verified": the
caller typed it. That is why `case_gate_check` reports
`provenance_effective = PRE_RESULT_RECORD_UNVERIFIED` whatever arrives, and why
it lists `file_binding`, `historical_order`, `run_validity` and
`scientific_truth` separately as `NOT_PERFORMED_BY_GATE`. Only a module that
re-opened the original file may describe a check as passed — today that is
`science.feedback_link`, whose `verification_axes` block does exactly that.

The same rule reaches the gate's own cache: the fingerprint hashes the
**complete** bounded event (20 fields × 1200 characters, enforced by the event
validator), because a key computed from a clipped field would let a changed
declaration reuse an earlier advisory. Clipping is a display concern and lives
only in the returned basis (`gate_fingerprint(...)[1]`).

## AI context budget

1. WorkBuddy discovers the Skill through YAML `description`.
2. When triggered, read the short `SKILL.md` (<160 lines).
3. Resolve one project; inspect only its current snapshot and state index.
4. Read PD-RW `AGENTS.md` and the **one relevant authority document**; follow
   references on demand.
5. Read original evidence and permission only to the depth needed for the next action.
6. Preserve existing state and give a concise output; do not echo the context.

## Stable interfaces

| Interface | Producer | Consumer | Guarantee |
| --- | --- | --- | --- |
| Skill YAML + `SKILL.md` | This repository | WorkBuddy Skill loader | Trigger and documented workflow, not automatic compliance |
| `pdrw_agent.cli` | This repository | Terminal / operator | Same `ResearchService` as MCP; read-only unless an operation receipt is written |
| `pdrw_agent.integrations.mcp_server` | This repository | WorkBuddy MCP client | 11 / 21 / 24 tools by profile; visibility is not authorization |
| `python -m pdrw_agent.science.cli` | This repository | Operator | Card/feedback/decision checks; exit code `3` means "not an approval" |
| `project-map.local.json` | Operator's machine | `bridge`/service | Locator only, not identity or permission proof |
| Run/protocol and original messages | Research project / user | Research Agent | Primary evidence and real authorization, checked independently |
| `AGENTS.md` / `WORKFLOW.md` | PD-RW | Research Agent | Scientific routing and decision authority |

### Legacy standalone helpers (still supported, not the primary path)

| Interface | Guarantee | Limit |
| --- | --- | --- |
| `scripts/bridge.py doctor` | Local rule-file existence and local HEAD only | Does not check remote freshness |
| `scripts/bridge.py resume` | Explicit project paths, bounded snapshot, STATE index, no edits | Locator, not identity proof |
| `scripts/context.py route` | Routing labels derived from the live checkout | Not duplicate science policy |
| `scripts/context.py action-review` | Wraps PD-RW `core.execution_preflight` | Advisory only; grants nothing |
| `scripts/context.py delivery-review` | Wraps PD-RW `core.delivery_check` | Existence/path-only; no content or SEALED clearance |

## Not implemented (honest scope for v0.9.13)

- No original-user-message authentication, tool interceptor, sandbox or OS ACL.
- No re-reading of a Run inside `case_gate_check`: it reports declared feedback
  and never certifies it. Binding checks live in `science.feedback_link`, which
  also resolves the frozen plan a Run names: premise attribution is answered by
  the record or its plan (`premise_binding_basis`), never by two labels the
  caller wrote, and a plan that cannot be read leaves the closure unverified.
- No real DEV/GPU execution, no SEALED filesystem isolation, no manuscript,
  figure or submission action.
- No second scientific ledger, database or vector store; case reuse is a
  read-only advisory index.
- No measured WorkBuddy research gain, Token saving or wall-clock saving. See
  [WORKBUDDY_ACCEPTANCE.md](WORKBUDDY_ACCEPTANCE.md) and
  [RUNTIME_AND_MCP.md](RUNTIME_AND_MCP.md).

## Adding a capability without increasing confusion

1. Decide whether it is scientific policy (edit **PD-RW**), tool integration
   (add a script here), or operational guidance (a narrow reference here).
2. Reuse existing state/logs and PD-RW checks; never copy the original files.
3. Change `SKILL.md` only to add a short trigger/reference when genuinely needed;
   keep it under the 160-line contract.
4. Add one focused automated test; if model behavior matters, add a real
   WorkBuddy replay scenario instead of claiming one.
5. Report measured outcomes and remaining limitations. Passing CI proves
   engineering behavior, not scientific correctness or a secure gate.

## Where each decision was recorded

- [DECISION_COVERAGE.md](DECISION_COVERAGE.md): agreed design decisions, their
  single owner, and the **constraint preservation map** for this review.
- [EXPERIMENT_FEEDBACK_LINK.md](EXPERIMENT_FEEDBACK_LINK.md): proposal → Run →
  next-action contract.
- [RUNTIME_AND_MCP.md](RUNTIME_AND_MCP.md): current operator entry; historical
  increments are labelled and kept.
