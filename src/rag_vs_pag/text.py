from __future__ import annotations

import re


WORD_RE = re.compile(r"[a-z0-9]+")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def words(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def redact_pii(text: str) -> str:
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", "[email]", text)
    text = re.sub(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", "[phone]", text)
    text = re.sub(r"\b\d{1,5}\s+[A-Z][A-Za-z0-9 .'-]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr)\b", "[address]", text)
    return text


def strip_request_boilerplate(text: str) -> str:
    cleaned = text
    patterns = [
        r"(?i)to whom it may concern[:,]?",
        r"(?i)pursuant to the freedom of information act,?\s*i hereby request",
        r"(?i)sincerely,.*$",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL)
    return normalize_space(cleaned)
