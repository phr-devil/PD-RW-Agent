"""Evaluate the frozen packets under both code versions, blind-label ready.

Runs each packet through 0.9.11 and the patched tree, then prints a comparison
keyed by packet. Nothing is written into the projects.

The 0.9.11 arm is a detached worktree; create it once with:

    git worktree add D:/workbuddy-agent/_v0911 16e7dd4

Run: python audit/science03d/eval_packets.py > audit/science03d/eval_packets.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEW = HERE.parents[1]
OLD = Path("D:/workbuddy-agent/_v0911")
PACKETS = HERE / "packets"

PROJECTS = {
    "D1_independent": HERE / "fixture-project",
    "D1_fixed": HERE / "fixture-project",
    "D1_misattributed": HERE / "fixture-project",
    "D2_independent": Path("D:/workbuddy-work/48"),
    "D3_old": Path("D:/workbuddy-work/48"),
    "D3_new": Path("D:/workbuddy-work/48"),
}


def run(src: Path, packet: Path, project: Path) -> dict:
    env = dict(os.environ, PYTHONPATH=str(src / "src"))
    proc = subprocess.run(
        [sys.executable, "-m", "pdrw_agent.science.cli", "decision",
         "--packet", str(packet), "--project-root", str(project)],
        capture_output=True, text=True, env=env, timeout=120, check=False)
    if proc.returncode != 0:
        text = (proc.stderr or proc.stdout).strip()
        detail = [line for line in text.splitlines() if "error_code" in line or "detail" in line]
        return {"error": detail or text.splitlines()[-3:]}
    return json.loads(proc.stdout)


def summarize(result: dict) -> dict:
    if "error" in result:
        return {"error": result["error"]}
    eff = result["declared_probe_efficiency"]
    probes = {}
    for item in result["probe_comparisons"]:
        prior = item.get("prior_execution") or {}
        binding = prior.get("run_binding") or {}
        probes[item["id"]] = {
            "applicability": item["applicability"],
            "next_action": item["next_action"],
            "findings": item["findings"],
            "status_verified": prior.get("status_verified"),
            "premise_binding": prior.get("premise_binding"),
            "premise_binding_basis": prior.get("premise_binding_basis"),
            "premise_plan_match": binding.get("premise_plan_match"),
            "run_id_consistency": binding.get("run_id_consistency"),
            "record_structure": binding.get("record_structure"),
        }
    return {
        "frontier": eff["frontier_candidate_ids_as_declared"],
        "historical": eff["historical_evidence_ids"],
        "premise_unbound": eff["premise_unbound_ids"],
        "premise_contradicted": eff.get("premise_contradicted_ids"),
        "status_conflict": eff["status_conflict_ids"],
        "no_executable_next_probe": result["no_executable_next_probe"],
        "probes": probes,
    }


def main() -> None:
    out = {}
    for name, project in PROJECTS.items():
        packet = PACKETS / f"{name}.json"
        if not packet.exists():
            out[name] = {"missing": True}
            continue
        out[name] = {
            "packet": str(packet.relative_to(NEW)).replace("\\", "/"),
            "project": str(project),
            "old_0_9_11": summarize(run(OLD, packet, project)),
            "new_0_9_12": summarize(run(NEW, packet, project)),
        }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
