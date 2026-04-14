"""Deterministic keyword-based feature extractor.

Zero LLM calls. Reads each feature's `keywords` list from
feature_dictionary.json and sets the feature TRUE if ANY keyword appears
as a case-insensitive substring of the description AND no `negative_keywords`
match. Otherwise FALSE.

This gives a fully-LLM-free path from free-text record description to a
feature vector the pearl can run. On easy cases it works as well as the
LLM; on paraphrased or oblique descriptions it under-extracts (sets
features FALSE that the LLM would set TRUE). The tradeoff is full
determinism, zero cost, zero latency, and a trust boundary that's a
reviewable JSON file instead of an LLM's behavior.

Audit surface: read `keywords` lists in feature_dictionary.json.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
FD_PATH = ROOT / "feature_dictionary.json"


def _normalize(text: str) -> str:
    # Lowercase; collapse whitespace; normalize hyphen-with-spaces forms
    # like "inter- agency" → "inter-agency" (matches the statute rendering).
    text = text.lower()
    text = re.sub(r"-\s+", "-", text)
    text = re.sub(r"\s+", " ", text)
    return text


def extract_features(description: str, fd: dict | None = None) -> dict[str, bool]:
    """Return {feature_name: bool} for every feature in feature_dictionary."""
    if fd is None:
        fd = json.loads(FD_PATH.read_text())
    norm = _normalize(description)
    out: dict[str, bool] = {}
    for key, meta in fd.items():
        kws = [k.lower() for k in meta.get("keywords", [])]
        neg = [k.lower() for k in meta.get("negative_keywords", [])]
        has_pos = any(kw in norm for kw in kws)
        has_neg = any(kw in norm for kw in neg)
        out[key] = has_pos and not has_neg
    return out


if __name__ == "__main__":
    import argparse, sys

    p = argparse.ArgumentParser(description="Extract features from a record description via keywords (no LLM).")
    p.add_argument("--file", type=Path, help="path to a text file; default: read stdin")
    args = p.parse_args()
    text = args.file.read_text() if args.file else sys.stdin.read()
    print(json.dumps(extract_features(text), indent=2))
