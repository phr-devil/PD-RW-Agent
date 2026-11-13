# Troubleshooting: stop guessing, preserve valid work

Load only when normal project resolution, rule routing, or state recovery fails.

| Symptom | Diagnostic | Response |
| --- | --- | --- |
| Skill not triggered | Check whether the user explicitly selected PD-RW or an existing PD-RW project | Invoke the skill by name if supported; don't trigger for unrelated research |
| Project ID ambiguous | Compare project ID, research line, dataset, and real root | Request the one missing identity anchor; never merge projects |
| Project map absent | Inspect the external local `project-map.local.json` location | Use known user-provided paths; do not recursively scan the entire disk |
| Snapshot file absent | Check listed record paths and known original Run references | Report `MISSING`, use available original artifacts, never fabricate state |
| State conflicts with Run | Read original protocol, run artifacts, and evidence lineage | Mark `SOURCE_CONFLICT`, preserve both claims until resolved |
| Git HEAD missing / stale | Read-only inspect local `git rev-parse HEAD`; compare remote only with suitable access | `RULE_VERSION_UNVERIFIED`; no automatic pull/rebase |
| Authorization unclear | Locate the original user instruction and scope | Hold **only** dependent restricted action; continue legal read-only work |
| Experiment repeats | Compare the factual hypothesis, configuration, and previous valid result | Reuse evidence or change the scientific discriminator, not merely random seed |
| SEALED protection requested | Check tool/filesystem isolation, not merely markdown or JSON | Report `ENFORCEMENT_NOT_CONNECTED` unless independently installed and tested |
| WorkBuddy ZIP rejected | Check a single skill folder with `SKILL.md` at its root and required metadata | Repackage from the repository; use WorkBuddy's import diagnostics |

When a case recurs, modify the smallest owner module and one regression test. Do not append the same warning to every reference.
