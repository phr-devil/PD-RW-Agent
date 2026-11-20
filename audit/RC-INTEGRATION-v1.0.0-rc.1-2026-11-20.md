# RC-INTEGRATION — frozen identifiers, v1.0.0-rc.1

Recorded after the build, so the hashes are of the bytes that were installed and
not of a draft. Date 2026-11-20.

## Integration branch

| item | value |
| --- | --- |
| branch | `rc/v1.0-integration` |
| base | `origin/main` (`09bd554` is an ancestor; the stack main → #17 → … → #26 is linear, 51 commits) |
| merge commit | `e0ac093` — the 0.9.2→0.9.14 stack landed as one history on top of `main` |
| release commit | `d3b35de` — `1.0.0rc1`, plus the three repairs the acceptance sessions found |
| this commit | `0ff9948` — positioning, comparison plan, task freeze, acceptance record |
| open PRs | #26 → #25 → #24 → #23 → #22 → #21 → #20 → #19 → #18 → #17 → `main`, all `MERGEABLE`; the integration branch supersedes them as one merge |
| not merged | nothing is pushed to `main` |

PRs #16 and #12 are deliberately not re-landed. #16 is already contained (merged
into the 0.9.2 branch at `904896b`). #12's strict Markdown identity parse and its
`runtime_identity.process` snapshot were reworked in 0.9.6/0.9.8 as
`markdown_project_id` + `DECLARED_ID_MATCH`/`UNKNOWN`; re-landing it would
reintroduce a second identity path. Recorded as a known gap, not as a merge.

## Versions

| item | value |
| --- | --- |
| package | `1.0.0rc1` (`pyproject.toml`, `src/pdrw_agent/__init__.py`) |
| Skill frontmatter | `version: 1.0.0rc1` |
| MCP `serverInfo` | `PD-RW Research 1.0.0rc1` |
| interpreter | CPython 3.13.14 (system and `.venv`) |
| MCP surface | 21 tools by default; profiles still 11/21/24 |

## Skill archive

| item | value |
| --- | --- |
| file | `dist/pd-rw-research-1.0.0rc1.zip` |
| sha256 | `a5428aae81a55adfbf3ee5e4495f3ccbc64b0adaaaac4b3c4ec0d943b551196f` |
| entries | 10 |
| determinism | two consecutive `tools/package_skill.py` runs give the same sha256 |
| installed | `~/.workbuddy/skills/pd-rw-research/`, byte-identical to `skills/pd-rw-research/` on all 10 files |
| rollback | `~/.workbuddy/skill-backups/pd-rw-research-pre-rc/` holds the previous install |

## Verification run against this tree

| check | result |
| --- | --- |
| `pytest tests -q` | **617 passed, 8 skipped, 151 subtests** |
| `unittest discover -s tests` | 625 tests, OK (8 skipped) |
| `evals/case_gate_eval.py` | 13 gate calls, 9 verified checkpoints, **0 false / 0 missed** triggers |
| `audit/science04/freeze.py --verify` | 35 files, **1 509 332 bytes**, 0 skipped |
| `audit/agent_comparison/build_tasks.py --verify` | 5 bundles OK (CAL-1 4 files, CAL-2 8, T1 14, T2 6, T3 9) |
| MCP stdio handshake | initialize + tools/list + `get_project_context` on project 48 → `DECLARED_ID_MATCH` |

Task bundle digests (first 12 hex of the manifest digest, full value in each
`MANIFEST.json`): CAL-1 `980523aebc4d`, CAL-2 `2d38e322fee8`, T1 `e4446e733b91`,
T2 `0d36799b0e9c`, T3 `7dc06ce6830e`.

## Environment

Python 3.13.14, no Docker, one RTX 4080 (16 GB, unused this round), Windows 11 +
Git Bash. Paid compute `0`, downloads `0`, training `0`, SEALED reads `0`.

## Not measured

Token counts (no meter in the host), real-LLM end-to-end success rate, MCP calls
from inside the host (the stdio server works by hand), `artifact_links_verified`
(still `false`), `run_integrity` wiring, and any claim about research gain or time
saved. The comparison tasks are frozen but unrun.
