# v0.6.1 history, Run evidence and negative-lesson applicability

Authoritative science, Run contracts and event writing remain in
[PD-RW](https://github.com/phr-devil/Problem-Data-Research-Workflow).
The Agent never creates a second STATE/EVENTS ledger or authenticates user approvals.

## Python / MCP / CLI

| Interface | Reads | Exact limitation |
| --- | --- | --- |
| reconstruct_project_history(project_id) | registered STATE.json and EVENTS.jsonl | Reconstructs event-chain and PD-RW state **metadata**; does not open SEALED artifacts or verify Run bytes |
| verify_run_evidence(project_id, run_id) | event-indexed DEV/VAL Run JSON, original PD-RW contract, bounded declared linked artifacts | SHA/contract structural check only; no scientific validity, permission or label/split independence attestation |
| review_lesson_applicability(proposal, lessons) | caller-supplied premise/scope/declared-negative packet | Literal scope comparison only; never automatic GO/STOP, no proof of equivalent physical mechanisms or original Run provenance |

CLI equivalents:

    python -m pdrw_agent.cli history --project-id 37
    python -m pdrw_agent.cli verify-run --project-id 37 --run-id run-001
    python -m pdrw_agent.cli lesson-scope --packet proposal-with-lessons.json

The last file contains:

    {
      "proposal": {"premise_id": "p1", "scope": {
        "dataset_version": "D1", "evaluation_unit": "subject",
        "group_split": "LOSO", "metric": "macro-F1"
      }},
      "lessons": [{"premise_id": "p1", "scope": {
        "dataset_version": "D1", "evaluation_unit": "subject",
        "group_split": "LOSO", "metric": "macro-F1"
      }, "validity": "VALID_NEGATIVE", "evidence_refs": ["runs/r1.json"]}]
    }

EXACT_DECLARED_SCOPE_CANDIDATE means only that the specified fields and
identifiers match. Critical fields dataset_version/evaluation_unit/group_split/
metric must be declared in *both* packets. For stronger claims, review legal
prediction-time inputs, label semantics, baseline, subject/sample histories,
original Run and independent validation explicitly.

## Safety and incomplete recovery

- JSONL event chain is checked for duplicate IDs, project mismatch,
  missing/invalid metadata, order/prev-event continuity and consistency with
  PD-RW STATE.json. Missing files, broken chain and changed state are distinct.
- This does **not** replace PD-RW core.state.status(deep=True); no protected
  event artifacts are hashed or opened by the history checker.
- Run verification refuses a mismatched or incomplete STATE/EVENTS history,
  any SEALED Run, protected linked file, unknown contract, conflicting metadata,
  source SHA mismatch, missing link SHA or oversized source. The original
  Run contract is checked through PD-RW core.contracts.validate_run.
- Inspecting a negative Run whose JSON says INVALID/INCONCLUSIVE/NOT_RUN
  never turns the outcome into a scientifically valid negative.
- All statuses remain bounded, read-only and non-authorizing.
- No new training, resumed jobs, user-confirmation gates, Run/Claim/STATE
  writes, or data downloads have been added.

## Required real-system verification

Existing CI synthetic fixtures on Windows/Linux are engineering checks,
not a measurement of scientific correctness or WorkBuddy performance. Run
actual frozen historical cases with original valid DEV Run artifacts, compare
A/B/C at matched scope and log the actual MCP calls, tool costs and limits.
