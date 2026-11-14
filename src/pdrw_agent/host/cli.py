"""Operator-launched host diagnostic CLI. No WorkBuddy MCP execution API."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import Settings, read_json
from ..schemas import failure
from .authorization import preview_dev_admission
from .supervisor import HostSupervisor, get_host_diagnostic_status


def main():
    p = argparse.ArgumentParser(description="PD-RW host diagnostics; DEV execution disabled")
    p.add_argument("--project-map")
    p.add_argument("--workflow-root")
    s = p.add_subparsers(dest="command", required=True)
    run = s.add_parser("run-fixed-diagnostic")
    run.add_argument("--plan-file", required=True)
    query = s.add_parser("status")
    query.add_argument("--project-id", required=True)
    query.add_argument("--operation-id", required=True)
    preview = s.add_parser("dev-preview")
    preview.add_argument("--plan-file", required=True)
    args = p.parse_args()
    try:
        settings = Settings.load(args.project_map, args.workflow_root)
        if args.command == "run-fixed-diagnostic":
            result = HostSupervisor(settings).run_fixed_diagnostic(
                read_json(Path(args.plan_file)))
        elif args.command == "status":
            result = get_host_diagnostic_status(
                settings, args.project_id, args.operation_id)
        else:
            result = preview_dev_admission(settings, read_json(Path(args.plan_file)))
    except (ValueError, OSError, TypeError) as exc:
        result = failure(exc)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 2 if result["status"] == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
