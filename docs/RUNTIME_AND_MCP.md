# Python Runtime + MCP — operator documentation (v0.7.1)

> The legacy v0.4-v0.5 sections below are retained as historical
> setup examples. Current MCP has 19 tools defined in the server and
> tested by tests/test_mcp.py. v0.7.1 adds Python-only internal host
> validation and readiness diagnostics, not a new MCP execution tool.
> See V071_HOST_READINESS.md. DEV/GPU execution is not yet enabled.

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

The MCP server exposes **11 tools** (5 original read-only + 4 new read-only + 2 write-only-operational-metadata). No tool registers an original PD-RW Run. Original user authorization, Windows ACL and independent trusted host **remain out of scope of this release**. Install/import Skill and MCP separately.

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
