"""Keyword-only memory: public PD-RW case index, never a second science ledger."""
from __future__ import annotations
import re
from .config import Settings
from .schemas import AgentError

def search_research_memory(settings: Settings, query: str, limit: int = 5) -> dict:
    if not isinstance(query, str) or len(query.strip()) < 2:
        raise AgentError("QUERY_REQUIRED", "Use a query of at least two characters")
    source = settings.workflow_root / "LESSONS" / "CASE_REGISTRY.md"
    if not source.is_file():
        raise AgentError("CASE_INDEX_MISSING", "PD-RW case index unavailable")
    if source.stat().st_size > 2 * 1024 * 1024:
        raise AgentError("CASE_INDEX_TOO_LARGE", "Case index requires explicit indexing")
    # Non-embedding, transparent search; more than one term can be matched.
    terms = [x.casefold() for x in re.findall(r"[\w\u4e00-\u9fff-]+", query) if len(x) >= 2][:6]
    if not terms:
        raise AgentError("QUERY_REQUIRED", "Query needs at least one meaningful word")
    hits = []
    for lineno, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.startswith("|") or line.lstrip().startswith("| ---"):
            continue
        score = sum(1 for x in terms if x in line.casefold())
        if score == 0:
            continue
        hits.append({"line": lineno, "score": score,
                     "excerpt": line.strip()[:360],
                     "source_file": "LESSONS/CASE_REGISTRY.md",
                     "evidence_level": "REPOSITORY_CASE_INDEX_NOT_RAW_RUN"})
    hits.sort(key=lambda x: (-x["score"], x["line"]))
    return {"status": "MATCHES_FOUND" if hits else "NO_CASE_INDEX_MATCH",
            "query": query, "matches": hits[:max(1, min(limit, 10))],
            "truncated": len(hits) > max(1, min(limit, 10)),
            "limitations": "Index only; verify case scope, original project Run and updated evidence before reuse"}
