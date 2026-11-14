"""PD-RW MCP v0.5: bounded reads plus private operational-only receipts.

There is deliberately NO MCP tool to write PD-RW Run/Claim/STATE. A separately
trusted host must authenticate permission and call the internal adapter.
MCP stdout remains exclusively protocol traffic.
"""
from __future__ import annotations
import os
from typing import Any
from ..config import Settings
from ..service import ResearchService


# Visibility profiles reduce tool-choice overhead, NOT authority. The service
# and original PD-RW permission boundaries are unchanged.
CORE_TOOLS = frozenset({
    "get_project_context", "get_applicable_rules", "search_research_memory",
    "find_experiment_evidence", "check_duplicate_experiment",
    "get_resume_context", "get_execution_status",
    "begin_operation_receipt", "checkpoint_operation_receipt",
    "preview_experiment_record", "prepare_handoff",
})
AUDIT_TOOLS = frozenset({
    "audit_project_state", "reconstruct_project_history",
    "verify_run_evidence", "audit_scientific_experiment",
    "review_evidenced_lesson", "review_lesson_applicability",
})
DIAGNOSTIC_TOOLS = frozenset({
    "preflight_execution_plan", "get_synthetic_job_status",
    "get_host_diagnostic_status",
})
PROFILE_TOOLS = {
    "minimal": CORE_TOOLS,
    "research": CORE_TOOLS | AUDIT_TOOLS,
    "diagnostic": CORE_TOOLS | AUDIT_TOOLS | DIAGNOSTIC_TOOLS,
}


def tools_for_profile(profile: str | None = None) -> frozenset[str]:
    selected = profile if profile is not None else os.getenv("PDRW_MCP_PROFILE", "research")
    if not isinstance(selected, str) or selected not in PROFILE_TOOLS:
        raise ValueError("Invalid PDRW_MCP_PROFILE; use minimal, research or diagnostic")
    return PROFILE_TOOLS[selected]


