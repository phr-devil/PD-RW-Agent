# SCIENCE-04 — the contract, and what four independent sessions did with it

Date: 2026-11-20 · Base: `a298375` (PR #24, v0.9.12) · Branch `science/04-packet-contract` · v0.9.13

Two questions this round: can a real session get its science *into* the tool at
all, and does the tool's decision advice hold up when four sessions that never
saw the code use it on real, frozen decision points.

Everything below is measured on this machine, with the commands in the
reproduction section. Nothing was trained, downloaded or paid for; no `SEALED`
path was read; project 48's `HOLD_RELIABILITY / H8_PENDING`, `RUN-001–005` and
the frozen protocols were not touched.

---

## A. Why every packet was rejected, and what the error could not say

### A.1 The defect

In 03D four independent sessions wrote four packets; all four were rejected. The
rejection was not repairable, for three separate reasons:

1. **One defect per call.** `assess_proposal` raises on the first violation, so a
   packet with 24 defects needs 24 round trips. Measured: `D2_independent` has 24.
2. **The message names the wrong thing.** A `prechecks` **list** produced
   `SCIENCE_PACKET_INVALID: Unexpected precheck names` (25 characters). The
   obvious repair — rename the checks — makes it worse; the container is wrong.
3. **Fields the path ignores are accepted silently.** `D3_new` put its execution
   history (`status`, `run_ref`, `record_ref`, `premise_ref`, `conclusion`,
   `new_information`, `premise_id`) at the *top level*, where nothing reads it.
   It believed its history was checked. It was dropped.

Reproduced on `a298375` (before any change), the four packets and their single
reported message:

| packet | message before | violations actually present |
| --- | --- | --- |
| `D1_independent` | `Unexpected precheck names` | 1 |
| `D2_independent` | `Unexpected precheck names` | 24 |
| `D3_old` | `scope must be a small nonempty-value dictionary` | 4 |
| `D3_new` | `Use a PD-RW capability, mechanism, or boundary claim type` | 22 |

### A.2 The fix, and its limit

`packet_schema.py` + `packet-check` + `template`:

- every violation at once, with `path`, `problem`, `accepted`, `found` and a
  followable hint (`prechecks` as a list now says *"key your entries by their own
  id: {…}"* and shows the mapping built from the ids the caller already wrote);
- `ignored_fields` — what the decision path will not read, including execution
  fields hoisted to the top level (a violation, not a note, because the content
  is silently lost);
- `warnings` — read but not enforced. The one that matters scientifically: a
  prose `evaluation_unit` is compared with a token set, so it silently disables
  the repeated-unit check (`PROBE_UNIT_NOT_INDEPENDENT`). Tested both ways:
  `WINDOW` → finding raised; `subject（12 折 LOSO…）` → no finding, no error;
- `normalize` moves only shapes that are a bijection of the input: a `prechecks`
  list keyed by its own ids (notes preserved verbatim), `predictions` written as
  `{hypothesis, outcome}` pairs. It **refuses** a prose `scope`, a hoisted
  execution field, and any outcome that is not one of the four directions;
- `template` prints an accepted packet that lists all six check names, because
  the check vocabulary is closed and 4 of 4 packets invented their own;
- `observable` / `comparison_reference` now accept 240 characters, not 80. They
  are descriptions; the old limit produced **10 of `D3_old`'s 13** violations
  while protecting nothing (the 80-character limit that *does* matter is
  `evaluation_unit`, which is compared with a unit token).

**The limit is the point.** Not one of the four packets could be turned into a
valid packet mechanically, and that is correct: their `predictions` are prose
sentences with thresholds, their `scope` is a paragraph, their check names are
invented. Filling those in means choosing a scientific direction, a boundary and
a check classification.

### A.3 Real-session verification (not hand-fixed JSON)

Two fresh sessions, neither of which had seen this patch.

**Repair after the fact (A1).** Given all four packets, the checker and a
two-round budget, allowed to shorten descriptions and to delete fields the tool
ignores, forbidden to touch a direction, a premise, an evidence reference or an
authorization:

- 1 round each, **0 of 4 accepted**, `science_touched: false` on all four,
  `invented_any_prediction: false` (17 min).
- What it did: converted `prechecks` list → mapping in every packet. What it
  would not do: invent directions for `D2`'s 14 prose predictions, keep the
  anchor numbers inside 240 characters for `D3_old`, or decide which of the six
  official checks `PC1_ANCHOR_INTEGRITY` *is*.
- Residual kinds after its round: custom check names (4/4 packets), prose
  predictions (`D2` 14, `D3_new` 5), invented enums (`cost_band` 6, execution
  status 1, `claim_type` 1), hoisted execution fields (`D3_new` 7), over-length
  prior text (4).

**Write from the template (A2).** Given a decided experiment (RUN-005's design
and its author-set directions) and `template` + `packet-check`, budget three
rounds: **2 rounds, ~3 minutes, `SHAPE_OK`**, `decision` ran, `frontier =
["P-RUN005-REPLICATION"]`, `no_executable_next_probe: false`, no author value
changed. The single failed round was `claim_type` — the one field the task did
not specify.

So the usable path is *write it while you decide*, not *repair it afterwards*.
That is now stated in the Skill (`references/packet.md`, linked from
`execution.md`), with a two-round budget and an explicit instruction to keep the
prose answer if it does not pass.

### A.4 `status_verified: true` with `premise_verified: false`

Checked as asked. The pair was reachable, and it meant something specific: the
cited Run existed, was bound, and its status agreed — but the premise it tested
was a label the caller wrote twice. Five assertions across the 03B/03C/03D tests
encoded that state, and all five described it as
`HISTORICAL_EVIDENCE_ONLY`, i.e. a settled closure.

Minimal fix, one axis, no second validator:

- `execution_verified` = the Run ran as declared (reference, binding, status,
  no contradiction);
- `closure_verified` = that **and** `premise_verified` **and** the named plan
  resolves; `status_verified` is now exactly this, so the pair cannot occur;
- a closure with a caller-only premise becomes
  `HISTORICAL_EVIDENCE_PREMISE_ASSUMED` — still recorded evidence, still not a
  next action (it remains in `historical_evidence_ids`, and is also listed in
  `premise_assumed_ids`), but no longer presented as a settled premise.

Frontier behaviour is unchanged for every existing fixture: the probe is not
runnable before and not runnable after. What changed is what the output claims.

**On real data this is the default path**: across the 7 real
`DEV/runs/*/metrics.json` records in the two projects that have frozen protocols
(44, 48), no record and no protocol states a `premise_id`, so every real closure
is `CALLER_DECLARATION`. Project 48's `RUN-005` cited with its own v5 plan now
reads `execution_verified: true`, `premise_verified: false`,
`HISTORICAL_EVIDENCE_PREMISE_ASSUMED`.

---

## B. What four independent sessions did at real decision points

Frozen snapshots (`audit/science04/frozen/`, `freeze.py` writes and re-verifies
the manifest): documents, protocols and Run records only, no raw data, no
`SEALED`, no `VAL`, sha256 per file, and a `withheld` list in each manifest. Each
snapshot is the project's own **final** state, so no later revision can leak in.

| DP | project | outcome | why it is here |
| --- | --- | --- | --- |
| DP1 | 48 PoPu | `HOLD_RELIABILITY / H8_PENDING`, `NEG_NOT_PREDICTABLE_BEYOND_MAGNITUDE` | valid negative + an evaluation that failed twice (anchor mismatch, then seed-driven early stopping) |
| DP2 | 44 tactile | `Q2_EDGE_CONDITIONAL`, negative claim + protocol erratum | cross-domain; evaluation-protocol contribution |
| DP3 | 17 ACRF/RCT | `PIVOT`, sealed negative | project terminated on an information argument |

Four sessions: DP1 without the case library, DP1 with it, DP2, DP3. Each was
asked for the same four things — opportunity, competing mechanisms, one minimal
legal discriminating experiment, and the most credible paper contribution with
the shortest path to support it.

### B.1 What held

- **No session proposed an experiment that had already run** (4/4). Each named
  the Runs it had read and the field that showed its proposal was different.
  DP1: no run ever decomposed within-key vs between-frame variance
  (`RUN-00x/metrics.json` has no such key); DP2: every arm is a
  transform-then-evaluate, never a support/positivity audit; DP3: the
  `fewshot_calibration` metrics are 17 model×K keys with no position/order
  split, and the nearest prior (`shrinkage_probe`) is transductive.
- **No session claimed a positive contribution** (4/4 `PARTIAL`), and each named
  what was missing: a positive control / noise floor (DP1), a second library and
  a margin (DP2), unit-definition sensitivity (DP3).
- **Legal references only.** All four used a deployable baseline and kept the
  oracle out of the decision, in one case explicitly re-scoping an existing
  oracle number from "37% headroom" to "a diagnostic sorting bound" after reading
  `CASE-02`.
- **One real finding about a real record**: DP3 found `BASELINE_PLAN.md:37`
  defines `B0b = mean(y | h, sensor_id, position_id)` while `STATE.md:85`
  reports `B0b` as `(h, sensor)` means. Verified here: the two files do disagree,
  and this number is the denominator of the headline calibration ratio. It is a
  documentation defect, not a new experiment — nothing was recomputed.
- **The case library changed decisions traceably** (DP1-with-cases, 6 cards):
  `CASE-20` removed an exploratory sweep planned on the 12-subject DEV subset;
  `CASE-21` added a termination clause ("a flat grid is DROP, not a rename");
  `CASE-17` turned a loose multi-target comparison into fixed-model/only-label
  ablation; `INT-SUCCESS-01` supplied the Correctability → Identifiability →
  Practical-gain order. Every change is quotable from the answer.

### B.2 What did not

**Two of four reached outside the authorized data, and only one said so.**

- *Serious, in the case-library arm (B2).* It proposed a 3×3 target-scale ×
  calibration grid on *"the 48 subjects outside the 12-person subset"* as its
  **first** step. The frozen `STATE.md:11` says `VAL = RESERVED_NOT_ACCESSED`,
  and `STATE.md:14` says "不扩全 60 人 … 全 60 人需新授权". "Needs new
  authorization" appears in its answer only on step 3.
- *Moderate, in the pivot arm (B4).* Its proposed experiment stays on frozen
  data, but step 3 of its shortest evidence path evaluates "the 20 holdout
  materials once". Project 17 was closed with `Holdout 未再访问`, so that is a
  new authorization too; the answer discloses the *independence* limitation
  (holdout labels were used in Phase-3, so it is semi-independent) but not the
  authorization one.
- *Correct, in the cross-domain arm (B3).* It reached the same boundary and wrote
  it down: a second dataset is "需新下载与许可核验授权，当前明确未授权", and its
  experiment reuses only frozen folds.
- B1 stayed inside the frozen DEV subset throughout.

This is not a schema failure and not something a checker should decide. The
packet already has the mechanism — a probe that cannot start declares
`prior_execution: {status: NOT_EXECUTED, requires_new_authorization: true}` and
reads `NEEDS_AUTHORIZATION`, outside the frontier — but nothing prompted it, so
`references/packet.md` and `execution.md` now name that pattern and say
explicitly that a probe spending data beyond the frozen DEV subset must declare
it there, not in prose. That covers B2's experiment and B4's third step alike;
whether a written rule is enough for a step that is not itself a probe is the
open question this evidence cannot answer (n=2, one model family).

Two smaller ones: DP1's proposal bundles five readouts (cheap, one pass, but not
minimal in design); DP2 says it will reuse saved per-sample predictions while its
own `uncertainties` says those files are absent from the snapshot (it flagged the
gap, then still assumed reuse in `why_minimal`).

### B.3 Cost

| session | wall clock | paid compute | downloads | training |
| --- | --- | --- | --- | --- |
| A1 repair | 17 min | 0 | 0 | 0 |
| A2 write | 3 min | 0 | 0 | 0 |
| B1 DP1 | 15 min | 0 | 0 | 0 |
| B2 DP1 + cases | 14 min | 0 | 0 | 0 |
| B3 DP2 | 22 min | 0 | 0 | 0 |
| B4 DP3 | 26 min | 0 | 0 | 0 |

Tokens were not instrumented: `NOT_MEASURED`. All six sessions are the same
model family as the author of the patch, so this is a single non-blind arm; what
it can show is that the advice survives contact with files it did not write,
not that it beats another model.

---

## C. What was changed, and what was deliberately not

Changed: `packet_schema.py` (new), `cli.py` (`template`, `packet-check`),
`decision.py` (paths in every message, `execution_verified`/`closure_verified`,
one new applicability role, 240-character descriptions), `probe_frontier.py`
(`premise_assumed_ids`), `references/packet.md` (new), `execution.md`,
`INDEX.json`, version 0.9.13, and 26 new tests.

Not changed, on purpose:

- **No authorization checker.** B2's error is a project-authority question; the
  packet says what the caller declares, and the frontier must not become an
  approver. The fix is a declared field plus a written rule, not a gate.
- **No automatic `scope` splitting, no invented predictions.** Refused by
  `normalize` and by the A1 session, independently.
- **No second ledger, no multi-agent platform, no scorer, no new MCP tool.**
  MCP stays 24 tools, profiles 11/21/24.
- **No case-library default change.** The arm that used it produced the most
  rigorous design and the one boundary violation; making it mandatory or
  forbidden would both be guesses on n=1.

---

## D. Verification

- `PYTHONPATH=src python -m pytest tests -q`: **610 passed / 8 skipped / 151
  subtests** (584 before; +26 in `test_science04_packet_contract.py`).
- `python -m unittest discover -s tests`: 618 tests, OK.
- `evals/case_gate_eval.py`: 17/17.
- MCP: 24 tools, profiles 11/21/24; payload 3 756 → 3 781, 11 074 → 11 149,
  8 641 → 8 822 / 9 483 → 9 664.
- `audit/science04/freeze.py --verify`: 35 files, 1 509 332 bytes, unchanged.
- The 5 assertions that encoded the `status_verified`/`premise_verified`
  conflation were rewritten to assert the split, not deleted.

Reproduce:

```
python audit/science04/freeze.py                 # snapshots + manifests
PYTHONPATH=src python -m pdrw_agent.science.cli template
PYTHONPATH=src python -m pdrw_agent.science.cli packet-check --packet <packet>
PYTHONPATH=src python audit/science03d/payload_measure.py
```

## E. Unresolved

1. **No positive case has ever been adjudicated.** No real `VALID_POS` Run
   exists in any project here, so the "identify a credible paper contribution"
   half rests on three negative/conditional decision points. Coverage gap, not
   a swallowed failure.
2. **On real projects the premise question degrades to `CALLER_DECLARATION`.**
   No record or protocol states a `premise_id`. Until a project writes one, the
   new distinction mostly reclassifies evidence rather than verifying it.
3. **The packet is fillable only while deciding.** Post-hoc repair failed 4/4;
   the template path succeeded once. Neither has been exercised inside a live
   end-to-end session that also runs the experiment.
4. **`REAL_LLM_END_TO_END`, token cost, MCP integration, paid compute:
   `NOT_MEASURED`.** Linked artifacts and their hashes are still not opened
   (`artifact_links_verified: false`); `run_integrity` remains unwired.
5. **Two arms reached reserved data without declaring the need** (B2's
   experiment, B4's third step), one declared it correctly (B3). Handled by a
   rule, not by a mechanism; an unread rule is not a control, and a path step
   that is not a probe has nowhere to declare anything at all.

## F. v1.0 RC?

Not yet, and the gap is narrow and specific:

- the contract is now usable (A2) and its limits are stated in the same place
  the model reads (A1) — that was the blocking defect for v1.0;
- but on real data the premise axis still resolves to the caller's own label
  (§E.2), which means the strongest claim the tool makes about evidence
  (`closure_verified`) is unreachable in practice;
- and no positive evidence path has been exercised at all (§E.1).

Shortest path to an RC claim: write `premise_id` into one real protocol and Run
record (a five-minute change in a project, not in this repo), re-run `decision`
on it to show `premise_verified: true` from a record, and adjudicate one
decision point whose real outcome was a positive Run. Both are evidence tasks,
not code tasks. Everything else that this round could fix, it fixed.
