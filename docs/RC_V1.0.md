# PD-RW-Agent 1.0 — release candidate

**Status: release candidate, feature-frozen.** Package version `1.0.0rc1`, Skill
version `1.0.0rc1`, tag `v1.0.0-rc.1`. Nothing in this repository is merged to
`main`; the RC lives on `rc/v1.0-integration` and is mergeable as one history.

**What it is, before what it does.** PD-RW-Agent is a component that WorkBuddy
loads — Skill, CLI, optional stdio MCP server. It is not an LLM and it does not
compete with WorkBuddy. The division the RC assumes is: WorkBuddy executes;
PD-RW supplies the research rules; the project's own records supply the evidence;
ChatGPT supplies strategy and review. Every claim below is about what the
component adds *inside* that division, and the comparison plan in
`audit/agent_comparison/PLAN.md` varies that component rather than treating it as
a rival system.

This page exists so that no claim about the RC has to be taken from the README.
It separates three things that are easy to blur:

| Tier | Meaning | Where |
| --- | --- | --- |
| **A · accepted by a real WorkBuddy session** | An independent session, given only the Skill and the project, produced this behaviour and its tool calls are recorded | `audit/rc_integration/answers/` |
| **B · accepted by tests only** | A contract test pins the behaviour; no real session has exercised it | `tests/` |
| **C · `NOT_MEASURED`** | Nobody has measured it; do not quote a number | listed below |

Frozen identifiers (commit, Skill archive hash, MCP tool count, interpreter,
freeze-snapshot digest) are in
`audit/RC-INTEGRATION-v1.0.0-rc.1-2026-11-20.md` — they are recorded after the
build so that the hash is of the bytes that were installed, not of a draft.

---

## 1. Install

Three surfaces, one implementation. The CLI and MCP both dispatch into
`ResearchService`; the Skill is prompt text and grants nothing.

**Python package** (editable, Python ≥ 3.11):

```bash
cd PD-RW-Agent
python -m venv .venv && .venv/Scripts/pip install -e .     # POSIX: .venv/bin/pip
```

**Local configuration is mandatory and there is no default.** Without it every
project command returns `CONFIG_REQUIRED`:

```bash
export PDRW_AGENT_CONFIG=/abs/path/project-map.local.json
export PDRW_WORKFLOW_ROOT=/abs/path/Problem-Data-Research-Workflow
export PDRW_RUNTIME_DIR=/abs/path/runtime          # optional: receipts
export PDRW_CASE_LIBRARY_ROOT=/abs/path/CASE_LIBRARY  # optional: read-only cases
```

`project-map.local.json` maps a project id to its root and to the file names of
its `STATE` / `RESEARCH_RECORD` / `PAPER_BLUEPRINT`. A project that is not in
the map cannot be resumed — that is a property, not a bug: the map *is* the
operator's statement of which project a short id means.

**Skill**: build the archive, then import it in WorkBuddy. Rebuilding the
repository does **not** update an installed copy.

```bash
python tools/package_skill.py        # -> dist/pd-rw-research.zip
```

After importing, verify what was actually installed — an out-of-date Skill is
silent and will keep telling a model to use a field that no longer exists:

```bash
grep -n '^version:' ~/.workbuddy/skills/pd-rw-research/SKILL.md
# must print: version: 1.0.0rc1
```

**MCP** (stdio, optional): the server is `python -m pdrw_agent.integrations.mcp_server`
with the four environment variables above. Profiles: `minimal` 11 tools,
`research` 21 (default), `diagnostic` 24. The host must be restarted after an
upgrade, because the payload schema is read once at connect time.

---

## 2. Minimal scientific workflow

The whole point of the science CLI is that a decision is written **at the moment
of the decision**, not reconstructed afterwards — a session that was asked to
repair four declined packets repaired none of them, while a session that started
from `template` produced a valid one in two rounds.

```bash
# 1. A packet that already passes, with the closed vocabularies visible.
PYTHONPATH=src python -m pdrw_agent.science.cli template > my-packet.json

# 2. Edit only what is yours to decide: question, hypotheses, premise, probes,
#    predictions.  Never invent a prediction direction to satisfy the checker.

# 3. Every violation at once, each with a path and the accepted values.
PYTHONPATH=src python -m pdrw_agent.science.cli packet-check --packet my-packet.json
#    exit 0 = SHAPE_OK, exit 3 = violations.  Two rounds is the budget; if it
#    still fails, keep the natural-language answer and say so.

# 4. What can be the next experiment, and what may not.
PYTHONPATH=src python -m pdrw_agent.science.cli decision \
    --packet my-packet.json --project-root /abs/path/to/project
```

Read four keys and nothing else first:

| Key | What it answers |
| --- | --- |
| `frontier_candidate_ids_as_declared` | probes that can start today, under the current grant, and can still produce information |
| `needs_authorization_ids` | probes that would be decisive but spend a grant nobody has given |
| `historical_evidence_ids` | probes this project already answered — cite, do not rerun |
| `no_executable_next_probe` | `true` means the honest state is "nothing left to run here", not "pick the cheapest" |

