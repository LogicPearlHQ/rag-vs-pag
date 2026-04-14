from pathlib import Path

import pytest

from rag.retrieve import merge_hybrid


def test_merge_dedups_and_sums():
    bm25 = [("a", 10.0), ("b", 5.0), ("c", 1.0)]
    dense = [("b", 0.9), ("d", 0.8)]
    merged = merge_hybrid(bm25, dense)
    ids = [x[0] for x in merged]
    assert set(ids) == {"a", "b", "c", "d"}
    # shared entry 'b' has highest combined score (1.0 from each normalized side)
    scores = dict(merged)
    assert scores["b"] == pytest.approx(0.5 + 1.0, rel=0.01)


def test_merge_handles_empty_inputs():
    assert merge_hybrid([], []) == []
    assert [id_ for id_, _ in merge_hybrid([("x", 1.0)], [])] == ["x"]


@pytest.mark.skipif(
    not (Path(__file__).parent.parent / "rag" / "index" / "bm25.pkl").exists(),
    reason="indices not built — run `make index`",
)
def test_retrieve_returns_relevant_chunks_for_b5_query():
    from rag.retrieve import retrieve

    chunks = retrieve("Is a pre-decisional draft memo exempt under the deliberative process?", top_k=5)
    assert len(chunks) == 5
    # At least one retrieved chunk should mention deliberative/predecisional vocabulary.
    joined = " ".join(c.text.lower() for c in chunks)
    assert "deliberative" in joined or "pre-decisional" in joined or "predecisional" in joined


@pytest.mark.skipif(
    not (Path(__file__).parent.parent / "rag" / "index" / "bm25.pkl").exists(),
    reason="indices not built — run `make index`",
)
def test_retrieve_returns_relevant_chunks_for_b1_query():
    from rag.retrieve import retrieve

    chunks = retrieve("A memo classified TOP SECRET under an Executive Order", top_k=5)
    joined = " ".join(c.text.lower() for c in chunks)
    assert "classified" in joined or "executive order" in joined or "national security" in joined
