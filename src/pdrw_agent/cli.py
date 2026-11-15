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
    r = sub.add_parser("rules")
    r.add_argument("--topic", default="")
    m = sub.add_parser("memory")
    m.add_argument("--query", required=True)
    m.add_argument("--limit", type=int, default=5)
    m.add_argument("--mechanism", default="")
    m.add_argument("--domain", default="")
    m.add_argument("--applicability", default="")
    m.add_argument("--verdict", default="")
    m.add_argument("--evidence-level", default="")
    m.add_argument("--origin", default="")
    m.add_argument("--keyword", default="")
    m.add_argument("--max-experiences", type=int, default=5)
    m.add_argument("--legacy-only", action="store_true")
    m.add_argument("--task-profile-file", help="JSON file with the 8-dimension task profile")
    cr = sub.add_parser("case-review")
    cr.add_argument("--task-profile-file", required=True)
    cr.add_argument("--query", default="case transfer review")
    cr.add_argument("--limit", type=int, default=5)
    cr.add_argument("--mechanism", default="")
    cr.add_argument("--domain", default="")
    cr.add_argument("--verdict", default="")
    cr.add_argument("--evidence-level", default="")
    cc = sub.add_parser("case-candidates")
    cc.add_argument("--project-id", required=True)
    cc.add_argument("--observations-file", required=True)
    cc.add_argument("--evidence-root", default="")
    cc.add_argument("--evidence-manifest", default="")
    cg = sub.add_parser("case-gate")
    cg.add_argument("--event-file", required=True)
    cg.add_argument("--detail", choices=("compact", "full"), default="compact")
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
        elif command == "rules":
            out = service.call("get_applicable_rules", topic=options.topic)
        elif command == "memory":
            profile = (read_json(Path(options.task_profile_file))
                       if options.task_profile_file else None)
            out = service.call(
                "search_research_memory", query=options.query, limit=options.limit,
                mechanism=options.mechanism, domain=options.domain,
                applicability=options.applicability, verdict=options.verdict,
                evidence_level=options.evidence_level, origin=options.origin,
                keyword=options.keyword, max_experiences=options.max_experiences,
                include_cases=not options.legacy_only, task_profile=profile)
        elif command == "case-review":
            filters = {k: v for k, v in {
                "mechanism": options.mechanism, "domain": options.domain,
                "verdict": options.verdict,
                "evidence_level": options.evidence_level}.items() if v}
            out = service.call("review_case_transfer",
                               task_profile=read_json(Path(options.task_profile_file)),
                               filters=filters, query=options.query, limit=options.limit)
        elif command == "case-candidates":
            manifest = (read_json(Path(options.evidence_manifest))
                        if options.evidence_manifest else None)
            out = service.call("extract_case_candidates", project_id=options.project_id,
                               observations=read_json(Path(options.observations_file))["observations"],
                               evidence_root=options.evidence_root or None,
                               evidence_manifest=manifest)
        elif command == "case-gate":
            packet = read_json(Path(options.event_file))
            event = packet.get("event", packet) if isinstance(packet, dict) else packet
            out = service.call("case_gate_check", event=event, detail=options.detail)
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
