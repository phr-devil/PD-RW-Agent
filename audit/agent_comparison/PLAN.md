# Agent comparison plan — v1.0 RC

**Status: prepared, not run.** No arm has been executed against these tasks. This
file freezes what would be compared, on what inputs, under which budget, and how
it would be scored — so that the comparison cannot be redesigned after the
numbers arrive.

## 0. What is being compared

PD-RW-Agent is **not** a system that competes with WorkBuddy and it is **not** an
LLM. It is a component that WorkBuddy loads: a Skill (rules and procedure), a CLI
(`pdrw-agent`, `science`), and an optional stdio MCP server. PD-RW supplies the
research rules; the project's own records supply the evidence; WorkBuddy executes;
ChatGPT supplies strategy and review. The experiment therefore varies a
*component* inside one system, not one system against another.

| config | what runs | what it adds |
| --- | --- | --- |
| **A** | ChatGPT + WorkBuddy + PD-RW rules and project records | baseline: the workflow as practised before this component existed |
| **B** | A + PD-RW-Agent (Skill, CLI; MCP where the host exposes it) | the component under test |
| **C** | B + one external agent capability | read-only feasibility only this round (§6) |

The earlier component ablation is preserved as a **sub-axis of B**, not replaced:

- `B1` = Skill only (rules, packet format, three-tier plan; no CLI calls)
- `B2` = Skill + CLI/MCP (`packet-check`, `decision`, `resume`, `context`)

So the old A/B/C (WorkBuddy+PD-RW · +Skill · +Python/MCP) is still measurable, and
the new A/B/C sits above it. `evals/AB_C_CAPTURE_TEMPLATE.md` is updated to say
this instead of treating the Skill and the Python layer as rival systems.

## 1. Held fixed across arms

- **Model family**: one family, one version, recorded per run. A run on a
  different family is reported separately and never pooled.
- **ChatGPT strategy brief**: the same text, frozen with a sha256, given to every
  arm. It may state the question and the constraint; it must not contain the
  answer key, the project's later verdict, or a recommended probe.
- **Tool permissions**: identical filesystem scope (the bundle, read-only),
  identical shell access, no network. Component-specific tools are the variable.
- **Budget per (task, arm)**: ≤ 40 min wall clock, ≤ 60 tool calls, ≤ 12 model
  turns, ≤ 1 human clarification, 0 paid compute, 0 downloads, 0 training.
  Exceeding the budget ends the run and is recorded as such — it is a result, not
  an accident.
- **Output contract**: the task's `answer.json` shape, nothing else. Free-text
  reasoning is allowed in a separate `notes` field but is not graded.

## 2. Task set

Two calibration tasks, three formal ones. Bundles are frozen copies of real
project files under `tasks/<ID>/inputs/` with per-file sha256 in `MANIFEST.json`;
answers are in `answers/` and are never placed in a bundle.

| id | kind | project | dimension | what the arm must produce |
| --- | --- | --- | --- | --- |
| CAL-1 | calibration | 19 | recompute vs quote | five numbers and one boundary, recomputed from JSON |
| CAL-2 | calibration | 44 | identity, runs, permission | identity basis, rule digest, Run binding, the verbatim unauthorized list |
| T1 | formal | 48 | scientific judgement | ≥2 mechanisms with different predictions + the cheapest legal discriminating probe |
| T2 | formal | 19 | algorithm design | smallest legal fix after a refuted mechanism, with the unit rule and the budget argument |
| T3 | formal | 19 | evidence validity and paper contribution | tier, supported claim, unrebuildable figures, shortest evidence path |

Why these: 19 has a positive result, a refuted mechanism and a coverage dispute;
44 has a reserved `VAL`/`SEALED` boundary, a large Run record and an author HOLD;
48 has a valid negative with an invalidated sibling and a documented "do not run
this again" instruction. Between them they cover the four dimensions the release
claims, on artifacts that exist rather than on synthetic fixtures.

Rebuild or verify with:

```
PYTHONPATH=src python audit/agent_comparison/build_tasks.py --verify
```

## 3. Freezing and leakage

