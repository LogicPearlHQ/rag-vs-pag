"""Scan DOJ Guide PDFs for substantive case discussions (V3, strict).

Pattern: find sentences where the case is grammatically the subject of
a court-outcome verb — "In <Case>, <court> <held|ruled|found|concluded>
that <X>." This filters out mere citations ("see X v. Y, NNN F.3d NNN")
and picks up the main-text discussion the Guide does of each precedent.

Emits JSON candidates to stdout. Quotes for cases.json still require
human review; the test suite enforces that every quote is a real
substring of the fetched PDF page.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).parent.parent
RAW = ROOT / "corpus" / "raw"

CHAPTERS = [
    ("doj_guide_exemption_1", "b1"),
    ("doj_guide_exemption_2", "b2"),
    ("doj_guide_exemption_3", "b3"),
    ("doj_guide_exemption_4", "b4"),
    ("doj_guide_exemption_5", "b5"),
    ("doj_guide_exemption_6", "b6"),
    ("doj_guide_exemption_7", "b7"),
    ("doj_guide_exemption_8", "b8"),
    ("doj_guide_exemption_9", "b9"),
]

# Sentence-level match. Two shapes:
#   A: "[In|The court in] <Case>, [clause] <verb> that [record desc]."
#   B: "<Case> <verb> that [record desc]." — case as subject
# The case-name capture goes up to the next comma, footnote digits, or
# " held/ruled/found" so we get full names like "Doe v. Veneman" not "Doe v. Ven".
CASE_NAME = (
    r"([A-Z][A-Za-z.\-'’ &]{1,60}?\s+v\.\s+"
    r"[A-Z][A-Za-z.\-'’ &0-9]{1,80}?)"
    r"(?=,|\d|\s+(?:held|ruled|found|concluded|determined|rejected|affirmed|upheld|reasoned|explained))"
)
VERBS = r"(?:held|ruled|found|concluded|determined|rejected|affirmed|upheld|reversed|required|recognized|confirmed|reasoned|established|explained|emphasized|refused)"

PATTERN_A = re.compile(
    rf"(?:[Ii]n|[Tt]he [Cc]ourt in)\s+{CASE_NAME}"
    rf"(?P<between>[^.]{{0,300}}?)"
    rf"(?P<verb>\b{VERBS}\b)"
    rf"(?P<rest>[^.]{{40,500}}\.)",
    re.S,
)
PATTERN_B = re.compile(
    rf"{CASE_NAME}"
    rf"(?P<between>[^.]{{0,120}}?)"
    rf"(?P<verb>\b{VERBS}\b)"
    rf"(?P<rest>[^.]{{40,500}}\.)",
    re.S,
)

# Parenthetical case summaries: "Case Name, Citation (holding/finding/
# protecting/rejecting description-of-records)".
# Very common in DOJ Guide footnotes — each is a self-contained case
# summary with a clear verb-ing + record description.
CASE_PAREN = re.compile(
    r"([A-Z][A-Za-z.\-'’ &]{1,60}?\s+v\.\s+[A-Z][A-Za-z.\-'’ &0-9]{1,80}?),\s*"
    r"\d{1,4}\s+[A-Z][A-Za-z.\d]{1,10}\.?\s*\d+[a-z]?(?:\s*[,-]\s*\d+[a-z]?)?"
    r"(?:\s*\([A-Za-z0-9.\-\s]{1,40}\))?\s*"
    r"\("
    r"(?P<verbing>holding|finding|protecting|rejecting|upholding|affirming|ruling|concluding|determining|applying|granting|denying|recognizing|reasoning|requiring)"
    r"\s+"
    r"(?P<paren>[^)]{40,400})"
    r"\)",
    re.S,
)

PAREN_EXEMPT = [
    "holding that", "upholding", "protecting", "finding that",
    "applying", "allowing", "granting",
]
PAREN_RELEASE = [
    "rejecting", "denying", "finding that exemption", "holding that exemption",
    "holding that the", "finding no", "concluding that no", "denying protection",
]


def _classify_paren(verbing: str, content: str) -> str | None:
    low = content.lower()
    # Clear release cues win.
    if any(cue in low for cue in [
        "not exempt", "not qualify", "not apply", "could not",
        "rejecting", "reversing", "not encompass", "not protect",
        "must be released", "must be disclosed", "not within",
        "not justify", "insufficient to",
    ]):
        return "release"
    if verbing in {"rejecting", "denying"}:
        return "release"
    if verbing in {"holding", "finding", "protecting", "upholding", "affirming", "applying", "granting", "recognizing"}:
        # These lean exempt unless the content says otherwise.
        if any(cue in low for cue in ["that exemption", "exempt", "withheld", "protected", "within", "properly"]):
            return "exempt"
        return "exempt"  # default lean for these verbs
    return None

EXEMPT_CUES = [
    "properly withheld", "were properly withheld", "was properly withheld",
    "properly invoked", "properly classified", "properly applied",
    "was properly exempt", "exempt from disclosure",
    "was protected", "properly protected",
    "upheld the agency", "upheld the withholding",
    "permitted to withhold", "could be withheld",
    "covered by exemption", "fell within exemption", "fall within exemption",
    "within the scope of exemption", "held to be exempt",
    "could be withheld", "within exemption",
]
RELEASE_CUES = [
    "not exempt", "does not apply", "did not apply",
    "does not qualify", "did not qualify",
    "could not be used", "did not encompass",
    "must be released", "must be disclosed",
    "rejected the agency", "failed to qualify",
    "cannot be withheld", "outside exemption",
    "outside the scope", "is not covered",
    "improperly withheld", "erroneously withheld",
    "could not withhold", "was not exempt", "were not exempt",
]


def _classify(text: str) -> str | None:
    low = text.lower()
    e = any(cue in low for cue in EXEMPT_CUES)
    r = any(cue in low for cue in RELEASE_CUES)
    if e and not r:
        return "exempt"
    if r and not e:
        return "release"
    return None


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def scan_chapter(doc_id: str, chapter_label: str) -> list[dict]:
    path = RAW / f"{doc_id}.bin"
    if not path.exists():
        return []
    reader = PdfReader(str(path))
    out: list[dict] = []
    seen: set[tuple[int, str]] = set()

    for page_idx in range(1, len(reader.pages) + 1):
        text = _norm(reader.pages[page_idx - 1].extract_text() or "")

        # Parenthetical case summaries (rich in Guide footnotes).
        for m in CASE_PAREN.finditer(text):
            case_name = m.group(1).strip().rstrip(",. ")
            if len(case_name) < 8:
                continue
            key = (page_idx, case_name.lower())
            if key in seen:
                continue
            classification = _classify_paren(m.group("verbing"), m.group("paren"))
            if classification is None:
                continue
            seen.add(key)
            gold = chapter_label if classification == "exempt" else "releasable"
            out.append(
                {
                    "case_name": case_name,
                    "source_doc": doc_id,
                    "source_page": page_idx,
                    "full_sentence": m.group(0),
                    "record_description_candidate": m.group("paren").strip(),
                    "suggested_gold_exemption": gold,
                    "classification_cue": classification,
                    "pattern": "P",
                }
            )

        for pattern_name, pattern in [("A", PATTERN_A), ("B", PATTERN_B)]:
            for m in pattern.finditer(text):
                case_name = m.group(1).strip().rstrip(",. ")
                if len(case_name) < 8:
                    continue
                key = (page_idx, case_name.lower())
                if key in seen:
                    continue
                seen.add(key)

                full = m.group(0)
                classification = _classify(full)
                if classification is None:
                    continue
                gold = chapter_label if classification == "exempt" else "releasable"

                between = m.group("between").strip().lstrip(",").strip()

                out.append(
                    {
                        "case_name": case_name,
                        "source_doc": doc_id,
                        "source_page": page_idx,
                        "full_sentence": full,
                        "record_description_candidate": between,
                        "suggested_gold_exemption": gold,
                        "classification_cue": classification,
                        "pattern": pattern_name,
                    }
                )
    return out


def main() -> int:
    results: list[dict] = []
    for doc_id, label in CHAPTERS:
        hits = scan_chapter(doc_id, label)
        print(f"{doc_id}: {len(hits)}", file=sys.stderr)
        results.extend(hits)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
