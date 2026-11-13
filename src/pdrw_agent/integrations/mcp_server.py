"""Five read-only MCP v2 tools. stdout is exclusively MCP protocol output."""
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
        "Read-only PD-RW context tools. Responses never authenticate user "
        "authorization, scientific claims, or SEALED access. "
        "Always consult original PD-RW rules and genuine project evidence."
    ))

    @mcp.tool()
    def get_project_context(project_id: str) -> dict[str, Any]:
        """Restore only a registered project's bounded snapshot and machine STATE index."""
        return service.call("get_project_context", project_id=project_id)

    @mcp.tool()
    def get_applicable_rules(topic: str = "") -> dict[str, Any]:
        """List/select current PD-RW AGENTS.md rule references; no copied policy."""
        return service.call("get_applicable_rules", topic=topic)

    @mcp.tool()
    def search_research_memory(query: str, limit: int = 5) -> dict[str, Any]:
        """Search evidence-qualified historical case lessons, not raw science truth."""
        return service.call("search_research_memory", query=query, limit=limit)

    @mcp.tool()
    def find_experiment_evidence(project_id: str, task_id: str = "",
                                 run_id: str = "", limit: int = 6) -> dict[str, Any]:
        """Read indexed DEV Run metadata only; do not access SEALED."""
        return service.call("find_experiment_evidence", project_id=project_id,
                            task_id=task_id, run_id=run_id, limit=limit)

    @mcp.tool()
    def check_duplicate_experiment(project_id: str, spec: dict[str, Any]) -> dict[str, Any]:
        """Compare declared fingerprints with indexed DEV Runs; never infer scientific equivalence."""
        return service.call("check_duplicate_experiment", project_id=project_id, spec=spec)

    return mcp

def main():
    create_server().run(transport="stdio")

if __name__ == "__main__":
    main()
