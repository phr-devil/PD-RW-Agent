# Scientific agent value: frozen replay experiments before adding new tools

The goal is **better evidence-grounded algorithm research**, not more MCP tools.
This document defines evaluation gates, **not new PD-RW scientific policy**.

| Proposed aid | Required original evidence | Positive replay | Critical counterexample |
| --- | --- | --- | --- |
| Prior negative premise retrieval | Original Run, frozen protocol, evidence-backed premise and applicability scope | Finds genuinely repeated failed assumption; suggests independent discriminating probe | Must not call a new mechanism invalid merely because the same keywords/backbone appear |
| Experiment information value | Competing hypotheses, predicted qualitative outcomes, legal measurements, resource cost | Ranks a low-cost probe separating plausible mechanisms | Do not invent expected probabilities, effect sizes or scientific merit scores |
| Leakage / pseudo gain precheck | True label derivation, group/time split, metric, legal prediction inputs, full evaluation units | Surfaces risk using cited evidence, with `UNKNOWN` when missing | Never equate `not reported` with clean or contaminated data; never turn a check into evidence of valid science |
| Literature nearest-neighbor | Verifiable DOI/metadata/full text in authorized source with retrieval date | Flags genuine claim overlap and precise differences | No DOI/title invention or automatic novelty/pass recommendation without adequate sources |
| Skill routing index | Same WorkBuddy client/model/task/time-frozen sources | Fewer irrelevant file reads without lost rule coverage | Do not confuse a file-index hit with an authorized rule path |

**Experiment design:** Use PD-RW `REPLAY_PROTOCOL.md` with prior evidence frozen at decision time; compare A direct WorkBuddy+PD-RW, B +Skill, C +Skill+Python+MCP. Record actual tools/files opened, wrong project, unsafe effect, claim errors, manual interventions, wall time and model/GPU tokens. Reviewer should blind-mark scientific correctness, applicability of prior negatives, valid baseline preservation and next probe discriminative power. Preserve only anonymized/fake fixtures in public GitHub. No WorkBuddy behavior/Token improvement is measured yet.

**Engineering preview v0.5.1:** Optional local `science/decision.py` and `science/replay.py` inspect declared premise/probe contrasts and validate frozen local source hashes and blinding packets. They do not attest true scientific value or prevent future knowledge embedded in prose. No new MCP tools. Real A/B/C remains `NOT_MEASURED`.

**Implementation gate:** Add a new MCP tool only if it improves a replay failure with bounded input/output, explicit evidence citations, safe UNKNOWN handling and no extra unauthorized action. First fix existing recovery/measurement semantics.
