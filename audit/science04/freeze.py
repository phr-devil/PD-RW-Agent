"""Freeze three real decision points into read-only evidence snapshots.

A decision point is only testable if the evidence is fixed: same files, same
bytes, no later conclusion visible. This copies an explicit allowlist out of the
live projects, never the whole tree, never `SEALED/` or `VAL/`, and records the
sha256 of every file plus everything it deliberately left behind.

    python audit/science04/freeze.py            # writes audit/science04/frozen/
    python audit/science04/freeze.py --verify   # re-hashes against MANIFEST.json

Each snapshot is one decision point, taken at the project's own final state so
that no later revision can leak into it:

    48  PoPu reliability  -- valid negative, and an evaluation that failed twice
                            (anchor mismatch, then seed-driven early stopping)
    44  tactile dataset   -- cross-domain confusion audit; negative claim, and a
                            protocol/errata contribution
    17  ACRF / RCT        -- sealed negative, project pivoted at Phase 5
"""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

WORK = Path("D:/workbuddy-work")
OUT = Path(__file__).resolve().parent / "frozen"
MAX_BYTES = 2 * 1024 * 1024

POINTS = {
    "DP1-POPU-HOLD": {
        "project": "48",
        "question": "在 PoPu DEV 数据上，可靠性机制相对基座是否带来可部署的增量？",
        "truth": {"decision": "HOLD_RELIABILITY / H8_PENDING",
                  "verdict": "NEG_NOT_PREDICTABLE_BEYOND_MAGNITUDE"},
        "files": [
            "STATE.md", "RESEARCH_RECORD.md", "PAPER_BLUEPRINT.md",
            "protocol/PROTO-POPU-DEPLOY-v3-DEV003.json",
            "protocol/PROTO-POPU-INF-INC-v1.json",
            "protocol/PROTO-POPU-INF-INC-v2-DEV002.json",
            "protocol/PROTO-POPU-POSTUREVALUE-v4-DEV004.json",
            "protocol/PROTO-POPU-RELIABILITY-v5-DEV005.json",
            "protocol/PROTO-POPU-RELIABILITY-v5-DEV005.amendment-001.json",
            "protocol/PROTO-POPU-RELIABILITY-v5-DEV005.amendment-002.json",
            "DEV/runs/RUN-001/metrics.json", "DEV/runs/RUN-002/metrics.json",
            "DEV/runs/RUN-003/metrics.json", "DEV/runs/RUN-004/metrics.json",
            "DEV/runs/RUN-005/metrics.json", "DEV/runs/RUN-005/verification.json",
            "DEV/runs/RUN-005/RUN-005_RESULT.md",
        ],
        "withheld": ["原始数据与训练产物（DEV/data、*.npz、*.csv）",
                     "SEALED/ 与任何 holdout 路径",
                     "RUN-003 的 248 KB 中间产物（仅保留 metrics.json）"],
    },
    "DP2-TACTILE-NEG": {
        "project": "44",
        "question": "公开触觉数据集的评估协议是否把类别/窗口的直流水平与真实线索混在一起？",
        "truth": {"decision": "H8：单库 16 试件/4 形状组，预注册负结果",
                  "verdict": "Q2_EDGE_CONDITIONAL"},
        "files": [
            "STATE.md", "RESEARCH_RECORD.md", "PAPER_BLUEPRINT.md",
            "D1_ACCEPTANCE_REPORT_2026-11-14.md", "H8_DECISION_BRIEF_2026-11-16.md",
            "RUN-001_PRINCIPAL_RESULT.md",
            "protocol/PROTO-GEOM-HS-v1.json", "protocol/PROTO-GEOM-HS-v2.json",
            "DEV/runs/RUN-001/metrics.json", "DEV/runs/RUN-002/metrics.json",
        ],
        "withheld": ["SEALED/ 与 VAL/（本决策点不可见）",
                     "D1_raw/ 原始数据与 68 MB 配对产物",
                     "RUN-002/paired 抽样明细"],
    },
    "DP3-ACRF-PIVOT": {
        "project": "17",
        "question": "一次性少样本校准能否预测 ACRF 的 ΔF，从而支撑后续研发？",
        "truth": {"decision": "PIVOT：终止 ACRF 的 ΔF 预测研发线",
                  "verdict": "sealed negative"},
        "files": [
            "STATE.md", "HOLDOUT_STATUS.md", "SPLIT_PROTOCOL.md",
            "BASELINE_PLAN.md", "DATA_AUDIT.md",
            "RUNS.tsv", "RUNS_PHASE4.tsv", "RUNS_PHASE5.tsv",
        ],
        "withheld": ["_rct_repo/ 与 artifacts/（原始与中间数据）",
                     "9.9 GB RCT 数据归档"],
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def freeze_one(name: str, spec: dict) -> dict:
    source = WORK / spec["project"]
    target = OUT / name
    if not source.is_dir():
        raise SystemExit(f"missing project: {source}")
    if target.exists():
        shutil.rmtree(target)
    manifest = {"decision_point": name, "project": spec["project"],
                "question": spec["question"], "truth": spec["truth"],
                "source_root": str(source), "files": [], "skipped": [],
                "withheld": spec["withheld"], "total_bytes": 0}
    for relative in spec["files"]:
        path = source / relative
        if not path.is_file():
            manifest["skipped"].append({"path": relative, "reason": "absent"})
            continue
        size = path.stat().st_size
        if size > MAX_BYTES:
            manifest["skipped"].append({"path": relative, "reason": f"{size} bytes > cap"})
            continue
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        manifest["files"].append({"path": relative, "bytes": size, "sha256": sha256(path)})
        manifest["total_bytes"] += size
    (target / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def verify() -> int:
    bad = 0
    for manifest_path in sorted(OUT.glob("*/MANIFEST.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for entry in manifest["files"]:
            path = manifest_path.parent / entry["path"]
            if not path.is_file() or sha256(path) != entry["sha256"]:
                print(f"CHANGED {path}")
                bad += 1
        print(f"{manifest['decision_point']}: {len(manifest['files'])} files, "
              f"{manifest['total_bytes']} bytes, "
              f"{len(manifest['skipped'])} skipped")
    return 1 if bad else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        return verify()
    OUT.mkdir(parents=True, exist_ok=True)
    for name, spec in POINTS.items():
        manifest = freeze_one(name, spec)
        print(f"{name}: {len(manifest['files'])} files, "
              f"{manifest['total_bytes']} bytes, "
              f"{len(manifest['skipped'])} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
