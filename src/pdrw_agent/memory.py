"""Bounded case-index retrieval; scientific facts remain with original PD-RW Runs.

One structured response per existing CASE_REGISTRY table row. All metadata is
reported, never elevated to independently verified lessons or permissions.
"""
from __future__ import annotations

import re
from .config import Settings
from .schemas import AgentError

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


def search_research_memory(settings: Settings, query: str, limit: int = 5) -> dict:
    """Rank existing case-index declarations, never infer case equivalence."""
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
    return {"status": "MATCHES_FOUND" if hits else "NO_CASE_INDEX_MATCH",
            "query": query, "matches": hits[:cap],
            "truncated": len(hits) > cap, "searched_case_rows": True,
            "source_scope": "EXISTING_PD_RW_CASE_INDEX_ONLY",
            "limitations": "Source-reported case summaries only; check project identity, original Run, validity and premise scope before reuse"}
