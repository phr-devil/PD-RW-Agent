"""PD-RW MCP v0.5: bounded reads plus private operational-only receipts.

There is deliberately NO MCP tool to write PD-RW Run/Claim/STATE. A separately
trusted host must authenticate permission and call the internal adapter.
MCP stdout remains exclusively protocol traffic.
"""
from __future__ import annotations
from typing import Any
from ..config import Settings
from ..service import ResearchService


def create_server(settings: Settings | None = None):
    try:
        from mcp.server import MCPServer
    except ImportError as exc:
        raise RuntimeError('Install MCP extra: pip install -e ".[mcp]"') from exc
    service = ResearchService(settings or Settings.load())
    mcp = MCPServer("PD-RW Research", instructions=(
        "PD-RW is the only scientific rule source. The only mutations allowed "
        "here are private execution receipts, never research artifacts. "
        "A reported operation, preflight, checkpoint, or memory is not "
        "original-user authorization or scientific validation. "
        "CASE_LIBRARY lookups are read-only advisory candidates: keyword "
        "similarity is NOT scientific premise equivalence, no GO/STOP is "
        "emitted, unresolved cases stay candidates, and no STATE/Run/SEALED "
        "or research rule is modified. "
        "case_gate_check implements 3 advisory checkpoints (G1 H2-H3 question "
        "selection, G2 H6-H7 protocol freeze, G3 H8-H10 claim/closure) and 2 "
        "conditional triggers (T1 anomaly/negative results, T2 material "
        "decision change) with priority G1>G2>G3>T1>T2. It reuses the existing "
        "retriever, verifies a REAL retrieval plus applicability judgement, "
        "deduplicates by fingerprint and marks missing/insufficient/conflicting "
        "evidence UNKNOWN. These are Skill/tool-level advisory requests, NOT a "
        "host state-transition hard gate; PD-RW H6/H8 author choices and "
        "writing permissions are unchanged. "
        "Do not auto-restart uncertain GPU jobs or open SEALED."
    ))

    @mcp.tool()
    def get_project_context(project_id: str) -> dict[str, Any]:
        """Read a registered project's minimal snapshot and unverified machine STATE index."""
        return service.call("get_project_context", project_id=project_id)

    @mcp.tool()
    def get_applicable_rules(topic: str = "") -> dict[str, Any]:
        """Get current local PD-RW AGENTS.md routing hints, never grant authorization."""
        return service.call("get_applicable_rules", topic=topic)

    @mcp.tool()
    def search_research_memory(query: str, limit: int = 5, mechanism: str = "",
                               domain: str = "", applicability: str = "",
                               verdict: str = "", evidence_level: str = "",
                               origin: str = "", keyword: str = "",
                               max_experiences: int = 5,
                               include_cases: bool = True,
                               case_scope: str = "auto",
                               task_profile: dict[str, Any] | None = None) -> dict[str, Any]:
        """Legacy PD-RW case index + read-only CASE_LIBRARY cases/review/impacts.

        Old (query, limit) calls keep their exact result shape; new keys are
        additive. Supply task_profile to request an 8-dimension migration
        review (mechanisms, legal inputs, labels, grouping, evaluation unit,
        baseline, boundaries, counterexamples). case_scope='auto' skips the
        full case library for general lookups; 'force' always retrieves,
        'off' never does. Never emits GO/STOP.
        """
        return service.call("search_research_memory", query=query, limit=limit,
                            mechanism=mechanism, domain=domain,
                            applicability=applicability, verdict=verdict,
                            evidence_level=evidence_level, origin=origin,
                            keyword=keyword, max_experiences=max_experiences,
                            include_cases=include_cases, case_scope=case_scope,
                            task_profile=task_profile)

    @mcp.tool()
    def review_case_transfer(task_profile: dict[str, Any], limit: int = 5,
                             query: str = "case transfer review",
                             mechanism: str = "", domain: str = "",
                             verdict: str = "", evidence_level: str = "",
                             keyword: str = "") -> dict[str, Any]:
        """Independent advisory review of current task vs historical cases.

        Outputs APPLICABILITY_RISK / CONDITIONS_DIFFER / USEFUL_ANALOGY /
        EVIDENCE_INSUFFICIENT per case. Declared-text keyword triage only;
        scientific equivalence and GO/STOP are never asserted.
        """
        filters = {k: v for k, v in {
            "mechanism": mechanism, "domain": domain, "verdict": verdict,
            "evidence_level": evidence_level, "keyword": keyword}.items() if v}
        return service.call("review_case_transfer", task_profile=task_profile,
                            filters=filters, query=query, limit=limit)

    @mcp.tool()
    def extract_case_candidates(project_id: str,
                                observations: list[dict[str, Any]],
                                evidence_root: str = "",
                                evidence_manifest: dict[str, Any] | None = None
                                ) -> dict[str, Any]:
        """Read-only candidate experiences from the original Run + science audit.

        Never writes CASE_LIBRARY, STATE, Run or EVENTS; unverified outcomes
        stay CANDIDATE_ONLY and are never promoted to a formal case.
        """
        return service.call("extract_case_candidates", project_id=project_id,
                            observations=observations,
                            evidence_root=evidence_root or None,
                            evidence_manifest=evidence_manifest)

    @mcp.tool()
    def case_gate_check(event: dict[str, Any], detail: str = "compact") -> dict[str, Any]:
        """Advisory case gate: 3 mandatory checkpoints + 2 conditional triggers.

        event declares h_stage, milestone (QUESTION_SELECTION / PROTOCOL_FREEZE /
        CLAIM_OR_CLOSURE / NONE), signals, task_id, hypothesis, protocol,
        declared task_profile (8 dimensions), query and filters. Ordinary DEV
        signals are suppressed. The tool reuses case_learning.case_search for
        the real retrieval and 8-dimension applicability review; it does NOT
        add a second retriever or ranking. Returns at most 5 compact cases, a
        verifiable retrieval_record, UNKNOWN reasons, cache/fingerprint info
        and the actual (non-hard-gate) enforcement level. No GO/STOP, no writes.
        """
        return service.call("case_gate_check", event=event, detail=detail)

    @mcp.tool()
    def find_experiment_evidence(project_id: str, task_id: str = "",
                                 run_id: str = "", limit: int = 6) -> dict[str, Any]:
        """Read indexed non-SEALED Run metadata; scientific validity remains unverified."""
        return service.call("find_experiment_evidence", project_id=project_id,
                            task_id=task_id, run_id=run_id, limit=limit)

    @mcp.tool()
    def check_duplicate_experiment(project_id: str, spec: dict[str, Any]) -> dict[str, Any]:
        """Check declared Run configuration similarity, never assume scientific equivalence."""
        return service.call("check_duplicate_experiment", project_id=project_id, spec=spec)

    @mcp.tool()
    def get_resume_context(project_id: str) -> dict[str, Any]:
        """Resume research context and operational receipts; do NOT start any job."""
        return service.call("get_resume_context", project_id=project_id)

    @mcp.tool()
    def get_execution_status(project_id: str, operation_id: str = "",
                             limit: int = 6) -> dict[str, Any]:
        """Query private receipts and artifact hashes; reported RUNNING is not process proof."""
        return service.call("get_execution_status", project_id=project_id,
                            operation_id=operation_id, limit=limit)

    @mcp.tool()
    def begin_operation_receipt(project_id: str, operation_id: str,
                                task_id: str, action: str) -> dict[str, Any]:
        """Write a private metadata receipt only. Does NOT execute/authorize a DEV action."""
        return service.call("begin_operation_receipt", project_id=project_id,
                            operation_id=operation_id, task_id=task_id, action=action)

    @mcp.tool()
    def checkpoint_operation_receipt(project_id: str, operation_id: str,
                                     expected_revision: int, phase: str,
                                     artifact_ref: str = "") -> dict[str, Any]:
        """Checkpoint a declared operational phase; never certify live process or science."""
        return service.call("checkpoint_operation_receipt", project_id=project_id,
                            operation_id=operation_id, expected_revision=expected_revision,
                            phase=phase, artifact_ref=artifact_ref)

    @mcp.tool()
    def preview_experiment_record(project_id: str, artifact_ref: str) -> dict[str, Any]:
        """Preview original PD-RW Run contract, duplicate and STATE/EVENTS consistency; no write."""
        return service.call("preview_experiment_record", project_id=project_id,
                            artifact_ref=artifact_ref)

    @mcp.tool()
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
