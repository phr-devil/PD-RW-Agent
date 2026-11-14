# v0.7.3 — Fixed-host reliability and isolated-account acceptance probe

This increment remains operator diagnostic only. The main repository already
implements a fixed CPU host pilot in v0.7.2; no arbitrary DEV runner,
model command execution, GPU scheduler or scientific writer is enabled.

## Changes

- Win32 process identity now observes GetExitCodeProcess as well as process
  birth FILETIME. Matching PID/birth token is NOT reported as running after
  the process is observed exited. Linux /proc remains best-effort. These
  snapshots never confer host ownership or permission.
- Operator interrupts are recorded as INTERRUPTED, not mislabeled as
  technical scientific failures. Idempotent restart protection remains.
- Operator-only synthetic ACL probe is available from host CLI:

      python -m pdrw_agent.host.cli acl-probe --project-id demo \
        --dev-fixture /path/to/fixtures/dev-readable.fixture \
        --denied-fixture /path/to/fixtures/sealed-denied.fixture

  The dev-readable.fixture file must contain precisely the bytes
  PDRW_ACL_PROBE_V1_DEV followed by LF. An operator independently creates
  both synthetic files, and sets the intended ACL. Run the probe under the
  intended restricted OS host account, not the WorkBuddy account.
  A denied read produces HOST_FIXTURE_ACL_DENIAL_OBSERVED_ONLY (exit code 0);
  both files readable produces HOST_FIXTURE_ACL_GAP (exit code 3).
  Missing fixtures are inconclusive. Neither outcome authorizes execution,
  authenticates the principal or checks any real SEALED data.

## Still NOT COMPLETE

1. Provision a separate restricted Windows principal and ACL-protected
   grant/registry/runtime directories on the actual user workstation.
2. Verify genuine DEV-allow/SEALED-deny under the separately restricted SID,
   including access to real project paths and original PD-RW source controls.
3. Authenticated host IPC and authoritative original-user grant storage.
   A model-provided approval or environment flag must never be accepted.
4. Registered real DEV CPU runner binding, immutable TaskSpec/code/dataset,
   live cancellation, crash reconciliation and original PD-RW Run recording.
5. Verified GPU/VRAM budget enforcement and matched WorkBuddy A/B/C utility.

CI runs synthetic tests on Windows and Ubuntu. The mocked PermissionError
test checks classification only and does NOT establish OS ACL acceptance.
