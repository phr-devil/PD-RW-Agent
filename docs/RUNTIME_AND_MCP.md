# Python Runtime + MCP — operator documentation

**Current release: 1.0.0rc1 (the v1.0 release candidate).** Read this section only; everything below the
historical index is kept verbatim for audit.

| Fact | Current value |
| --- | --- |
| Package version | `1.0.0rc1` (`pyproject.toml`, `pdrw_agent.__version__`, Skill frontmatter) |
| MCP tools | 24 defined; profiles `minimal` **11**, `research` **21** (default), `diagnostic` **24** |
| CLI | `python -m pdrw_agent.cli <command>`; same `ResearchService` as MCP |
| Optional science CLI | `python -m pdrw_agent.science.cli {template,packet-check,decision,lessons,candidate-review,h6-review,early-review,feedback-link,replay-check,replay-blind}` |
| Real DEV/GPU execution | Not enabled |
| Original-user authentication / OS isolation | Not implemented |
| Gate fingerprint | digests the **complete** bounded event; the returned basis is clipped for reading only (`CASE_GATES_VERSION` 1.3) |
| WorkBuddy research gain, token or wall-clock saving | `NOT_MEASURED` |

What the current release adds on top of the v0.8 line: an evidence-linked Run
feedback contract with three separate provenance states (`docs/EXPERIMENT_FEEDBACK_LINK.md`),
a next action derived from the judged Run rather than from case keywords, a
strict `as_of` historical view for evaluation replay, and one downgrade-only
projection (`to_run_feedback`, `feedback-link --as-run-feedback`) so the gate
never receives a hand-translated credibility level.

The candidate review (`science/candidate_review.py`, CLI only) is the one new
science check in 0.9.7. It validates a `pdrw-candidate-card-v1` card's declared
relations and returns finding codes plus the cheapest check; no MCP tool, no
profile count and no payload of an existing tool changed. It reads no project
file, no Run and no literature, and it exits 3 like the other card reviews.
As of 0.9.8 the card can also express a theory or simulation path
(`ANALYTIC_DERIVATION`, `INSTANCE`, `REPLICATE`), so its form check no longer
removes a legal PD-RW evidence path.

`decision.assess_proposal` gained three declaration-level outputs in 0.9.8, all
additive: `probe_findings` (`REFERENCE_NOT_LEGAL`, `PROBE_UNIT_NOT_INDEPENDENT`),
a `DECLARED_CONFLICT` downgrade of the `group_independence` precheck when a probe
counts repeated units, and `no_decisive_probe` when no candidate separates a
hypothesis pair. The `declared_probe_efficiency` frontier is empty in that case
instead of naming the cheapest uninformative probe. Payload grows 2 813 → 2 965
characters on a clean two-probe packet and 7 400 → 8 640 on three defective ones.

0.9.9 closes the hole the 0.9.8 frontier left open. Before it, a LOW-cost probe
that separated nothing still appeared as a frontier candidate, and an
oracle-referenced probe could **dominate** the legal one (equal pairs, lower
cost) — so the only remaining candidate was the illegal comparison. Now
dominance is computed only between eligible probes, where eligible means
"separates ≥1 declared pair" and "no `REFERENCE_NOT_LEGAL`". The rest stay
visible with their permitted use: `exploratory_probe_ids`,
`diagnostic_upper_bound_ids`, `needs_unit_verification_ids`, plus
`no_legal_decisive_probe` and its question. `PROBE_UNIT_NOT_INDEPENDENT` asks for
an independent-unit count and never bans a window/frame observable; each finding
also carries `usage` and `blocks_decisive_frontier`. No probe is deleted, nothing
stops automatically, and no key was removed. Measured size cost (compact JSON, a
character proxy — not tokens): clean two-probe packet 2 858 → 3 054 (+6.9%),
three defective packets 8 211 → 9 124 (+11.1%); the increase is the three new
ID lists and the per-finding `usage`.

