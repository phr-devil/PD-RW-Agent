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

`prereg.proposal` may be inline instead of `proposal_ref`, but an inline object
written together with the link **cannot** support verified provenance: the link
is created after the Run. Prefer `proposal_ref` plus a `proposal_sha256` inside
the frozen record, so the record itself binds the proposal. The proposal must
already satisfy `science.decision.assess_proposal` and carry per-probe
categorical predictions (`INCREASE/DECREASE/NO_CHANGE/UNKNOWN`). The canonical
digest is recomputed by the tool; a user-supplied hash is never trusted, and a
proposal file that no longer matches the record's digest is reported as
`PROPOSAL_CHANGED_SINCE_FREEZE` instead of being compared.

## What is actually checked

| Check | Meaning |
| --- | --- |
| `prereg.sha256` | the declaration file bytes are unchanged |
| `proposal_sha256` | the proposal object matches its canonical digest |
| record's `proposal_sha256` | the frozen record names the same digest as the proposal file |
| `declared_at` | taken from the record's own `frozen_at`; the later of record/link wins, and a disagreement is flagged |
| `declared_at < started_at` | the **declared** order (not proof of real order) |
| `run_record_ref` | the project's own Run record exists and parses |
| `evidence_refs` / `evidence_sha256` | cited result files exist and match |
| Run status vs declared validity | `VALID/INVALID/PARTIAL/CRASH/NOT_RUN` consistency; `VALID` may be `INCONCLUSIVE` |
| paths | every reference stays inside the project; `SEALED/holdout/confirmation` is refused |

Never verified: that the prediction really existed before the result, that the
Run is scientifically valid, that the mechanism is causal, or that the author
authorized anything. `historical_order_verified`, `original_run_verified`,
`scientific_inference_verified` and `permission_to_execute` stay `false`.

## Three separate states

| Field | Values | Meaning |
| --- | --- | --- |
| `provenance.prediction_comparison` | `DECLARED_PREDICTION_COMPARED` / `NO_VALID_SCIENTIFIC_INFERENCE` / `NOT_COMPARABLE` / `NOT_PERFORMED` | whether a declared prediction/observation contrast was actually computed |
| `provenance.pre_result_provenance` | `PRE_RESULT_PROVENANCE_VERIFIED` / `PRE_RESULT_RECORD_UNVERIFIED` | whether the frozen record is a project file, binds the proposal digest, is dated before the Run and has no timestamp conflict |
| `prediction_verification_performed` | boolean | true **only** when both of the above hold |

`provenance.checks` lists every individual condition, so a reader can see which
one failed. `PRE_RESULT_RECORD_UNVERIFIED` is a first-class result, not an
error. Reasons include `PREREG_WITHOUT_FEEDBACK_PROPOSAL`,
`PREREG_HASH_MISMATCH`, `PREREG_DECLARED_AFTER_RUN`, `ORDER_NOT_DECLARED`,
`PROPOSAL_SNAPSHOT_MISMATCH`, `PROPOSAL_CHANGED_SINCE_FREEZE`. Exploration may
continue; the write-up must not say the prediction was verified.

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

## Case timing: pre-decision vs post-Run

The binder runs **after** the Run, so every retrieval it performs is
`post_run_related_case_ids`. Those cases explain a result; they are not
evidence that the decision used them. `consulted_case_ids` (kept for
compatibility) now carries **only** pre-decision IDs and is empty otherwise;
`consulted_case_ids_semantics` states this.

Pre-decision use needs a small receipt stored in the project, written at
retrieval time:

```json
{
  "schema_version": "pdrw-case-usage-receipt-v1",
  "retrieved_at": "2026-11-14T10:00:00+09:00",
  "query": "受试者分组 泄漏 平衡准确率",
  "case_ids": ["EXT-C04", "EXT-C05"],
  "index_sha256": "<index.json sha256 at retrieval time>"
}
```

