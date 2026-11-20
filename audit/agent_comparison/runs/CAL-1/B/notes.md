# CAL-1 notes — recompute of project 19's final algorithm round (read-only)

## Verified (recomputed from the frozen inputs, no re-training possible)
- `results[obj]['SF|lag3'|'GRUctx|lag3'].seg_f1` over 17 objects: SF 0.671750 (both files), GRUctx 0.713501 (EVAL) / 0.709091 (ALGO_ROUND). The report quotes both (table 0.7091, §1 Champion 0.7135) — same SF, different GRUctx per file.
- Object wins: 17/17 in EVAL (strict >), but only 15/17 in ALGO_ROUND — the round the report summarises does not carry the 17/17 claim it repeats in §4.
- Episode pairing: 1464 object-episode rows, 111 unique episode ids; per-episode mean dSegF1 -> EVAL 97/111 positive (mean +0.0446), ALGO_ROUND 92/111. Neither is 96.
- STATS_AUDIT `date_signs` sum to 96, and its per-date cells match my recount except 2025-01-13 (declares 26/34, EVAL yields 27/34) — the 96 looks like a one-episode stale count from before the HMM-index fix that the report says regenerated EVAL.
- Boundary check: macro `bnd_F1_full_0_5` 0.5948 (SF) vs 0.5894 (GRUctx) — matches the report's 0.5948/0.5894; audit says 0.5954/0.5901 (slightly different).
- Wilcoxon on the 111 EVAL episode deltas: W=508, p=2.01e-14; audit declares W=493, p=1.43e-14. Same direction, not identical.
- GateCtx: 8/17 object wins vs GRUctx, 20/111 episode wins (18%); the report's "1.6%" equals 23/1464 object-episode rows, i.e. a row fraction mislabelled as a fraction of 111 episodes.
- volume_match macro 0.685442 > SF 0.671750 on 14/17 objects — a training-volume-matched SF variant that is legally deployable; it lives outside `results{}` (only seed means), so I kept SF as the baseline but the SF number understates the strongest no-context comparator. Report itself cites VolMatch 0.6854 elsewhere.

## What the component contributed
- Skill read; its boundary discipline applied (declarations are not evidence; report treated as claim; no case library touched).
- CLI used only to test capability: `science-audit --project-id 19 --run-id final_algo_round` returned `CONFIG_REQUIRED` (no PDRW_AGENT_CONFIG / project map, no registered Run). `cli --help` and `science.cli --help` list no metric-recompute subcommand.
- Net scientific contribution: zero numbers. All arithmetic is plain Python over the JSON. MCP_NOT_USED: no registered project mapping and no permitted MCP server in this isolated workspace (one call, no retry loop).

## Could not verify
- Anything requiring predictions, frames or training code: the four files hold only aggregates (seg_f1, per-class F1, confusion matrices, per-episode pairings). No recomputation of the metric itself, only of the aggregation.
- The DualHead/GRUskill architectural-equivalence claim, the shuffle control's distribution shift, Lift→Approach and Push→Grasp transition percentages (no transition tables per scheme in these files; `conf` matrices only), and the bootstrap CIs (no resampling code/seed disclosed; I did not re-derive them).
- The sealed-37 status ("never read") is unverifiable from these artifacts — no hash or access log.
- `bnd_F1_0_5` is 0.0 per object while `bnd_F1_full_0_5` is ~0.59 for the same scheme; the per-object key appears to be a different (unsatisfiable) slice — I report the macro of `bnd_F1_full_0_5` only.

## Boundary / authorization issues noticed
- Report §5 asserts "STOP algorithm development, start paper" and DRAFTABLE status; nothing in these four files shows an author grant, an H8/H10 decision record or a publication authorization — those are declarations, not evidence.
- Project identity is only a path/filename convention ("project 19"); I did not assert identity, and the CLI could not confirm it (CONFIG_REQUIRED).
- Deviation from prompt: prompt says "do not write outside answer.json", but the session also requires `notes.md` and `calls.log`; I wrote only those three files in the workspace root.
