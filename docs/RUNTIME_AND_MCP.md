# Python Runtime + MCP — operator documentation (v0.5)

This is an adapter. PD-RW remains the one and only scientific-rule authority. Python and MCP **cannot** authorize operations, decide scientific merit, or read SEALED data by virtue of being installed.

## Setup: Windows 11 PowerShell

Clone both repositories to distinct directories. Use **Python 3.11+** and a private virtual environment in PD-RW-Agent:

```powershell
cd D:\path\to\PD-RW-Agent
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[mcp]"
Copy-Item config\project-map.example.json project-map.local.json
```

Edit the private `project-map.local.json` with actual project IDs, roots, existing `STATE.md` or `STATE.json`, `RESEARCH_RECORD.md` paths, and optional `expected_state_project_id`. Never commit it, unpublished materials, secrets, or personal data. Use a read-only, non-SEALED project first.

CLI and MCP use the **same service layer**:

```powershell
$env:PDRW_AGENT_CONFIG = "D:\path\to\PD-RW-Agent\project-map.local.json"
$env:PDRW_WORKFLOW_ROOT = "D:\path\to\Problem-Data-Research-Workflow"
.\.venv\Scripts\python.exe -m pdrw_agent.cli context --project-id "example-project"
.\.venv\Scripts\python.exe -m pdrw_agent.cli rules --topic "DEV"
.\.venv\Scripts\python.exe -m pdrw_agent.cli memory --query "HAR"
.\.venv\Scripts\python.exe -m pdrw_agent.cli evidence --project-id "example-project"
```

MCP local stdio example (replace every path; do not publish real paths):

```json
{
  "mcpServers": {
    "pd-rw-research": {
      "type": "stdio",
      "command": "D:\\path\\to\\PD-RW-Agent\\.venv\\Scripts\\python.exe",
      "args": ["-m", "pdrw_agent.integrations.mcp_server"],
      "env": {
        "PDRW_AGENT_CONFIG": "D:\\path\\to\\PD-RW-Agent\\project-map.local.json",
        "PDRW_WORKFLOW_ROOT": "D:\\path\\to\\Problem-Data-Research-Workflow"
      }
    }
  }
}
```

Import the existing `skills/pd-rw-research/` Skill independently, or use its ZIP. WorkBuddy installation/configuration varies by edition. Check the client's own MCP UI/validation; do not assume importing a Skill alone installs the Python environment or starts MCP.

## Five MCP tools (read-only)

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

The MCP server exposes **14 tools** (5 original read-only + 4 later read-only + 2 CASE_LIBRARY advisory read-only + 1 case-gate orchestrator + 2 write-only-operational-metadata). No tool registers an original PD-RW Run. Original user authorization, Windows ACL and independent trusted host **remain out of scope of this release**. Install/import Skill and MCP separately.

## v0.5.3 WorkBuddy MCP-first routing acceptance

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

The CLI uses `PDRW_AGENT_CONFIG` and `PDRW_WORKFLOW_ROOT`; set them on this PowerShell session if absent. Confirm the Python package reports `0.5.3`. Re-import/refresh `dist/pd-rw-research.zip` in WorkBuddy and verify the **actually returned Skill content** says `version: 0.5.3` and `MCP-first for a registered, permitted project`. Restart/reconnect the stdio MCP after changing the venv or repo. Confirm MCP tool visibility and do a non-benchmark call to `get_project_context("37")` once; this functional preflight does NOT count as autonomous tool selection.

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
