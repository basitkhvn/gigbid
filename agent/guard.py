"""E4 guardrails: job posts / client messages are UNTRUSTED DATA. Delimit, detect, sanitise; never obey."""
from __future__ import annotations

import os
import re

INJECTION_PATTERNS = [
    r"ignore (all )?(previous|prior|above) (instructions|rules)", r"\bsystem\s*:", r"\[?assistant instructions\]?",
    r"note to (the )?ai", r"disclose (your )?system prompt", r"\bas an ai\b.*\b(must|should)\b", r"skip all compliance",
    r"approve this job automatically", r"you must (reply|write|say|include)", r"<!--.*?-->",
]
_INJ = re.compile("|".join(INJECTION_PATTERNS), re.I | re.S)


def input_defence_on() -> bool:
    """Evaluation switch only (evals/runners/injection_eval.py ablates the layers). Always on in production."""
    return os.environ.get("GIGBID_INPUT_DEFENCE", "1") != "0"


def wrap_untrusted(text: str, tag: str = "job_post") -> str:
    if not input_defence_on():
        return text
    safe = re.sub(rf"</?{tag}>", "", text)
    return f"<{tag}>\n{safe}\n</{tag}>"


def detect_injection(text: str) -> bool:
    return bool(_INJ.search(text))


def sanitize(text: str) -> str:
    """Remove injected instruction lines before any downstream agent reads the text."""
    if not input_defence_on():
        return text
    out = []
    for line in text.splitlines():
        if _INJ.search(line):
            out.append("[removed: suspected injected instruction]")
        else:
            out.append(line)
    return "\n".join(out)
