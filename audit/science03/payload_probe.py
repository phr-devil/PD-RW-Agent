"""Character cost of the probe payload, before and after the 0.9.9 frontier fix.

Same packets as the existing evals, so the numbers are comparable with the
2 813 / 2 965 (clean) and 7 400 / 8 640 (three defective) figures quoted in
``docs/RUNTIME_AND_MCP.md``. A character count is a SIZE proxy, not tokens.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "evals"))

from pdrw_agent.science.decision import assess_proposal  # noqa: E402
import science02_probe_design as B  # noqa: E402


def clean_two_probe():
    return {
        "question": "Does a new lawful signal explain the residual?",
        "claim_type": "MECHANISM",
        "proposed_premise": {"premise_id": "lawful-signal",
                             "scope": {"dataset": "synthetic-development"}},
        "hypotheses": ["mechanism", "shortcut", "null"],
        "probes": [
            {"id": "cheap-control", "observable": "group error", "evaluation_unit": "subject",
             "comparison_reference": "simple-model",
             "predictions": {"mechanism": "INCREASE", "shortcut": "DECREASE",
                             "null": "NO_CHANGE"}, "cost_band": "LOW"},
            {"id": "expensive-repeat", "observable": "group error", "evaluation_unit": "subject",
             "comparison_reference": "simple-model",
             "predictions": {"mechanism": "INCREASE", "shortcut": "DECREASE",
                             "null": "NO_CHANGE"}, "cost_band": "HIGH"},
        ],
    }


def size(packet):
    # Compact separators, matching how the runtime serialises tool output.
    return len(json.dumps(assess_proposal(packet), ensure_ascii=False, separators=(",", ":")))


def main() -> int:
    defective = {name: size(p) for name, p in B.PACKETS.items()}
    print(json.dumps({"clean_two_probe": size(clean_two_probe()),
                      "defective": defective,
                      "defective_total": sum(defective.values())},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