- The bundle is a **copy**, taken once; the source project may keep changing.
- **The copies stay local.** This repository is public and the projects are not,
  so what is committed is the manifest (paths, bytes, sha256, exclusions), the
  prompt, the build script and the answer key — never the project bytes.
  `build_tasks.py --verify` re-checks the copies on the machine that holds the
  projects, and a manifest is enough for a third party to confirm that the bundle
  they were given is the one that was frozen.
- Each bundle excludes the directories that hold the answer: `dev_h8_v1/`,
  `dev_h9_v1/`, `dev_h10_v1/`, `VAL/`, `SEALED/`, `REASSEMBLE/`. The exclusion
  list is in each `MANIFEST.json` and is part of the freeze.
- CASE_LIBRARY is **not** mounted for A or B in this comparison. It is read-only
  in the component and its cards are drawn from other projects; leaving it out
  keeps the arm difference to one variable. A later `B3 = B2 + case library` arm
  is legitimate but is a separate question and needs its own freeze.
- The answer keys are scored by a grader script or a human who has the key, never
  by an arm. An arm that has read `answers/` invalidates its own run.

## 4. Metrics

Scored per task on four dimensions (0–3 each, anchors in `RUBRIC.md`), plus three
recorded-but-not-scored quantities:

| scored | recorded |
| --- | --- |
| scientific correctness | wall clock |
| validity of the proposed experiment | tool calls and turns |
| innovation and paper-contribution calibration | tokens (`UNKNOWN` if no meter) |
| boundary and authorization handling | human interventions |
| | major errors (counted, weighted in the write-up) |

Cost is never converted into a quality point. A cheaper arm that is wrong is
wrong; a more expensive arm that is right is still more expensive.

## 5. Grading protocol

1. Three graders, none of whom built the arm they grade; each receives the
   answer files with the arm label stripped and the order shuffled per task.
2. Each grader scores independently against `answers/*_KEY.json` and `RUBRIC.md`.
3. Agreement: the median per dimension. If the range on any dimension is ≥ 2
   points, a fourth grader adjudicates that dimension and writes one paragraph
   saying why.
4. Major errors are counted, not averaged: a fabricated number, a repeated
   already-answered experiment, a reserved-data read, or an overclaim that the
   key names. One major error caps the task score at 1 regardless of the rest.
5. No arm is favoured in advance. The pre-registered expectation is that A and B
   differ mainly on boundary handling and on numbers actually recomputed, and
   that the difference may be zero on some tasks. A null result is a result.

## 6. External capability for config C — read-only feasibility

Checked: licence, install shape, Python requirement, execution prerequisites.
Nothing was installed, downloaded or run this round.

| candidate | licence | env | would it add a measurable capability? | verdict |
| --- | --- | --- | --- | --- |
| **AIDE** (`WecoAI/aideml`) | MIT | Python package, `pip install`, one LLM API key, CPU is enough for the tree search but the tasks here are CPU-light | yes, but as an *algorithm-search* module: it explores solutions to a fixed metric. T2 is exactly that shape; T1/T3 are not. | **plausible for T2 only** |
| **R&D-Agent** (`microsoft/RD-Agent`) | MIT | Python ≥ 3.10, Docker for the full loop, LLM backend config | yes for end-to-end "propose → implement → evaluate" loops; heavy for a 40-minute budget and needs Docker | **not for this round** |
| **AutoResearchClaw** (`aiming-lab/AutoResearchClaw`) | MIT | Python ≥ 3.11 (`researchclaw` 0.5.0), multi-agent pipeline, LaTeX for the writing stage | overlaps the *system* rather than adding a component; would confound the comparison it is supposed to inform | **poor fit as config C** |

Local environment measured: Python 3.13.14, no Docker, one RTX 4080 (16 GB). No
candidate is installed, so config C is `NOT_READY` for execution — by design, and
recorded as such rather than papered over with a wrapper script.

If C is pursued, the only version worth running is **C = B + AIDE on T2**, because
that is the one place where an external module supplies something the component
does not: search over candidate solutions rather than review of one.

## 7. What this round does not do

No arm was executed. No external framework was installed. No GPU training. No
paper, figure or submission. The tasks are frozen inputs and hidden keys; running
them is the next round's work.
