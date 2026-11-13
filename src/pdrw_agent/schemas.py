"""Shared bounded JSON responses; never authenticate user permissions."""
from __future__ import annotations

class AgentError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

def failure(exc: Exception) -> dict:
    return {"status": "ERROR", "error_code": getattr(exc, "code", "INVALID_INPUT"),
            "detail": str(exc)[:250], "authorization_verified": False}
