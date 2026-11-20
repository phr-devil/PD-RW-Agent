# WorkBuddy acceptance — v1.0.0rc1

What a real session did, what a test pinned, and what nobody measured. Written
after the release commit, so every number below is from the tree tag `v1.0.0-rc.1`
(package `1.0.0rc1`).

## 0. The build that was installed

| item | value |
| --- | --- |
| package version | `1.0.0rc1` (`pdrw_agent.__version__`, `pyproject.toml`, `--serverInfo.version`) |
| Skill version | `1.0.0rc1`, 10 files |
| Skill archive | `dist/pd-rw-research-1.0.0rc1.zip`, sha256 `a5428aae81a55adfbf3ee5e4495f3ccbc64b0adaaaac4b3c4ec0d943b551196f` |
| archive determinism | two consecutive `tools/package_skill.py` runs produced the same sha256 |
| installed copy | `~/.workbuddy/skills/pd-rw-research/`, byte-identical to `skills/pd-rw-research/` on all 10 files |
| interpreter | Python 3.13.14 (system), same version in `.venv` |
| MCP | stdio handshake OK: `PD-RW Research 1.0.0rc1`, 21 tools, `get_project_context` answered |

## 1. Three independent sessions

Each session received one project, the installed Skill, and a task file. None had
seen `src/`, `tests/`, `docs/` or the audit trail. Their answers are in
`answers/`; the tasks are in `tasks/`.

| session | project | wall clock | what it did | what it got right | what it got wrong or could not do |
| --- | --- | --- | --- | --- | --- |
| S1 | 19 (CRPS) | 45 min | `template` → `packet-check` (2 rounds) → `decision`; recomputed every mean from JSON | found the headline `0.6717 → 0.7135` is **refuted inside the project** (`B−A = −0.84 pt`, 5/5 dates negative); found `96/111` rebuildable from no artifact (97 EVAL / 92 ALGO_ROUND) and `17/17` true only in `CRPS_L2_EVAL.json`; ranked `SF|lag3` above the arm the report calls the fair baseline | quoted one GRUctx mean from `CRPS_L2_EVAL.json` (0.7135) while comparing baselines taken from `CRPS_L2_ALGO_ROUND.json` (0.7091) without saying the files differ |
| S2 | 48 (PoPu) | 17 min | two packets differing only in `premise_ref`, both `SHAPE_OK` on round 1, both through `decision` | same Run read as **attributed** when it names the plan RUN-005 executed, and as `CLOSURE_PREMISE_CONTRADICTED` with the probe back in the frontier when it names another line's plan; kept an unauthorized probe in `needs_authorization_ids` in both runs | nothing material; it correctly reported `premise_verified: false` instead of rounding up |
| S3 | 44 (D1 tactile) | 11 min | cold `resume` → `context` → `rules` → `history` → `template` → `packet-check` (2 rounds) → `decision` | both reserved probes (`VAL`, `SEALED`) landed in `needs_authorization_ids`; read no bytes from either and proved it with before/after `stat` (size/mtime/ctime/inode) plus a command audit; said plainly that the boundary held because it complied, **not** because the tool enforced it | `history` returned `HISTORY_SOURCES_MISSING`; `RUN-002` binding failed with `RUN_RECORD_TOO_LARGE` (411 202 B record vs a 128 KiB cap) |

Total 73 minutes, 0 paid compute, 0 downloads, 0 training, 0 SEALED reads. Tokens
`NOT_MEASURED` for S1/S2; S3 supplied an *estimate* (~46–58k) and labelled it as
one.

## 2. What the sessions found that the tests had not

1. **The record cap was smaller than the records.** 128 KiB refused project 44's
   411 202-byte fold-level `metrics.json`, so a Run that really ran fell through to
   `unverified_closure_ids`. Raised to 4 MiB and pinned both ways (411 KB binds, a
   5 MB dump is still refused). Re-verified after the fix: the same packet now
   reports `file_binding: BOUND` where the session saw `UNRESOLVED`.
2. **`VAL` was not in the protected-path set** although PD-RW reserves it. Measured:
   `VAL/README.md` was handed to the JSON parser as a Run candidate. A reserved root
   is now refused at the root segment only, so `data/val/` inside DEV still binds.
3. **The version identity was asserted, not checked.** Two documents called the
   0.9.14 tree "0.9.13". `test_arch_convergence` now fails on drift.

## 3. Model-autonomous vs scripted vs CI

| behaviour | how it was established |
| --- | --- |
| `template` → `packet-check` → `decision` on three projects | **model-autonomous**: three independent sessions, recorded tool calls |
| attribution by named plan; contradiction by wrong plan | **model-autonomous** (S2), and pinned by tests |
| reserved `VAL`/`SEALED` staying out of the frontier | **model-autonomous** (S3), and the binder path pinned by tests |
| refusal of `SEALED`/`HOLDOUT`/`CONFIRMATION`/`VAL` paths | **scripted**: `bind_run_reference` on real paths, no model involved |
| 617 tests, `case_gate_eval` 13 calls / 9 checkpoints / 0 false / 0 missed | **CI / scripted** |
| MCP handshake, 21 tools, one tool call | **scripted** over stdio; the host session did not expose the MCP tools, so no model ever called them |

## 4. What remains unaccepted

- **MCP inside the host.** The server works when driven by hand; the host never
  surfaced its tools in these sessions, so acceptance ran through the CLI. Recorded
  rather than worked around.
- **`AUTH/BUDGET` is not echoed by `resume`.** The unauthorized list only exists in
  `STATE.md`; S3 had to read it there. Truncating the line into a state index would
  drop the "not authorized" half, which is worse than omitting it.
- **`history` has no event chain.** With no `STATE.json`/`EVENTS.jsonl`, the run
  list is a Markdown echo. `resume` reports `SOURCE_REVIEW_REQUIRED` and nothing
  stronger.
- **Identity is declared, not verified.** `DECLARED_ID_MATCH` /
  `EXPLICIT_PROJECT_ID`: the project map and `STATE.md` agree about a string.
- **Rule freshness is local.** `rule_freshness: REMOTE_NOT_CHECKED`; the digest
  proves which rules were used, never that they are current.
- **Tokens, real-LLM success rate, MCP-in-host, paid cost**: `NOT_MEASURED`.
