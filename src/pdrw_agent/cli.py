"""Python command line entry using exactly the MCP service layer."""
from __future__ import annotations
import argparse
import json
import sys
from .config import Settings
from .schemas import failure
from .service import ResearchService

def main() -> int:
    cli = argparse.ArgumentParser(description="PD-RW research adapter (read-only)")
    cli.add_argument("--project-map", help="Path to private project-map.local.json")
    cli.add_argument("--workflow-root", help="Local checkout of authoritative PD-RW")
    sub = cli.add_subparsers(dest="command", required=True)
    p = sub.add_parser("context")
    p.add_argument("--project-id", required=True)
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
    d.add_argument("--spec-file", required=True, help="Local JSON fingerprint input; CLI only")
    args = cli.parse_args()
    try:
        service = ResearchService(Settings.load(args.project_map, args.workflow_root))
        if args.command == "context":
            out = service.call("get_project_context", project_id=args.project_id)
        elif args.command == "rules":
            out = service.call("get_applicable_rules", topic=args.topic)
        elif args.command == "memory":
            out = service.call("search_research_memory", query=args.query, limit=args.limit)
        elif args.command == "evidence":
            out = service.call("find_experiment_evidence", project_id=args.project_id,
                               task_id=args.task_id, run_id=args.run_id, limit=args.limit)
        else:
            from .config import read_json
            out = service.call("check_duplicate_experiment", project_id=args.project_id,
                               spec=read_json(__import__("pathlib").Path(args.spec_file)))
    except (OSError, ValueError) as exc:
        out = failure(exc)
    try:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except UnicodeEncodeError:
        print(json.dumps(out, ensure_ascii=True, indent=2))
    return 2 if out["status"] == "ERROR" else 0

if __name__ == "__main__":
    sys.exit(main())
