"""One stable service for CLI and MCP. No scientific effect by default."""
from __future__ import annotations
import sqlite3
from .config import Settings
from .schemas import failure, classify_storage_error
from .projects import get_project_context
from .rules import get_applicable_rules
from .memory import search_research_memory
from . import case_learning, case_gates
from .evidence import find_experiment_evidence
from .experiments import check_duplicate_experiment
from .runtime.receipts import begin_operation, checkpoint_operation, execution_status
from .runtime.recovery import get_resume_context
from .runtime.registration import preview_experiment_record
from .delivery import prepare_handoff


class ResearchService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def call(self, name: str, **kwargs) -> dict:
        handlers = {
            "get_project_context": get_project_context,
            "get_applicable_rules": get_applicable_rules,
            "search_research_memory": search_research_memory,
            "review_case_transfer": case_learning.case_transfer_review,
            "extract_case_candidates": case_learning.extract_candidates,
            "case_gate_check": case_gates.case_gate_check,
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