0.9.10 adds one optional per-probe field and never requires it: `prior_execution`
(`status`, `run_ref`, `premise_id`, `conclusion`, `new_information`,
`requires_new_authorization`). The frontier now only names a probe that can
still produce information and can start today; a probe that already answered
this premise is `HISTORICAL_EVIDENCE_ONLY`, an invalid one is
`TARGETED_REPAIR`, an inconclusive one waits for named new information, and an
ungranted one is `NEEDS_AUTHORIZATION`. A closure claimed without a `run_ref`
becomes `CLOSURE_DECLARED_NOT_VERIFIED` plus an `EXECUTION_DECLARED_NOT_VERIFIED`
finding — checked, not trusted, and not rerun on assumption. New keys:
`historical_evidence_ids`, `repair_required_ids`, `awaiting_new_information_ids`,
`revisit_on_new_information_ids`, `needs_authorization_ids`, `blocked_ids`,
`unverified_closure_ids`, and `no_executable_next_probe` (distinct from
`no_legal_decisive_probe`: legal and decidable, but nothing startable now). Each
probe summary carries `applicability` and `next_action`. Packets without the
field behave exactly as in 0.9.9. Measured cost (compact JSON, character proxy):
clean two-probe packet 3 054 → 3 541 (+15.9%), three defective packets
9 124 → 10 429 (+14.3%), all of it the two short per-probe codes.

