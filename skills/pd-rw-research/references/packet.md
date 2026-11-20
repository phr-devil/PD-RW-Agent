# The decision packet: write it while you decide

`decision` answers one question — *does this next experiment have information
value, and is it a step you can take now?* It can only answer that from a packet.
This page is the shortest path to a packet that the tool accepts, and the
boundary of what it will do for you.

```
python -m pdrw_agent.science.cli template > p.json      # a packet that already passes
# ... replace the placeholder values, keeping the shapes
python -m pdrw_agent.science.cli packet-check --packet p.json
python -m pdrw_agent.science.cli decision --packet p.json --project-root <project>
```

`packet-check` exits `0` when the shape is accepted, `3` when it is not (that is
not an execution error: the science may be fine, the input is not a packet yet),
`2` on anything else. It reports **every** violation at once, each with a field
path, the value found, and what the field accepts. Read the paths, not the
summary.

## Four things only you can write

The checker will not guess these, and must not:

| field | what it accepts | why it is yours |
| --- | --- | --- |
| `predictions` | one of `INCREASE` / `DECREASE` / `NO_CHANGE` / `UNKNOWN` per hypothesis | a direction is a scientific claim; a sentence has no direction |
| `proposed_premise.scope` | ≤12 short keys → short values (`dataset`, `input`, `unit`, `outcome`, …) | which phrase belongs to which key is a boundary decision |
| `prechecks` names | six fixed names: `label_provenance`, `group_independence`, `legal_inputs`, `evaluation_integrity`, `metric_appropriateness`, `effect_size` | the decision path reads these six; a seventh would be ignored |
| `hypotheses` | 2–6 short IDs, referenced exactly by `predictions` | the ID is a key; its explanation belongs in `question` |

Everything else is mechanical: `observable` and `comparison_reference` are free
text (≤240 characters), `evaluation_unit` is a **token** (`SUBJECT`, `WINDOW`,
`FRAME`, …) because the independence check compares it with the metric's unit,
and `cost_band` is `LOW`/`MEDIUM`/`HIGH`/`UNKNOWN`.

## Bounded repair: two rounds, then stop

1. Run `packet-check`, fix what the paths name, run it again.
2. **Two rounds is the budget.** If it is still rejected, stop: keep your
   scientific answer in prose, say which field blocked it, and do not force a
   tool call. A packet that was invented to pass a check is worse than no packet.
3. Never change a prediction, a premise, an evidence reference or an
   authorization to make the checker happy. `packet-check` also lists
   `ignored_fields` (the decision path will not read them) and `warnings` (read
   but not enforced — e.g. a prose `evaluation_unit` silently disables the
   repeated-unit check).

The reason for the budget is measured, not stylistic: four independent sessions
in 03D each wrote a packet and all four were rejected, and a fifth session given
these four packets plus the checker repaired none of them — the residual
violations were prose predictions, invented check names and a prose `scope`,
i.e. exactly the fields above.

## A probe that already ran, and one that cannot start

```json
{"id": "P2", "observable": "subject-level MAE", "evaluation_unit": "SUBJECT",
 "comparison_reference": "same folds, magnitude-only baseline",
 "predictions": {"H_ADD": "DECREASE", "H_BASE": "NO_CHANGE"}, "cost_band": "MEDIUM",
 "prior_execution": {"status": "COMPLETED_VALID", "run_ref": "DEV/runs/RUN-005",
                     "premise_ref": "protocol/PROTO-...-v5-DEV005.json",
                     "premise_id": "PREMISE-ID"}}
```

`run_ref` is a **project-relative path**; `premise_ref` names the frozen plan
that encodes the premise under study. A probe you have not run but cannot start
is declared, not omitted:

```json
{"id": "P3", "prior_execution": {"status": "NOT_EXECUTED",
                                 "requires_new_authorization": true}}
```

That reads `NEEDS_AUTHORIZATION`: a candidate nobody can start yet, and never
counted as the next action. Use it whenever the probe spends data beyond the
frozen DEV subset (a reserved validation set, a second dataset, a SEALED read) —
"we would need permission" written in prose is not the same thing, and the
frontier will otherwise offer the probe as executable.

## What a green check does not mean

`SHAPE_OK` means the packet can be read. It does not mean the experiment is
legal, decisive, authorized or already run — `decision` reports those separately
(`probe_findings`, `frontier_candidate_ids_as_declared`, `applicability`), and
none of them authorizes anything. `scientifically_ranked` and
`source_predictions_verified` stay `false` by design.
