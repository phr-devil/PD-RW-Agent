# Linked experiment feedback — optional, read-only, no new workflow

`science/feedback.py` (from PR #16) compares a **declared** proposal with a
**declared** observation. It cannot see whether those two objects really belong
to one project, whether the cited files still exist, or whether the declaration
came first. `science/feedback_link.py` adds only that binding:

```sh
python -m pdrw_agent.science.cli feedback-link \
  --link link.json --project-root <project> \
  [--case-index <CASE_LIBRARY>] [--mirror-manifest <manifest.json>]
```

Exit code `0` means `ADVISORY_FEEDBACK_ONLY`; every other status returns `3`
(an unverified link must not look like a completed check); `2` is a hard error.

This is **not** an H-stage, a research ledger, an MCP tool, an approval, or an
automatic GO/STOP. It writes nothing. Ordinary code changes, debugging and
routine DEV must not call it.

## What the link declares

```json
{
  "schema_version": "pdrw-probe-feedback-link-v1",
  "project_id": "44",
  "prereg": {
    "ref": "protocol/PROTO-...json",
    "sha256": "<sha256 of that file>",
    "declared_at": "2026-11-15T23:57:46+09:00",
    "proposal_ref": "protocol/feedback-proposal.json"
  },
  "run": {
    "ref": "DEV/runs/RUN-002",
    "run_record_ref": "DEV/runs/RUN-002/run_record.json",
    "started_at": "2026-11-16T00:12:00+09:00",
    "observation": {
      "run_ref": "DEV/runs/RUN-002",
      "probe_id": "heldout-probe",
      "prior_proposal_sha256": "<computed by proposal_sha256, never typed by hand>",
      "observable": "balanced-accuracy-delta",
      "evaluation_unit": "held-out-subject",
      "comparison_reference": "matched-simple-baseline",
      "validity": "VALID",
      "outcome": "INCREASE",
      "evidence_refs": ["DEV/runs/RUN-002/metrics.json"],
      "evidence_sha256": {"DEV/runs/RUN-002/metrics.json": "<sha256>"}
    }
  },
  "cases": {"query": "受试者分组 泄漏 平衡准确率", "limit": 3}
}
```

`prereg.proposal` may be inline instead of `proposal_ref`. The proposal itself
must already satisfy `science.decision.assess_proposal` and carry per-probe
categorical predictions (`INCREASE/DECREASE/NO_CHANGE/UNKNOWN`). The canonical
digest is recomputed by the tool; a user-supplied hash is never trusted.

## What is actually checked

| Check | Meaning |
| --- | --- |
| `prereg.sha256` | the declaration file bytes are unchanged |
| `proposal_sha256` | the proposal object matches its canonical digest |
| `declared_at < started_at` | the **declared** order (not proof of real order) |
| `run_record_ref` | the project's own Run record exists and parses |
| `evidence_refs` / `evidence_sha256` | cited result files exist and match |
| Run status vs declared validity | `VALID/INVALID/PARTIAL/CRASH/NOT_RUN` consistency |
| paths | every reference stays inside the project; `SEALED/holdout/confirmation` is refused |

Never verified: that the prediction really existed before the result, that the
Run is scientifically valid, that the mechanism is causal, or that the author
authorized anything. `historical_order_verified`, `original_run_verified`,
`scientific_inference_verified` and `permission_to_execute` stay `false`.

## Statuses

| Status | Meaning | What you may claim |
| --- | --- | --- |
| `ADVISORY_FEEDBACK_ONLY` | declaration bound, order declared, axes match, Run consistent | declared predictions matched/contradicted — as a **declared** contrast only |
| `PRE_RESULT_RECORD_UNVERIFIED` | no bindable proposal, hash mismatch, order missing or reversed, proposal not assessable | the observation is preserved; **no** prior-prediction verification |
| `NOT_COMPARABLE` | observable / evaluation unit / comparison reference changed | the change is not a failed hypothesis |
| `RUN_EVIDENCE_UNVERIFIED` | cited result missing, hash changed, or declared validity impossible | nothing about the hypothesis |
| `RUN_STATUS_CONFLICT` | declared validity contradicts the project's Run record | resolve the record first |

`PRE_RESULT_RECORD_UNVERIFIED` is a first-class result, not an error. Reasons
include `PREREG_WITHOUT_FEEDBACK_PROPOSAL`, `PREREG_HASH_MISMATCH`,
`PREREG_DECLARED_AFTER_RUN`, `ORDER_NOT_DECLARED`, `PROPOSAL_SNAPSHOT_MISMATCH`.
Exploration may continue; the write-up must not say the prediction was verified.

`INVALID`, `INCONCLUSIVE` and `NOT_RUN` observations yield
`NO_VALID_SCIENTIFIC_INFERENCE`: no compatible/contradicted predictions and no
negative scientific claim.

## Case context is explanatory only

When `--case-index` is given, the tool attaches at most three candidates:

- `evidence_grade` and `evidence_tier` (`DECISION_GRADE`, `EXPLORATORY_LEAD`,
  `CANDIDATE_ONLY`): preprints, `REVIEW_REQUIRED`, internal reports and
  abstract-only sources are never upgraded to independent confirmation;
- `same_source_with`: cases sharing a DOI/arXiv/PMID/PMCID are **one**
  independent unit, not two; `independent_source_units` counts units, not cards;
- `counterexample`, `next_minimal_check`: the conditions under which the case
  would not transfer, and the smallest local check;
- `mirror`: when `--mirror-manifest` is given, the published subset size and
  `content_sha256` of the cloud Markdown mirror. The local library remains the
  source of truth; a missing match is `NOT_FOUND_WITHIN_SCOPE`, not proof that
  no prior evidence exists.

A case never certifies the current Run, and keyword similarity never yields
GO/STOP (`automatic_go_stop: false` on every level of the response).

## Recording the outcome

Put the advisory contrast and the reason the next probe changed in the existing
`RESEARCH_RECORD.md`; update `PAPER_BLUEPRINT.md` only when a Claim or section
materially changes. Do not create a second ledger and do not re-run a check to
"confirm" a contrast that was already recorded.
