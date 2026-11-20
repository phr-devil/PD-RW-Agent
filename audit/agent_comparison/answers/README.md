# Answer keys — held outside this repository

The five keys for the v1.0 comparison task set are **not in this tree**. They live at

```
~/.pdrw-eval/keys/agent_comparison-rc1/{CAL-1,CAL-2,T1,T2,T3}_KEY.json
```

and their sha256 values are in `KEYS.sha256` next to this file, so a third party can
confirm which key a score was computed against without being handed the key.

## Why they were moved, and what it does not fix

The keys were committed in `0ff9948` (2026-11-20) and shipped in tag `v1.0.0-rc.1` and in
PR #27 on a **public** repository. Removing them from the tree stops the next commit from
carrying them; it does not make them secret again. Anyone who fetched the branch, the tag
or the PR diff has them, and any arm that can read this repository's git history can
recover them.

Consequence, recorded before any run: **CAL-1, CAL-2, T1, T2 and T3 are not blind tasks.**
They may be used for grader calibration, regression and exploratory comparison. A claim
that a model was tested blind on them would be false.

A second channel has the same effect and is not fixable by moving files: the public audit
reports under `audit/` already quote the numbers these tasks ask for (`0.6717`, `96/111`,
`411202`, the RUN-002 binding state). A task drawn from projects 19, 44 or 48 cannot be
blind to an arm that can read this repository, whatever happens to `answers/`.

New formal tasks therefore have to satisfy three conditions, all of which this tree
cannot supply by editing:

1. the source project's result is not quoted anywhere in this repository;
2. the source project's files are not reachable from the arm's workspace;
3. the key is generated after the bundle is frozen and is never committed.

## Scoring without the key in the tree

A grader reads the key from the private path above, scores the answer, and writes the
score plus the key's sha256 into the run record. The key itself is never copied back.

## Test fixtures are unaffected

`answers/` was also used by nothing in the test suite; `build_tasks.py --verify` checks
bundles against manifests and does not read the keys.
