# SCIENCE-03D — a premise label is not a bound premise (v0.9.12)

Date: 2026-11-20. Base: PR #23 / `16e7dd4` (v0.9.11). Branch: `science/03d-premise-evidence`.
Scope: close the last principled error of SCIENCE-03, measure what the fix does and does not buy,
and hand over. No SCIENCE-04 feature work, no merge to `main`, no training, no change to project
48's Runs or protocols.

## 1. The defect, reproduced before any patch

`decision._prior_execution` decided "was this run under this premise?" by comparing two strings the
caller wrote: `prior_execution.premise_id` and `proposed_premise.premise_id`. A real Run, readable,
status-consistent and bound to a *different* frozen plan therefore closed the probe.

Fixture: `audit/science03d/fixture-project` (built by `build_fixture.py`), two frozen plans with
`premise_id` (`BEAM_STIFFNESS_MECHANISM`, `SENSOR_DRIFT_MECHANISM`), `RUN-101` executing the beam
plan with `protocol_id` + `protocol_sha256`, `RUN-102` a copy whose record still says `RUN-101`,
`RUN-103` aggregate numbers only.

`python audit/science03d/repro_prefix.py` on unmodified `16e7dd4` (`repro_before.json`):

| packet | verdict before | why it is wrong |
| --- | --- | --- |
| cites RUN-101, premise = SENSOR | `HISTORICAL_EVIDENCE_ONLY`, `status_verified: true`, `premise_binding: MATCH` | RUN-101 executed the beam plan; only the caller said "sensor" |
| same, but the single probe in the packet | `frontier: []`, `no_executable_next_probe: true` | the never-run sensor experiment is reported as nothing to run |
| cites `DEV/runs/RUN-102` | `HISTORICAL_EVIDENCE_ONLY`, `status_verified: true` | the directory holds RUN-101's record; identity never checked |
| cites RUN-103 (numbers only) | `CLOSURE_DECLARED_NOT_VERIFIED` but `file_binding: BOUND` | a readable file was reported as a bound Run |

After the patch (`repro_after.json`): `NOT_YET_RUN` + `CLOSURE_PREMISE_CONTRADICTED` for the first two,
`STATUS_CONFLICT` for the copied Run, `METRICS_ONLY` + `CLOSURE_DECLARED_NOT_VERIFIED` for RUN-103.

## 2. What was changed (one resolver, one axis, no new machinery)

`science/feedback_link.bind_run_reference` keeps answering only "what does this file say about
itself", and now reads three more things, all read-only, all inside the project (SEALED/holdout paths
still refused by `_resolve`):

- **identity**: `run_id` in the record against the directory or record filename it was found in
  (`run_id_consistency`), and whether the file is a Run record or only metrics (`record_structure`);
- **premise stated by the record**: `premise_id` / `scientific_premise_id` / `premise`
  (`premise_id_recorded`);
- **the frozen plan it executed**: the record's `protocol_ref` or `protocol_id`, resolved as
  `protocol/<id>.json` / `protocols/<id>.json` inside the project, hash-compared with a declared
  `protocol_sha256`, and the plan's own `premise_id` read when present. A packet may add one optional
  field, `premise_ref`, naming the plan that encodes the premise under study; it is compared with the
  plan the record names (`premise_plan_match`).

`decision` then answers the premise question from that evidence, and says who answered it:

| `premise_binding_basis` | meaning | effect |
| --- | --- | --- |
| `RUN_RECORD` | the record states the premise | `premise_verified: true` when equal |
| `FROZEN_PLAN` | the plan the record names states the premise | `premise_verified: true` when equal |
| `PREMISE_PLAN` | the caller's `premise_ref` disagrees with the executed plan | `CLOSURE_PREMISE_CONTRADICTED` |
| `CALLER_DECLARATION` | nothing on disk speaks to it | `premise_verified: false`; evidence stays history, the label does not become evidence |

