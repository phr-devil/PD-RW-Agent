# Evidence-first experimental feedback — optional v1 adapter

**Purpose:** small read-only bridge from a meaningful *pre-result* hypothesis/probe to an actual experiment observation. This is **not** a new PD-RW workflow, H-stage, research ledger, mandatory DEV gate or automatic Agent training. The author, original PD-RW protocol, Run evidence, and trusted WorkBuddy host retain authority.

## Invocation

```sh
python -m pdrw_agent.science.feedback --packet feedback.json
```

The output is JSON. The comparator does not write project, SQLite or scientific files and does not register an MCP tool. In the local v0.9.1 integration WorkBuddy may call it as a library (`review_probe_feedback`) from an existing **meaningful Run/decision** event. Ordinary code changes and routine DEV must not call it by default.

### Input (synthetic; no source verified)

```json
{
  "schema_version": "pdrw-probe-feedback-v1",
  "prior_decision_ref": "frozen/prior-scientific-decision.json",
  "prior_proposal_sha256": "<canonical proposal_sha256(prior_proposal)>",
  "prior_proposal": {
    "question": "Does a subject-independent gain persist?",
    "claim_type": "MECHANISM",
    "hypotheses": ["true-gain", "group-leakage"],
    "proposed_premise": {
      "premise_id": "subject-independent-gain",
      "scope": {"dataset": "synthetic", "group_unit": "person"}
    },
    "probes": [{
      "id": "heldout-probe",
      "observable": "macro-f1-delta",
      "evaluation_unit": "held-out-subject",
      "comparison_reference": "matched-simple-baseline",
      "predictions": {"true-gain": "INCREASE", "group-leakage": "NO_CHANGE"},
      "cost_band": "LOW"
    }]
  },
  "observation": {
    "prior_proposal_sha256": "<same canonical digest>",
    "run_ref": "DEV/run-001",
    "probe_id": "heldout-probe",
    "observable": "macro-f1-delta",
    "evaluation_unit": "held-out-subject",
    "comparison_reference": "matched-simple-baseline",
    "validity": "VALID",
    "outcome": "NO_CHANGE",
    "evidence_refs": ["DEV/run-001/eval.json"]
  },
  "consulted_case_ids": ["EXT-X3"]
}
```

Use `proposal_sha256(proposal)` from this module, not an arbitrary user-supplied hash. `prior_proposal` uses the existing `science.decision.assess_proposal` contract. Observation validity must be one of `VALID | INVALID | INCONCLUSIVE | NOT_RUN`; only a **declared** valid Run with a known qualitative outcome and refs is compared against predicted outcomes. Run validity and hypothesis support are never certified by this pure function.

### Evidence and time boundaries

- The original prior-decision file must exist **before** the observed Run. Hash equality does not establish temporal order. Check the original immutable run/protocol/decision records and their trusted timestamps or frozen-history evidence separately.
- A Run must be checked against its original label derivation, group independence, legal prediction-time inputs, evaluation unit, matched baseline and DEV/VAL/SEALED protocol. The comparator reports `original_run_verified=false` even when fields look correct.
- Changed observable / evaluation unit / comparison reference is **not comparable**, not a valid failed hypothesis. Invalid, inconclusive and unrun work is never promoted to scientific negative evidence.
- `compatible_predictions` means only *same declared categorical prediction as declared observation*, not proved mechanism; `contradicted_predictions` does not prove impossibility. No automatically inferred effect sizes, statistical significance, paper novelty, project-wide STOP or GO.
- Preserve valid positive observations, negative limits and independent baselines. A failed new neural network should not hide an evidence-supported narrower traditional-method improvement.
- Use historical case cards only as explanatory candidates; evidence grade, source group, applicability and counterexamples matter. A cloud Markdown `VERIFIED_FAILURE` classification plus `REVIEW_REQUIRED` grade does **not** certify the user's local original Run.
- The cloud knowledge mirror may be a limited subset. A missing match means `NOT_FOUND_WITHIN_SCOPE`, not an absence of prior evidence.

### Local v0.9.1 integration boundary

The existing WorkBuddy checkout v0.9.1 is **not** on GitHub main. Integrate this *additive* module and tests with that checkout, never replace its local `case_learning.py`, `case_export.py`, `case_knowledge.py`, `case_gates.py`, `memory.py`, Skill or MCP registry with older main versions.

For a meaningful, legitimate DEV Run: link an existing original pre-result hypothesis/probe reference and its digest to the evaluated original Run. Record the returned advisory contrast and why the next probe or paper strategy changes in the **existing** `RESEARCH_RECORD.md` (and update `PAPER_BLUEPRINT.md` only when a Claim/section materially changes). Never create a third scientific ledger or require a new author selection within authorized H7. Any new download, sealed access, publication, uploads or material H6/H8 scope change still needs its original independent authorization.

## What to measure before calling the Agent smarter

Use PD-RW `REPLAY_PROTOCOL.md` with genuinely time-frozen cases. Compare the same model and resource budget across (A) no prior cases, (B) keyword retrieval, (C) evidence-linked retrieval + decision feedback. Mask future results across all source aliases and near duplicates; blinded experts score scientific decision quality, important missed hypotheses, unnecessary repeats, false STOP/GO, real tool behavior, source validity, human steps, GPU cost and token use. Pure Python tests and CLI outputs are **not** an end-to-end scientific capability measurement.
