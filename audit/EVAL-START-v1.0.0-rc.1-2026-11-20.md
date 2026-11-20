# EVAL-START — the first real A/B runs, and why they are not a blind test

**Date:** 2026-11-20 · **Base:** `rc/v1.0-integration` (v1.0.0rc1, PR #27) · **Runs:** four,
on CAL-1 and CAL-2 only · **Paid compute:** 0 · **Downloads:** 0 · **Training:** 0 · **GPU:** 0

This round did not build features. It ran the two calibration tasks on both arms, fixed the
evaluation isolation that was already broken, and checked whether the three formal tasks can
carry a real comparison. Two of the three answers are unwelcome: the tasks are not blind, and
the keys ask for facts their own bundles do not contain.

---

## 1. Evaluation isolation

### 1.1 What was leaking

| channel | state found | what an arm could get |
| --- | --- | --- |
| `answers/*_KEY.json` in the tree | 5 files, committed in `0ff9948`, shipped in tag `v1.0.0-rc.1` and in PR #27 on a **public** repo | every expected value, every trap, the grading note |
| public audit reports | `audit/RC-PREFLIGHT`, `audit/rc_integration/answers/*`, `docs/RC_V1.0.md`, `README.md` quote `0.6717`, `0.7135`, `96/111`, `0.5948`, `411202`, `RUN-002` binding | the same answers, without needing the keys |
| CASE_LIBRARY | `cases/internal/INT-SUCCESS-03.md` is project 19's CRPS line and states `SF=0.6717、GRUctx=0.7135`, plus `GRUctx 0.7091` | CAL-1's headline numbers verbatim, through a component tool |
| original project roots | `D:/workbuddy-work/19`, `/44`, `/48` exist on this machine with `VAL/`, `SEALED/`, full records | the ground truth, by walking the filesystem |
| `MANIFEST.json` in each bundle | carries `source_root: D:\workbuddy-work\19` | where to walk to |

The second and fourth rows matter more than the first. Removing the keys does not make the
tasks blind, because the answers are also in the reports and on the disk.

### 1.2 What was changed (minimal)

- Keys moved out of the tree to `~/.pdrw-eval/keys/agent_comparison-rc1/`; `answers/KEYS.sha256`
  records their sha256; `answers/README.md` states the exposure and its consequences.
- Each run workspace is a copy of `inputs/` plus `PROMPT.md` **only** — no manifest, no keys, no
  sibling task, nothing above the root.
- `PLAN.md` §3a records all of this, including that the claim "CASE_LIBRARY cards are drawn from
  other projects" was wrong.

### 1.3 What could not be fixed from inside the repository

Nothing stops a determined arm from reading `D:/workbuddy-work/19` or this repository's git
history. There is no OS-level restriction on the arm's filesystem, and the component itself says
so (`EXECUTION_ASSURANCE.md` §1: no trusted SEALED isolation). So the honest label is:

- **grading is blind** — arm labels stripped, order shuffled per task, two independent graders,
  neither told which system produced which;
- **execution is not** — an arm that chose to read outside its workspace could have found the
  answers, and self-reported `calls.log` is the only evidence that it did not.

Leakage flatters the arm that reads more files, which is B. Any B advantage measured here is
therefore an **upper bound**, not a lower bound.

---

## 2. CAL-1 and CAL-2, actually run

Four runs, one model family, identical inputs, identical prompt, identical budget, no human
intervention. A = shell + Python + editor. B = A + the installed Skill and the CLI.

| task | arm | wall | calls | D1 correctness | D3 contribution | D4 boundary | major errors |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CAL-1 | A | 2.3 min | 15 | **2** | 3 | 3 | 0 |
| CAL-1 | B | 2.2 min | 20 | **3** | 3 | 3 | 0 |
| CAL-2 | A | 1.9 min | 16 | 2 | 3 | **2** | 0 |
| CAL-2 | B | 1.9 min | 22 | 2 | 3 | **3** | 0 |

Two graders per task scored independently; both produced identical integers on every dimension,
so no adjudication was needed. The three-grader rule in `PLAN.md` §5 was revised to two graders
plus author adjudication on any ≥2-point gap, and that revision was made before the first score
existed.

### 2.1 The differences are small and each has a name

**CAL-1, D1: 0.7091 vs 0.7135.** Both arms recomputed everything and both found that the
report's `96/111` does not reproduce — `97/111` in `CRPS_L2_EVAL.json`, `92/111` in
`CRPS_L2_ALGO_ROUND.json` — and both traced the audit's 96 to a stale per-date count
(`26/34` on 2025-01-13 where the pairing gives `27/34`). The only difference is which file the
macro was filed under: A used the algorithm-round file (`0.70909`), B used the main L2 file
(`0.713501`, the keyed value). The prompt asks for one `file` field for both schemes and never
says which file the macro must come from, so this is a **convention mismatch, not a capability
gap**. Both graders said so in `key_dispute` and still scored per the key.

**CAL-2, D4: 2 vs 3.** Both quoted the eight unauthorized items verbatim and both put the
boundary at the step. A's `cannot_do_without_new_grant` dropped `read VAL/`; B kept it. The
graders counted that as a required item, not a phrasing difference.

**CAL-2, the interesting one: the component made B more wrong, not less.** B ran
`verify-run RUN-002`, got `RUN_HISTORY_NOT_ATTESTABLE / HISTORY_SOURCES_MISSING`, and reported
`bindable=false`. The key says `true`. Both graders scored B's D1 = 2 and refused to call it
fabrication, because B's reasoning is reproducible and its numbers exact — the bundle really does
contain only `metrics.json`, with no `run_manifest.json`, `verification.json` or
`predictions.jsonl` to close a hash chain. A said `true`, but its status field is its own recount,
not a binding check. So on this field **the component produced a defensible false negative and the
baseline produced a defensible unverified positive**, and the key picks one of the two readings
without saying so.

### 2.2 The keys ask for facts their bundles do not contain

Both graders, independently, on both tasks:

- **CAL-1**: `does_not_license` and `strongest_deployable_baseline` are keyed to
  `TRAINING_PROTOCOL_AUDIT.md` (`85.3%` shared test frames, `37.6%` of training frames). That file
  is not among the four frozen inputs, so no answer can reach the keyed statement. The key's own
  grading note ("names a real boundary — unit, corpus, or mechanism") is what saved it.
- **CAL-2**: `next_legal_action` is keyed to "a zero-new-fit re-analysis", but `STATE.md:13` says
  `NEXT_ACTION_OWNER = NONE` and "唯一下一合法行动＝NONE（HOLD）"; and `bindable` is keyed to a
  tool result that requires files absent from the bundle.

This is the calibration failing at its own job: a key that cannot be reached from the frozen
inputs cannot certify a grader. Both keys need one revision pass before they are used again —
add the missing file to CAL-1's bundle, and decide CAL-2's two ambiguous fields in writing.

---

## 3. Formal tasks

### 3.1 T1–T3 cannot be blind

Exposure measured against the current public tree, after the keys were removed:

| task | key | answer values already in public reports | verdict |
| --- | --- | --- | --- |
| T1 | public (now offline) | project 48's records quoted in `audit/SCIENCE-03B/03C/03D/04`; its key is qualitative (mechanisms + probe) | exploratory only |
| T2 | public (now offline) | 4 of 6 numeric tokens (`0.0003`, `0.0084`, `0.0625`) appear in `audit/rc_integration/answers/S1_report.json` and `docs/RC_V1.0.md` | exploratory only |
| T3 | public (now offline) | all 6 numeric tokens (`0.0625`, `0.5894`, `0.5948`, `0.6717`, `0.7135`, `1464`) appear in public audit docs | exploratory only |

They remain usable for regression ("does a change break what used to work") and for an
**exploratory** comparison that is labelled as such. They cannot support a blind claim.

### 3.2 No unexposed formal task currently qualifies

Checked, not assumed:

- The only projects with PD-RW records are 19, 44 and 48, and all three are quoted in the public
  audit; the case library additionally quotes 19's numbers.
- The other directories under `D:/workbuddy-work` (10, 15, 21, 22, 42, 46, 47, …) have no
  `STATE.md` and no PD-RW record; they are not research projects in this sense and cannot supply
  a key.
- A new task would have to come from a new project with real records — that is research work,
  not evaluation work, and inventing one to fill a table would be exactly the "manufacture a Run
  for a test" this round forbids.

### 3.3 No real DEV task is authorized

The one low-cost real DEV that this round was allowed to schedule **if** the original grant was
explicit. It is not:

| project | the line that decides it |
| --- | --- |
| 19 | `STATE.md` §3: the action-conditioned candidate is still "待决策"; no grant line exists |
| 44 | `STATE.md:13`: `NEXT_ACTION_OWNER = NONE`, `HOLD`, "不再追加同类消融、新模型或新预测分析"; `:14` STOPPED_SCOPE covers new prediction analyses |
| 48 | `STATE.md:47`: `HOLD_RELIABILITY + H8_PENDING`, "下一步唯一合法行动 = H8 作者决定" |

So **NOT_SCHEDULED**, and the distinction the round asked for is preserved: T1/T2 measure
*plan design*, not DEV completion, and no execution task exists to measure. A design score is
not a substitute for a Run, and this document does not present it as one.

---

## 4. Cost and errors

| item | value |
| --- | --- |
| subject wall clock | 2.3 + 2.2 + 1.9 + 1.9 = **8.3 min** |
| subject tool calls | 15 + 20 + 16 + 22 = **73** (cap was 60 each; none exceeded) |
| grading | 4 blind grader runs, 2 per task, ~9 min total |
| paid compute / downloads / training / GPU | 0 / 0 / 0 / 0 |
| tokens | `NOT_MEASURED` (host exposes no meter) |
| major errors | **0** across four answers — no fabricated number, no reserved read, no repeated experiment |
| wrong fields | 2 (A's CAL-1 file attribution; B's CAL-2 `bindable`), both reasoned and disclosed |
| protocol incidents | 0; B disclosed the `project-map.json` and the STUB rule root it wrote to make the CLI load |
| budget exceeded | no |

The two wrong fields are the most useful data in the table: they are not sloppiness, they are the
two places where the task's own definition is underspecified.

---

## 5. Verdict

**Next batch of real scientific comparison: `NOT_READY` — and the blocker is not the agent.**

What *can* start now: an **exploratory** comparison on T1–T3, labelled non-blind, scored with
`RUBRIC.md`, useful for seeing where the two arms diverge on plan design. What cannot start: a
blind comparison of real DEV work, because (a) every task on this machine is reachable from the
arm's filesystem, (b) no project has an open grant for a new Run, (c) the only three formal tasks
are contaminated, and (d) the two calibration keys have unreachable fields.

Minimum unblock, in order of cost:

1. **One run environment that mounts only the bundle** (container or VM, no `D:/`, no repo, no
   network). Until then no task is blind, and every number carries an unknown upward bias toward
   the arm that reads more.
2. **One author grant** for a bounded CPU DEV task on a live project — this is what makes "real
   DEV" measurable at all; without it the comparison measures design only.
3. **Fix the two keys**: add `TRAINING_PROTOCOL_AUDIT.md` to CAL-1's bundle; decide in writing
   whether `bindable` means "record resolves" (key: true) or "hash chain attests" (B: false), and
   whether `next_legal_action` is the record's `NONE` or a permissible read-only re-check.
4. **Three graders**, or the revised two-plus-adjudication rule declared before scoring (it was,
   here; no gap appeared, which is weak evidence that the rubric is tight, not strong).

What this round does **not** license: any statement that B is better than A. The measured
difference is +1 point on one dimension in each task, from a file-labelling convention and one
list item, on 2.2–2.3 minute tasks whose answers were public. It is a calibration of the
harness, not a result about the component.

---

## 6. Evidence

```
audit/agent_comparison/runs/CAL-1/{A,B}/{answer.json,notes.md,calls.log}
audit/agent_comparison/runs/CAL-2/{A,B}/{answer.json,notes.md,calls.log}
audit/agent_comparison/runs/scores/{CAL-1,CAL-2}_{r1,r2}.json
audit/agent_comparison/runs/MAPPING.json      # answer_N -> arm, per task
audit/agent_comparison/answers/KEYS.sha256    # key identity without the key
audit/agent_comparison/run_sheet.csv          # filled rows for the four runs
```

Keys: `~/.pdrw-eval/keys/agent_comparison-rc1/` (outside the repository, outside every run
workspace).
