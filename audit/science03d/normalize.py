"""Mechanically normalize one independently authored packet, and make one variant.

Two independent sessions produced schema-invalid packets (4 of 4); the violations
are recorded in the audit. For the one packet whose *only* violation is the
`prechecks` shape, this script applies exactly one mechanical change -- a list of
`{id, status}` entries becomes the `{name: {status}}` mapping the contract asks
for -- and writes `D1_fixed.json`. Content is untouched.

`D1_misattributed.json` then changes one field of the independently authored
packet: the premise label of the probe that cites RUN-101. The session had
labelled it `BEAM_STIFFNESS_MECHANISM` (honest: RUN-101 executed the beam plan);
the variant labels it `SENSOR_DRIFT_MECHANISM`, which is what a session that
conflates the two lines writes. Same files, same Run, one label different.

Run: python audit/science03d/normalize.py
"""
from __future__ import annotations

import json
from pathlib import Path

PACKETS = Path(__file__).resolve().parent / "packets"
CHECKS = {"label_provenance", "group_independence", "legal_inputs",
          "evaluation_integrity", "metric_appropriateness", "effect_size"}


def main() -> None:
    source = json.loads((PACKETS / "D1_independent.json").read_text(encoding="utf-8"))
    fixed = dict(source)
    entries = source.get("prechecks")
    if isinstance(entries, list):
        normalized = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("id") or entry.get("name")
            if name in CHECKS and isinstance(entry.get("status"), str):
                normalized[name] = {"status": entry["status"], "evidence_refs": []}
        fixed["prechecks"] = normalized
    (PACKETS / "D1_fixed.json").write_text(
        json.dumps(fixed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    variant = json.loads(json.dumps(fixed))
    changed = []
    for probe in variant["probes"]:
        prior = probe.get("prior_execution") or {}
        if prior.get("run_ref", "").startswith("DEV/runs/RUN-101"):
            prior["premise_id"] = "SENSOR_DRIFT_MECHANISM"
            changed.append(probe["id"])
    (PACKETS / "D1_misattributed.json").write_text(
        json.dumps(variant, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"prechecks_normalized": list(fixed["prechecks"]),
                      "misattributed_probes": changed}, ensure_ascii=False))


if __name__ == "__main__":
    main()
