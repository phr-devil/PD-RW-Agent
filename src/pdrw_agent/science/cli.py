"""Optional local-only research proposal, negative lesson and A/B/C replay checks.

No MCP tool; no research ledger or authorization writes. Blind mapping is the
sole output file and is protected from checkout-path writes.
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
from .lessons import compile_declared_lessons
from .provenance import bind_frozen_evidence, bind_source_refs
from .replay import validate_case, blind_responses


def _write_secret(path: Path, value: dict, root: Path) -> None:
    target = path.expanduser().resolve()
    if target == root.resolve() or root.resolve() in target.parents:
        raise AgentError("REPLAY_KEY_LOCATION_INVALID",
                         "Keep blind unblinding key outside the fixture directory")
    if not target.parent.is_dir():
        raise AgentError("REPLAY_KEY_LOCATION_INVALID", "Private key directory must already exist")
    if any((parent / ".git").exists() for parent in (target.parent, *target.parents)):
        raise AgentError("REPLAY_KEY_LOCATION_INVALID", "Private blind key cannot be written under a Git checkout")
    fd = os.open(str(target), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(value, out, indent=2, ensure_ascii=False)
            out.write("\n")
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def _binding_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--evidence-manifest", type=Path)


def _binding(args, packet: dict, *, kind: str) -> dict:
    if (args.evidence_root is None) != (args.evidence_manifest is None):
        raise AgentError("EVIDENCE_CONFIG_INCOMPLETE",
                         "Supply both --evidence-root and --evidence-manifest")
    if args.evidence_root is None:
        return {"status": "NOT_CHECKED", "scientific_claims_verified": False}
    manifest = read_json(args.evidence_manifest, limit=128 * 1024)
    if kind == "decision":
        return bind_frozen_evidence(args.evidence_root, manifest, packet)
    refs = [ref for observation in packet["observations"]
            for ref in observation["evidence_refs"]]
    return bind_source_refs(args.evidence_root, manifest, refs)


def main() -> int:
    cli = argparse.ArgumentParser(description="Optional evidence-aware scientific checks")
    sub = cli.add_subparsers(dest="action", required=True)
    for kind in ("decision", "lessons"):
        p = sub.add_parser(kind)
        p.add_argument("--packet", type=Path, required=True)
        _binding_options(p)
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
        if args.action in {"decision", "lessons"}:
            packet = read_json(args.packet, limit=128 * 1024)
            result = (assess_proposal(packet) if args.action == "decision"
                      else compile_declared_lessons(packet))
            binding = _binding(args, packet, kind=args.action)
            if binding["status"] in {"NOT_REPLAYABLE", "EVIDENCE_OUT_OF_FREEZE",
                                     "NO_REFERENCES_DECLARED"}:
                result = {"status": "EVIDENCE_BINDING_FAILED", "source_binding": binding,
                          "assessment_not_authorized": True}
            else:
                result["source_binding"] = binding
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
                result = result["review_packet"]
    except (ValueError, OSError, TypeError, KeyError) as exc:
        result = failure(exc)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "ERROR":
        return 2
    return 3 if result.get("status") in {"NOT_REPLAYABLE", "EVIDENCE_BINDING_FAILED"} else 0


if __name__ == "__main__":
    sys.exit(main())