and is declared in the link as:

```json
"cases": {
  "query": "...",
  "pre_decision": {
    "case_ids": ["EXT-C04"],
    "receipt_ref": "protocol/CASE-RECEIPT.json",
    "receipt_sha256": "<sha256>"
  }
}
```

`case_timing.usage_status` is then one of `VERIFIED`,
`UNKNOWN_NO_RECEIPT`, `RECEIPT_SHA_MISMATCH`, `RECEIPT_TIME_UNVERIFIED`,
`RECEIPT_AFTER_DECISION`, `DECLARED_CASE_NOT_IN_RECEIPT`. A verified receipt
still only proves **retrieval**; `case_influence_verified` becomes
`VERIFIED_IN_FROZEN_DECLARATION` only when the frozen record itself cites the
same IDs, otherwise `RECEIPT_VERIFIED_RETRIEVAL_ONLY`.

## Connecting the Run to the next action

`case_gate_check` accepts an optional bounded `run_feedback` object in the
event (values copied from the binder output; the gate does not re-verify them):

```json
"run_feedback": {
  "run_ref": "DEV/runs/RUN-002", "validity": "VALID", "outcome": "INCREASE",
  "prediction_review": "DECLARED_PREDICTION_CONTRAST",
  "provenance": "PRE_RESULT_PROVENANCE_VERIFIED",
  "compatible": ["real-gain"], "contradicted": ["leakage-explains-gain"],
  "evidence_refs": ["DEV/runs/RUN-002/metrics.json"]
}
```

`next_actions.situation.kind` then selects the first proposed action:

| Situation | First action |
| --- | --- |
| `PROTOCOL_OR_EXECUTION_DEFECT` / `EXECUTION_UNVERIFIED` | fix or locate the execution record first |
| `RUN_NOT_EXECUTED` | confirm the blocker, rerun the same probe |
| `INCONCLUSIVE_MEASUREMENT` | quantify noise before adding data |
| `NO_VALID_INFERENCE` / `NO_DISCRIMINATING_CONTRAST` | repair evidence / design a discriminating probe |
| `COMPETING_EXPLANATIONS_SPLIT` | verify the Run, then a probe that separates the surviving explanations |
| `SUPPORTS_DECLARED_HYPOTHESIS` | keep the champion, fill the paper evidence gap |
| `VALID_NEGATIVE_RESULT` | reassess the failed premise and alternatives, never stop the project |

Every action carries `basis`, `applicability`, `minimal_validation`,
`open_questions` and `automatic_go_stop: false`. `next_actions.decision_basis`
summarises what was used (`run_ref`, evidence refs, case index sha) and leaves
`selected: null` — the choice stays with the researcher and PD-RW.

## Recording the outcome

Put the advisory contrast and the reason the next probe changed in the existing
`RESEARCH_RECORD.md`; update `PAPER_BLUEPRINT.md` only when a Claim or section
materially changes. Do not create a second ledger and do not re-run a check to
"confirm" a contrast that was already recorded.

## Strict historical view (evaluation only)

`case_learning.search(..., as_of=<ISO timestamp with timezone>)` restricts the
index to cards that carry a `visibility_time` (or `library_added_at`) not later
than `as_of`. Cards without such a field are **excluded** and counted in
`excluded_unknown_visibility`, because assuming them visible would leak future
knowledge into a replay. The default `as_of=None` is byte-identical to the old
behaviour, so real research retrieval is never blocked by a missing history
field.

When nothing in the index carries a visibility time, the result reports
`blocked: "NO_CASE_IN_INDEX_CARRIES_A_VISIBILITY_TIME"`. In this checkout that
is the current state: the 65 cards have no such field, and file mtimes are only
a hint, not a trustworthy library-entry record. A strict A/B/C replay therefore
needs the corpus to start recording a visibility time (or a decision-time usage
receipt, see above) before it can run; fabricating one is not an option.
