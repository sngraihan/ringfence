"""Brief contract: a task without an owner identity and without content is rejected.

Modeled on harmonist (MIT): the first line of a subagent prompt must be `AGENT: <slug>`,
and the delegation must have a minimum length. Without that marker, the call does not
count as work — here: the brief is rejected before the worker runs.
"""

from __future__ import annotations

import re

__all__ = ["check_brief", "OWNER_RE", "REQUIRED_SECTIONS"]

# Agent-facing text is English by owner decision (26/10). Legacy Indonesian markers
# stay accepted so older briefs keep working.
REQUIRED_SECTIONS = (("DONE", "SELESAI"), ("FORBIDDEN", "DILARANG"))

OWNER_RE = re.compile(r"^\s*OWNER:\s*([A-Za-z0-9_.-]+)\s*$", re.M)


def check_brief(text: str, min_chars: int = 80, require_owner: bool = True) -> tuple[bool, list[str]]:
    """Return (passed?, list of problems)."""
    problems: list[str] = []
    if not text or not text.strip():
        return False, ["empty brief"]
    first_line = text.strip().splitlines()[0].strip()
    if require_owner and not OWNER_RE.match(first_line):
        problems.append("first line must be `OWNER: <name>`")
    body = OWNER_RE.sub("", text).strip()
    if len(body) < min_chars:
        problems.append(f"brief body too short ({len(body)} < {min_chars} chars)")
    upper = text.upper()
    for alternatives in REQUIRED_SECTIONS:
        if not any(marker in upper for marker in alternatives):
            problems.append(f"brief must mention the section {alternatives[0]}")
    return (not problems), problems