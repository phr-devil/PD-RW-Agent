"""Rule routes are read from current PD-RW AGENTS.md; no copied scientific policy."""
from __future__ import annotations
import re
from .config import Settings
from .projects import rule_commit
from .schemas import AgentError

def get_applicable_rules(settings: Settings, topic: str = "") -> dict:
    root = settings.workflow_root
    source = root / "AGENTS.md"
    text = source.read_text(encoding="utf-8-sig")
    section = re.search(r"(?ms)^##\s+2\.[^\n]*\n(.*?)(?=^##\s+3\.|\Z)", text)
    if not section:
        raise AgentError("RULE_ROUTE_MISSING", "Cannot locate existing AGENTS.md rule-routing table")
    rows = []
    for line in section.group(1).splitlines():
        if not line.startswith("|"):
            continue
        cells = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        refs = []
        for rel in re.findall(r"\]\(([^)]+)\)", cells[1]):
            rel = rel.split("#", 1)[0]
            try:
                from .config import under_root
                candidate = under_root(root, rel, protect_data=False)
            except AgentError:
                continue
            if candidate.is_file() and candidate.suffix.lower() == ".md" and rel not in refs:
                refs.append(rel)
        if refs:
            rows.append({"topic": re.sub(r"[*\x60]", "", cells[0]).strip(),
                         "rule_paths": refs[:8]})
    if not rows:
        raise AgentError("RULE_ROUTE_MISSING", "AGENTS.md contains no valid rule routes")
    key = topic.strip().casefold()
    matches = ([r for r in rows if r["topic"].casefold() == key]
               or [r for r in rows if key in r["topic"].casefold()]) if key else rows
    return {"status": "ROUTE_FOUND" if len(matches) == 1 and key else "ROUTE_SELECTION_REQUIRED",
            "query": topic, "matches": matches[:12],
            "rule_commit_local_only": rule_commit(root),
            "rule_freshness": "REMOTE_NOT_CHECKED",
            "source": "AGENTS.md#2",
            "authorization_verified": False,
            "scope": "NAVIGATION_ONLY_NOT_POLICY_ATTESTATION"}
