# Frozen decision points

One directory per decision point, produced by `../freeze.py` from the live
projects under `D:/workbuddy-work`, and re-checkable with `freeze.py --verify`.

Only `MANIFEST.json` is committed. It records every file's path, size and
sha256, the project's own final decision (`truth`), and — in `withheld` — what
was deliberately left out (raw data, `SEALED/`, `VAL/`, intermediate products).
The bytes themselves stay in the research project: copying another project's
records into this repository would create a second copy that drifts, and the
hash is what makes the comparison reproducible anyway.

Each snapshot is taken at the project's **final** state, so no later revision
can leak into a session asked to decide at that point. A session that needs the
bytes runs `freeze.py` on a machine that has the projects.

| point | project | outcome |
| --- | --- | --- |
| `DP1-POPU-HOLD` | 48 PoPu | `HOLD_RELIABILITY / H8_PENDING`, valid negative, evaluation failed twice |
| `DP2-TACTILE-NEG` | 44 tactile | negative claim + protocol erratum, cross-domain |
| `DP3-ACRF-PIVOT` | 17 ACRF/RCT | sealed negative, project pivoted |
