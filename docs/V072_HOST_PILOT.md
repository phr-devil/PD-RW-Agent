# v0.7.2 — Supervised host pilot (fixed CPU diagnostic only)

## Exact scope / authority

**This is not a production trusted DEV executor.** The host CLI is a
separately launched local OS process, but *it runs under the launching OS
account*. It is not an authenticated service, protected grant store, secure
network API, GPU scheduler, scientific ledger writer, or general Python
sandbox. WorkBuddy/MCP cannot launch fixed host jobs through their exposed
tool surface. Only the operator-side \`pdrw_agent.host.cli\` can run one
**package-defined, fixed CPU computation**, with no model-defined code/data
path, subprocess args, imports, device, network or working directory.

Original PD-RW v1.13 remains authority for rules, STATE/EVENTS, Run, H6/H8
author decisions and permission. Host status is operational metadata only.

## Host launch / local smoke test

From a separate trusted terminal/environment (PowerShell syntax):

    cd D:\workbuddy-agent\PD-RW-Agent
    .\.venv\Scripts\python.exe -m pip install -e ".[mcp]"
    $env:PDRW_AGENT_CONFIG = "D:\workbuddy-agent\PD-RW-Agent\project-map.local.json"
    $env:PDRW_WORKFLOW_ROOT = "D:\workbuddy-agent\Problem-Data-Research-Workflow"
    $env:PDRW_RUNTIME_DIR = "D:\PD-RW-Private\agent-runtime"
    .\.venv\Scripts\python.exe -m pdrw_agent.host.cli run-fixed-diagnostic --plan-file .\config\host-pilot-plan.example.json

Edit the *example* plan's \`project_id\` and \`task_id\` to refer only to an
explicitly mapped, machine-consistent synthetic test project before running.
The host tests require original STATE.json + EVENTS.jsonl consistency and
a research-record snapshot, but that is not user authorization.

Plan schema is the existing \`pdrw-exec-plan-v1\` fixed \`CPU_SELFTEST_V1\`.
Accepted scenarios: SUCCESS, EXIT_NONZERO, SLEEP. Timeout 1..5 seconds,
iterations 1..100000; no GPU/network/custom scripts. SLEEP is intentional
to exercise timeout and cancellation.

Read-only queries from operator terminal:

    .\.venv\Scripts\python.exe -m pdrw_agent.host.cli status --project-id demo --operation-id host-demo-1
    .\.venv\Scripts\python.exe -m pdrw_agent.cli host-status --project-id demo --operation-id host-demo-1

The same \`get_host_diagnostic_status(project_id, operation_id)\` is exposed
via MCP as **read-only**. \`get_resume_context\` includes the latest host
diagnostic checkpoints and reports whether reconciliation is necessary.
Status NEVER authorizes execution, proves a live process belongs to this
host, or retries an uncertain attempt.

## Process constraints

- **Windows:** CreateProcessW suspended, configure Job Object with
  JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, assign child, then resume. Cancellation
  calls TerminateJobObject. If the host loses its final Job handle, Windows
  kills child processes in that Job. *This is process-tree containment,
  not filesystem or credential isolation.* The pilot does not test nested
  job restrictions in a user's real WorkBuddy session.
- **Linux:** start_new_session creates a dedicated process session; the fixed
  worker sets PR_SET_PDEATHSIG=SIGKILL and checks parent PID. Cancellation
  terminates the process group and escalates if required. These rules
  do not constitute a sandbox.
- **SQLite:** \`user_version=3\` extends the existing independent private
  runtime database with \`host_jobs\`. Original operation receipts and
  scientific STATE/EVENTS are never rewritten. The host commits
  STARTING_UNVERIFIED *before* launching the child, then records PID,
  creation token, exit code, phase, and output SHA256.
- Duplicate \`(project_id, operation_id)\` never relaunches a job, even
  following host failure or partial completion; different plan hash returns
  HOST_PLAN_CONFLICT. After restart a matching PID+creation token is only
  OBSERVED; the host does not adopt or kill an unowned process.
- A diagnostic output is counted complete only when the original fixed
  synthetic checksum exactly matches. Read-only queries rehash it.
  No original Run, data or SEALED files are opened or written.

## Runner catalog: read-only integrity check

\`host.runner_registry.inspect_registered_runner\` reads an optional
operator-selected catalog **outside** the science project, workflow and
project-map directory. It verifies a bounded Python source file hash and
rejects protected or escaping paths. It never launches any catalog script.
A matching hash does *not* authenticate a user grant, the catalog origin,
actual imports or Windows ACL configuration.

\`host.isolation.assess_host_isolation()\` only records the current UID/SID
and always says HOST_OS_ISOLATION_NOT_ATTESTED. This is deliberate:
\`approved: true\` in a prompt or an environment variable is not a grant.

## Required independent Windows on-device acceptance before real DEV

1. Provision a **separate least-privileged Windows account** for the host;
   keep WorkBuddy and host under separate OS identities and restrict access
   to the host's private registry/grants/runtime files. Validate identity
   by native Windows token SID, not user-supplied text.
2. On an isolated test fixture, create DEV-readable and SEALED-denied
   directories; launch under the actual host account and test OS-enforced
   positive DEV read and negative SEALED read. Do not test against actual
   hidden scientific SEALED contents. Verify host cannot alter original
   PD-RW rule files or unauthorized Run/STATE.
3. Validate Job Object assignment, kill-on-close, descendants, forced host
   death, PID reuse, resource budget and durable checkpoint reconciliation
   under the **actual Windows 11 host account**.
4. Establish a host-owned trusted runner and original-user-grant registry
   separate from WorkBuddy's writable files, bind DEV TaskSpec and signed
   author consent/scope, verify installed code/data hashes, and test
   adversarial model-supplied forged approvals and arbitrary commands.
5. Introduce a separately authenticated host IPC only after the OS account,
   ACL, trusted grant source and process isolation tests pass. WorkBuddy
   should receive bounded submit/status/cancel interfaces *only then*.
6. Gate real CPU DEV first. Defer GPU execution until monitoring and GPU
   budget policies are validated; GPU telemetry is not hard VRAM isolation.

## CI versus genuine acceptance

Synthetic CI runs with the GitHub runner's account, not a separately
provisioned restricted user. It exercises Windows Job Objects, POSIX child
processes, process cancellation/timeout, immutable plan IDs, forged command
rejection, SHA tampering, registry source-hash checks, cross-session
read-only status, and fixed CPU host CLI. It **cannot** establish
independent user authorization, scientific correctness, host account ACL
enforcement, GPU bounds, or reduced research/Token cost.
