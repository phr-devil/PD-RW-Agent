#!/usr/bin/env python3
"""Explicit read-only PD-RW rule router and checker adapter (Python 3.9+).

Routes are parsed from *current* PD-RW AGENTS.md, not duplicated here.
Checker results are structural/advisory: NEVER user authorization.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def emit(data, code=0):
    print(json.dumps(data, ensure_ascii=False, indent=2))
    return code


def rule_root(raw):
    root = Path(raw).expanduser().resolve()
    if not (root / "AGENTS.md").is_file() or not (root / "WORKFLOW.md").is_file():
        raise ValueError("PD-RW checkout missing AGENTS.md or WORKFLOW.md")
    return root


def route_rows(root):
    text = (root / "AGENTS.md").read_text(encoding="utf-8-sig")
    section = re.search(r"(?ms)^##\s+2\.[^\n]*\n(.*?)(?=^##\s+3\.|\Z)", text)
    if not section:
        raise ValueError("PD-RW AGENTS.md section 2 routing table not found")
    rows = []
    for line in section.group(1).splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not re.search(r"\]\([^)]+\.md(?:#[^)]*)?\)", cells[1]):
            continue
        topic = re.sub(r"[*\x60]", "", cells[0]).strip()
        refs = []
        for raw in re.findall(r"\]\(([^)]+)\)", cells[1]):
            rel = raw.split("#", 1)[0]
            if (rel.endswith(".md") and not rel.startswith(("http:", "https:")) and
                    not Path(rel).is_absolute()):
                candidate = (root / rel).resolve()
                if root in candidate.parents and candidate.is_file() and rel not in refs:
                    refs.append(rel)
        if topic and refs:
            rows.append({"topic": topic, "rule_paths": refs})
    if not rows:
        raise ValueError("PD-RW AGENTS.md contained no usable routing rows")
    return rows


def route(root, topic=None):
    rows = route_rows(root)
    if topic:
        key = topic.strip().casefold()
        exact = [r for r in rows if r["topic"].casefold() == key]
        matches = exact or [r for r in rows if key in r["topic"].casefold()]
    else:
        matches = rows
    return {
        "status": "ROUTE_FOUND" if topic and len(matches) == 1
                  else "ROUTE_SELECTION_REQUIRED",
        "query": topic,
        "matches": matches,
        "source": "PD-RW AGENTS.md §2 (live local checkout)",
        "meaning": "HINT_ONLY_READ_CURRENT_OWNER_WHEN_RELEVANT",
        "no_authorization_granted": True,
    }


def run_pd_rw(root, module, args):
    # No shell, no arbitrary module selection, no side-effect command.
    process = subprocess.run(
        [sys.executable, "-m", module, *args],
        cwd=str(root), capture_output=True, text=True, check=False, timeout=15,
    )
    try:
        output = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("PD-RW checker did not return JSON: " +
                         process.stderr.strip()[:200]) from exc
    if not isinstance(output, dict):
        raise ValueError("PD-RW checker returned a non-object response")
    return output, process.returncode


def action_review(root, packet):
    packet = Path(packet).expanduser().resolve()
    if not packet.is_file() or packet.stat().st_size > 1024 * 1024:
        raise ValueError("action packet must be an existing JSON file <= 1 MB")
    # Review a declaration only: no independent authorization is asserted.
    result, exit_code = run_pd_rw(
        root, "core.execution_preflight", ["action", str(packet)]
    )
    return {
        "status": "ADVISORY_ONLY",
        "pd_rw_action_result": result,
        "pd_rw_exit_code": exit_code,
        "original_user_permission_authenticated": False,
        "trusted_tool_interceptor_connected": False,
        "next": "Verify original user instruction and tool-level restrictions; no action executed.",
    }


def delivery_review(root, output_root, primary, files):
    result, exit_code = run_pd_rw(
        root, "core.delivery_check",
        ["--root", str(Path(output_root).expanduser().resolve()),
         "--primary", primary] + [v for f in files for v in ("--file", f)],
    )
    return {
        "status": "PATH_CHECK_ONLY",
        "pd_rw_delivery_result": result,
        "pd_rw_exit_code": exit_code,
        "scientific_truth_verified": False,
        "authorization_verified": False,
        "sealed_isolation_verified": False,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    sub = cli.add_subparsers(dest="command", required=True)
    r = sub.add_parser("route", help="Read live AGENTS.md routing table")
    r.add_argument("--workflow-root", required=True)
    r.add_argument("--topic", help="Full or unambiguous substring of route label")
    a = sub.add_parser("action-review", help="Run PD-RW advisory action preflight")
    a.add_argument("--workflow-root", required=True)
    a.add_argument("--packet", required=True)
    d = sub.add_parser("delivery-review", help="Run PD-RW path-only delivery checker")
    d.add_argument("--workflow-root", required=True)
    d.add_argument("--output-root", required=True)
    d.add_argument("--primary", required=True)
    d.add_argument("--file", action="append", default=[])
    options = cli.parse_args()
    try:
        root = rule_root(options.workflow_root)
        if options.command == "route":
            result = route(root, options.topic)
        elif options.command == "action-review":
            result = action_review(root, options.packet)
        else:
            result = delivery_review(
                root, options.output_root, options.primary, options.file
            )
        return emit(result)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        return emit({"status": "ERROR", "reason": str(error)}, 2)


if __name__ == "__main__":
    sys.exit(main())
