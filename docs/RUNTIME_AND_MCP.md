# Python Runtime + MCP — operator documentation

**Current release: 0.9.4.** Read this section only; everything below the
historical index is kept verbatim for audit.

| Fact | Current value |
| --- | --- |
| Package version | `0.9.4` (`pyproject.toml`, `pdrw_agent.__version__`, Skill frontmatter) |
| MCP tools | 24 defined; profiles `minimal` **11**, `research` **21** (default), `diagnostic` **24** |
| CLI | `python -m pdrw_agent.cli <command>`; same `ResearchService` as MCP |
| Optional science CLI | `python -m pdrw_agent.science.cli {decision,lessons,h6-review,early-review,feedback-link,replay-check,replay-blind}` |
| Real DEV/GPU execution | Not enabled |
| Original-user authentication / OS isolation | Not implemented |
| WorkBuddy research gain, token or wall-clock saving | `NOT_MEASURED` |

What the current release adds on top of the v0.8 line: an evidence-linked Run
feedback contract with three separate provenance states (`docs/EXPERIMENT_FEEDBACK_LINK.md`),
a next action derived from the judged Run rather than from case keywords, a
strict `as_of` historical view for evaluation replay, and one downgrade-only
projection (`to_run_feedback`, `feedback-link --as-run-feedback`) so the gate
never receives a hand-translated credibility level.

Nothing here authorizes anything: Python and MCP **cannot** approve a download,
a SEALED read, a manuscript, a figure, a payment or a submission, and no
profile grants real execution. Only the WorkBuddy host holds those capabilities.

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

The following paragraph concerns *reproducing the historical v0.5.3 A/B/C study*, not upgrading the current installation. For that replay, install the originally tested versions and keep tool counts matched (that release reported **0.7.5** with **17**/20 tools) — **do not** apply those counts to the current 0.9.4 installation, which reports 11/21/24. A manual MCP smoke call does not count as autonomous tool selection.

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
