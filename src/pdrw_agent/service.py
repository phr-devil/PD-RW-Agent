"""One error-safe service used by both CLI and MCP; never executes experiments."""
from __future__ import annotations
from .config import Settings
from .schemas import failure
from .projects import get_project_context
from .rules import get_applicable_rules
from .memory import search_research_memory
from .evidence import find_experiment_evidence
from .experiments import check_duplicate_experiment

class ResearchService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def call(self, name: str, **kwargs) -> dict:
        tools = {
            "get_project_context": get_project_context,
            "get_applicable_rules": get_applicable_rules,
            "search_research_memory": search_research_memory,
            "find_experiment_evidence": find_experiment_evidence,
            "check_duplicate_experiment": check_duplicate_experiment,
        }
        try:
            if name not in tools:
                return {"status": "ERROR", "error_code": "UNKNOWN_TOOL"}
            return tools[name](self.settings, **kwargs)
        except (ValueError, OSError, UnicodeError) as exc:
            return failure(exc)