`decision` is `ADVISORY_REVIEW_ONLY`. It reports `automatic_go: false`,
`automatic_stop: false` and `authorization_basis: CALLER_DECLARED_ONLY_NEVER_A_PERMIT`.
It never reads `SEALED`, `HOLDOUT` or a reserved `VAL` root, and it never writes
to a project.

---

## 3. What a real session actually did

Three independent sessions, none of which had seen this repository's source,
each given one project and the Skill. Recorded in
`audit/rc_integration/answers/` (`S1_*`, `S2_*`, `S3_*`), and summarised here
because the failures are more informative than the successes.

**Project 19 (CRPS) — positive result.** Two rounds of `packet-check`, then
`decision --project-root`: `frontier = [P1]`, `needs_authorization = [P2]`,
`historical_evidence_ids = []`. The session recomputed every mean from JSON
rather than quoting the reports, and found that the headline the reports still
carry (`0.6717 → 0.7135`, +4.18 pt) was **refuted inside the project** by a
same-condition control (`B−A = −0.84 pt`, `B′−B″ = −0.0003`, 5/5 dates
negative; `dev_h8_v1/results/H8_VERDICT.json`). What survives is narrower: the
**readout layer** — a closed-form linear probe instead of the jointly trained
softmax head — `A 0.7001 → P 0.7477` (+4.76 pt, 35/37, CI [+3.47, +5.99]) on 37
once-only episodes (`dev_h9_v1/H9_RESULT_REPORT.md`), carrying a disclosed
`underpowered` flag (CI width 0.0252 > the pre-registered 0.020). It also found
`96/111` rebuildable from no JSON at all (EVAL gives 97/111, ALGO_ROUND 92/111),
and `17/17` true only in `CRPS_L2_EVAL.json` (ALGO_ROUND: 15/17). The strongest
**deployable** baseline by number is `SF|lag3` 0.6717 — not the arm the report
calls the fair baseline (`DualHead` 0.6468, which is 2.5 pt *below* the
no-context baseline).

**Project 48 (PoPu) — valid negative + attribution.** Both packets passed
`packet-check` on the first round. Two packets identical except
`premise_ref`: pointing at the plan `RUN-005` executed gives
`attribution_basis: CALLER_PREMISE_PLAN` → `HISTORICAL_EVIDENCE_PREMISE_ATTRIBUTED`,
`CITE_AS_EVIDENCE_ONLY_AND_CONFIRM_THE_PLAN_IS_THIS_EXPERIMENT`, frontier empty;
pointing at another frozen plan of the same project gives
`attribution_basis: NONE` + `CLOSURE_PREMISE_CONTRADICTED`, probe back in the
frontier with `CONFIRM_WHICH_EXPERIMENT_THE_RUN_ANSWERED`. A probe declaring
`requires_new_authorization: true` (all 60 subjects / second library / SEALED)
stayed in `needs_authorization_ids` in both runs. `premise_verified`,
`status_verified` and `closure_verified` are all `false`: the record states no
`premise_id`, and the tool says so instead of rounding up.

**Project 44 (D1 tactile) — cold recovery + reserved data.** `identity` was
`DECLARED_ID_MATCH` with `identity_verified: false`; `rule_commit_local_only`
was a commit digest with `rule_freshness: REMOTE_NOT_CHECKED` — it proves which
rules were used, never that they are current. `history` returned
`HISTORY_SOURCES_MISSING` (no `STATE.json`, no `EVENTS.jsonl`), so the run list
is a Markdown echo rather than an event chain. Both reserved probes
(`VAL`, `SEALED`) landed in `needs_authorization_ids`; the session read no bytes
from either (verified by before/after `stat` on size/mtime/ctime/inode plus a
command audit), and stated plainly that the boundary held because it complied,
**not** because the tool enforced it.

---

## 4. Capability tiers

**A — accepted by a real WorkBuddy session** (this round, three sessions,
73 min wall clock total):

- `template` → `packet-check` → `decision` end to end on two different projects;
  packets accepted on round 1 (48) and round 2 (19, 44) of a two-round budget.
- Attribution: the same Run reads as *attributed* or *contradicted* depending
  only on which plan the caller names; a `NONE` basis is not evidence and not a
  next action.
- An unauthorized probe lands in `needs_authorization_ids` and stays out of the
  frontier, on real `VAL`/`SEALED`/60-subject boundaries.
- A cold session recovers identity, run, rules and permissions from disk, and
  reports which of those the tool could not supply.
- Recomputing a project's numbers from JSON instead of its reports, including
  catching a refuted headline and two coverage figures that no artifact supports.

**B — tests only**: the 617-test suite (including the frontier, dominance,
premise-binding and packet-contract matrices), `evals/case_gate_eval.py`
(13 gate calls, 9 verified checkpoints, 0 false/0 missed triggers), the MCP
profile counts, and the payload-size measurements. No human or model has
exercised most of these paths end to end.

