"""Shared conservative parsing of declared Markdown project IDs.

This parser extracts metadata only. A matching ID is not source authenticity,
author permission or evidence that a project mapping is correct.
"""
from __future__ import annotations
import re

_ID_LINE = re.compile(
    r"^\s*(?:-\s*)?(?:\*\*项目身份\*\*\s*[：:]\s*)?"
    r"(?:\*\*)?\x60?PROJECT_ID\x60?(?:\*\*)?\s*[:：=]\s*"
    r"\x60?([A-Za-z0-9][A-Za-z0-9_.-]{0,127})\x60?\s*(?:#.*)?$"
)
_ID_PREFIX = re.compile(
    r"^\s*(?:-\s*)?(?:\*\*项目身份\*\*\s*[：:]\s*)?"
    r"(?:\*\*)?\x60?PROJECT_ID\x60?(?:\*\*)?\s*[:：=]"
)


def parse_markdown_project_id(content: str) -> tuple[str | None, str]:
    """Return (ID, DECLARED | MISSING | AMBIGUOUS)."""
    values: set[str] = set()
    malformed = False
    fence = None
    for line in content[:32_000].splitlines():
        stripped = line.strip()
        if stripped.startswith(("~~~", "\x60\x60\x60")):
            marker = stripped[:3]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence:
            continue
        match = _ID_LINE.fullmatch(line)
        if match:
            values.add(match.group(1))
        elif _ID_PREFIX.match(line):
            malformed = True
    if malformed or len(values) > 1:
        return None, "AMBIGUOUS"
    if values:
        return next(iter(values)), "DECLARED"
    return None, "MISSING"
