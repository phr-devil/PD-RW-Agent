# v0.6 Python state and evidence engine (bounded read-only)

Implementation owner: `src/pdrw_agent/runtime/audit.py`. PD-RW remains the only
scientific rules/record authority. This is not a new STATE or third research ledger.

## Contract

- `audit_project_state(project_id)` returns a bounded diagnostic view:
  registered root, current (unverified) STATE index and snapshot excerpt,
  source availability, SHA256-manifest coverage, local declared rule version
  discrepancy, and blockers. It **does not** grant permission or verify science.
- The manifest audit searches at most 128 non-protected directories, 16
  `.sha256` manifests, 512 entries; hashes at most 64 MiB per artifact.
  It skips `data`, symlink directories and SEALED/holdout/confirmation paths.
  Relative refs are checked against the registered root before opening.
  `AUDIT_INCOMPLETE` means the bounded check was not exhaustive.
- `PARTIAL_RECOVERY` means there are recoverable source hints despite
  missing or conflicting authoritative artifacts. It does **not** mean an
  experiment may resume. Missing STATE/EVENTS cannot be invented.
- `find_experiment_evidence` distinguishes `EVIDENCE_INDEX_MISSING` from a
  present index with zero qualifying Run events (`NO_INDEXED_DEV_RUN`).
- `get_applicable_rules` exposes available topics on unmatched requests
  and recognizes unambiguous query tokens (e.g., DEV in longer text).
  Navigation is not policy or authorization.
- SQLite execution-status reads use a read-only connection. Only explicit
  receipt begin/checkpoint operations may mutate the private receipt DB.

## Usage

```powershell
python -m pdrw_agent.cli audit --project-id 37
```

The MCP tool is also called `audit_project_state`. Use it after the
registered-project scope gate, when a combined state/evidence diagnosis
will materially reduce repeated file reading. It is optional for quick
informational tasks. CLI and MCP share `ResearchService`.

## Structured memory increment

`search_research_memory` now parses the existing four-column CASE_REGISTRY
case table into bounded, ranked cards with case IDs, declared status tags,
boundaries and source declarations. It is **not** a new memory database,
not a semantic-equivalence detector, and never promotes historical prose
to scientific evidence. Only search this cross-project index when the
current user's allowed source scope permits doing so.

## Non-goals and pending work

No automatic data downloads, experiment runs, GPU restarts, scientific
ledger writes, original-user approval verification, live process proof,
SEALED enforcement outside this adapter, or historical-content authenticity
claim. Structured lesson search and durable authorized executor are
subsequent v0.6 increments, subject to real WorkBuddy A/B/C evaluation.
