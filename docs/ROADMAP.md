# Implementation roadmap (not a second research workflow)

## Current delivery: v0.3/v0.4 foundations

- Shared installable Python package under `src/pdrw_agent/`.
- Five bounded, **read-only** tools available through both Python CLI and optional MCP v2.
- Explicit project registry, selective PD-RW rule lookup, historical case-index search, non-SEALED run index, conservative fingerprint checking.
- Existing `skills/pd-rw-research/scripts/bridge.py` and `context.py` retained temporarily as standalone compatibility tools. In a later version, either package the shared runtime for Skill use or retire legacy scripts after a measured WorkBuddy migration.
- CI validates existing plus new unit tests across Windows and Linux, including the MCP SDK where installed.

## Next: WorkBuddy client integration gate

- Validate startup/handshake and each of five tools from the real WorkBuddy UI.
- Verify automatic Skill selection, correct on-device source root, no fabricated Run, no SEALED read, fresh-session recovery and minimal tool outputs.
- Compare against direct PD-RW-document baseline on the same frozen task, model and input budget. **NOT_MEASURED** until real traces collected.

## Later: governed writes and real execution durability

- Add a *trusted* tool host to authenticate original user actions independently; test protected paths at OS/tool level.
- Reuse PD-RW `core.state` event writer; idempotent record registration and crash-safe recovery with conflict tests.
- Optional bounded external execution receipt/checkpoint for an already authorized local task; never a parallel scientific record.
- Preserve user choices H1–H6/H8, autonomous authorized H7 DEV, and separate SEALED/confirm/writing/figure/upload/pay/submit gates.
- Add real historical blind A/B tests using PD-RW `REPLAY_PROTOCOL.md`; no fake measures or token-saving claims.

## Non-goals

No new scientific policy, unbounded shell/file tools, cloud service, vector database, speculative multi-agent planner, training scheduler or new GPT API billing by default.
