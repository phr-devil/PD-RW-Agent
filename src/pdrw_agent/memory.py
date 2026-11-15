"""Keyword-only memory: public PD-RW case index, never a second science ledger.

Compatibility contract (unchanged for old callers):
  search_research_memory(settings, query, limit) -> {status, query, matches,
  truncated, limitations}. Legacy CASE_REGISTRY.md rows keep their exact shape.

Extension (opt-in, additive keys only):
  when CASE_LIBRARY is configured, ONE self-contained `case_library` object is
  added (holding `cases`, `case_review` only with a task_profile, and
  `decision_experiences`), plus a compact `case_learning_summary` with status
  and lookup paths and a `case_evidence_note`. No legacy key is removed or
  reinterpreted. A CASE_LIBRARY failure never breaks the legacy result.
"""
from __future__ import annotations
import re
from .config import Settings
from .schemas import AgentError
from . import case_learning


def search_research_memory(settings: Settings, query: str, limit: int = 5,
                           *, mechanism: str = "", domain: str = "",
                           applicability: str = "", verdict: str = "",
                           evidence_level: str = "", origin: str = "",
                           keyword: str = "", task_profile: dict | None = None,
                           max_experiences: int = 5,
                           include_cases: bool = True) -> dict:
    if type(limit) is not int or limit < 1:
        raise AgentError("LIMIT_INVALID", "limit must be a positive integer")
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
    cap = min(limit, 10)
    result = {"status": "MATCHES_FOUND" if hits else "NO_CASE_INDEX_MATCH",
              "query": query, "matches": hits[:cap],
              "truncated": len(hits) > cap,
              "limitations": "Index only; verify case scope, original project Run and updated evidence before reuse"}

    if not include_cases:
        return result

    filters = {"mechanism": mechanism, "domain": domain,
               "applicability": applicability, "verdict": verdict,
               "evidence_level": evidence_level, "origin": origin,
               "keyword": keyword}
    filters = {k: v for k, v in filters.items() if v}
    try:
        cl = case_learning.case_search(
            settings, query, filters, limit=limit,
            task_profile=task_profile, max_experiences=max_experiences)
    except (AgentError, OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        cl = {"status": "CASE_LIBRARY_UNAVAILABLE",
              "error_code": getattr(exc, "code", "CASE_LIBRARY_ERROR"),
              "detail": str(exc)[:200],
              "legacy_memory_still_available": True,
              "automatic_go_stop": False}
    # Single self-contained object; no duplicated review/experience payloads.
    result["case_library"] = cl
    result["case_learning_summary"] = {
        "status": cl.get("status"),
        "case_hits": cl.get("cases", {}).get("returned", 0),
        "review_status": (cl.get("case_review") or {}).get("status"),
        "classification_counts": (cl.get("case_review") or {}).get("classification_counts"),
        "experience_count": (cl.get("decision_experiences") or {}).get("returned", 0),
        "cache_hit": cl.get("cache_hit"),
        "query_fingerprint": cl.get("query_fingerprint"),
        "paths": {"cases": "case_library.cases.results",
                  "review": "case_library.case_review.comparisons",
                  "experiences": "case_library.decision_experiences.experiences"},
    }
    result["case_evidence_note"] = (
        "CASE_LIBRARY results are candidates with source verification; "
        "keyword similarity != scientific premise equivalence. No GO/STOP is emitted.")
    if cl.get("status") == "MATCHES_FOUND" and not hits:
        result["case_library_match_only"] = True
    return result
