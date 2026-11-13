# Proven design decisions and ownership map — NOT a second PD-RW policy

This index preserves the **effective design decisions** from prior WorkBuddy + ChatGPT + PD-RW discussions, while referring to the **current** authoritative sources instead of copying their rules. If a rule changes, its PD-RW owner wins; this index may need its *reference* updated, not its own competing interpretation.

| Agreed principle / pain point | Sole source of scientific/permission meaning | What PD-RW-Agent actually does or must test |
| --- | --- | --- |
| **Agent ≠ newly trained LLM**: leverage WorkBuddy model/tools and local Windows + RTX 4080; avoid mandatory API/fine-tuning | Platform configuration outside PD-RW; user tool choice | Skill-based tool adapter, no model API/fees required; optional integrations later |
| **Single Skill first**, no speculative multi-agent architecture | PD-RW `AGENTS.md` / `docs/STRUCTURE.md` | One `SKILL.md` and on-demand references; no duplicate agents or approval phases |
| **Memory loss after restarts/compaction** | Project `STATE` + `RESEARCH_RECORD.md` + optional `PAPER_BLUEPRINT.md` and original Run | `bridge.py resume` reads bounded snapshot, locates files, flags missing/conflicting identity; no third project ledger |
| **Number/name collisions across projects** | PD-RW `DUAL_DOCUMENT_WORKFLOW.md`; `LESSONS/CASE_REGISTRY.md` only as index | Explicit operator mapping and original project ID / dataset cross-check; no guesses |
| **Rule drift and stale versions** | PD-RW `AGENTS.md`, `WORKFLOW.md` | Local HEAD in `doctor`; remote unverified until independently checked; no silent pull/rebase |
| **Scattered/duplicate rule loading** | PD-RW `AGENTS.md` section 2 | `context.py route` derives current owner-file hints from the live checkout; progressive disclosure |
| **Separate author strategy from technical autonomy** | PD-RW `WORKFLOW.md`, `AUTHOR_STRATEGY_REVIEW.md`, `NEXT_ACTION_POLICY.md` | Respect H1–H6, H8 and applicable H9/H10 author choices; H7 and already authorized DEV can progress without repetitive sign-off |
| **User suggestions are not automatic scientific verdicts** | PD-RW `AGENTS.md` entry and `NEXT_ACTION_POLICY.md` | Classify IDEA / EXPLICIT_INSTRUCTION / STRATEGIC_CHOICE at task start; require original message evidence for strategy change |
| **Operational authorization separate from chosen Task/Claim** | PD-RW `WORKFLOW.md` and relevant SEALED/writing/figure owners | `context.py action-review` wraps existing advisory checker; never grants permission. Host-level enforcement still absent |
| **SEALED, confirmations, writing, drawing, payments, uploads/submission are independent gates** | PD-RW `CONFIRMATION.md`, `WRITING_GATE.md`, `FIGURE_POLICY.md`, `EXECUTION_ASSURANCE.md` | No automatic sealed access, model fitting beyond scope, manuscript, chart, upload, payment or submission based on Skill/STATE text |
| **Scientific evidence must be traceable** | PD-RW `EXPERIMENT_LOOP.md` and `core/` | Compare original versioned Run, group split, label provenance, legal prediction-time inputs, evaluator; INVALID/NOT_RUN is not a scientific negative |
| **Stay scientifically open but avoid fake innovation** | PD-RW `HIGH_VALUE_RESEARCH_DESIGN.md`, `PAPER_FIRST.md`, `CONTRIBUTION_TAXONOMY.md` | Preserve strong simple baselines, named nearest work, independent evidence and competing hypotheses; no automatic Q2 prediction |
| **Excessive narrow falsification / endless parameter tuning** | PD-RW `EXPERIMENT_LOOP.md`, `ALGORITHM_ENGINEERING.md`, `core.probes`, `core.failure_triage` | Before a new probe check changed prediction, legal leverage, reusable Run, cost and termination premise; distinguish crash vs valid negative |
| **Important positive / negative results remain useful** | PD-RW `SCIENCE_RESULT_HARVEST.md`, `POST_ALGORITHM_SCIENCE_AUDIT.md` | Route to existing result-harvest tooling as appropriate; do not discard a valid baseline because one mechanism failed |
| **Incremental research memory and paper blueprint** | PD-RW `DUAL_DOCUMENT_WORKFLOW.md` | Update existing record only for meaningful event; re-check affected blueprint SEC_ID without writing manuscript |
| **Small, consistent delivery instead of a pile of files** | PD-RW `NEXT_ACTION_POLICY.md`, `core.delivery_check` | `context.py delivery-review` delegates path check; output main entry, actual tests/evidence, limits, one next action |
| **Token and time efficiency as a whole-task objective** | PD-RW `NEXT_ACTION_POLICY.md`, `REPLAY_PROTOCOL.md` | Minimal snapshots, no default full read, avoid repeated experiments; compare real tokens/DEV hours/human interventions, do not invent savings |
| **Four optional calibration triggers, not repeated prompt spam** | PD-RW `AGENTS.md` entry/hand-off, `NEXT_ACTION_POLICY.md`, `REPLAY_PROTOCOL.md` | On new session: recovery; observed drift: execution calibration; restricted action: gate check; changed evidence/claim: scientific-value check. Not four new mandatory phases |
| **Keep completed old project decisions valid unless a dependency actually changes** | PD-RW `WORKFLOW.md`, `AUTHOR_STRATEGY_REVIEW.md` | Local reopen only affected decision; don't silently re-approve downstream H nodes |
| **Test actual WorkBuddy behavior** | PD-RW `REPLAY_PROTOCOL.md` / `evals/` | This repo: offline unit/CI plus manually captured, same-budget WorkBuddy A/B traces; until then `NOT_MEASURED` |
| **Future flexibility** | Adapter architecture in this repo | WorkBuddy-first, API/MCP optional later; no duplicate science rules, migrate via narrow interfaces |

## Out of scope and unresolved

1. **No authenticated user-message source** is supplied to a trusted executor in v0.2. A self-written JSON or `APPROVED` marker is not consent.
2. **No OS-level SEALED isolation or WorkBuddy tool interception** has been installed or tested.
3. **No supervised autonomous scheduler/model orchestration** is bundled. WorkBuddy continues tasks under its own supported runtime.
4. **No credible empirical token savings or research-success claim** exists until real paired WorkBuddy tasks are recorded.
5. **No full reproduction of private local project evidence** is possible from this public adapter repository.

Whenever a gap is fixed, update the implementation + focused tests, and mark evidence scope precisely.
