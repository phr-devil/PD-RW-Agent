# v0.7.0 — Host execution foundation (fixed synthetic CPU)

## Decision

The Python runtime now has a **bounded engineering-only execution proof**.
It deliberately does **not** permit WorkBuddy/MCP to execute arbitrary
commands, train scientific models, register Runs, or authenticate historical
user approval. The first step toward a trusted host is a durable, idempotent
fixed-code subprocess exercised only through the internal Python host API.

PD-RW \`WORKFLOW.md\`, original STATE/EVENTS and scientific Run contracts
remain the source of authority. The private runtime DB is **operational**
only; it never becomes a scientific ledger or paper evidence.

## Interfaces

Read-only MCP and CLI:

- \`preflight_execution_plan(plan)\`
- \`get_synthetic_job_status(project_id, operation_id)\`
- \`python -m pdrw_agent.cli execution-preflight --plan-file PLAN.json\`
- \`python -m pdrw_agent.cli synthetic-status --project-id demo --operation-id test-1\`

No launch method is exposed through MCP/CLI. The host-side Python-only
\`run_synthetic_in_host(settings, plan)\` is for controlled self-tests. Its
importability is **not a security boundary** against a user or Agent with
arbitrary terminal access. Never treat it as a DEV executor.

Example exact input schema:

    {
      "schema_version": "pdrw-exec-plan-v1",
      "project_id": "demo", "operation_id": "selftest-1",
      "task_id": "synthetic", "profile": "CPU_SELFTEST_V1",
      "scenario": "SUCCESS", "iterations": 10000,
      "timeout_seconds": 3, "network": false, "gpu": false
    }

No extra fields, command names, scripts, args, URLs, data paths, GPU,
network, runtime escape, shell or environment changes are permitted.
\`project_id\` must exist in the explicit project map, its original STATE
and EVENTS metadata must agree, and the Task must not conflict with an
active Task. Preflight returns \`execution_authorized=false\` even if ready.

## Checkpoint behavior

- Existing \`PDRW_RUNTIME_DIR\` must point to a private directory independent
  of scientific project, rules and the project-map directory.
- The fixed synthetic worker is launched through \`sys.executable -I -B -c\`
  with package-defined code, restricted 1..100000 iterations, 1..5s timeout,
  three synthetic exit scenarios, and a private output directory.
- SQLite \`synthetic_jobs\` records one unique \`(project_id, operation_id)\`,
  immutable plan fingerprint, one attempt, \`RUNNING_UNVERIFIED\`, and
  terminal result hash/status. The RUNNING transition is committed **before**
  starting the subprocess.
- Repeating the same operation does **not** rerun it. Changing the plan with
  the same operation ID creates \`SYNTHETIC_PLAN_CONFLICT\`.
- An interrupted host may leave \`RUNNING_UNVERIFIED\`: even with an output
  present, this cannot establish real process liveness. Return
  \`RECONCILIATION_REQUIRED_NO_AUTOMATIC_RESTART\` and require explicit
  operator-controlled reconciliation.
- Failure/timeout are recorded as terminal; no automatic retries.
- Output hashes are not scientific validation; no project, STATE, EVENTS or
  Run writes are performed.

## Required gates before real DEV/GPU execution

1. Separately authenticated trusted host with OS-enforced command, project
   path, process identity, GPU/network and permission restrictions; no
   model-supplied approval strings or permissive Python callback substitutes.
2. Frozen protocol/TaskSpec, original user grant resolution and bounded
   operation-specific authorization, including H6/H8/SEALED restrictions.
3. Host-owned process liveness, cancellation, resource tracking and
   checkpoint recovery without duplicate scientific jobs.
4. Run provenance (code/data/environment/seeds/versions) and registration
   through original PD-RW core, not this operational DB.
5. Real WorkBuddy integration, fault-injection, repeated-call concurrency,
   experiment budget and A/B/C efficiency measurement.

**Non-goals of v0.7.0**: autonomous DEV, scientific writes, GPU scheduling,
near-real-time process status, process cancellation, arbitrary job commands,
scientific permission gating solely by WorkBuddy/MCP, or paper writing.