A contradiction returns the probe to `NOT_YET_RUN` with
`next_action: CONFIRM_WHICH_EXPERIMENT_THE_RUN_ANSWERED`, not `RUN_IF_LEGAL_AND_DISCRIMINATING`: the
experiment may be closed *elsewhere*, under the premise the Run actually executed. A plan the record
names but that cannot be read keeps the closure `CLOSURE_DECLARED_NOT_VERIFIED`
(`CLOSURE_PLAN_UNRESOLVED`); plan bytes that differ from the declared hash, or a directory holding
another Run's record, are `STATUS_CONFLICT`. `record_ref` is now actually passed to the resolver (it
was validated and ignored before). `artifact_links_verified: false` is returned explicitly: linked
artifacts and their hashes are still not opened here.

Old packets are unaffected: `premise_ref` is optional, custom binders with the 0.9.11 signature are
detected and called with one argument, and payloads without `prior_execution` are unchanged.

## 3. Verification boundary — what the axes do and do not prove

- `file_binding: BOUND` means a file was read, not that a Run exists. `record_structure` separates the
  two; a `METRICS_ONLY` file cannot close anything because it carries no status.
- `run_id_consistency` compares a label with a directory name. A correct label on a wrong file is not
  detected; only a disagreement is.
- `premise_verified` requires the record or its plan to *state* a premise. In the whole local fleet
  no Run record and no protocol carries `premise_id` (`grep` over the 7 real `DEV/runs/*/metrics.json` records in the two projects that have frozen protocols: 44, 48), so on
  real projects the answer is `CALLER_DECLARATION` even when the plan bytes match. That is reported,
  not hidden — and it is why `premise_ref` exists.
- `premise_plan_match` proves the cited Run executed the plan the caller named for the premise. It
  does not prove the plan *is* that premise; that remains a review judgment.
- `status_consistency` is still a bounded term match, `bind_run_reference` still reads one file
  (≤128 KiB) plus one plan (≤128 KiB), and no link hash or event chain is verified (that is
  `run_integrity`, still unwired).

Real-project check (`audit/science03d/real_48_check.py`, project 48 RUN-005):

| packet | result |
| --- | --- |
| premise `POPU_LOWER72_RECOVERY`, `premise_ref` = v5 protocol | plan bound, hash matches, `premise_plan_match: true`, `HISTORICAL_EVIDENCE_ONLY`, `premise_verified: false` (the plan states no premise) |
| premise `POPU_DEPLOY_UPPER72`, `premise_ref` = v3 protocol, still citing RUN-005 | `premise_plan_match: false` → `NOT_YET_RUN` + `CLOSURE_PREMISE_CONTRADICTED` |

## 4. Independent acceptance

Four packets were written by sessions that never saw this round's code or notes
(`tasks/D1_PRESS26.md`, `D2_PROJECT48.md`, `D3_old.md`, `D3_new.md`; transcripts summarised in
`packets/`). Result before any repair: **4 of 4 packets rejected on schema**, all for shape rather
than science — `prechecks` written as a list of objects (D1, D2), `scope` written as prose (D3-old),
`claim_type: DEPLOYABLE_INCREMENT` plus `predictions` as prose and free-text `cost_band` (D3-new). The
same rejections occur on 0.9.11 and on 0.9.12, so they are not a regression, but they mean an
independent session cannot currently get its packet adjudicated without either reading the schema
source or being told the exact shapes. That is the most consequential usability finding of this round
and is left to SCIENCE-04 rather than fixed here.

One packet (D1) had exactly one violation, the `prechecks` shape; `normalize.py` converts it
mechanically and writes `D1_fixed.json` (no content change). A second file, `D1_misattributed.json`,
changes exactly one field of that independently authored packet: the premise label of the probe that
cites RUN-101, from `BEAM_STIFFNESS_MECHANISM` (honest) to `SENSOR_DRIFT_MECHANISM` (what a session
that conflates the two lines writes). Both arms were then run on the same packets
(`eval_packets.py` → `eval_packets.json`).

