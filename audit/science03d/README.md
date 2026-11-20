# SCIENCE-03D artifacts

Everything here is read-only evidence for `audit/SCIENCE-03D-v0.9.12-2026-11-20.md`.
No script writes into a research project.

| file | what it is |
| --- | --- |
| `build_fixture.py` → `fixture-project/` | two frozen plans (beam, sensor), `RUN-101` executing the beam plan with `protocol_sha256`, `RUN-102` a copy still claiming RUN-101, `RUN-103` aggregate numbers only |
| `repro_prefix.py` → `repro_before.json` / `repro_after.json` | the same four packets against 16e7dd4 and against the patch |
| `real_48_check.py` | RUN-005 cited for its own plan and for another line's plan, on real project files |
| `tasks/` | the frozen prompts handed to the independent sessions |
| `packets/` | what those sessions wrote (4, all schema-rejected), plus `D1_fixed.json` (one mechanical shape fix) and `D1_misattributed.json` (one label changed) |
| `normalize.py` | produces the two files above; records exactly what it changed |
| `eval_packets.py` → `eval_packets.json` | both code versions on the same packets; needs the 0.9.11 worktree (see the module docstring) |
| `review_bundle.json` / `review_key.json` / `review/review_report.md` | blinded review of the two arm pairs, the unblinding key, and the reviewer's own words |
| `payload_measure.py` → `payload_measure.json` | compact-JSON size of the same payloads used in 0.9.9–0.9.11 |

Rerun order: `build_fixture.py`, `repro_prefix.py`, `normalize.py`, `eval_packets.py`,
`payload_measure.py`. The fixture is committed, so `build_fixture.py` is only needed to regenerate
the hashes after editing a plan.
