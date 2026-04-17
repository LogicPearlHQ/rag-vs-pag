from __future__ import annotations

from rag_vs_pag.retrieval_core import parse_authority_text, retrieve


def test_retrieve_finds_b7_chunk() -> None:
    chunks = parse_authority_text(
        "SOURCE foia_b7\nTITLE b7\nlaw enforcement investigation records\n"
        "SOURCE foia_b4\nTITLE b4\ntrade secrets\n"
    )
    rows = retrieve("law enforcement investigation", chunks, k=1)
    assert rows[0]["source_id"] == "foia_b7"