0.9.11 makes those closures checkable instead of declarable. Before it,
`status_verified` was `status != NOT_EXECUTED and bool(run_ref)`: a Run that did
not exist, a Run belonging to another project and a Run whose own record said
INVALID all came back verified, and a closure with no `premise_id` was still
accepted as history. `decision` now takes an optional `--project-root`; the
existing `feedback_link` resolver binds a cited `run_ref` to a Run record inside
that project (SEALED/holdout paths are refused, not read) and reports five
separate axes: `reference_present`, `file_binding`, `status_consistency`
(the record's own `status`/`verdict`/`anchor_pass` vs the declaration),
`premise_binding`, and only then `status_verified`. Two new outcomes keep the
distinction honest: `STATUS_CONFLICT` (the record contradicts the claim) and
`CLOSURE_PREMISE_UNBOUND` (a closure that never named its premise). Neither
closes the premise nor removes a live candidate; both are new ID lists
(`status_conflict_ids`, `premise_unbound_ids`). Without a root every closure is
`NOT_CHECKED` — the same answer as "not verified", never "true". The payload also
states `run_binding_checked`, `run_binding_scope`, and
`authorization_basis: CALLER_DECLARED_ONLY_NEVER_A_PERMIT`, because a boolean in
a packet is a caller statement and not an execution permit. Measured cost
(compact JSON): clean two-probe 3 541 → 3 726 (+5.2%), three defective
10 429 → 10 984 (+5.3%), a three-probe packet carrying real history
6 706 → 8 180 (+22%, ~490 characters per closed probe).

0.9.13 makes the packet contract usable from the error message, and stops
`status_verified` from answering two questions at once. `packet-check` (and
`template`) are the only new surface: every shape violation at once with
`path`/`problem`/`accepted`/`found`, the `ignored_fields` the decision path
would have dropped silently, and `warnings` for what is read but not enforced
(a prose `evaluation_unit` is compared with a token set, so it silently disables
the repeated-unit check). `normalize` applies only lossless moves — a
`prechecks` list keyed by its own ids (notes preserved), `predictions` written as
pairs — and refuses a prose `scope`, a hoisted execution field or an unknown
outcome, because each of those needs an author decision. `observable` and
`comparison_reference` accept 240 characters instead of 80: they are
descriptions, and the old limit produced ten of one packet's thirteen
violations without protecting anything. On the four real 03D packets the checker
now names 1 / 24 / 4 / 22 violations individually; a fresh session given
`template` reached a valid packet in two rounds (3 min), and a fresh session
asked to repair the four declined all four rather than invent a prediction
direction. Also: `status_verified` = the closure is verified, so it can no longer
be true while `premise_verified` is false; `execution_verified` reports the other
half; a closure whose premise is only the caller's label is
`HISTORICAL_EVIDENCE_PREMISE_ASSUMED` (not a next action, not a settled premise)
and appears in `premise_assumed_ids`. **Superseded in 0.9.14** — that label still
counted as evidence; both the name and the list are gone, see the 0.9.14
paragraph below. Measured cost (compact JSON): clean
two-probe 3 756 → 3 781 (+0.7%), three defective 11 074 → 11 149 (+0.7%),
three-probe packet with real history 8 641 → 8 822 (+2.1%) declared and
9 483 → 9 664 (+1.9%) bound. MCP unchanged: 24 tools, profiles 11/21/24.

0.9.12 stops answering the premise question with the caller's own words. Both
`prior_execution.premise_id` and `proposed_premise.premise_id` are packet text,
so their equality cannot show that a cited Run tested this premise; a real,
status-consistent Run that executed a *different* frozen plan still closed the
probe. The resolver now also reads what the record claims about itself — its
`run_id` against the directory it was found in (`run_id_consistency`), whether
it is a Run record or a bare metrics file (`record_structure`), the premise it
states (`premise_id`), and the frozen plan it names (`protocol_id` /
`protocol_ref`, resolved inside the project and hash-compared when a hash is
declared). A packet may add `premise_ref`: the project-relative plan that
encodes the premise under study. When that plan and the plan the Run executed
disagree, or when the record's own premise disagrees with the declared one, the
probe returns to `NOT_YET_RUN` with `CLOSURE_PREMISE_CONTRADICTED` and
`next_action: CONFIRM_WHICH_EXPERIMENT_THE_RUN_ANSWERED` — not a closure, not a
silent rerun. `premise_binding_basis` names the source that answered the
question (`RUN_RECORD`, `FROZEN_PLAN`, `PREMISE_PLAN`, `CALLER_DECLARATION`),
`premise_verified` is false when only the caller named the premise, and a plan
the record names but that cannot be read keeps the closure
`CLOSURE_DECLARED_NOT_VERIFIED` (`CLOSURE_PLAN_UNRESOLVED`). A directory holding
another Run's record, or plan bytes that differ from the declared hash, are
`STATUS_CONFLICT`. `artifact_links_verified` stays false: linked artifacts and
their hashes are still not opened here. Measured cost (compact JSON): clean
two-probe 3 726 → 3 756 (+0.8%), three defective 10 984 → 11 074 (+0.8%), the
three-probe packet with real history 8 180 → 8 641 (+5.6%).

0.9.14 splits the third question out of the premise answer, and gives the plan a
place to say what it needs permission for. `execution_verified` said only that a
Run ran; `premise_verified` said the record or its frozen plan states this
premise; between them sat a case the tool got wrong — a valid, bound, consistent
Run that nothing on disk ties to *this* experiment. 0.9.13 filed that as
`HISTORICAL_EVIDENCE_PREMISE_ASSUMED` and put it in `historical_evidence_ids`,
so a caller's own label could retire a probe that may never have been run.
Measured: a k-scale probe citing `DEV/runs/RUN-005` (whose frozen plan fixes one
scale and states no premise) left the frontier and entered recorded evidence with
no finding. Now `attribution_basis` names what ties the Run to the experiment —
`RUN_RECORD`, `FROZEN_PLAN`, `CALLER_PREMISE_PLAN` (the Run executed the plan the
caller named, checked against the record's `protocol_id`/`protocol_sha256`), or
`NONE`. `NONE` reads `CLOSURE_ATTRIBUTION_UNCHECKED` with
`next_action: CHECK_WHICH_PLAN_THE_RUN_EXECUTED`: not evidence, not a next action,
not a rerun, and listed in `attribution_unchecked_ids`. Naming the plan reads
`HISTORICAL_EVIDENCE_PREMISE_ATTRIBUTED`: citable evidence with
`premise_verified: false`, still not a closure. 0.9.13's
`HISTORICAL_EVIDENCE_PREMISE_ASSUMED` and `premise_assumed_ids` are renamed
accordingly; five 03B/03C/03D/04 assertions were rewritten to assert the split
rather than the old label. The Skill's handoff is now three tiers
(NOW / NEEDS_NEW_AUTHORIZATION / FUTURE_CONDITIONAL) because 04 produced the
failure twice with one flat list: a reserved-VAL grid as "step 1" with the
permission note at step 3, and a holdout evaluation as "step 3" of a shortest
path. Measured cost (compact JSON): clean two-probe 3 781 → 3 787 (+0.2%),
three defective 11 149 → 11 167 (+0.2%), three-probe packet with real history
8 822 → 9 075 (+2.9%) declared and 9 664 → 9 917 (+2.6%) bound — the last two
carry two more per-probe axes (`attribution_basis`, `attribution_verified`) and
the renamed ID list. MCP unchanged: 24 tools, profiles 11/21/24.

Nothing here authorizes anything: Python and MCP **cannot** approve a download,
a SEALED read, a manuscript, a figure, a payment or a submission, and no
profile grants real execution. Only the WorkBuddy host holds those capabilities.

1.0.0rc1 adds no axis and no tool; it is the same 24 tools with three integration
repairs found by running real sessions against real projects, and a version
identity that is now checked instead of asserted:

- **A bounded read smaller than the artefacts it reads.** `MAX_RUN_RECORD_BYTES`
  was 128 KiB, and project 44's `DEV/runs/RUN-002/metrics.json` is 411 202 bytes
  of fold-level metrics. The binder answered `RUN_RECORD_TOO_LARGE`, so a Run
  that really ran could not be attributed and fell through to
  `unverified_closure_ids`. The cap is now 4 MiB — still refuses a prediction
  dump — and `DEV/runs/RUN-002` binds (`RUN_RECORD_BOUND`).
- **A reserved root that was not reserved.** `SEALED`, `HOLDOUT` and
  `CONFIRMATION` were refused at any depth, but not `VAL`: on project 44
  `VAL/README.md` was read and handed to the JSON parser as a Run candidate.
  A reserved root is now reserved at the root segment only, so a legitimate
  `data/val/` split inside DEV is still readable; `VAL/` answers
  `FEEDBACK_LINK_PATH_REJECTED`.
- **A release note that named the wrong release.** `README.md` and this file
  still said "0.9.13" while the package was 0.9.14, and the 0.9.13 paragraph
  still described `premise_assumed_ids` as live. Both are corrected, and
  `test_arch_convergence` now fails if the header drifts from `__version__`.

What each tier of the RC was verified *by* — a real session, a test, or nothing
— is the point of [`docs/RC_V1.0.md`](RC_V1.0.md); the frozen identifiers are in
`audit/RC-INTEGRATION-v1.0.0-rc.1-2026-11-20.md`.

## Historical index (audit trail — anchors preserved)

| Section | Applies to |
| --- | --- |
| [v0.5 local continuation](#v05-local-continuation) | Operation receipts |
| [v0.5.3 routing acceptance](#historical-v053-workbuddy-mcp-first-routing-acceptance-replay-only) | Replay study only; **not** current setup |
| [v0.5.4 CASE_LIBRARY advisory reuse](#v054-local-increment-case_library-advisory-reuse) | Historical |
| [v0.5.5 five case gates](#v055-local-increment-five-case-application-gates) | Historical |
| Tool-count notes | Read the current table above; older counts are labelled |

## Setup (current)

Windows 11 PowerShell, Python 3.11+:

```powershell
cd D:\path\to\PD-RW-Agent
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[mcp]"
Copy-Item config\project-map.example.json project-map.local.json
```

Edit the private `project-map.local.json` (project IDs, roots, `STATE` paths).
Never commit it or any unpublished/SEALED material. Then:

```powershell
$env:PDRW_AGENT_CONFIG = "D:\path\to\PD-RW-Agent\project-map.local.json"
$env:PDRW_WORKFLOW_ROOT = "D:\path\to\Problem-Data-Research-Workflow"
.\.venv\Scripts\python.exe -m pdrw_agent.cli resume --project-id "example-project"
.\.venv\Scripts\python.exe -m pdrw_agent.cli rules --topic "DEV"
.\.venv\Scripts\python.exe tools\package_skill.py
```

MCP stdio example (replace every path; do not publish real paths):

```json
{
  "mcpServers": {
    "pd-rw-research": {
      "type": "stdio",
      "command": "D:\\path\\to\\PD-RW-Agent\\.venv\\Scripts\\python.exe",
      "args": ["-m", "pdrw_agent.integrations.mcp_server"],
      "env": {
        "PDRW_AGENT_CONFIG": "D:\\path\\to\\PD-RW-Agent\\project-map.local.json",
        "PDRW_WORKFLOW_ROOT": "D:\\path\\to\\Problem-Data-Research-Workflow",
        "PDRW_MCP_PROFILE": "research"
      }
    }
  }
}
```

Import `skills/pd-rw-research/` (or `dist/pd-rw-research.zip`) separately: an
already-running stdio server keeps the old schema, and editing this repository
does not update the installed Skill copy. A profile changes **visibility**, not
authority.


## First five MCP tools (historical snapshot, not current tool count)

| Tool | Purpose | Important limitation |
| --- | --- | --- |
| `get_project_context` | Registered project state/snapshot/paths | Does **not** authenticate source, user approvals, or ledger integrity |
| `get_applicable_rules` | Local AGENTS.md table routes | Does **not** check remote freshness or return all rules |
| `search_research_memory` | Case-index keyword matches | Case registry is a **secondary** index, not raw evidence |
| `find_experiment_evidence` | Indexed non-SEALED Run metadata | Event/Run scientific validity remains unverified |
| `check_duplicate_experiment` | Declared fingerprint match against last indexed DEV Runs | A match is a candidate, not proof of reproducibility |

The first five tools **cannot** download, train, write evidence, unlock SEALED, produce papers, draw figures, pay, upload, or submit. The MCP process should run under a Windows account without SEALED directory access. WorkBuddy's separate terminal/filesystem permissions must also be configured independently.

For tests:
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Extension rules

1. One public service in `service.py`, used by CLI and MCP; scientific-policy owner is always PD-RW.
2. Register only a genuinely new, bounded tool. Do not expose a filesystem explorer or arbitrary shell executor.
3. Inputs use registered project IDs, never arbitrary model-supplied disk roots. Outputs are bounded JSON with original source/verification limits.
4. Research records stay at existing project paths; case index stays in PD-RW. Never create another mutable science memory ledger.
5. Adding write tools requires independent trusted authorization, actual filesystem/tool controls, idempotent event writes and failure replay tests.
6. CI proves engineering behavior. WorkBuddy on-device evaluation is still **NOT_MEASURED** until real capture.


## v0.5 local continuation

A private `PDRW_RUNTIME_DIR` (absolute directory **outside** the research project, rule checkout and agent repository) enables small SQLite **operation receipts**, NOT scientific records. No directory is required for normal read-only project/memory tools. An example on Windows:

```powershell
$env:PDRW_RUNTIME_DIR = "$env:LOCALAPPDATA\\PD-RW-Agent\\private-runtime"
.\\.venv\\Scripts\\python.exe -m pdrw_agent.cli resume --project-id "example-project"
.\\.venv\\Scripts\\python.exe -m pdrw_agent.cli begin-operation --project-id "example-project" --operation-id "op-example-1" --task-id "dev-task" --action DEV_EVALUATE
.\\.venv\\Scripts\\python.exe -m pdrw_agent.cli operations --project-id "example-project"
.\\.venv\\Scripts\\python.exe -m pdrw_agent.cli preview-record --project-id "example-project" --artifact-ref "runs/example.json"
```

Add `PDRW_RUNTIME_DIR` to the stdio MCP `env` block. WorkBuddy must use the same private directory across sessions; otherwise only science-project recovery works. All tool interfaces are defined in [V05_EXECUTION.md](V05_EXECUTION.md).

Historical v0.5 tool inventory: 11. **v0.8.2 inventory (historical): 24 tools in the `diagnostic` profile** — 11 core, 6 audit/science, 3 host-diagnostic and 4 optional CASE_LIBRARY advisory (`case_gate_check`, `review_case_transfer`, `extract_case_candidates`, `project_case_bridge`). Profiles: `minimal` 11, `research` 21, `diagnostic` 24 — unchanged in 0.9.x. Two tools are private operational-receipt mutations; there are zero scientific write or arbitrary command tools. No MCP interface can register an original PD-RW Run, authenticate a user grant, or execute a real DEV/GPU process. Install/import Skill and MCP separately.

## Historical v0.5.3 WorkBuddy MCP-first routing acceptance (replay only)

For a **registered project ID** and an enabled, permitted `pd-rw-research` MCP connection, the installed `pd-rw-research` Skill now requests a **real** `get_project_context(project_id)` call at the beginning of a fresh project task (once per task, no repeat loop). This invokes the canonical Python service via MCP. A missing/blocked STATE does not prohibit separate authorized read-only inspection of the frozen evidence. Without MCP, the same Skill falls back to direct sources and reports `MCP_NOT_USED`. No tool response itself verifies original author approval.

Before comparing B and C, update **both the local Python checkout and WorkBuddy's installed Skill**; a `git pull` alone does not prove WorkBuddy loaded the revised Skill. On the operator's Windows PC:

```powershell
cd D:\workbuddy-agent\PD-RW-Agent
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -e ".[mcp]"
.\.venv\Scripts\python.exe -c "import pdrw_agent; print(pdrw_agent.__version__)"
.\.venv\Scripts\python.exe -m pdrw_agent.cli context --project-id 37
.\.venv\Scripts\python.exe tools\package_skill.py
```

The following paragraph concerns *reproducing the historical v0.5.3 A/B/C study*, not upgrading the current installation. For that replay, install the originally tested versions and keep tool counts matched (that release reported **0.7.5** with **17**/20 tools) — **do not** apply those counts to the current 0.9.13 installation, which reports 11/21/24. A manual MCP smoke call does not count as autonomous tool selection.

**Matched evaluation:** A = PD-RW only, no Skill/MCP; B = PD-RW + Skill v0.5.3, MCP disabled; C = PD-RW + the SAME Skill v0.5.3, MCP enabled. The user prompt, frozen input, model and permissions must be identical. In C, verify an **actual** project MCP tool call. If C does not call it, record `INTEGRATION_NOT_EXERCISED` (do not fabricate MCP usage). Compare scientific correctness separately from call overhead. B may legitimately fall back to direct file reads. The updated Skill improves routing instructions but **cannot force** the WorkBuddy host to invoke a tool or intercept terminal/SEALED operations.

## v0.5.4 local increment: CASE_LIBRARY advisory reuse

The v0.5.3 lines above are historical acceptance notes. The **local** checkout is `0.5.4`; the operator-mentioned `v0.7.6` was not found on this machine (`REMOTE_NOT_CHECKED`), and no remote state was assumed.

Added read-only MCP tools: `review_case_transfer`, `extract_case_candidates`. `search_research_memory` keeps its legacy `(query, limit)` result shape and adds `case_library` / `case_learning_summary`. No tool writes CASE_LIBRARY, STATE, Run, EVENTS, SEALED or PD-RW rules; no GO/STOP is emitted and keyword similarity is never treated as scientific premise equivalence.

Configure the single read-only case source with **either**:

- `PDRW_CASE_LIBRARY_ROOT=D:\workbuddy-work\CASE_LIBRARY` in the stdio MCP `env` block, or
- a top-level `"case_library_root": "D:/workbuddy-work/CASE_LIBRARY"` in `project-map.local.json`.

Operator steps on this PC:

```powershell
cd D:\workbuddy-agent\PD-RW-Agent
.\.venv\Scripts\python.exe tools\package_skill.py
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Then re-import/refresh `dist\pd-rw-research.zip` in WorkBuddy, verify the **actually returned** Skill says `version: 0.5.4`, and restart/reconnect the stdio MCP — an already-running stdio server keeps the old schema. Confirm `review_case_transfer` and `extract_case_candidates` are visible and do one non-benchmark call. The installed Skill copy at `C:\Users\user\.workbuddy\skills\pd-rw-research\SKILL.md` is **not** updated automatically by editing this repository.

Local engineering check: `evals\case_learning_ablation.py` measures only the CASE_LIBRARY ON/OFF advisory-field differential and writes `evals\case_learning_ablation_result.json`. Real WorkBuddy A/B/C decision quality, tokens and wall time remain `NOT_MEASURED`; unit tests and this differential are not scientific-utility evidence.

## v0.5.5 local increment: five case-application gates

The v0.5.4 lines above are historical notes. The **local** checkout is now `0.5.5`; no remote state was assumed.

Added **one** read-only MCP tool, `case_gate_check(event, detail="compact")`, plus the CLI command `case-gate --event-file FILE [--detail compact|full]`. It is an orchestrator, not a new retrieval implementation: it reuses `case_learning.case_search` -> `CASE_LIBRARY/scripts/search_cases.py` for ranking, source verification, 8-dimension applicability review and decision experiences. `search_research_memory`, `review_case_transfer` and `extract_case_candidates` are unchanged; the legacy `(query, limit)` result shape is intact.

- **3 mandatory checkpoints**: G1 H2–H3 `QUESTION_SELECTION`, G2 H6–H7 `PROTOCOL_FREEZE`, G3 H8–H10 `CLAIM_OR_CLOSURE`. Each must show a real `retrieval_record` and per-case `applicability_judgments`; `verify_gate_record` rejects a bare `CASE_CHECK: COMPLETED`.
- **2 conditional triggers**: T1 anomaly / consecutive valid negatives (with outcome-class triage), T2 material decision change. Ordinary DEV signals are suppressed with zero retrieval.
- **Priority** `G1 > G2 > G3 > T1 > T2`; other matched triggers are reported but do not cause a second retrieval.
- **Fingerprint reuse**: Task, hypothesis, protocol, h_stage, milestone, task_profile, query, filters, evidence declaration and `index.json` sha256. Unchanged conditions return the verified cached record (`cache_hit=true`, zero new retrieval); any key change invalidates it. Bounded in-process cache, no second science-state database. Compact default returns at most 3–5 cases; `detail="full"` or the existing tools supply full evidence.
- **UNKNOWN**: no case match, insufficient sources, `CONDITIONS_DIFFER`, missing task profile, or inaccessible library — all recorded with reasons, `may_proceed=true`, `blocks_work=false`, no fake completion.
- **Enforcement level**: `ADVISORY_SKILL_AND_TOOL_LEVEL`; `hard_gate=false`, `host_state_transition_interception=false`. WorkBuddy has no trusted state-transition hook here, so these checkpoints cannot block a transition and must not be described as a hard gate. PD-RW H6/H8 author strategy choices and separate writing permission are unchanged.

Operator steps are the same as v0.5.4: repackage with `tools\package_skill.py`, re-import `dist\pd-rw-research.zip` in WorkBuddy, verify the returned Skill says `version: 0.5.5`, restart/reconnect the stdio MCP (an already-running server keeps the old schema), confirm `case_gate_check` is visible and do one non-benchmark call. The installed Skill copy is not updated automatically by editing this repository.

Local engineering check: `evals\case_gate_eval.py` writes `evals\case_gate_eval_result.json` with actual retrieval calls, cache hits, false/missed triggers and payload-character counts. Scientific decision quality and real WorkBuddy token/wall-time costs remain `NOT_MEASURED`.
