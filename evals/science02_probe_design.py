"""SCIENCE-02 stage B: what ``assess_proposal`` says about three real experiment designs.

Each packet reproduces the algorithm/experiment decision of a documented case,
with the same framing the record contains:

* ``PB-01`` CASE-11 / EXT-X3 — the probe counts windows while declaring group
  independence PASS;
* ``PA-01`` CASE-02 / CASE-12 — the probe's reference condition is a test-label
  oracle, i.e. not a legal baseline;
* ``PC-01`` CASE-08 — none of the candidate probes separates any hypothesis
  pair, so no experiment can change the judgment.

The script prints the current output plus an explicit "detected" column so the
gap is visible without reading the whole payload.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pdrw_agent.science.decision import assess_proposal  # noqa: E402

SCOPE = {"material": "未见材料", "condition": "未见条件", "evaluator": "ridge"}
BASE = {
    "claim_type": "MECHANISM/CAUSAL",
    "question": "跨条件塌缩由几何/材料机制决定，还是由观测预算决定",
    "claim_evidence_refs": ["DEV/runs/RUN-011/metrics.json"],
    "hypotheses": ["H_mechanism", "H_budget"],
    "proposed_premise": {"premise_id": "MECHANISM", "scope": SCOPE},
    "prechecks": {
        "group_independence": {"status": "PASS", "evidence_refs": ["DEV/protocol.md"]},
        "label_provenance": {"status": "PASS", "evidence_refs": ["DEV/labels.md"]},
        "legal_inputs": {"status": "UNKNOWN", "evidence_refs": []},
    },
}

PB_01 = dict(BASE, probes=[{
    "id": "PB-01-WINDOW-PROBE",
    "observable": "边界误差",
    "evaluation_unit": "WINDOW",
    "comparison_reference": "VT_plain",
    "predictions": {"H_mechanism": "DECREASE", "H_budget": "NO_CHANGE"},
    "cost_band": "LOW",
}])

PA_01 = dict(BASE, probes=[{
    "id": "PA-01-ORACLE-REFERENCE",
    "observable": "R2",
    "evaluation_unit": "SPECIMEN",
    "comparison_reference": "ORACLE_OFFSET_REMOVAL_DEV_VAL_LABELS",
    "predictions": {"H_mechanism": "INCREASE", "H_budget": "NO_CHANGE"},
    "cost_band": "LOW",
}])

PC_01 = dict(BASE, probes=[
    {"id": "PC-01-A", "observable": "R2", "evaluation_unit": "SPECIMEN",
     "comparison_reference": "VT_plain", "predictions": {}, "cost_band": "LOW"},
    {"id": "PC-01-B", "observable": "MAE", "evaluation_unit": "SPECIMEN",
     "comparison_reference": "VT_plain", "predictions": {"H_mechanism": "UNKNOWN"},
     "cost_band": "MEDIUM"},
])

PACKETS = {"PB-01": PB_01, "PA-01": PA_01, "PC-01": PC_01}


def main() -> int:
    rows = []
    for name, packet in PACKETS.items():
        result = assess_proposal(packet)
        probes = result["probe_comparisons"]
        rows.append({
            "packet": name,
            "pair_counts": {p["id"]: p["pair_count"] for p in probes},
            "frontier": result["declared_probe_efficiency"]["frontier_candidate_ids_as_declared"],
            "precheck_review": {k: v["review"] for k, v in result["prechecks"].items()},
            "probe_findings": result.get("probe_findings", []),
            "no_decisive_probe": result.get("no_decisive_probe"),
        })
    print(json.dumps({"stage": "B", "model_invoked": False, "rows": rows},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
