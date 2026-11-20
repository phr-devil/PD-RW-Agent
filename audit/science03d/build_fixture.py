"""Build the SCIENCE-03D replay fixture: a project whose Runs do state their plan.

The defect under test is premise attribution. For it to be decidable at all, the
Run has to record *which frozen plan it executed* -- otherwise nothing on disk
can contradict a caller's story. Real projects in the fleet record
``protocol_id`` + ``protocol_sha256`` in ``metrics.json``; this fixture mirrors
that shape and adds the ``premise_id`` that a frozen plan is supposed to carry.

Two plans, two premises, one Run each:

* ``PROTO-PRESS-BEAM-26``  -> premise ``BEAM_STIFFNESS_MECHANISM``
* ``PROTO-PRESS-SENSOR-26``-> premise ``SENSOR_DRIFT_MECHANISM``

``RUN-101`` executed the beam plan, ``RUN-102`` carries a record whose ``run_id``
disagrees with its directory, ``RUN-103`` is a directory holding only aggregate
metrics (no run identity, no status). Names and numbers are synthetic; the file
structure, hashes and status vocabulary are the ones the runtime actually reads.

Run with ``python audit/science03d/build_fixture.py``.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE / "fixture-project"

BEAM = {
    "protocol_id": "PROTO-PRESS-BEAM-26",
    "premise_id": "BEAM_STIFFNESS_MECHANISM",
    "scientific_line": "contact force reconstruction under press deformation",
    "frozen_before_fitting": True,
    "scope": {"dataset": "PRESS DEV 26", "input": "beam strain channels", "unit": "SUBJECT"},
    "goal": "Does beam stiffness carry information the load cell does not?",
    "primary_outcome": "subject-level MAE of reconstructed contact force",
    "decision_rule_frozen_before_results": "NEG if paired delta CI includes 0 at 95%",
    "authorization_basis": "DEV_ONLY",
}
SENSOR = {
    "protocol_id": "PROTO-PRESS-SENSOR-26",
    "premise_id": "SENSOR_DRIFT_MECHANISM",
    "scientific_line": "sensor drift as the dominant residual after calibration",
    "frozen_before_fitting": True,
    "scope": {"dataset": "PRESS DEV 26", "input": "raw sensor channels", "unit": "SUBJECT"},
    "goal": "Is the residual explained by sensor drift rather than by beam compliance?",
    "primary_outcome": "subject-level MAE of reconstructed contact force",
    "decision_rule_frozen_before_results": "POS if drift-corrected arm lowers paired MAE CI",
    "authorization_basis": "DEV_ONLY",
}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    beam_path = ROOT / "protocol" / "PROTO-PRESS-BEAM-26.json"
    sensor_path = ROOT / "protocol" / "PROTO-PRESS-SENSOR-26.json"
    write_json(beam_path, BEAM)
    write_json(sensor_path, SENSOR)

    write_json(ROOT / "DEV" / "runs" / "RUN-101" / "metrics.json", {
        "run_id": "RUN-101",
        "protocol_id": BEAM["protocol_id"],
        "protocol_sha256": sha256(beam_path),
        "status": "COMPLETED",
        "verdict": "NEG_BEAM_STIFFNESS",
        "anchor_pass": True,
        "scope": "DEV_ONLY / EXPLORATORY",
        "aggregate": {"base_mae": 9.171, "beam_arm_mae": 9.204, "delta_ci95": [-0.09, 0.16]},
        "cost": {"cpu_seconds": 41.2},
    })
    write_json(ROOT / "DEV" / "runs" / "RUN-101" / "verification.json", {
        "run_id": "RUN-101",
        "checks": {"anchor": "PASS", "folds": 12, "subjects": 12},
    })

    # A directory named RUN-102 whose record claims to be RUN-101.
    write_json(ROOT / "DEV" / "runs" / "RUN-102" / "metrics.json", {
        "run_id": "RUN-101",
        "protocol_id": BEAM["protocol_id"],
        "protocol_sha256": sha256(beam_path),
        "status": "COMPLETED",
        "verdict": "NEG_BEAM_STIFFNESS",
        "anchor_pass": True,
    })

    # Only aggregate numbers: no run identity, no status, nothing to compare.
    write_json(ROOT / "DEV" / "runs" / "RUN-103" / "metrics.json", {
        "aggregate": {"base_mae": 9.17, "sensor_arm_mae": 8.98},
        "note": "copied from a scratch run; identity and status were never recorded",
    })

    (ROOT / "STATE.md").write_text(
        "# PRESS-26 (SCIENCE-03D replay fixture)\n\n"
        "Two frozen plans on one dataset, two different premises, three Run\n"
        "directories. RUN-101 executed the beam plan and reported a negative for\n"
        "beam stiffness. RUN-102 is a copy whose record still says RUN-101.\n"
        "RUN-103 holds aggregate metrics only.\n\n"
        "The open question of the *sensor* line is not answered by any of them.\n",
        encoding="utf-8")
    print(f"fixture written to {ROOT}")


if __name__ == "__main__":
    main()
