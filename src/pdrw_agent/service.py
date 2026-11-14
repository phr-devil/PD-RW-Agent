"""One stable service for CLI and MCP. No scientific effect by default."""
from __future__ import annotations
import sqlite3
from .config import Settings
from .schemas import failure
from .projects import get_project_context
from .rules import get_applicable_rules
from .memory import search_research_memory
from .evidence import find_experiment_evidence
from .experiments import check_duplicate_experiment
from .runtime.receipts import begin_operation, checkpoint_operation, execution_status
from .runtime.recovery import get_resume_context
from .runtime.registration import preview_experiment_record
from .delivery import prepare_handoff
from .runtime.audit import audit_project_state
from .runtime.history import reconstruct_project_history
from .science.run_integrity import verify_run_evidence
from .science.applicability import review_lesson_applicability
from .science.validity import audit_scientific_experiment
from .science.lesson_evidence import review_evidenced_lesson
from .runtime.plan import preflight_execution_plan
from .runtime.synthetic_executor import get_synthetic_job_status
from .host.supervisor import get_host_diagnostic_status


class ResearchService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def call(self, name: str, **kwargs) -> dict:
        handlers = {
            "get_project_context": get_project_context,
            "preflight_execution_plan": preflight_execution_plan,
            "get_synthetic_job_status": get_synthetic_job_status,
            "get_host_diagnostic_status": get_host_diagnostic_status,
            "audit_project_state": audit_project_state,
            "reconstruct_project_history": reconstruct_project_history,
            "verify_run_evidence": verify_run_evidence,
            "audit_scientific_experiment": audit_scientific_experiment,
            "review_evidenced_lesson": review_evidenced_lesson,
            "review_lesson_applicability":
                lambda _settings, **inputs: review_lesson_applicability(**inputs),
            "get_applicable_rules": get_applicable_rules,
            "search_research_memory": search_research_memory,
            "find_experiment_evidence": find_experiment_evidence,
            "check_duplicate_experiment": check_duplicate_experiment,
            "get_resume_context": get_resume_context,
            "get_execution_status": execution_status,
            "begin_operation_receipt": begin_operation,
            "checkpoint_operation_receipt": checkpoint_operation,
            "preview_experiment_record": preview_experiment_record,
            "prepare_handoff": prepare_handoff,
        }
        try:
            handler = handlers.get(name)
            if handler is None:
                return {"status": "ERROR", "error_code": "UNKNOWN_TOOL"}
            return handler(self.settings, **kwargs)
        except (ValueError, OSError, UnicodeError, TypeError, sqlite3.Error) as exc:
            return failure(exc)
