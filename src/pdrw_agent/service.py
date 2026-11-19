"""One stable service for CLI and MCP. No scientific effect by default."""
from __future__ import annotations
import sqlite3
from .config import Settings
from .schemas import failure, classify_storage_error
from .projects import get_project_context
from .rules import get_applicable_rules
from .memory import search_research_memory
from . import (case_bridge, case_export, case_gates, case_knowledge,
               case_learning)
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
            "review_case_transfer": case_learning.case_transfer_review,
            "extract_case_candidates": case_learning.extract_candidates,
            "case_gate_check": case_gates.case_gate_check,
            "project_case_bridge": case_bridge.project_case_bridge,
            "export_case_markdown": case_export.export_case_markdown,
            "build_case_knowledge": case_knowledge.build,
            "verify_case_knowledge":
                lambda _settings, **inputs: case_knowledge.verify(settings=_settings,
                                                                 **inputs),
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
        except sqlite3.Error as exc:
            # Storage failures are operational, never INVALID_INPUT. Keep the
            # real SQLite class/message so a readonly or locked DB is visible.
            return {"status": "ERROR",
                    "error_code": classify_storage_error(exc),
                    "detail": f"{type(exc).__name__}: {exc}"[:250],
                    "storage_error_class": (type(exc).__module__ + "." +
                                            type(exc).__qualname__),
                    "authorization_verified": False}
        except (ValueError, OSError, UnicodeError, TypeError) as exc:
            return failure(exc)
