# Internal audit — PD-RW-Agent v0.5 (2026-11-13)

**Baseline:** PD-RW-Agent `41ae04ab847e388673a4bab9707883b6ea7d0c35`; PD-RW authority `68e29c367583d5c96ef70180819f8b3322ea840d`. Do not mistake CI results for scientific Agent performance.

## Scope and evidence standard

Static source review of `src/pdrw_agent`, its Skill/MCP/CLI adapters, CI, unit/integration tests, existing PD-RW evidence writer, authorization/SEALED boundaries, research-case retrieval and delivery. Follow up with Windows/Linux synthetic tests backed by pinned PD-RW. No real WorkBuddy client, original author messages, Windows OS ACL or GPU experiments were available in this audit.

## Prioritized findings / disposition

| ID | Severity | Finding (baseline) | Disposition |
| --- | --- | --- | --- |
| A01 | P1 | `get_resume_context` treated `INCOMPLETE_CONTEXT` as a generic source review, potentially producing a next-action hint without necessary state/record sources | **Fixed**: `BLOCKED_INCOMPLETE_CONTEXT`; covered by regression |
| A02 | P1 | New SQLite receipt could be attached to wrong project/Task despite observed identity or active Task mismatch | **Fixed**: source/identity/Task guard before changing receipts; read-only diagnostics remain available |
| A03 | P1 | `check_duplicate_experiment` only considered most recent ten indexed Runs, missing older exact fingerprints | **Fixed**: scan up to 500 eligible indexed Runs; return explicit `SEARCH_INCOMPLETE` for more and `UNVERIFIABLE_HISTORY` for missing/conflicting entries. A fingerprint candidate is still **not verified science** |
| A04 | P1 (deployment blocker for protected writes) | Prior `register_run_in_trusted_host` accepted a caller-supplied callback, which is **not** an independent security perimeter | **Hardened**: interface now always returns `TRUSTED_HOST_NOT_CONNECTED` and cannot write, even with dummy approval; a secured OS/tool host and actual filesystem ACL remain **open deployment blockers** |
| A05 | P1 | `ARTIFACT_REPORTED` is deliberately not a verified completion. It can be persistently pending reconciliation even after an ordinary DEV task | **Open**: add trustworthy completion evidence / explicit operator reconciliation later; do not auto-promote it to scientific success |
| A06 | P1 | Operational receipt DB security depends on Windows ACLs and operator's local environment; OS-level SEALED isolation untested | **Open**: must be tested on operator computer before protected/SEALED use |
| A07 | P2 | `get_project_context` reads a bounded snapshot and machine state **without validating full EVENTS integrity**; possible stale/corrupt index | **Open**: return integrity as unverified and require original PD-RW status/evidence checking before scientific decision or write |
| A08 | P2 | `memory.py` is keyword-only case-index retrieval, not verified scientific or semantic similarity memory | **Open**: real retrieval evaluation first; no automatic embedding/vector DB |
| A09 | P2 | `get_applicable_rules` parses section 2 of local PD-RW `AGENTS.md`; remote freshness not verified; fallback source may drift | **Open**: fail closed on source mismatch; validate WorkBuddy route selection on real trace |
| A10 | P2 | MCP SDK integration tests verify an in-process handshake and list/call, **not** the actual WorkBuddy stdio lifecycle, auto-selection or performance | **Open**: mandatory real client evaluation before v1.0 claims |
| A11 | P2 | Two legacy Skill-local scripts still duplicate read-only adapter logic from the shared Python service | **Deferred**: retain for fallback; retire only after actual WorkBuddy migration with backwards-compatibility test |

## Verified engineering invariants

- Runtime defaults to non-SEALED indexed metadata and bounded responses; file resolution rejects traversal and known protected names. This is **not** OS-level SEALED isolation.
- MCP exposes no original Run/Claim/STATE write tool; only private operational receipt write commands exist.
- PD-RW is scientific authority: `AGENTS.md`, original Run files, `STATE.json`, `EVENTS.jsonl`, `RESEARCH_RECORD.md`, `PAPER_BLUEPRINT.md`; SQLite is only non-scientific receipts.
- Original PD-RW writer provides event append lock + consistency checks. Synthetic CI exercises the **native PD-RW writer directly** for duplicate and concurrent writes, and tests the Agent facade cannot write even with a forged approval callback. Crash between EVENTS and STATE, protected-history reject, and no-auth rejection are covered.
- `VALID`/negative/invalid metrics must be judged against original Run protocol and independent groups; CI does not verify substantive science.

## Independent AI audit handoff (must not be primed by this report initially)

Reviewer should start from the **pinned current post-fix commit**, not from this file. Inspect all code and actual PD-RW owner docs independently; run existing CI; challenge trust boundaries, symlink/TOCTOU issues, sqlite identity and multi-project separation, incomplete/poisoned EVENTS and Run metadata, local-version drift, MCP/CLI/Skill parity, experiment-fingerprint coverage, scientific-meaning vs structural validity, and unbounded retries/outputs. Request minimal reproducible tests and cite exact source lines. Then compare to this report; resolve disagreements using original evidence, not AI votes.

## Real-v0.6 acceptance still required

No real WorkBuddy A/B/C, blinded historical decision replay, measured Token/GPU/user intervention, independent OS ACL, original author-authorization verification, or SEALED enforcement was performed. Those results are **NOT_MEASURED**. Use PD-RW `REPLAY_PROTOCOL.md`, with time-frozen legitimate evidence and no future leakage, before claiming an Agent science improvement.
