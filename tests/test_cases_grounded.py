"""Every case in scenarios/cases.json must be grounded in the fetched corpus.

For each entry, load the referenced DOJ Guide PDF, extract the text of
its named page, and assert both the record_description_quote and the
outcome_quote appear as substrings (after whitespace normalization).

If a quote drifts from the real Guide text — typo, OCR artifact, or an
author's paraphrase slipping in — this test fails. That's the same
trust pattern statute_structure.json uses for § 552(b) quotes.
"""
from __future__ import annotations

import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).parent.parent
CASES = ROOT / "scenarios" / "cases.json"
RAW = ROOT / "corpus" / "raw"


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


@lru_cache(maxsize=32)
def _page_text(doc_id: str, page: int) -> str:
    path = RAW / f"{doc_id}.bin"
    if not path.exists():
        pytest.skip(f"corpus doc {doc_id} not fetched; run `make fetch`")
    reader = PdfReader(str(path))
    # DOJ Guide pages are 1-indexed in the cases.json file.
    if page < 1 or page > len(reader.pages):
        return ""
    return reader.pages[page - 1].extract_text() or ""


def _load_cases() -> list[dict]:
    return json.loads(CASES.read_text()).get("cases", [])


def test_cases_file_loads():
    cases = _load_cases()
    assert cases, "scenarios/cases.json must contain at least one case"


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["case_id"])
def test_record_description_quote_appears_in_source_pdf(case):
    text = _norm(_page_text(case["source_doc"], case["source_page"]))
    quote = _norm(case["record_description_quote"])
    assert quote in text, (
        f"{case['case_id']}: record_description_quote not found in "
        f"{case['source_doc']} p.{case['source_page']}. First 100 chars of "
        f"page text: {text[:100]!r}"
    )


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["case_id"])
def test_outcome_quote_appears_in_source_pdf(case):
    text = _norm(_page_text(case["source_doc"], case["source_page"]))
    quote = _norm(case["outcome_quote"])
    assert quote in text, (
        f"{case['case_id']}: outcome_quote not found in "
        f"{case['source_doc']} p.{case['source_page']}."
    )


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["case_id"])
def test_gold_label_is_valid(case):
    allowed = {f"b{i}" for i in range(1, 10)} | {"releasable"}
    assert case["gold_exemption"] in allowed, case


def test_generator_emits_one_file_per_case(tmp_path, monkeypatch):
    import scenarios.generate_scenarios as gen

    monkeypatch.setattr(gen, "OUT_DIR", tmp_path)
    gen.main()
    assert len(list(tmp_path.glob("*.json"))) == len(_load_cases())


def test_generator_is_idempotent():
    subprocess.run(
        ["uv", "run", "python", "-m", "scenarios.generate_scenarios"],
        cwd=ROOT, check=True, capture_output=True,
    )
    first = {p.name: p.read_text() for p in (ROOT / "scenarios" / "cases").glob("*.json")}
    subprocess.run(
        ["uv", "run", "python", "-m", "scenarios.generate_scenarios"],
        cwd=ROOT, check=True, capture_output=True,
    )
    second = {p.name: p.read_text() for p in (ROOT / "scenarios" / "cases").glob("*.json")}
    assert first == second, "generate_scenarios is not idempotent"
