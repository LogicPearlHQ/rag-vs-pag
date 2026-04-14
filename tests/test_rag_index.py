from ragdemo.corpus import Chunk
from rag.index import build_bm25, tokenize


def test_tokenize_lowercases_and_filters_short():
    toks = tokenize("The Deliberative PROCESS privilege")
    assert "deliberative" in toks
    assert "privilege" in toks
    assert "process" in toks
    assert "the" in toks  # 3-letter word, kept


def test_bm25_ranks_keyword_match_first():
    chunks = [
        Chunk("pre-decisional deliberative process privilege protects memos", {"cite": "b5"}),
        Chunk("classified national security information executive order", {"cite": "b1"}),
        Chunk("personnel medical files unwarranted invasion privacy", {"cite": "b6"}),
    ]
    bm25, ids = build_bm25(chunks)
    scores = bm25.get_scores(tokenize("deliberative process privilege"))
    # First chunk should dominate.
    assert scores[0] > scores[1]
    assert scores[0] > scores[2]


def test_bm25_ids_match_chunk_order():
    chunks = [Chunk("alpha beta gamma", {"cite": "x"}), Chunk("delta epsilon zeta", {"cite": "y"})]
    _, ids = build_bm25(chunks)
    assert ids == ["x", "y"]
