"""PII masking for logs and traces (E4)."""
import re

_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[EMAIL]"),
    (re.compile(r"\+?\d[\d\s().-]{8,}\d"), "[PHONE]"),
    (re.compile(r"\b(?:\d[ -]?){13,16}\b"), "[CARD]"),
    (re.compile(r"\b(?:sk|tok|Bearer)[-_ ][A-Za-z0-9._-]{12,}"), "[SECRET]"),
]


def mask(text: str) -> str:
    for pat, rep in _PATTERNS:
        text = pat.sub(rep, text)
    return text


def mask_obj(o):
    if isinstance(o, str):
        return mask(o)
    if isinstance(o, dict):
        return {k: mask_obj(v) for k, v in o.items()}
    if isinstance(o, list):
        return [mask_obj(v) for v in o]
    return o
