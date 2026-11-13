# Python Runtime + MCP — operator documentation (v0.4 preview)

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