def create_server(settings: Settings | None = None, profile: str | None = None):
    try:
        from mcp.server import MCPServer
    except ImportError as exc:
        raise RuntimeError('Install MCP extra: pip install -e ".[mcp]"') from exc
    visible_tools = tools_for_profile(profile)
    service = ResearchService(settings or Settings.load())
    mcp = MCPServer("PD-RW Research", instructions=(
        "PD-RW is the only scientific rule source. The only mutations allowed "
        "here are private execution receipts, never research artifacts. "
        "A reported operation, preflight, checkpoint, or memory is not "
        "original-user authorization or scientific validation. "
        "Do not auto-restart uncertain GPU jobs or open SEALED."
    ))

    def register(name: str):
        # Unselected tools are never registered in the protocol tool list.
        return mcp.tool() if name in visible_tools else (lambda func: func)

    @register("get_project_context")
    def get_project_context(project_id: str) -> dict[str, Any]:
        """Read a registered project's minimal snapshot and unverified machine STATE index."""
        return service.call("get_project_context", project_id=project_id)

    @register("preflight_execution_plan")
    def preflight_execution_plan(plan: dict[str, Any]) -> dict[str, Any]:
        """Read-only fixed synthetic CPU plan check; never grants scientific execution."""
        return service.call("preflight_execution_plan", plan=plan)

    @register("get_synthetic_job_status")
    def get_synthetic_job_status(project_id: str, operation_id: str) -> dict[str, Any]:
        """Read-only private synthetic job checkpoint; no liveness/authorization claim."""
        return service.call("get_synthetic_job_status",
                            project_id=project_id, operation_id=operation_id)

    @register("get_host_diagnostic_status")
    def get_host_diagnostic_status(project_id: str, operation_id: str) -> dict[str, Any]:
        """Read-only OS-supervised fixed CPU checkpoint, never a scientific permission."""
        return service.call("get_host_diagnostic_status",
                            project_id=project_id, operation_id=operation_id)

    @register("audit_project_state")
    def audit_project_state(project_id: str) -> dict[str, Any]:
        """Audit registered state, evidence coverage and version drift (read-only)."""
        return service.call("audit_project_state", project_id=project_id)

    @register("reconstruct_project_history")
    def reconstruct_project_history(project_id: str) -> dict[str, Any]:
        """Check machine STATE/EVENTS metadata chain; never repair or certify Runs."""
        return service.call("reconstruct_project_history", project_id=project_id)

    @register("verify_run_evidence")
    def verify_run_evidence(project_id: str, run_id: str) -> dict[str, Any]:
        """Compare an indexed DEV/VAL Run to original contract and bounded artifact hashes."""
        return service.call("verify_run_evidence", project_id=project_id, run_id=run_id)

    @register("audit_scientific_experiment")
    def audit_scientific_experiment(project_id: str, run_id: str,
                                     baseline_run_id: str = "") -> dict[str, Any]:
        """Read-only DEV/VAL row-level leakage, metric and baseline checks; not science approval."""
        return service.call("audit_scientific_experiment",
                            project_id=project_id, run_id=run_id,
                            baseline_run_id=baseline_run_id)

    @register("review_evidenced_lesson")
    def review_evidenced_lesson(project_id: str, run_id: str,
                               proposal: dict[str, Any]) -> dict[str, Any]:
        """Match a hash-bound Run negative metric observation to declared new premise scope."""
        return service.call("review_evidenced_lesson",
                            project_id=project_id, run_id=run_id, proposal=proposal)

    @register("review_lesson_applicability")
    def review_lesson_applicability(proposal: dict[str, Any],
                                    lessons: list[dict[str, Any]]) -> dict[str, Any]:
        """Compare literal scientific premise and declared scopes; no automatic STOP."""
        return service.call("review_lesson_applicability",
                            proposal=proposal, lessons=lessons)

    @register("get_applicable_rules")
    def get_applicable_rules(topic: str = "") -> dict[str, Any]:
        """Get current local PD-RW AGENTS.md routing hints, never grant authorization."""
        return service.call("get_applicable_rules", topic=topic)

    @register("search_research_memory")
    def search_research_memory(query: str, limit: int = 5) -> dict[str, Any]:
        """Search case-index memory; confirm claims against original Run evidence."""
        return service.call("search_research_memory", query=query, limit=limit)

    @register("find_experiment_evidence")
    def find_experiment_evidence(project_id: str, task_id: str = "",
                                 run_id: str = "", limit: int = 6) -> dict[str, Any]:
        """Read indexed non-SEALED Run metadata; scientific validity remains unverified."""
        return service.call("find_experiment_evidence", project_id=project_id,
                            task_id=task_id, run_id=run_id, limit=limit)

    @register("check_duplicate_experiment")
    def check_duplicate_experiment(project_id: str, spec: dict[str, Any]) -> dict[str, Any]:
        """Check declared Run configuration similarity, never assume scientific equivalence."""
        return service.call("check_duplicate_experiment", project_id=project_id, spec=spec)

    @register("get_resume_context")
    def get_resume_context(project_id: str, detail_level: str = "compact") -> dict[str, Any]:
        """Resume research context and operational receipts; do NOT start any job."""
        return service.call("get_resume_context", project_id=project_id,
                            detail_level=detail_level)

    @register("get_execution_status")
    def get_execution_status(project_id: str, operation_id: str = "",
                             limit: int = 6) -> dict[str, Any]:
        """Query private receipts and artifact hashes; reported RUNNING is not process proof."""
        return service.call("get_execution_status", project_id=project_id,
                            operation_id=operation_id, limit=limit)

    @register("begin_operation_receipt")
    def begin_operation_receipt(project_id: str, operation_id: str,
                                task_id: str, action: str) -> dict[str, Any]:
        """Write a private metadata receipt only. Does NOT execute/authorize a DEV action."""
        return service.call("begin_operation_receipt", project_id=project_id,
                            operation_id=operation_id, task_id=task_id, action=action)

    @register("checkpoint_operation_receipt")
    def checkpoint_operation_receipt(project_id: str, operation_id: str,
                                     expected_revision: int, phase: str,
                                     artifact_ref: str = "") -> dict[str, Any]:
        """Checkpoint a declared operational phase; never certify live process or science."""
        return service.call("checkpoint_operation_receipt", project_id=project_id,
                            operation_id=operation_id, expected_revision=expected_revision,
                            phase=phase, artifact_ref=artifact_ref)

    @register("preview_experiment_record")
    def preview_experiment_record(project_id: str, artifact_ref: str) -> dict[str, Any]:
        """Preview original PD-RW Run contract, duplicate and STATE/EVENTS consistency; no write."""
        return service.call("preview_experiment_record", project_id=project_id,
                            artifact_ref=artifact_ref)

    @register("prepare_handoff")
    def prepare_handoff(project_id: str, primary_ref: str,
                        supporting_refs: list[str] | None = None) -> dict[str, Any]:
        """Read-only path check and primary-delivery hint; create no research files."""
        return service.call("prepare_handoff", project_id=project_id,
                            primary_ref=primary_ref, supporting_refs=supporting_refs)

    return mcp


def main():
    create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
