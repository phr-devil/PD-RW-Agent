"""Optional local scientific decision and frozen-history replay assistant.

Not an MCP tool and not a scientific authorization channel.
Usage: python -m pdrw_agent.science.cli decision --packet proposal.json
       python -m pdrw_agent.science.cli replay-check --root DIR --manifest case.json
       python -m pdrw_agent.science.cli replay-blind --root DIR --manifest case.json
           --a a.json --b b.json --c c.json --seed 7 --private-key DIR/key.json
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path
from ..config import read_json
from ..schemas import AgentError, failure
from .decision import assess_proposal
from .replay import validate_case, blind_responses


def _write_secret(path: Path, value: dict, root: Path) -> None:
    target = path.expanduser().resolve()
    if target == root.resolve() or root.resolve() in target.parents:
        raise AgentError("REPLAY_KEY_LOCATION_INVALID",
                         "Keep blind unblinding key outside the fixture directory")
    if not target.parent.is_dir():
        raise AgentError("REPLAY_KEY_LOCATION_INVALID", "Private key directory must already exist")
    fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(value, out, indent=2, ensure_ascii=False)
            out.write("\n")
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def main() -> int:
    cli = argparse.ArgumentParser(description="Optional read-only research decision checks")
    sub = cli.add_subparsers(dest="action", required=True)
    d = sub.add_parser("decision")
    d.add_argument("--packet", type=Path, required=True)
    for cmd in ("replay-check", "replay-blind"):
        p = sub.add_parser(cmd)
        p.add_argument("--root", type=Path, required=True)
        p.add_argument("--manifest", type=Path, required=True)
        if cmd == "replay-blind":
            for arm in ("a", "b", "c"):
                p.add_argument(f"--{arm}", type=Path, required=True)
            p.add_argument("--seed", type=int, required=True)
            p.add_argument("--private-key", type=Path, required=True)
    args = cli.parse_args()
    try:
        if args.action == "decision":
            result = assess_proposal(read_json(args.packet, limit=128 * 1024))
        else:
            manifest = read_json(args.manifest, limit=128 * 1024)
            if args.action == "replay-check":
                result = validate_case(args.root, manifest)
            else:
                responses = {arm.upper(): read_json(getattr(args, arm), limit=64 * 1024)
                             for arm in ("a", "b", "c")}
                result = blind_responses(args.root, manifest, responses, args.seed)
                _write_secret(args.private_key, {
                    "case_id": manifest["case_id"],
                    "mapping": result["private_unblinding_key"],
                }, args.root)
                result = result["review_packet"]  # Secret is never printed.
    except (ValueError, OSError, TypeError) as exc:
        result = failure(exc)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if result.get("status") == "ERROR" else 0


if __name__ == "__main__":
    sys.exit(main())
