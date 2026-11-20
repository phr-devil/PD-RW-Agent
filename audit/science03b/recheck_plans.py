"""Read-only re-check: were last round's two "next probes" already answered?

SCIENCE-03 (v0.9.9) proposed, for each project, a revised next experiment:
  MCS-HEMO-26  -> zero-fit subject-level cross-session ICC + motion control
  RCT-CONTACT-26 -> sensor-swap slope contrast on the 489 same-material pairs
Both are checked here against the projects' own recorded evidence. Nothing is
written under either project root; only their JSON/MD are read.
"""
import json
import re
from pathlib import Path

WORK = Path("D:/workbuddy-work")
OUT = Path("D:/workbuddy-agent/PD-RW-Agent/audit/science03b/plan_recheck.json")


def facts(state_path: Path, keys):
    text = state_path.read_text(encoding="utf-8")
    hits = {}
    for line in text.splitlines():
        for key in keys:
            if key in line and key not in hits:
                hits[key] = line.strip()[:400]
    return hits


def mcs():
    root = WORK / "MCS-HEMO-26/research"
    n1r = json.loads((root / "dev_audit/n1r_verification.json").read_text(encoding="utf-8"))
    cov = n1r.get("G1_coverage", {})
    return {
        "project": "MCS-HEMO-26",
        "proposed_by_science03": "zero-fit subject-level cross-session ICC + motion control, because the reference layer is same-source",
        "already_answered": True,
        "executed_as": ["O8 (02b) Ear_sync cross-session ICC", "O12 (02c) device-mask sensitivity ICC",
                        "O22 (02e) N1-R cross-session repeatability"],
        "measured": {
            "n1r_g1_coverage": cov,
            "n1r_bout_rows": n1r.get("bout_rows"),
            "n1r_valid_bout_core": n1r.get("validity_counts", {}).get("valid_bout_core"),
        },
        "state_facts": facts(root / "STATE.md", ["O8 FACT", "O12 FACT", "O22 FACT"]),
        "why_no_new_information": (
            "The cross-session ICC was already computed three times; O22 reports the main analysis "
            "has n=3 (LOW) / n=4 (HIGH) usable bouts, so rho/ICC are NOT ESTIMABLE, and the no-mask "
            "sensitivity analysis gives CIs that cross 0. Re-running the same statistic on the same "
            "DEV pool cannot produce a new estimate; only new instrumented data can."),
        "residual_value": {
            "documentation_check": "U9/U10 (was a cuff reading recorded; what generates HR) - non-decisive, no new data",
            "decisive_path": "channel-level group delay / independent calibration / new dataset - requires new authorization",
        },
    }


def rct():
    root = WORK / "RCT-CONTACT-26/research"
    table = json.loads((root / "dev_audit/contrast_table.json").read_text(encoding="utf-8"))
    r1b = table.get("Q_R1B_sensor_instance_vs_contact_physics", {})
    r1c = table.get("Q_R1C_identifiability_boundary", {})
    return {
        "project": "RCT-CONTACT-26",
        "proposed_by_science03": "split: sensor-swap contrast now, external-modulus press only for the material claim",
        "already_answered": True,
        "executed_as": ["Q_R1B sensor_1 vs sensor_2 on the same material AND position"],
        "measured": {
            "Q_R1B_contrast": r1b.get("CONTRAST"),
            "Q_R1B_group_n": r1b.get("GROUP_N"),
            "Q_R1B_verdict": r1b.get("VERDICT"),
            "Q_R1B_confounds": r1b.get("UNRESOLVED_CONFOUND"),
            "Q_R1C_verdict": r1c.get("VERDICT"),
        },
        "state_facts": facts(root / "STATE.md", ["NO_USEFUL_NEXT_PROBE", "R1_BRANCH_CLOSURE", "MODEL_TRAINING_NOT_AUTHORIZED"]),
        "why_no_new_information": (
            "The 489 same-material, same-position pairs were already contrasted and classified "
            "PARTIAL_OR_CONFOUNDED: the sensor instance is perfectly confounded with its own gel, "
            "illumination and background, and some force logs are byte-identical across sensors. "
            "Removing a per-sensor offset does not break that confound, so the contrast cannot "
            "separate material mechanics from sensor physics on this DEV pool."),
        "residual_value": {
            "external_modulus": "the only decisive comparison for the material claim; needs new truth and new authorization",
            "dev_only": "NO_USEFUL_NEXT_PROBE remains TRUE for another DEV-only probe of the same class",
        },
    }


def main():
    out = {"recheck_date": "2026-11-20", "read_only": True,
           "plans": [mcs(), rct()]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for p in out["plans"]:
        print(f"{p['project']}: already_answered={p['already_answered']} executed_as={p['executed_as']}")
        print(f"  measured={json.dumps(p['measured'], ensure_ascii=False)[:300]}")


if __name__ == "__main__":
    main()
