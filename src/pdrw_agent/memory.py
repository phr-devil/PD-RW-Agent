"""Bounded case-index retrieval; scientific facts remain with original PD-RW Runs.

One structured response per existing CASE_REGISTRY table row. All metadata is
reported, never elevated to independently verified lessons or permissions.

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

MAX_INDEX_BYTES = 2 * 1024 * 1024
MAX_QUERY = 250
MAX_MATCHES = 10
WORD = re.compile(r"[a-z][a-z0-9_.-]{1,}|[\u4e00-\u9fff]{2,}", re.I)
CASE_ID = re.compile(r"`([A-Za-z0-9][A-Za-z0-9_.-]{2,})`")
TAG = re.compile(r"`([A-Z][A-Z0-9_/-]{2,})`")


def _terms(query: str) -> list[str]:
    return list(dict.fromkeys(item.casefold() for item in WORD.findall(query)))[:8]


def _case_row(line: str) -> dict | None:
    """Parse only the four-column historical case table, not free prose."""
    if not line.startswith("|"):
        return None
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    # Current PD-RW uses four columns; some previous/compact indexes use
    # two. Preserve those searchable legacy records without inventing scope.
    if len(cells) not in (2, 4) or cells[0].casefold() in {
        "case_id", "case_id / 号（非强制唯一编号）", "---"}:
        return None
    match = CASE_ID.search(cells[0])
    raw_id = match.group(1) if match else cells[0]
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{1,79}", raw_id):
        return None
    boundaries = cells[2] if len(cells) == 4 else ""
    sources = cells[3] if len(cells) == 4 else ""
    return {"case_id": raw_id, "summary": cells[1],
            "declared_boundaries": boundaries,
            "source_declarations": sources,
            "declared_status_tags": list(dict.fromkeys(TAG.findall(boundaries)))[:10]}


# A legacy CASE_REGISTRY lookup for project state / rules should not pull the
# whole 65-card advisory into the conversation. Only a call that is actually
# about cases, mechanisms or a declared migration review does that.
CASE_INTENT = re.compile(
    r"(案例|经验|失败|成功|反例|复现|泄漏|标签|分组|基线|泛化|标定|捷径|"
    r"评价|适用|迁移|对照|负结果|传感器|机制|基线|实验协议|"
    r"case|leak|label|group|baseline|reproduc|negative|transfer|shortcut|"
    r"calibration|generaliz|har|esm|split)", re.I)
CASE_SCOPES = ("auto", "force", "off")


def _case_scope_reason(query: str, filters: dict, task_profile: dict | None,
                       legacy_hits: list) -> tuple[bool, str]:
    if task_profile:
        return True, "TASK_PROFILE_DECLARED"
    if filters:
        return True, "CASE_FILTERS_DECLARED"
    if legacy_hits:
        return True, "LEGACY_CASE_INDEX_MATCH"
    if CASE_INTENT.search(query):
        return True, "CASE_INTENT_TERMS_IN_QUERY"
    return False, "NO_CASE_SCOPE_SIGNAL_GENERAL_LOOKUP"


def search_research_memory(settings: Settings, query: str, limit: int = 5,
                           *, mechanism: str = "", domain: str = "",
                           applicability: str = "", verdict: str = "",
                           evidence_level: str = "", origin: str = "",
                           keyword: str = "", task_profile: dict | None = None,
                           max_experiences: int = 5,
                           include_cases: bool = True,
                           case_scope: str = "auto") -> dict:
    """Legacy index plus opt-in CASE_LIBRARY retrieval.

    ``case_scope='auto'`` (default) skips the full case library for general
    lookups; ``'force'`` always retrieves and ``'off'`` never does. The legacy
    keys keep their exact shape in every mode.
    """
    if case_scope not in CASE_SCOPES:
        raise AgentError("CASE_SCOPE_INVALID", "case_scope must be auto, force or off")
    if type(limit) is not int or limit < 1:
        raise AgentError("LIMIT_INVALID", "limit must be a positive integer")
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= MAX_QUERY:
        raise AgentError("QUERY_REQUIRED", "Use a 2..250-character query")
    source = settings.workflow_root / "LESSONS" / "CASE_REGISTRY.md"
    if not source.is_file():
        raise AgentError("CASE_INDEX_MISSING", "PD-RW case index unavailable")
    if source.stat().st_size > MAX_INDEX_BYTES:
        raise AgentError("CASE_INDEX_TOO_LARGE", "Case index requires explicit indexing")
    terms = _terms(query)
    if not terms:
        raise AgentError("QUERY_REQUIRED", "Query needs a meaningful word")
    hits = []
    for lineno, line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), 1):
        row = _case_row(line)
        if row is None:
            continue
        identifier = row["case_id"].casefold()
        score = sum(
            (5 if term == identifier else 3 if term in identifier else 0)
            + (2 if term in row["summary"].casefold() else 0)
            + (2 if term in row["declared_boundaries"].casefold() else 0)
            + (1 if term in row["source_declarations"].casefold() else 0)
            for term in terms
        )
        if score == 0:
            continue
        # A compact structured card avoids repeated consumption of whole rows
        # while keeping the specific declared scope and evidence caveats.
        matched_terms = [term for term in terms
                         if term in (identifier + " " + row["summary"].casefold()
                                     + " " + row["declared_boundaries"].casefold()
                                     + " " + row["source_declarations"].casefold())]
        hits.append({
            "matched_terms": matched_terms,
            "candidate_review": "OPEN_ORIGINAL_RUN_AND_COMPARE_PREMISE_SCOPE",
            "scientific_applicability": "UNKNOWN",
            "line": lineno, "score": score, "case_id": row["case_id"],
            "excerpt": line.strip()[:360], "source_file": "LESSONS/CASE_REGISTRY.md",
            "declared_status_tags": row["declared_status_tags"],
            "declared_boundaries": row["declared_boundaries"][:450],
            "source_declarations": row["source_declarations"][:240],
            "evidence_level": "REPOSITORY_CASE_INDEX_NOT_RAW_RUN",
            "original_run_verified": False,
            "premise_equivalence_verified": False,
        })
    hits.sort(key=lambda x: (-x["score"], x["line"]))
    cap = min(limit, MAX_MATCHES)
    result = {"status": "MATCHES_FOUND" if hits else "NO_CASE_INDEX_MATCH",
              "query": query, "matches": hits[:cap],
              "truncated": len(hits) > cap, "searched_case_rows": True,
              "source_scope": "EXISTING_PD_RW_CASE_INDEX_ONLY",
              "limitations": "Source-reported case summaries only; check project identity, original Run, validity and premise scope before reuse"}

    filters = {"mechanism": mechanism, "domain": domain,
               "applicability": applicability, "verdict": verdict,
               "evidence_level": evidence_level, "origin": origin,
               "keyword": keyword}
    filters = {k: v for k, v in filters.items() if v}
    relevant, reason = _case_scope_reason(query, filters, task_profile,
                                          result["matches"])
    if not include_cases:
        # Exact legacy shape for the pre-0.5.4 contract: no additive keys.
        return result
    if case_scope == "off" or (case_scope == "auto" and not relevant):
        skipped = {
            "status": "CASE_LIBRARY_RETRIEVAL_SKIPPED",
            "reason": "CASE_SCOPE_OFF" if case_scope == "off" else reason,
            "legacy_memory_still_available": True,
            "automatic_go_stop": False, "no_writes": True,
            "on_demand": ["case_gate_check(event)",
                          "review_case_transfer(task_profile=...)",
                          "search_research_memory(case_scope='force')"],
        }
        result["case_library"] = skipped
        result["case_learning_summary"] = {
            "status": skipped["status"], "case_hits": 0,
            "case_retrieval_executed": False, "reason": skipped["reason"],
        }
        return result

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
        "case_retrieval_executed": cl.get("status") not in
            {"CASE_LIBRARY_NOT_CONFIGURED", "CASE_LIBRARY_UNAVAILABLE"},
        "case_scope": case_scope,
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
