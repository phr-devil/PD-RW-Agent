"""Payload cost of the 03C binding axes, compact JSON characters (not tokens)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, "audit/science03")
from payload_probe import clean_two_probe, B  # noqa: E402

from pdrw_agent.science.decision import assess_proposal  # noqa: E402


def size(result):
    return len(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


def main():
    rows = {}
    rows["clean_two_probe_no_history"] = size(assess_proposal(clean_two_probe()))
    total = 0
    for name, packet in B.PACKETS.items():
        chars = size(assess_proposal(packet))
        rows[f"defective_{name}"] = chars
        total += chars
    rows["defective_total"] = total
    popu = Path("audit/science03b/session2/popu_next_action.json")
    if popu.is_file():
        packet = json.loads(popu.read_text(encoding="utf-8"))
        rows["popu_three_probes_declared_only"] = size(assess_proposal(packet))
        try:
            rows["popu_three_probes_bound"] = size(
                assess_proposal(packet, project_root=Path("D:/workbuddy-work/48")))
        except TypeError:  # pre-03C signature: no binding axis existed
            rows["popu_three_probes_bound"] = None
    print(json.dumps(rows, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