**C — `NOT_MEASURED`**: token counts (no meter in the host; one session supplied
an estimate and it is labelled as such), real-LLM end-to-end success rate,
paid-compute cost, MCP integration inside the host (the stdio server was
verified by handshake, 21 tools, but the host session did not expose the tools,
so acceptance ran through the CLI), `artifact_links_verified` (still `false`),
`run_integrity` wiring, and any claim about research gain or time saved.

---

## 5. Known limitations

1. **`premise_verified` is unreachable on the data that exists here.** No
   recorded `metrics.json` and no frozen protocol in projects 19/44/48 states a
   `premise_id`; every closure resolves to a caller declaration. The middle
   level (attribution *to a named plan*) is reachable and was exercised; the top
   level needs a project-side edit before the next fit.
2. **The tool cannot decide that the plan you named *is* this experiment.** It
   compares the record's `protocol_id`/`sha256` with the bytes you named. The
   last step — "this plan is the experiment my probe describes" — stays yours.
3. **The Skill is not a permission system.** Its three-tier plan
   (`NOW` / `NEEDS_NEW_AUTHORIZATION` / `FUTURE_CONDITIONAL`) is text. The
   binder mechanically refuses `SEALED`, `HOLDOUT`, `CONFIRMATION` and a
   reserved `VAL` root (`FEEDBACK_LINK_PATH_REJECTED`), which was measured on
   project 44; nothing stops a session from opening those files itself. Only the
   host can enforce filesystem access, and it does not.
4. **`AUTH/BUDGET` is not echoed by `resume`.** The state index carries
   `HOLDOUT`, `BEST_VALID_RUN`, `MANUSCRIPT_WRITE_AUTH` and the task/next keys,
   but not the authorization line — and truncating it at 280 characters would
   drop the "not authorized" half, which is worse than omitting it. A recovery
   session must quote the line from `STATE.md` itself; the Skill says so.
5. **A run whose record exceeds 4 MiB is refused** (`RUN_RECORD_TOO_LARGE`) and
   reported as an unverified closure rather than silently accepted. The cap was
   128 KiB, which refused project 44's 411 202-byte fold-level record; that was
   fixed here and pinned by a test.
6. **No decision point with a positive real outcome has been adjudicated.** The
   H9 result is a project artifact, not a `VALID_POS` Run; the "recognise a
   credible contribution" half rests on one narrow confirmation plus four
   negative/conditional points.
7. **One arm, non-blind.** Every acceptance session, and this patch, come from
   one model family; the case-library on/off comparison is n=1. The frozen task
   set for the next round is `audit/agent_comparison/` — two calibration tasks
   (`CAL-1`, `CAL-2`) and three formal ones (`T1` scientific judgement, `T2`
   algorithm design, `T3` evidence validity and paper contribution). Each has a
   manifest with per-file hashes, a prompt, an exclusion list and a hidden answer;
   the copied project bytes stay local because this repository is public.
   Prepared and verified; **not run**.

---

## 6. Not claims

- Not a claim that the science is new, correct or publishable.
- Not a claim that a packet being `SHAPE_OK` makes it legal, decisive,
  authorized, or un-run: `packet-check` says so in its own `note`.
- Not a claim that a written plan is permitted: no packet field is a permit.
- Not a claim that `identity` is verified: `DECLARED_ID_MATCH` means the project
  map and `STATE.md` agree about a string.

---

## 7. What is frozen for evaluation

`audit/agent_comparison/` holds the v1.0 comparison as prepared material: a plan,
a rubric, five task bundles and five answer keys. Nothing there has been run.

| config | what it is |
| --- | --- |
| `A` | ChatGPT + WorkBuddy + PD-RW rules and records — the workflow without this component |
| `B` | `A` + PD-RW-Agent; the old ablation survives inside it as `B1` (Skill only) vs `B2` (Skill + CLI/MCP) |
| `C` | `B` + one external agent capability — feasibility checked read-only; AIDE is the only candidate that would add a capability this component lacks, and only on `T2` |

Held fixed: model family and version, the ChatGPT strategy brief (hashed), tool
permissions, and the budget — ≤ 40 min, ≤ 60 tool calls, ≤ 12 model turns, one
clarification, zero paid compute, zero downloads, zero training per (task, arm).

Scored on four 0–3 dimensions (scientific correctness, validity of the proposed
experiment, contribution calibration, boundary and authorization) with cost and
interventions recorded beside the scores and never folded into them. Three blind
graders, median with a fourth adjudicator when the range is ≥ 2, and major errors
counted rather than averaged. No config is favoured in advance, and the
pre-registered expectation is written down in `RUBRIC.md` so that a null result
still counts as a result.

To verify the bundles are the ones that were frozen:

```
PYTHONPATH=src python audit/agent_comparison/build_tasks.py --verify
```
