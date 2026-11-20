# RC-PREFLIGHT — attribution, authorization, and one positive result

Date: 2026-11-20 · Base: `998826d` (PR #25, v0.9.13) · Branch `rc/preflight-0.9.14` · v0.9.14

Three questions, all answered on this machine: does the "premise assumed" role hide
an experiment that was never run; can a plan say what it needs permission for; and
is there a positive result here that can be checked without inventing one.

Nothing was trained, downloaded or paid for. No `SEALED`/`Holdout` path was read.
No historical Run, frozen protocol, hash or pre-registration date was modified:
`audit/science04/freeze.py --verify` still reports 35 files / 1 509 332 bytes.

---

## A. A Run that ran is not yet evidence about *your* experiment

### A.1 The defect, reproduced on real bytes

`HISTORICAL_EVIDENCE_PREMISE_ASSUMED` (0.9.13) said: the Run is real and ran as
declared, the premise is only your label — therefore recorded evidence, do not
rerun. The middle clause was doing work it could not support. Whether a Run is
*evidence about this probe* is a third question, and the tool answered it by
reading the label it had already been given.

`audit/rc_preflight/adversarial_attribution.py` asks it with four bounded cases
against real project bytes (48's `DEV/runs/RUN-005`, 19's `CRFW_RUN1`). The probe
in AD1/AD2 is a **k-scale grid** (`k ∈ {18, 173, 1728}`); RUN-005's frozen v5 plan
fixes one target scale, so the grid was never run.

| case | before 0.9.14 | after |
| --- | --- | --- |
| AD1 cites `RUN-005`, no plan named | `HISTORICAL_EVIDENCE_PREMISE_ASSUMED`, `in_historical_evidence: true`, `findings: []`, action `CITE_AS_EVIDENCE_ONLY_AND_DECLARE_THE_PREMISE_LINK` | `CLOSURE_ATTRIBUTION_UNCHECKED`, not in evidence, `CLOSURE_ATTRIBUTION_UNCHECKED` finding, action `CHECK_WHICH_PLAN_THE_RUN_EXECUTED` |
| AD2 cites `RUN-005` + the v5 plan | same as AD1 (`CALLER_DECLARATION`) — the Run↔plan link the record does prove was not expressed at all | `HISTORICAL_EVIDENCE_PREMISE_ATTRIBUTED`, `attribution_basis: CALLER_PREMISE_PLAN`, citable, `premise_verified: false` |
| AD3 `CRFW_RUN1/results.json` (19) | `CLOSURE_DECLARED_NOT_VERIFIED` (`record_structure: METRICS_ONLY`) | unchanged |
| AD4 `RUN-005/attempt-1-invalid-anchor` | `STATUS_CONFLICT` + `EXECUTION_STATUS_CONFLICT` | unchanged |

So yes: an unexecuted experiment could be retired. It was not merely a misleading
label — `historical_evidence_ids` is the list a session reads to decide *not to
run* something, and the same probe also made `no_executable_next_probe` true, so
the whole plan read as closed. The 0.9.13 pair was already an improvement on
`HISTORICAL_EVIDENCE_ONLY`, but it still asserted evidence.

### A.2 The fix: a fourth axis, not a new checker

`_prior_execution` now answers "is anything on disk tying this Run to this
experiment" separately from "did it run" and "is the premise settled":

- `attribution_basis` = `RUN_RECORD` (the record states `premise_id`) /
  `FROZEN_PLAN` (the plan it names states it) / `CALLER_PREMISE_PLAN` (the Run
  executed the plan you named — the binder already compares the record's
  `protocol_id`/`protocol_sha256` with that plan's bytes) / `NONE`;
- `attribution_verified` = basis ≠ `NONE`;
- `premise_verified` keeps its 0.9.13 meaning: a *recorded* premise id, original
  not post-hoc; `closure_verified` still needs all of it.

Three outcomes, three roles:

| what the disk shows | `applicability` | in `historical_evidence_ids` | next action |
| --- | --- | --- | --- |
| record/plan states the premise and it matches | `HISTORICAL_EVIDENCE_ONLY` | yes | `KEEP_AS_RECORDED_EVIDENCE_DO_NOT_RERUN` |
| the Run executed the plan you named, which states no premise | `HISTORICAL_EVIDENCE_PREMISE_ATTRIBUTED` | yes | `CITE_AS_EVIDENCE_ONLY_AND_CONFIRM_THE_PLAN_IS_THIS_EXPERIMENT` |
| nothing on disk | `CLOSURE_ATTRIBUTION_UNCHECKED` | **no** | `CHECK_WHICH_PLAN_THE_RUN_EXECUTED` |

`CLOSURE_ATTRIBUTION_UNCHECKED` sits beside the existing
`CLOSURE_PREMISE_UNBOUND` and is deliberately *not* runnable either: "run it
again" is the other wrong answer, and the instruction was to check attribution
first. The old names (`HISTORICAL_EVIDENCE_PREMISE_ASSUMED`,
`premise_assumed_ids`) are gone; the list is `attribution_unchecked_ids`.

**On real data** (`audit/science03d/real_48_check.py`): the same plan → attributed
evidence; a different line's plan (`PROTO-POPU-DEPLOY-v3-DEV003`) →
`CLOSURE_PREMISE_CONTRADICTED` and the probe is back in the frontier. Through the
CLI, with a packet citing RUN-005 and a live k-grid probe, the frontier is
`["SCALE-GRID"]` and `RELIABILITY-RERUN` is attributed evidence — the real answer
to "is there anything left to run here".

### A.3 What it does not do

It does not verify that the named plan *is* this experiment. A caller can name any
frozen plan the Run executed and get `ATTRIBUTED`. What changed is that the claim
is now attached to a specific, frozen, inspectable document instead of a repeated
string, and the action says to confirm it. Matching the plan's prose against the
probe's `observable` was considered and rejected: prose token overlap is exactly
the mechanism that silently disabled `PROBE_UNIT_NOT_INDEPENDENT` in 0.9.13.

It also does not edit history. A new experiment can record `premise_id` before
fitting and reach `closure_verified`. An old one can only be attributed
post-hoc — by naming the plan it executed, which reads `ATTRIBUTED`, not
`closure_verified`. No file convention for a "post-hoc attestation" was added:
that would be a second, weaker record of the same claim, and the test for it
would be the same string comparison in a new place.

---

## B. The plan could not say what it needed permission for

### B.1 Why two of four arms crossed the line

From `audit/science04/answers/`: B2 put a 3×3 target-scale × calibration grid on
the **reserved 48 subjects** as its `experiment.evaluation_unit` sentence
("*12 人子集之外的 48 名受试者*"), and "needs new authorization" appears only at
path step 3. B4's `contribution.shortest_path` is `["1) …", "2) …", "3) …"]` and
step 3 evaluates 20 Holdout materials *once*.

Neither is a schema failure. The output shape had one list and no per-step place
to say "this spends data nobody has authorised yet", so the fact went into
whichever sentence was convenient — or nowhere. A field cannot be missing from a
format that has no field.

### B.2 The format: three tiers, three rules

`references/execution.md` now requires the handoff plan in three labelled tiers:
`NOW` (legal under the current original grant, with the authority named),
`NEEDS_NEW_AUTHORIZATION` (the specific grant and who grants it), and
`FUTURE_CONDITIONAL` (the condition). Three rules: a tier-2 item does not weaken
tiers 1 and 3; `requires_new_authorization` is the machine form for a *probe* and
a non-probe step has no field, so it is written in tier 2; and no packet field is
a permit. `SKILL.md` step 7 points at it. This is text, not a permission checker —
B2's error is a project-authority question and the frontier must not become an
approver.

### B.3 Measured effect: the same decision point, replayed

An independent session re-ran DP3 (17, project terminated on an information
argument) from the same frozen snapshot, with the new format
(`audit/rc_preflight/answers/B5_DP3.json`, 24 min):

- `now` — **four** steps, all on TRAIN's 90 materials and already-cached features:
  a material-level cross-fitting re-estimate of the magnitude claims, a
  heterogeneity readout, an arithmetic re-check of the ICC bound, and widening the
  one STRONG result (calibration is harmful) from 12 to 90 materials. None of
  these existed in 04's answer.
- `needs_new_authorization` — **three**, each with its own grant: the 20 Holdout
  materials (`SPLIT_PROTOCOL.md §5`), the 40 sealed materials
  (`§2`, a *separate* grant), and new or external data (`DATA_AUDIT.md §1`,
  `HOLDOUT_STATUS.md §4`).
- `future_conditional` — three, keyed to what those grants return.

The 04 arm produced the holdout evaluation as step 3 of a running list and named
no grant. The change is not that the model became more cautious — it proposed
*more* legal work. It is that the format separated "what I can do now" from "what
someone must authorize", which is the thing the instruction asked for and the
thing the old shape could not express.

Caveats: n=1 per arm, same model family, single non-blind arm, and B5's `now` tier
depends on `artifacts/` files that the snapshot withheld — it says so itself in
`uncertainties`.

---

## C. Positive evidence, and one end-to-end session

### C.1 The positive result that is actually here: project 19

`CRPS_L2_EVAL.json` / `CRPS_L2_ALGO_ROUND.json` (17 objects, LODO, 111 dev
recordings):

| scheme | segF1 (ALGO_ROUND) | recomputed from per-object records |
| --- | --- | --- |
| `SF｜lag3` (single-frame LR, no context) | 0.6717 | 0.6717 |
| `GRUskill｜lag3` (temporal only, no action labels) | 0.6514 | 0.6514 |
| `DualHead｜lag3` (same capacity + action supervision, no explicit fusion) | 0.6468 | 0.6468 |
| `GRUctx｜lag3` (predicted parent-action posterior fused) | 0.7091 | 0.7091 |

- **Contribution**: explicit fusion of a *predicted* parent-action posterior into
  the low-level frame classifier, +0.037 over the no-context baseline and +0.062
  over the equal-capacity control — the second number is what rules out "capacity
  or action supervision", and two controls (`GRUskill`, `DualHead`) land *below*
  the baseline, which is the strongest part of the argument.
- **Strongest baseline by number is `SF｜lag3` (0.6717), not the arm the report
  calls the fair baseline** (DualHead, 0.6468). `GateCtx` is 0.7093, i.e. two
  ten-thousandths *above* the champion; the report drops it as "≈ and simpler",
  which is a design choice, not a numerical win.
- **Boundary**: DEV only; 5 recording dates, 111 recordings, 17 objects shared
  across folds; `UNKNOWN` frames excluded from classification; full-episode
  boundary F1 does **not** improve (0.5948 → 0.5889), so the gain is label-level;
  `Nudge` F1 is 0 for both arms.
- **Missing evidence**: the sealed 37 (G1), a second dataset, and any per-segment
  record — the JSON keeps confusion matrices and per-recording pairs, not segment
  outcomes.

**Recomputation, and where the report and the artifacts disagree** (an independent
session and this audit got the same answer separately):

| claim in `FINAL_ALGO_ROUND_REPORT.md` | what the files give |
| --- | --- |
| object-level `GRUctx > SF` **17/17** | true for `CRPS_L2_EVAL.json`; the ALGO_ROUND file it is summarizing gives **15/17** (`D-SUB −0.0211`, `medium gear −0.0116`) |
| recording-level **96/111 = 86.5%** | recorded in `CRPS_L2_STATS_AUDIT.json` (`improved_episodes: 96`) but **not rebuildable** from `episode_paired`: 92/111 (ALGO_ROUND) or 97/111 (EVAL) depending on the aggregation; the pairing rule is not in the artifact |
| `GateCtx` wins on **1.6% of 111 episodes** | 1.6% of **1464** object×recording pairs; at recording level it is 18.0% |
| date-level 5/5 positive | reproduced (5/5) |
| `Push→Grasp 33.9%` | 32.2% in the mechanism block |

None of this makes the result fake: every mean reproduces to four decimals, and
`CRPS_L2_STATS_AUDIT.json` already states that the 17 folds are correlated
replications, gives a date-clustered CI, and retires the old "17/17, p≈7.6e-6"
claim. What it shows is that the *coverage* sentences were assembled from
different files under one heading — which is exactly the kind of defect a positive
claim has to survive before it can carry a paper.

### C.2 End-to-end: a real session, template → packet-check → decision

Independent session, 14 min, given the Skill, the CLI and project 19
(`audit/rc_preflight/answers/C1_report.json`, `C1_packet.json`):

- `template` → one rewrite → `packet-check`: **`SHAPE_OK`, 0 violations, 0 warnings,
  on round 1** (budget was 2; used 0). Compare 04's A2 (2 rounds) and A1 (0/4).
- `decision --project-root D:\workbuddy-work\19`: `frontier =
  ["P1_CLUSTERED_REANALYSIS"]`, `needs_authorization_ids =
  ["P2_SEALED_CROSS_RECORDING"]`, `historical_evidence_ids = []`,
  `no_executable_next_probe: false`. Both probes were also flagged
  `PROBE_UNIT_NOT_INDEPENDENT` — the session had declared `evaluation_unit:
  EPISODE` with `group_independence: PASS`, and agreed with the finding: the true
  independent count is **5 recording dates**. That is a scientific catch the tool
  made on a real project, not a shape complaint.
- It also produced the tiered plan without being told the answer: `now` = re-run
  the contrast with date-clustered intervals, correct the coverage numbers in the
  report, add a sign test for `GateCtx − GRUctx`; `needs_new_authorization` = the
  sealed 37 + one full-Dev model, and a second dataset.

### C.3 A trusted Run feeding the decision

`decision --packet C4_run005_packet.json --project-root D:\workbuddy-work\48`
(exit 0): `frontier = ["SCALE-GRID"]`, `historical_evidence_ids =
["RELIABILITY-RERUN"]`, `attribution_basis: CALLER_PREMISE_PLAN`. The cited
RUN-005 is usable as recorded evidence and is not offered as a rerun; the
never-run k-grid is the next action.

### C.4 Not exercised

`feedback-link` (bind a pre-result proposal to a Run) was **not** run end-to-end:
no project here holds a `pdrw-packet-v1` proposal whose digest predates a Run, and
constructing one now to "test" it would be the artifact the task forbids. Project
19's `CRFW_RUN1/results.json` has no `run_id`/`status`, so it binds as
`METRICS_ONLY` (AD3) — a real result, not a Run record. `REAL_LLM_END_TO_END`,
token cost and MCP integration remain `NOT_MEASURED`.

---

## D. Verification and cost

- `pytest tests -q`: **613 passed / 8 skipped / 151 subtests** (610 before; +3).
  `unittest discover`: 621 tests, OK.
- `evals/case_gate_eval.py`: 13 gate calls, 9 verified checkpoints, 0 false / 0
  missed triggers, 4 retrieval calls avoided.
- MCP: 24 tools, profiles 11/21/24 (unchanged). Payload (compact JSON):
  3 781 → **3 787**, 11 149 → **11 167**, 8 822 → **9 075** declared and
  9 664 → **9 917** bound.
- `audit/science04/freeze.py --verify`: 35 files, 1 509 332 bytes, unchanged.
- The five assertions that broke (03B 2, 03C 1, 03D 1, 04 1) were rewritten to
  assert the split rather than the old label; three tests were added, so the count
  went 610 → 613 and no test was deleted.

| session | task | wall clock | paid compute | downloads | training |
| --- | --- | --- | --- | --- | --- |
| C1 | positive evidence + template + decision | 14 min | 0 | 0 | 0 |
| B5 | DP3 replay with the tiered plan | 24 min | 0 | 0 | 0 |

Tokens: `NOT_MEASURED`. Both sessions are the same model family as the patch
author: single non-blind arm.

---

## E. Unresolved

1. **`premise_verified` is still unreachable on real data.** No record or
   protocol in 44/48/19 states a `premise_id`, so `closure_verified` needs a
   project to write one before fitting. 0.9.14 makes the middle level reachable
   (`ATTRIBUTED` on real RUN-005), which is progress, not the same thing.
2. **The tool cannot check that the named plan is the experiment.** It can check
   the Run↔plan link. The plan↔probe link remains the caller's reading of a frozen
   document, and the action says to confirm it.
3. **No `VALID_POS` Run exists.** The positive half now has real, independently
   recomputable evidence (project 19), but it is a project artifact, not a Run
   record — and its coverage claims do not fully reproduce (C.1).
4. **`feedback-link` is not exercised**, for the reason in C.4.
5. **B2/B4-class boundary crossings are handled by a rule, not a mechanism.** B5
   obeyed the rule; one session is not evidence that the rule survives a model
   that does not read it.
6. **`artifact_links_verified` remains false**, `run_integrity` unwired, no host
   authentication of grants. Unchanged, and out of scope here.

---

## F. v1.0 RC?

**Code side: ready.** The two defects that blocked a release — a contract that
could not be repaired from the error, and evidence that outran its attribution —
are fixed, and both fixes are pinned by tests and by bounded cases on real bytes.
The remaining items in §E are evidence tasks in projects, not code.

**Evidence side: two gates, both project-side.**

1. write `premise_id` into one real protocol and its Run record, before fitting,
   and re-run `decision` to see `premise_verified: true` come from a record;
2. adjudicate one decision point whose real outcome was positive, so the
   contribution half is exercised on a Run rather than on a report.

Shortest integration path (no main merge from here):

1. `rc/preflight-0.9.14` → PR against `science/04-packet-contract` (stacked #26 on
   #25 on #24); CI must be green on both OS jobs.
2. Merge order when the stack is accepted: #24 → #25 → #26, each `--no-ff`, then
   `main` once.
3. `tools/package_skill.py` → `dist/pd-rw-research-0.9.14.zip`; re-import the Skill
   in WorkBuddy; verify the returned frontmatter says `0.9.14` (editing this repo
   does not update the installed copy).
4. Restart the stdio MCP so the payload schema matches; confirm 24 tools and the
   11/21/24 profiles, and one `decision` call on a real packet.
5. State recovery: `audit/science04/frozen/*/MANIFEST.json` is the only state
   this work depends on; `freeze.py --verify` must print 35 files / 1 509 332
   bytes before and after.
6. Known limits to carry into the RC notes: §E.1–§E.6, plus `NOT_MEASURED` for
   tokens, real LLM end-to-end and MCP integration.

Reproduce:

```
PYTHONPATH=src python audit/rc_preflight/adversarial_attribution.py
PYTHONPATH=src python audit/science03d/real_48_check.py
PYTHONPATH=src python -m pdrw_agent.science.cli decision \
  --packet audit/rc_preflight/answers/C4_run005_packet.json --project-root D:/workbuddy-work/48
PYTHONPATH=src python -m pytest tests -q
```
