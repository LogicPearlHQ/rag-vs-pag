from pathlib import Path

import pytest

from ragdemo.corpus import (
    chunk_case,
    chunk_cfr,
    chunk_doj_guide_pdf,
    load_corpus,
)

RAW = Path(__file__).parent.parent / "corpus" / "raw"


def test_chunk_cfr_splits_by_section_with_cite_metadata():
    text = (
        "§ 16.1 Scope and purpose.\n"
        "This part sets forth rules.\n\n"
        "§ 16.2 Definitions.\n"
        "As used in this subpart:\n"
        "Record includes all physical records.\n"
    )
    chunks = chunk_cfr(text, doc_id="28_cfr_16")
    assert len(chunks) == 2
    assert chunks[0].metadata["cite"] == "28 C.F.R. § 16.1"
    assert chunks[1].metadata["cite"] == "28 C.F.R. § 16.2"


def test_chunk_case_emits_paragraphs_with_cite():
    text = (
        "Justice OPINION.\n\n"
        "The issue in this case concerns the deliberative process privilege "
        "and its application to pre-decisional memoranda prepared by agency "
        "staff.\n\n"
        "We hold that such memoranda fall within Exemption 5 when they are "
        "both pre-decisional and deliberative. The government bears the "
        "burden of demonstrating both prongs.\n"
    )
    chunks = chunk_case(text, doc_id="nlrb", cite_root="NLRB v. Sears")
    assert len(chunks) >= 2
    assert chunks[0].metadata["cite"].startswith("NLRB v. Sears")


@pytest.mark.skipif(
    not (RAW / "doj_guide_exemption_5.bin").exists(),
    reason="requires `make fetch` first",
)
def test_chunk_doj_guide_real_pdf_yields_pages():
    path = RAW / "doj_guide_exemption_5.bin"
    chunks = chunk_doj_guide_pdf(path, doc_id="doj_guide_exemption_5", cite_root="DOJ FOIA Guide, Exemption 5")
    assert len(chunks) >= 5
    # Each chunk carries a page cite.
    for c in chunks:
        assert c.metadata["cite"].startswith("DOJ FOIA Guide, Exemption 5, p. ")
        assert isinstance(c.metadata["page"], int)


@pytest.mark.skipif(
    not (RAW / "MANIFEST.json").exists(),
    reason="requires `make fetch` first",
)
def test_load_corpus_integrates_all_kinds():
    chunks = load_corpus(RAW)
    # Expect statute + CFR sections + DOJ Guide pages. Loose lower bound.
    assert len(chunks) > 50
    sources = {c.metadata["source"] for c in chunks}
    assert "5_usc_552" in sources
    assert "28_cfr_16" in sources
    # At least a few DOJ Guide chapters came through.
    doj = {s for s in sources if s.startswith("doj_guide_")}
    assert len(doj) >= 5
    # Every chunk has a cite.
    assert all(c.metadata.get("cite") for c in chunks)
