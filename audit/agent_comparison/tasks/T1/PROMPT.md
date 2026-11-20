# T1 — a mechanism fork, and the cheapest probe that separates it

`inputs/` is a frozen copy of project 48 (a PoPu human-pose study) as it stood
**before the author's HOLD decision**. It contains the project's own state and
research record, seven frozen protocol/amendment files, and the `metrics.json`
of five Runs (`RUN-001` … `RUN-005`).

The project's own reading of its Runs is that performance is **not predictable
beyond magnitude**. That statement can be explained by more than one mechanism,
and the project has to decide what to do next under a fixed budget.

## Deliver

Write `answer.json`:

```
{
  "competing_mechanisms": [
    {"id": "M1", "statement": "<one sentence>",
     "predicted_observation": "<what differs if this is true>",
     "evidence_for": "<Run + key path that already supports it>"}
  ],
  "cheapest_discriminating_probe": {
    "id": "<short id>", "observable": "<what you measure>",
    "evaluation_unit": "<SUBJECT / RECORDING / WINDOW / FRAME / ...>",
    "reference": "<the comparison arm or baseline>",
    "separates": {"<M1>": "<predicted direction>", "<M2>": "<predicted direction>"},
    "why_cheap": "<existing traces? zero new fits? how many subjects>",
    "why_not_already_answered": "<the field of the cited Run that shows it is not>"
  },
  "must_not_run": [{"probe": "<what>", "why": "<already answered / unauthorized / uninformative>"}],
  "authorization": {"inside_grant": ["<steps legal today>"],
                    "needs_new_grant": ["<steps that do not have one>"]},
  "packet": "<path to a machine-checkable packet if your tooling supports one, else null>",
  "calls": ["<each command or tool call you actually ran>"]
}
```

Rules:

- At least two mechanisms that predict **different** observations. Two restatements
  of the same claim is the failure mode this task exists to catch.
- The probe must be able to *falsify* one of them. Say which Run already covers
  it if the answer is "this was already done".
- Reusing an existing record with zero new fits is cheaper than a new fit and
  counts as a real probe if it discriminates.
- Do not invent a result. Do not modify anything under `inputs/`; write only
  `answer.json` (and a packet file if you produce one).
