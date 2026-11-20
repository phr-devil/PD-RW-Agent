"""Freeze the A/B/C comparison task bundles.

Each task is a directory `tasks/<ID>/` holding `MANIFEST.json`, `PROMPT.md` (the
arm-facing brief, byte-identical across arms) and `inputs/` (a frozen copy of the
visible project files).  The answer key lives in `answers/` and is never copied
into a bundle.

Copying is deliberate: a manifest that only names paths would let a later project
edit change what the arm saw.  Hash and byte count are recorded per file and in
the total, so a bundle can be re-verified without the source project.

Run:  PYTHONPATH=src python audit/agent_comparison/build_tasks.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = Path("D:/workbuddy-work")

# Not a sampled task list: these are the three projects that already carry a
# frozen protocol, a real Run and an adjudicated outcome, plus the two cheap
# calibration probes whose answers are computable here.
TASKS = [
    {
        "id": "CAL-1",
        "kind": "calibration",
        "project": "19",
        "frozen_at": "2026-11-05",
        "question": "recompute rates from artifacts, not from the report",
        "visible": [
            "CRPS_L2_EVAL.json",
            "CRPS_L2_ALGO_ROUND.json",
            "CRPS_L2_STATS_AUDIT.json",
            "FINAL_ALGO_ROUND_REPORT.md",
        ],
        "excluded": [
            "dev_h8_v1/ (the later refutation)",
            "dev_h9_v1/ (the one-time confirmation)",
            "CRPS_HIERARCHICAL.json and every other CRPS_*.json",
            "REASSEMBLE/ (raw data)",
        ],
    },
    {
        "id": "CAL-2",
        "kind": "calibration",
        "project": "44",
        "frozen_at": "2026-11-16",
        "question": "identity, rule version, Run binding and the authorization line",
        "visible": [
            "STATE.md",
            "RESEARCH_RECORD.md",
            "H8_DECISION_BRIEF_2026-11-16.md",
            "D1_ACCEPTANCE_REPORT_2026-11-14.md",
            "protocol/PROTO-GEOM-HS-v1.json",
            "protocol/PROTO-GEOM-HS-v2.json",
            "DEV/runs/RUN-001/metrics.json",
            "DEV/runs/RUN-002/metrics.json",
        ],
        "excluded": ["VAL/", "SEALED/", "any *.csv prediction dump"],
    },
    {
        "id": "T1",
        "kind": "formal",
        "project": "48",
        "dimension": "scientific judgement",
        "frozen_at": "before the H8 HOLD decision",
        "question": "which mechanism explains 'not predictable beyond magnitude', and what is the cheapest probe that separates them",
        "visible": [
            "STATE.md",
            "RESEARCH_RECORD.md",
            "protocol/PROTO-POPU-DEPLOY-v3-DEV003.json",
            "protocol/PROTO-POPU-INF-INC-v1.json",
            "protocol/PROTO-POPU-INF-INC-v2-DEV002.json",
            "protocol/PROTO-POPU-POSTUREVALUE-v4-DEV004.json",
            "protocol/PROTO-POPU-RELIABILITY-v5-DEV005.json",
            "protocol/PROTO-POPU-RELIABILITY-v5-DEV005.amendment-001.json",
            "protocol/PROTO-POPU-RELIABILITY-v5-DEV005.amendment-002.json",
            "DEV/runs/RUN-001/metrics.json",
            "DEV/runs/RUN-002/metrics.json",
            "DEV/runs/RUN-003/metrics.json",
            "DEV/runs/RUN-004/metrics.json",
            "DEV/runs/RUN-005/metrics.json",
        ],
        "excluded": ["data/PoPu/*.zip", "VAL/", "any future STATE revision"],
    },
    {
        "id": "T2",
        "kind": "formal",
        "project": "19",
        "dimension": "algorithm design",
        "frozen_at": "after the H8 refutation, before the H9 readout probe",
        "question": "given a refuted mechanism and a 5-date, 17-object corpus, design the smallest legal algorithm fix and say what it cannot fix",
        "visible": [
            "STATE.md",
            "TRAINING_PROTOCOL_AUDIT.md",
            "CRPS_L2_EVAL.json",
            "CRPS_L2_ALGO_ROUND.json",
            "CRPS_L2_STATS_AUDIT.json",
            "dev_h8_v1/results/H8_VERDICT.json",
        ],
        "excluded": [
            "dev_h9_v1/ (the answer: the readout probe)",
            "dev_h10_v1/ (the verdict on the answer)",
            "PAPER_BLUEPRINT.md (framing, not evidence)",
            "REASSEMBLE/",
        ],
    },
    {
        "id": "T3",
        "kind": "formal",
        "project": "19",
        "dimension": "evidence validity and paper contribution",
        "frozen_at": "before the H8 contribution review",
        "question": "what does this corpus support today, and what is the shortest evidence path to a defensible claim",
        "visible": [
            "STATE.md",
            "FINAL_ALGO_ROUND_REPORT.md",
            "CRPS_L2_EVAL.json",
            "CRPS_L2_ALGO_ROUND.json",
            "CRPS_L2_STATS_AUDIT.json",
            "CRPS_L2_ANALYSIS.json",
            "CRPS_EVAL_AUDIT.json",
            "TRAINING_PROTOCOL_AUDIT.md",
            "PAPER_BLUEPRINT.md",
        ],
        "excluded": [
            "dev_h8_v1/ (the answer: the mechanism is refuted)",
            "dev_h9_v1/",
            "dev_h10_v1/",
            "REASSEMBLE/",
        ],
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(task: dict) -> dict:
    src = WORK / task["project"]
    if not src.is_dir():
        raise SystemExit(f"source project missing: {src}")
    target = ROOT / "tasks" / task["id"]
    inputs = target / "inputs"
    if inputs.exists():
        shutil.rmtree(inputs)
    inputs.mkdir(parents=True)

    files = []
    for rel in task["visible"]:
        s = src / rel
        if not s.is_file():
            raise SystemExit(f"{task['id']}: missing input {s}")
        d = inputs / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
        data = d.read_bytes()
        files.append({"path": rel, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})

    manifest = {
        "task": task["id"],
        "kind": task["kind"],
        "project": task["project"],
        "frozen_at": task["frozen_at"],
        "question": task["question"],
        "source_root": str(src),
        "visible": files,
        "excluded": task["excluded"],
        "total_bytes": sum(f["bytes"] for f in files),
        "bundle_sha256": hashlib.sha256(
            "\n".join(f"{f['path']}:{f['sha256']}" for f in files).encode()
        ).hexdigest(),
        "note": (
            "Inputs are copies, taken once. Re-verify with "
            "`python audit/agent_comparison/build_tasks.py --verify`; a change in the "
            "source project must not change what an arm saw."
        ),
    }
    if "dimension" in task:
        manifest["dimension"] = task["dimension"]
    (target / "MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return manifest


def verify() -> int:
    bad = 0
    for mf in sorted((ROOT / "tasks").glob("*/MANIFEST.json")):
        manifest = json.loads(mf.read_text(encoding="utf-8"))
        base = mf.parent / "inputs"
        for f in manifest["visible"]:
            p = base / f["path"]
            if not p.is_file():
                print(f"MISSING {manifest['task']} {f['path']}")
                bad += 1
                continue
            data = p.read_bytes()
            if len(data) != f["bytes"] or hashlib.sha256(data).hexdigest() != f["sha256"]:
                print(f"CHANGED {manifest['task']} {f['path']}")
                bad += 1
        print(f"{manifest['task']:6} {len(manifest['visible']):2} files "
              f"{manifest['total_bytes']:>8} bytes  bundle {manifest['bundle_sha256'][:12]}")
    return bad


if __name__ == "__main__":
    import sys

    if "--verify" in sys.argv:
        bad = verify()
        print("OK" if not bad else f"{bad} problem(s)")
        raise SystemExit(0 if not bad else 1)
    for t in TASKS:
        m = build(t)
        print(f"{m['task']:6} {len(m['visible']):2} files {m['total_bytes']:>8} bytes")
