"""Generate pearl/traces.csv by extracting from the real statute corpus.

Inputs:
  corpus/raw/5_usc_552.bin OR corpus/snapshot/5_usc_552.txt — verified statute text
  pearl/feature_dictionary.json — feature names + pinpoint cites into § 552(b)
  pearl/statute_structure.json — element groupings per exemption, each with a
                                 VERBATIM QUOTE from the statute

Output:
  pearl/traces.csv — the training set, deterministically derived

Design:

The pearl's trust boundary is the feature dictionary + the statute structure
file. Both are reviewed against verbatim statute text:

  - feature_dictionary.json names features and cites the clauses they encode.
  - statute_structure.json names element groupings per exemption. Each group
    carries a VERBATIM QUOTE from § 552(b). This generator asserts every such
    quote appears as a substring of the fetched statute (whitespace-normalized).
    A drift makes the generator fail-fast.

Given the validated inputs, the generator emits:

  1. One exemplar row per element group. All features in the group are TRUE;
     everything else is FALSE. Label = "b{N}". Source = the pinpoint cite.
     Note = first 200 chars of the quoted clause.

  2. Releasable controls: all-FALSE baseline (label = releasable). Plus, for
     every element group that has >1 features, a row with all-FALSE
     (controlled by default_action). We intentionally do NOT emit "partial"
     rows where one feature of a conjunctive group is TRUE alone, because
     that would conflict with single-feature rules the learner tends to
     discover; the user-facing policy is "the exemption applies when its
     statute-named elements are ALL present" and nothing else.

No row is hand-typed. The generator is idempotent.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
PROJECT = ROOT.parent
FD_PATH = ROOT / "feature_dictionary.json"
STRUCTURE_PATH = ROOT / "statute_structure.json"
TRACES = ROOT / "traces.csv"
STATUTE_RAW = PROJECT / "corpus" / "raw" / "5_usc_552.bin"
STATUTE_SNAPSHOT = PROJECT / "corpus" / "snapshot" / "5_usc_552.txt"


def _load_statute_text() -> str:
    """Prefer the fetched corpus; fall back to the committed snapshot."""
    if STATUTE_RAW.exists():
        from ragdemo.corpus import _html_to_text

        return _html_to_text(STATUTE_RAW.read_bytes())
    return STATUTE_SNAPSHOT.read_text()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def extract_exemption_paragraphs(statute_text: str) -> dict[int, str]:
    """Return {N: verbatim_paragraph_text} for the nine (b)(N) paragraphs."""
    b_start = statute_text.find("(b) This section does not apply")
    if b_start < 0:
        raise RuntimeError("could not find (b) subsection in statute text")
    b_end = statute_text.find("(c)", b_start + 5)
    block = statute_text[b_start:b_end] if b_end > 0 else statute_text[b_start:]

    markers = [
        (m.start(), int(m.group(1)))
        for m in re.finditer(r"(?m)^\((\d)\)\s", block)
        if 1 <= int(m.group(1)) <= 9
    ]
    out: dict[int, str] = {}
    for i, (pos, n) in enumerate(markers):
        end = markers[i + 1][0] if i + 1 < len(markers) else len(block)
        out[n] = block[pos:end].strip()
    missing = [n for n in range(1, 10) if n not in out]
    if missing:
        raise RuntimeError(f"statute parse missed exemptions: {missing}")
    return out


def verify_structure_against_statute(
    structure: dict, statute_text: str, fd: dict
) -> list[str]:
    """Return a list of verification error strings; empty means OK."""
    normalized_statute = _norm(statute_text)
    errors: list[str] = []
    for key, entry in structure.items():
        if key.startswith("_"):
            continue
        if key == "releasable_patterns":
            for i, p in enumerate(entry.get("patterns", [])):
                for f in p.get("features", []):
                    if f not in fd:
                        errors.append(f"releasable_patterns[{i}]: unknown feature {f!r}")
                quote = p.get("quote", "")
                if not quote:
                    errors.append(f"releasable_patterns[{i}]: empty quote")
                    continue
                if _norm(quote) not in normalized_statute:
                    errors.append(
                        f"releasable_patterns[{i}]: quote not found in statute text (drift or typo)"
                    )
            continue
        if not re.match(r"^b[1-9]$", key):
            errors.append(f"unknown exemption key: {key}")
            continue
        groups = entry.get("groups") or []
        if not groups:
            errors.append(f"{key}: no groups defined")
            continue
        for i, g in enumerate(groups):
            feats = g.get("features") or []
            for f in feats:
                if f not in fd:
                    errors.append(f"{key}.groups[{i}]: unknown feature {f!r}")
            quote = g.get("quote", "")
            if not quote:
                errors.append(f"{key}.groups[{i}]: empty quote")
                continue
            if _norm(quote) not in normalized_statute:
                errors.append(
                    f"{key}.groups[{i}]: quote not found in statute text (drift or typo)"
                )
    return errors


def _row(positive: set[str], feature_order: list[str], label: str, source: str, note: str) -> list[str]:
    return [
        "true" if f in positive else "false" for f in feature_order
    ] + [label, source, note]


def generate_rows() -> list[list[str]]:
    fd = json.loads(FD_PATH.read_text())
    structure = json.loads(STRUCTURE_PATH.read_text())
    statute = _load_statute_text()
    paragraphs = extract_exemption_paragraphs(statute)

    errors = verify_structure_against_statute(structure, statute, fd)
    if errors:
        raise RuntimeError(
            "statute_structure.json failed verification:\n  - "
            + "\n  - ".join(errors)
        )

    feature_order = list(fd.keys())
    header = feature_order + ["exemption", "source", "note"]
    rows: list[list[str]] = [header]

    # One exemplar per element group.
    for key in sorted(structure):
        if key.startswith("_") or key == "releasable_patterns":
            continue
        n = int(key[1:])
        cite = f"5 U.S.C. § 552(b)({n})"
        groups = structure[key]["groups"]
        for g in groups:
            pos = set(g["features"])
            quote = g["quote"]
            note = quote if len(quote) <= 200 else quote[:197] + "..."
            rows.append(_row(pos, feature_order, key, cite, note))

    # Releasable baseline (all features false).
    rows.append(
        _row(
            set(),
            feature_order,
            "releasable",
            "5 U.S.C. § 552(a)",
            "No (b)(N) element present — baseline releasable.",
        )
    )

    # Statute-grounded releasable inverses: a single element of a multi-element
    # exemption present without its co-elements is not sufficient to trigger
    # the exemption. The statute's own language for the co-element (quoted
    # verbatim in statute_structure.json) backs each of these rows.
    for p in structure.get("releasable_patterns", {}).get("patterns", []):
        pos = set(p["features"])
        quote = p["quote"]
        note = (
            f"{p['description']} — co-requirement absent: {quote}"
            if len(f"{p['description']} — co-requirement absent: {quote}") <= 220
            else f"{p['description']} — co-requirement absent"
        )
        rows.append(_row(pos, feature_order, "releasable", p["cite"], note))

    return rows


def main() -> int:
    rows = generate_rows()
    with TRACES.open("w", newline="") as f:
        csv.writer(f).writerows(rows)
    print(f"wrote {TRACES}  ({len(rows) - 1} data rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
