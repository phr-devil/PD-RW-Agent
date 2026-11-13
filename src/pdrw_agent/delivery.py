"""Read-only project handoff preview; reuse authoritative PD-RW checker."""
from __future__ import annotations
from .config import Settings, under_root
from .projects import get_project_context
from .runtime.registration import _invoke_rules
from .schemas import AgentError


def prepare_handoff(settings: Settings, project_id: str, primary_ref: str,
                    supporting_refs: list[str] | None = None) -> dict:
    ctx = get_project_context(settings, project_id)
    if ctx["status"] != "SOURCE_REVIEW_REQUIRED":
        return {"status": "BLOCKED_PROJECT_CONTEXT", "project_id": project_id,
                "project_status": ctx["status"], "new_files_created": False}
    if not isinstance(supporting_refs, list) or len(supporting_refs) > 8 or any(
        not isinstance(x, str) for x in supporting_refs
    ):
        if supporting_refs is not None:
            raise AgentError("INVALID_DELIVERY_REFS", "Use at most eight relative support paths")
        supporting_refs = []
    root, _ = settings.project(project_id)
    # Path-check metadata first; no protected artifact or external root.
    for ref in [primary_ref, *supporting_refs]:
        under_root(root, ref)
    args = ["-m", "core.delivery_check", "--root", str(root),
            "--primary", primary_ref]
    for ref in supporting_refs:
        args.extend(["--file", ref])
    checked, ok = _invoke_rules(settings, args)
    if not ok:
        return {"status": "CHECKER_UNAVAILABLE", "project_id": project_id,
                "output_ready": False}
    passed = checked.get("result") == "PASS_PATHS_ONLY"
    return {"status": "PATHS_VERIFIED_ONLY" if passed else "DELIVERY_PATHS_INVALID",
            "project_id": project_id,
            "primary_ref": primary_ref,
            "supporting_refs": supporting_refs,
            "path_check": checked,
            "scientific_truth_verified": False,
            "original_authorization_verified": False,
            "paper_or_figure_permission_granted": False,
            "new_files_created": False,
            "next": "REVIEW_ORIGINAL_RUN_AND_PDRW_NEXT_ACTION_POLICY"}
