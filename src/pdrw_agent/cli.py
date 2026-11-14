"""The command line uses exactly the same ResearchService as MCP."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .config import Settings, read_json
from .schemas import failure
from .service import ResearchService


def main() -> int:
    cli = argparse.ArgumentParser(description="PD-RW Research Agent runtime")
    cli.add_argument("--project-map", help="Private local project-map.json")
    cli.add_argument("--workflow-root", help="Local PD-RW checkout")
    sub = cli.add_subparsers(dest="command", required=True)
    p = sub.add_parser("context")
    p.add_argument("--project-id", required=True)
    xp = sub.add_parser("execution-preflight")
    xp.add_argument("--plan-file", required=True)
    xs = sub.add_parser("synthetic-status")
    xs.add_argument("--project-id", required=True)
    xs.add_argument("--operation-id", required=True)
    a = sub.add_parser("audit")
    a.add_argument("--project-id", required=True)
    history = sub.add_parser("history")
    history.add_argument("--project-id", required=True)
    vr = sub.add_parser("verify-run")
    vr.add_argument("--project-id", required=True)
    vr.add_argument("--run-id", required=True)
    science = sub.add_parser("science-audit")
    science.add_argument("--project-id", required=True)
    science.add_argument("--run-id", required=True)
    science.add_argument("--baseline-run-id", default="")
    sourced_lesson = sub.add_parser("lesson-evidence")
    sourced_lesson.add_argument("--project-id", required=True)
    sourced_lesson.add_argument("--run-id", required=True)
    sourced_lesson.add_argument("--proposal-file", required=True)
    scope = sub.add_parser("lesson-scope")
    scope.add_argument("--packet", required=True,
                       help="JSON with proposal and lessons")
    r = sub.add_parser("rules")
    r.add_argument("--topic", default="")
    m = sub.add_parser("memory")
    m.add_argument("--query", required=True)
    m.add_argument("--limit", type=int, default=5)
    e = sub.add_parser("evidence")
    e.add_argument("--project-id", required=True)
    e.add_argument("--task-id", default="")
    e.add_argument("--run-id", default="")
    e.add_argument("--limit", type=int, default=6)
    d = sub.add_parser("duplicate")
    d.add_argument("--project-id", required=True)
    d.add_argument("--spec-file", required=True)
    rs = sub.add_parser("resume")
    rs.add_argument("--project-id", required=True)
    st = sub.add_parser("operations")
    st.add_argument("--project-id", required=True)
    st.add_argument("--operation-id", default="")
    st.add_argument("--limit", type=int, default=6)
    begin = sub.add_parser("begin-operation")
    begin.add_argument("--project-id", required=True)
    begin.add_argument("--operation-id", required=True)
    begin.add_argument("--task-id", required=True)
    begin.add_argument("--action", required=True)
    checkpoint = sub.add_parser("checkpoint")
    checkpoint.add_argument("--project-id", required=True)
    checkpoint.add_argument("--operation-id", required=True)
    checkpoint.add_argument("--expected-revision", required=True, type=int)
    checkpoint.add_argument("--phase", required=True)
    checkpoint.add_argument("--artifact-ref", default="")
    preview = sub.add_parser("preview-record")
    preview.add_argument("--project-id", required=True)
    preview.add_argument("--artifact-ref", required=True)
    handoff = sub.add_parser("handoff")
    handoff.add_argument("--project-id", required=True)
    handoff.add_argument("--primary-ref", required=True)
    handoff.add_argument("--support-ref", action="append", default=[])
    options = cli.parse_args()

    try:
        service = ResearchService(Settings.load(options.project_map,
                                                 options.workflow_root))
        command = options.command
        if command == "context":
            out = service.call("get_project_context", project_id=options.project_id)
        elif command == "execution-preflight":
            out = service.call("preflight_execution_plan",
                               plan=read_json(Path(options.plan_file)))
        elif command == "synthetic-status":
            out = service.call("get_synthetic_job_status",
                               project_id=options.project_id,
                               operation_id=options.operation_id)
        elif command == "audit":
            out = service.call("audit_project_state", project_id=options.project_id)
        elif command == "history":
            out = service.call("reconstruct_project_history", project_id=options.project_id)
        elif command == "verify-run":
            out = service.call("verify_run_evidence", project_id=options.project_id,
                               run_id=options.run_id)
        elif command == "science-audit":
            out = service.call("audit_scientific_experiment",
                               project_id=options.project_id, run_id=options.run_id,
                               baseline_run_id=options.baseline_run_id)
        elif command == "lesson-evidence":
            out = service.call("review_evidenced_lesson",
                               project_id=options.project_id, run_id=options.run_id,
                               proposal=read_json(Path(options.proposal_file)))
        elif command == "lesson-scope":
            packet = read_json(Path(options.packet))
            out = service.call("review_lesson_applicability",
                               proposal=packet.get("proposal"),
                               lessons=packet.get("lessons"))
        elif command == "rules":
            out = service.call("get_applicable_rules", topic=options.topic)
        elif command == "memory":
            out = service.call("search_research_memory", query=options.query, limit=options.limit)
        elif command == "evidence":
            out = service.call("find_experiment_evidence", project_id=options.project_id,
                               task_id=options.task_id, run_id=options.run_id, limit=options.limit)
        elif command == "duplicate":
            out = service.call("check_duplicate_experiment", project_id=options.project_id,
                               spec=read_json(Path(options.spec_file)))
        elif command == "resume":
            out = service.call("get_resume_context", project_id=options.project_id)
        elif command == "operations":
            out = service.call("get_execution_status", project_id=options.project_id,
                               operation_id=options.operation_id, limit=options.limit)
        elif command == "begin-operation":
            out = service.call("begin_operation_receipt", project_id=options.project_id,
                               operation_id=options.operation_id, task_id=options.task_id,
                               action=options.action)
        elif command == "checkpoint":
            out = service.call("checkpoint_operation_receipt", project_id=options.project_id,
                               operation_id=options.operation_id,
                               expected_revision=options.expected_revision,
                               phase=options.phase, artifact_ref=options.artifact_ref)
        elif command == "preview-record":
            out = service.call("preview_experiment_record", project_id=options.project_id,
                               artifact_ref=options.artifact_ref)
        else:
            out = service.call("prepare_handoff", project_id=options.project_id,
                               primary_ref=options.primary_ref,
                               supporting_refs=options.support_ref)
    except (OSError, ValueError) as exc:
        out = failure(exc)
    try:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        print(json.dumps(out, ensure_ascii=True, indent=2))
    return 2 if out["status"] == "ERROR" else 0


if __name__ == "__main__":
    sys.exit(main())
