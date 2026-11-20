# notes — CAL-1 recompute (2026-11-05 snapshot)

## Verified (recomputed, not quoted)
- Object macro (mean of `results[obj][scheme]["seg_f1"]`, 17 objects): SF|lag3 = 0.671750 in **both** files.
  GRUctx|lag3 = 0.709090 in CRPS_L2_ALGO_ROUND.json; 0.713501 in CRPS_L2_EVAL.json. Report table quotes
  the ALGO value (0.7091), body text quotes the EVAL value (0.7135); both are correct for their own file.
- Object wins: strict per-object `GRUctx>SF` is 17/17 in EVAL, but only 15/17 in ALGO (D-SUB −0.0211,
  medium gear −0.0116). The report's "17/17" is true only of the main L2 file.
- Episode claim: 1464 episode_paired rows collapse to 111 unique episodes (~13.2 folds each).
  Averaging dSegF1 within episode gives **97/111 positive, 14 negative** (EVAL) — not 96/15.
  Under the same rule ALGO gives 92/111. Mean per-episode dSegF1 = 0.044614 (report 0.0447 ✓).
  The audit's per-date signs (26+15+18+26+11) do sum to 96, but 2025-01-13 is 27/34 in the data, not 26/34.
- Audit fold geometry reproduces exactly: test size mean 86.1 (79–91), mean pairwise test overlap 75.8.
- Boundary F1@0.5 means: SF 0.594837, GRUctx 0.589447 → matches the report (0.5948/0.5894), **not** the
  audit (0.5954/0.5901, stale pre-fix values, as are its segF1 0.6724/0.7139).
- GateCtx "1.6% of episodes" does not reproduce: 20/111 episodes (18.0%), 8/17 objects, 23/1464 rows.

## Could not verify (null / not asserted)
- Sealed 37: no seal hash, access log or split file in `inputs/`; "never read / never trained on" is
  unverifiable from these four files. I did not attempt to access it and it is not in this workspace.
- Bootstrap CIs [0.036,0.054] / date-clustered [0.026,0.073], Wilcoxon W=493, p=1.4e-14: not recomputed
  (no bootstrap seeds or per-frame scores in the JSONs; only paired episode scalars).
- "Equal architecture/history/budget" for DualHead/GrupuSkill: only hparams (hidden 48, 1 layer, 10 epochs,
  subsample 60000) are present; ALGO records `seeds_global: 0` while EVAL has `R_SEEDS: 5`, so the seed
  protocol behind the ALGO numbers is undocumented — cannot check single-seed vs multi-seed variance.
- Per-class F1 and transition/confusion claims (Lift 52.9→20.8 etc.): `per_class_f1` is keyed by class
  index ("0".."8"), not names, so named-class mapping in the report/audit cannot be confirmed.

## Boundary / authorization issues in the material
- 17 folds share ~88% of test episodes and are correlated replications, not 17 independent tests; the audit
  itself retracts the earlier "17/17 Wilcoxon p≈7.6e-6". Any per-object "17/17" claim inherits this.
- DEV-only evidence; the report's own gate for SUBMISSION_CANDIDATE is the sealed cross-recording test (G1),
  which would need explicit authorization and is outside this task. Nothing here licenses G1 or submission.
- "DRAFTABLE" and venue choices are governance judgements, not measurements; recomputation neither confirms
  nor authorizes them.
