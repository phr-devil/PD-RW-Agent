#!/usr/bin/env python3
"""Local, read-only CASE_LIBRARY advisory ablation: cases ON vs cases OFF.

MEASUREMENT SCOPE (do not widen without a real WorkBuddy experiment):
This script measures ONLY which advisory fields become available when the
read-only case-library extension is enabled for an otherwise identical
`search_research_memory` service call. It is an ENGINEERING DIFFERENTIAL, not
an A/B/C replay and not a claim of research benefit.

The following remain NOT_MEASURED, consistent with
evals/AB_C_CAPTURE_TEMPLATE.md and evals/SCIENTIFIC_UTILITY_GATES.md:
  WorkBuddy task completion, decision correctness, blind reviewer grades,
  model/GPU tokens, wall time, human turns, and scientific utility.
Unit tests and this differential MUST NOT be reported as scientific gain.

Safety: no writes, no network fetch, no SEALED access, no GO/STOP, no changes
to PD-RW rules, STATE, Run, EVENTS or any frozen A/B/C snapshot. The script
hashes CASE_LIBRARY/index.json and every case card before and after both arms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pdrw_agent.config import Settings  # noqa: E402
from pdrw_agent.service import ResearchService  # noqa: E402

DEFAULTS = {
    "PDRW_AGENT_CONFIG": str(ROOT / "project-map.local.json"),
    "PDRW_WORKFLOW_ROOT": str(ROOT.parent / "Problem-Data-Research-Workflow"),
    "PDRW_CASE_LIBRARY_ROOT": str(Path("D:/workbuddy-work/CASE_LIBRARY")),
}

# Fixed decision scenarios. Filters use CONTROLLED taxonomy labels; profile
# fields are free-text declarations for the independent 8-dimension review.
SCENARIOS = [
    {
        "id": "S1_HAR_GROUP_LEAKAGE",
        "query": "HAR 分组 泄漏 窗口",
        "filters": {"mechanism": "GROUP_INDEPENDENCE"},
        "profile": {
            "decision": "滑窗 HAR 分类采用随机 k-fold，拟直接报告窗口级准确率",
            "mechanisms": "分组独立性不足与数据泄漏",
            "legal_inputs": "预测时刻可得的 IMU 窗口",
            "labels": "受试者活动标注",
            "grouping": "随机 k-fold 窗口级划分，同一受试者窗口跨集合",
            "evaluation_unit": "窗口级 accuracy，以窗口数作独立单位",
            "baseline": "未配对简单线性基线",
            "boundaries": "仅本数据集随机划分",
            "counterexamples": "若按受试者分组且窗口不重叠，泄漏前提不成立",
        },
    },
    {
        "id": "S2_ROBOT_DEMO_FAILURE",
        "query": "机器人示教 因果混淆 数据质量",
        "filters": {"mechanism": "CAUSAL_MISIDENTIFICATION,DEMONSTRATION_QUALITY"},
        "profile": {
            "decision": "用混合操作员示教数据做行为克隆，拟增加网络容量",
            "mechanisms": "因果误识与示教质量",
            "legal_inputs": "当前帧观测与历史动作",
            "labels": "示教动作作为监督信号",
            "grouping": "按演示片段随机划分",
            "evaluation_unit": "仿真成功率",
            "baseline": "简单线性策略未配对",
            "boundaries": "单一机器人本体与固定相机",
            "counterexamples": "若有干预式数据或动作后果可辨识，则因果混淆前提不成立",
        },
    },
    {
        "id": "S3_CROSS_SENSOR_SUCCESS",
        "query": "跨传感器迁移 标定 成功",
        "filters": {"mechanism": "SENSOR_CALIBRATION", "verdict": "SUCCESS"},
        "profile": {
            "decision": "电容触觉阵列重佩戴后复用标定迁移方案",
            "mechanisms": "传感器物理标定与跨域泛化",
            "legal_inputs": "已知物理激励下的 taxel 响应",
            "labels": "施加力/位置的物理真值",
            "grouping": "按独立器件实例分组",
            "evaluation_unit": "跨实例力估计误差",
            "baseline": "无标定直接迁移",
            "boundaries": "仅限可施加已知物理激励的电容式阵列",
            "counterexamples": "光学视触觉凝胶互换后无法迁移",
        },
    },
    {
        "id": "S4_SIMPLE_BASELINE",
        "query": "简单基线 复杂算法 增益归因",
        "filters": {"mechanism": "COMPLEX_VS_SIMPLE_BASELINE"},
        "profile": {
            "decision": "拟以复杂模型相对默认参数基线的小幅增益作为算法创新",
            "mechanisms": "复杂算法不及简单基线与实现归因",
            "legal_inputs": "同一份公开特征",
            "labels": "基准测试集标签",
            "grouping": "官方固定划分",
            "evaluation_unit": "排行榜指标",
            "baseline": "强简单基线未做等预算调参",
            "boundaries": "单一基准与固定超参预算",
            "counterexamples": "若等预算强基线已配对且做了消融，则增益归因可辨",
        },
    },
    {
        "id": "S5_LABEL_ERROR_AND_VERSION",
        "query": "错误标签 外部验证 模型版本",
        "filters": {"mechanism": "LABEL_ERROR,EXTERNAL_VALIDATION"},
        "profile": {
            "decision": "评估 Epic Sepsis Model v2 在本院 EHR 的部署表现",
            "mechanisms": "标签错误与独立第三方外部验证",
            "legal_inputs": "院内 EHR 预测时刻可得字段",
            "labels": "复合脓毒症标签",
            "grouping": "独立住院次",
            "evaluation_unit": "encounter AUROC",
            "baseline": "厂商报告 AUC",
            "boundaries": "v2 多中心前瞻验证",
            "counterexamples": "v1 结论不得泛化到 v2 或后续版本",
        },
    },
    {
        # Peer-reviewed success card (EXT-N03, ICRA 2024). S3's SENSOR_CALIBRATION
        # successes are preprints and are correctly held as candidates-only;
        # this scenario verifies SUCCESS_TRANSFER is reachable on real cards.
        "id": "S6_CROSS_EMBODIMENT_SUCCESS",
        "query": "跨机器人本体迁移 成功条件",
        "filters": {"mechanism": "CROSS_EMBODIMENT_TRANSFER", "verdict": "SUCCESS"},
        "profile": {
            "decision": "复用多本体混合数据训练的策略，拟直接推广到新机器人",
            "mechanisms": "跨机器人本体迁移与容量预训练",
            "legal_inputs": "本体无关的观测与动作接口",
            "labels": "示教轨迹监督",
            "grouping": "按本体域分组",
            "evaluation_unit": "小规模域任务成功率",
            "baseline": "单域 Original Method 与单域 RT-1",
            "boundaries": "仅限 small-scale domains 且对比单域基线",
            "counterexamples": "大数据域 RT-1-X underfits，跨本体数据必然更好不成立",
        },
    },
]

NOT_MEASURED = {
    "workbuddy_task_completion": "NOT_MEASURED",
    "scientific_decision_correctness": "NOT_MEASURED",
    "blind_reviewer_grades": "NOT_MEASURED",
    "input_output_token_delta": "NOT_MEASURED",
    "wall_time_delta": "NOT_MEASURED",
    "human_turns_or_interventions": "NOT_MEASURED",
    "scientific_utility": "NOT_MEASURED",
    "reason": ("No real WorkBuddy A/B/C replay was executed. A tool-output "
               "differential and unit tests cannot stand in for research benefit."),
}


def library_digest(root: Path) -> dict:
    """Read-only fingerprint of the single case source, before/after both arms."""
    files = [root / "index.json"] + sorted(
        p for p in (root / "cases").rglob("*.md") if p.is_file())
    h = hashlib.sha256()
    for p in files:
        h.update(p.name.encode("utf-8"))
        h.update(p.read_bytes())
    return {"files": len(files), "sha256": h.hexdigest()}


def summarize(out: dict) -> dict:
    """Extract only OBSERVABLE advisory fields; never score scientific value."""
    cl = out.get("case_library") or {}
    cases = cl.get("cases") or {}
    exp = cl.get("decision_experiences") or {}
    rev = cl.get("case_review") or {}
    results = cases.get("results") or []
    paths = sorted({p for r in results for p in r.get("evidence_paths", [])
                    if not str(p).startswith(("http://", "https://"))})
    return {
        "legacy_matches": len(out.get("matches") or []),
        "legacy_status": out.get("status"),
        "case_candidates_returned": cases.get("returned", 0),
        "negative_warnings": exp.get("negative_warning_count", 0),
        "success_transfers": exp.get("success_transfer_count", 0),
        "candidates_only_not_admitted": len(exp.get("candidates_only_not_admitted") or []),
        "review_classification_counts": rev.get("classification_counts") or {},
        "distinct_local_evidence_paths": len(paths),
        "automatic_go_stop_emitted": bool(cl.get("automatic_go_stop", False)),
        "keyword_similarity_flag": rev.get("keyword_similarity_is_not_premise_equivalence"),
        "case_library_status": cl.get("status"),
        "output_truncated": cl.get("output_truncated", False),
    }


def run_arm(service: ResearchService, scenario: dict, *, cases_on: bool) -> dict:
    kwargs = {
        "query": scenario["query"],
        "limit": 5,
        "task_profile": scenario["profile"],
        "max_experiences": 5,
        "include_cases": cases_on,
    }
    kwargs.update(scenario["filters"])
    return service.call("search_research_memory", **kwargs)


def build_report() -> dict:
    for key, value in DEFAULTS.items():
        os.environ.setdefault(key, value)
    settings = Settings.load()
    service = ResearchService(settings)
    library_root = Path(os.environ["PDRW_CASE_LIBRARY_ROOT"]).expanduser().resolve()

    before = library_digest(library_root)
    rows = []
    for sc in SCENARIOS:
        off = run_arm(service, sc, cases_on=False)
        on = run_arm(service, sc, cases_on=True)
        # Repeat the ON arm to observe the deterministic dedup fingerprint.
        on_repeat = run_arm(service, sc, cases_on=True)
        off_s, on_s = summarize(off), summarize(on)
        rows.append({
            "scenario_id": sc["id"],
            "query": sc["query"],
            "off": off_s,
            "on": on_s,
            "legacy_matches_unchanged": off_s["legacy_matches"] == on_s["legacy_matches"]
                                        and off_s["legacy_status"] == on_s["legacy_status"],
            "repeat_cache_hit": bool((on_repeat.get("case_library") or {}).get("cache_hit")),
            "same_query_fingerprint": (
                (on.get("case_library") or {}).get("query_fingerprint")
                == (on_repeat.get("case_library") or {}).get("query_fingerprint")),
        })
    after = library_digest(library_root)

    guardrails = {
        "no_writes_to_case_library": before == after,
        "legacy_index_unaffected_in_all_scenarios": all(r["legacy_matches_unchanged"] for r in rows),
        "no_automatic_go_stop": all(not r["on"]["automatic_go_stop_emitted"] for r in rows),
        "dedup_fingerprint_stable": all(r["same_query_fingerprint"] and r["repeat_cache_hit"]
                                        for r in rows),
        "case_arm_available": all(r["on"]["case_library_status"] == "MATCHES_FOUND" for r in rows),
        "coherent_retained_case_set": all(
            r["on"]["case_candidates_returned"]
            >= r["on"]["negative_warnings"] + r["on"]["success_transfers"] for r in rows),
        "both_polarities_observed": (
            any(r["on"]["negative_warnings"] > 0 for r in rows)
            and any(r["on"]["success_transfers"] > 0 for r in rows)),
    }
    payload = {
        "report_type": "ENGINEERING_ADVISORY_FIELD_DIFFERENTIAL",
        "not_a_scientific_utility_measurement": True,
        "arms": {"OFF": "search_research_memory(include_cases=False)",
                 "ON": "search_research_memory(include_cases=True) + independent 8-dimension review"},
        "library": {"root": str(library_root), "digest_before": before, "digest_after": after},
        "scenarios": rows,
        "guardrails": guardrails,
        "not_measured": NOT_MEASURED,
        "interpretation": ("ON surfaces bounded, source-verified negative/success "
                           "candidates and applicability classifications. Whether that "
                           "improves a real research decision is NOT measured here."),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":"))
    payload["report_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", default="", help="optional path for the JSON report")
    args = ap.parse_args()
    report = build_report()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        out = Path(args.output).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
        print("ABLATION_REPORT_WRITTEN", out)
        print("report_sha256", report["report_sha256"])
        print("guardrails", json.dumps(report["guardrails"], ensure_ascii=False, sort_keys=True))
    else:
        print(text)
    return 0 if all(report["guardrails"].values()) else 1


if __name__ == "__main__":
    sys.exit(main())
