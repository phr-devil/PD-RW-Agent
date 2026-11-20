# T2 — design the smallest legal fix after a refuted mechanism

`inputs/` is a frozen copy of project 19 as it stood **after the mechanism was
refuted and before the readout probe was run**. `dev_h8_v1/results/H8_VERDICT.json`
is the refutation; the corpus is 17 objects over **5 recording dates**, DEV only.

The refutation kills the proposed mechanism. The question is what a competent
researcher does next with the remaining budget — not whether to keep tuning.

## Deliver

Write `answer.json`:

```
{
  "what_is_refuted": {"claim": "<one sentence>", "evidence": "<file + key path + the numbers>"},
  "what_remains_true": {"claim": "<the part of the result that survives>",
                        "evidence": "<file + key path>"},
  "proposed_change": {
    "kind": "ANALYSIS_ONLY | READOUT | FEATURE | ARCHITECTURE | DATA",
    "one_sentence": "<the change>",
    "why_this_and_not_more": "<the cost argument: fits, GPU-hours, new data>",
    "pre_registered_endpoint": "<the metric and the comparison>",
    "evaluation_unit_you_will_use": "<and the count of independent units>",
    "grouping_rule": "<how you keep folds from sharing a recording date>"
  },
  "what_it_cannot_fix": ["<honest limits: generalization, boundary F1, ...>"],
  "must_not_do": [{"action": "<what>", "why": "<consumed / unauthorized / already refuted>"}],
  "expected_outcome_if_true": "<the number you would need to see, and why that number>",
  "packet": "<path to a machine-checkable packet if your tooling supports one, else null>",
  "calls": ["<each command or tool call you actually ran>"]
}
```

Rules:

- `evaluation_unit_you_will_use` must be defensible: 17 objects over 5 dates is
  not 17 independent units if a date is shared. If you claim independence, say
  what makes the folds independent.
- The change must be small enough to run inside the stated budget, and you must
  say what you are **not** doing because of that budget.
- Do not propose re-reading a one-time holdout; if a resource is consumed, say so
  and route around it.
- Write only `answer.json` (and a packet file if you produce one).
