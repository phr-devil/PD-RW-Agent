"""Shared bounded JSON responses; never authenticate user permissions."""
from __future__ import annotations

class AgentError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def classify_storage_error(exc: BaseException) -> str:
    """Keep the real SQLite failure class visible instead of flattening it.

    A SQLite error is an operational storage failure, never INVALID_INPUT.
    The original exception class and message are preserved by the caller.
    """
    text = str(exc).casefold()
    if "readonly" in text or "read-only" in text:
        return "RECEIPT_STORAGE_READONLY"
    if "locked" in text or "busy" in text:
        return "RECEIPT_STORAGE_BUSY"
    if "no such table" in text:
        return "RECEIPT_STORAGE_SCHEMA_MISSING"
    if "malformed" in text or "corrupt" in text or "not a database" in text:
        return "RECEIPT_STORAGE_CORRUPT"
    if "unable to open" in text or "i/o error" in text or "disk i/o" in text:
        return "RECEIPT_STORAGE_UNAVAILABLE"
    return "RECEIPT_STORAGE_ERROR"


def failure(exc: Exception) -> dict:
    return {"status": "ERROR", "error_code": getattr(exc, "code", "INVALID_INPUT"),
            "detail": str(exc)[:250], "authorization_verified": False}