| packet | 0.9.11 | 0.9.12 |
| --- | --- | --- |
| `D1_fixed` (honest labels) | frontier `P1, P2, P4`; the copied Run `P2` offered as a fresh experiment | frontier `P1, P4`; `P2` → `STATUS_CONFLICT`, `EXECUTION_STATUS_CONFLICT` |
| `D1_misattributed` | `P1` → `HISTORICAL_EVIDENCE_ONLY`, `status_verified: true`, "do not rerun" | `P1` → `NOT_YET_RUN`, `CLOSURE_PREMISE_CONTRADICTED`, "confirm which experiment the Run answered"; `P2` → `STATUS_CONFLICT` |

Blind review: a fresh session was given both pairs with the arm labels shuffled and the fixture files
(`review_bundle.json`; key in `review_key.json`, not shown to it). It verified each Run's plan and hash
against the files itself, then chose, for `D1_fixed`, the arm that "did the checkable provenance and
flagged the copied Run" and, for `D1_misattributed`, the arm that "judged the beam negative to be
another premise's evidence and flagged the run_id conflict". Unblinded, both choices are 0.9.12
(pair 1: B = new; pair 2: A = new).

The review also produced two corrections that are in the code: (a) `next_action` no longer says "run
it" for a contradicted probe (a probe that *is* the other experiment is closed there, not here);
(b) the finding's question now asks which experiment the Run answered, instead of implying the probe
is new. Its remaining criticism is accepted and documented rather than engineered away: a contradicted
probe stays in the frontier, because excluding it would re-close a live experiment on the strength of
a label — the exact error this round fixes.

Cost, measured: four independent sessions, self-reported wall clock 4–5, 8–10, 10–12 and 8–10 minutes
(one blind review, ~10 minutes); zero API cost, zero downloads, zero training. Token counts and
"the model decides better" remain `NOT_MEASURED`: the sessions' content judgments were not adjudicated
by the tool, because their packets were rejected, and one model wrote both the checker and the audit.

## 5. Preservation

| Requirement | Status | Evidence |
| --- | --- | --- |
| H1–H10, H5-with-H6, H7 in-scope DEV, SEALED, authorization boundaries | unchanged; no new node, approver, ledger or stop | full suite **584 passed / 8 skipped / 151 subtests** (568 + 16 new); `case_gate_eval` 17/17 |
| Old packets / old binders | accepted; a one-argument binder is still called with one argument | `test_a_binder_with_the_old_signature_still_works`, `test_a_packet_without_execution_fields_is_unchanged` |
| MCP surface | 24 tools, profiles 11/21/24, none added | `PROFILE_TOOLS` |
| Payload | clean two-probe 3 726 → 3 756 (+0.8%), three defective 10 984 → 11 074 (+0.8%), three-probe history 8 180 → 8 641 (+5.6%) | `payload_measure.json` |
| Project 48 | HOLD_RELIABILITY / H8_PENDING untouched; no training; no Run or protocol edited | only read |
| Science-03 history | no Run, verdict or number rewritten in any project | `git status` in the project trees |

## 6. Can SCIENCE-03 close?

Yes, with the boundary stated. The five capabilities requested at the start of SCIENCE-03 are now
each carried by something checkable: a scientific obstacle is named as a finding rather than a score;
competing explanations and strong baselines are compared as declared probes with legal references; a
probe is only "next" if it is discriminating, legal, unclosed *under evidence* and authorized; repair
follows a named defect instead of a rerun; negative results stay as recorded evidence. The two
remaining principled errors found across 03B/03C/03D (a closed probe offered again; a cited Run
trusted on words) are fixed with boundary tests, and no known defect is left unhandled in this axis.

What is *not* established: that a real session chooses better experiments (packets fail the schema
before reaching the checker), that token or wall-clock cost falls, that the premise axis works on
real projects without `premise_id` in records or protocols, and any `VALID_POS` behaviour on real
data. SCIENCE-04 should start from the packet contract's usability, not from another checker axis.

`NOT_MEASURED`: `REAL_LLM_END_TO_END`, `VALID_POS`, token counts, paid compute, MCP integration,
real experiment cost, and scientific value of any decision.
