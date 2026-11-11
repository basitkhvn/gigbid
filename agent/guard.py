"""E4 guardrails: job posts / client messages are UNTRUSTED DATA. Delimit, detect, sanitise; never obey."""
from __future__ import annotations

import re

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) (instructions|rules)", r"\bsystem\s*:", r"\[?assistant instructions\]?",
    r"note to (the )?ai", r"disclose (your )?system prompt", r"\bas an ai\b.*\b(must|should)\b", r"skip all compliance",
    r"approve this job automatically", r"you must (reply|write|say|include)", r"<!--.*?-->",
]
_INJ = re.compile("|".join(INJECTION_PATTERNS), re.I | re.S)


def wrap_untrusted(text: str, tag: str = "job_post") -> str:
    safe = re.sub(rf"</?{tag}>", "", text)
    return f"<{tag}>\n{safe}\n</{tag}>"


def detect_injection(text: str) -> bool:
    return bool(_INJ.search(text))


def sanitize(text: str) -> str:
    """Remove injected instruction lines before any downstream agent reads the text."""
    out = []
    for line in text.splitlines():
        if _INJ.search(line):
            out.append("[removed: suspected injected instruction]")
        else:
            out.append(line)
    return "\n".join(out)
