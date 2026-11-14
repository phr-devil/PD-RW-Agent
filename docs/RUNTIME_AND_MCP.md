# Python Runtime + MCP — operator documentation (v0.7.5)

> The diagnostic MCP surface has **20 tools** (the default research profile has 17), including one read-only
> host-diagnostic status endpoint. Host CPU selftests launch only via
> operator's separate host CLI, not through MCP/WorkBuddy. Real scientific
> DEV/GPU execution is not enabled. See [v0.7.2 pilot](V072_HOST_PILOT.md).

> The legacy v0.4-v0.5 sections below are retained as historical
> setup examples. Current MCP has 20 tools defined in the server and
> tested by tests/test_mcp.py. v0.7.1 adds Python-only internal host
> validation and readiness diagnostics, not a new MCP execution tool.
> See V071_HOST_READINESS.md. DEV/GPU execution is not yet enabled.

## v0.7.5 recommended WorkBuddy profile

At MCP startup the environment variable `PDRW_MCP_PROFILE` may be `minimal` (11 tools), `research` (17, default), or `diagnostic` (20). A profile is **tool discovery visibility, not authorization**: the Python CLI and WorkBuddy's own external tools retain their independently configured capabilities.

Add `"PDRW_MCP_PROFILE": "research"` under the MCP server `env` block and restart/reconnect the MCP connection. Import the updated Skill independently. For a fresh-session project recovery, the Skill calls `get_resume_context(project_id, detail_level="compact")` once. The CLI and Python code default to the backward-compatible full view.

For previously installed broad-inventory integration tests use `profile="diagnostic"` explicitly. Only explicitly configured `diagnostic` exposes the fixed CPU host/selftest diagnostics. No profile grants real DEV/GPU execution or OS isolation.

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

Historical v0.5 tool inventory: 11. **Current v0.7.1 MCP inventory: 19 tools** (17 read-only, 2 private operational-receipt mutations; zero scientific write or arbitrary command tools). No MCP interface can register an original PD-RW Run, authenticate a user grant, or execute a real DEV/GPU process. Install/import Skill and MCP separately.

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

The following paragraph concerns *reproducing the historical v0.5.3 A/B/C study*, not upgrading the current installation. For current use verify Python and installed Skill both report **0.7.5**, then restart/reconnect MCP and confirm **17 tools** with the default research profile (or 20 with diagnostic). Historical frozen comparisons must instead install their originally tested versions and maintain matched tools. A manual MCP smoke call does not count as autonomous tool selection.

**Matched evaluation:** A = PD-RW only, no Skill/MCP; B = PD-RW + Skill v0.5.3, MCP disabled; C = PD-RW + the SAME Skill v0.5.3, MCP enabled. The user prompt, frozen input, model and permissions must be identical. In C, verify an **actual** project MCP tool call. If C does not call it, record `INTEGRATION_NOT_EXERCISED` (do not fabricate MCP usage). Compare scientific correctness separately from call overhead. B may legitimately fall back to direct file reads. The updated Skill improves routing instructions but **cannot force** the WorkBuddy host to invoke a tool or intercept terminal/SEALED operations.
