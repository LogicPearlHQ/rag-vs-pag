from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag_vs_pag.jsonio import read_json, write_json


PATTERNS = [
    re.compile(r"exemptions?\s*(?:\(?b\)?\s*)?\(?([1-9])\)?", re.I),
    re.compile(r"exemptions?\s+b([1-9])", re.I),
    re.compile(r"(?:5\s*)?u\.?s\.?c\.?\s*§?\s*552\s*\(b\)\(([1-9])\)", re.I),
    re.compile(r"§\s*552\s*\(b\)\(([1-9])\)", re.I),
    re.compile(r"foia\s+exemptions?\s*\(b\)\(([1-9])\)", re.I),
]

BARE_B_PATTERN = re.compile(r"\(b\)\(([1-9])\)", re.I)
NON_EXEMPTION_CONTEXT = re.compile(r"(?:c\.?f\.?r\.?|16\.10|fee|commercial use request)", re.I)
EXEMPTION_CONTEXT = re.compile(r"(?:foia|exemption|withheld|withhold|redact|552|u\.?s\.?c\.?)", re.I)


def extract_exemptions(text: str) -> list[str]:
    hits: list[tuple[int, str]] = []
    for pattern in PATTERNS:
        for match in pattern.finditer(text):
            hits.append((match.start(), f"b{match.group(1)}"))
    for match in BARE_B_PATTERN.finditer(text):
        start = match.start()
        before = text[max(0, start - 90):start]
        after = text[start:start + 60]
        context = before + after
        if NON_EXEMPTION_CONTEXT.search(context):
            continue
        if EXEMPTION_CONTEXT.search(context):
            hits.append((start, f"b{match.group(1)}"))
    exemptions: list[str] = []
    seen: set[str] = set()
    for start, exemption in sorted(hits):
        _ = start
        if exemption in seen:
            continue
        seen.add(exemption)
        exemptions.append(exemption)
    return exemptions


def label_record(record: dict) -> dict:
    exemptions = extract_exemptions(record.get("response_text", ""))
    distinct = []
    for exemption in exemptions:
        if exemption not in distinct:
            distinct.append(exemption)
    if distinct:
        record["primary_exemption"] = distinct[0]
        record["all_cited_exemptions"] = distinct
        record["extraction_confidence"] = "regex"
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    rows = [label_record(dict(row)) for row in read_json(args.input)]
    write_json(args.output, rows)


if __name__ == "__main__":
    main()
