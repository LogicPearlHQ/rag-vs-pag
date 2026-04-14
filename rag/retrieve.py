"""Hybrid retrieval: BM25 ∪ dense → rerank → top-k.

BM25 and dense similarity are both imperfect proxies for relevance. Taking
the union of their top-20s and then re-ranking with a small cross-encoder
is what most production legal RAG systems do — and what this demo must do
to give the RAG side a fair shot against the pearl.
"""
from __future__ import annotations

import functools
import pickle
from pathlib import Path

from ragdemo.corpus import Chunk

from .index import BM25_PATH, CHROMA_DIR, tokenize


def merge_hybrid(
    bm25_hits: list[tuple[str, float]], dense_hits: list[tuple[str, float]]
) -> list[tuple[str, float]]:
    """Normalize each list to [0,1], take union, sum scores for shared ids."""
    def _norm(hits: list[tuple[str, float]]) -> dict[str, float]:
        if not hits:
            return {}
        peak = max(s for _, s in hits)
        peak = peak if peak != 0 else 1.0
        return {id_: score / peak for id_, score in hits}

    a, b = _norm(bm25_hits), _norm(dense_hits)
    combined = {k: a.get(k, 0.0) + b.get(k, 0.0) for k in set(a) | set(b)}
    return sorted(combined.items(), key=lambda x: -x[1])


@functools.lru_cache(maxsize=1)
def _bm25_state():
    with BM25_PATH.open("rb") as f:
        d = pickle.load(f)
    return d["bm25"], d["chunks"]


@functools.lru_cache(maxsize=1)
def _chroma_collection():
    import chromadb

    from .index import _embedding_function

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection("foia", embedding_function=_embedding_function())


@functools.lru_cache(maxsize=1)
def _cross_encoder():
    from sentence_transformers import CrossEncoder

    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def retrieve(query: str, top_k: int = 8, pool: int = 20) -> list[Chunk]:
    bm25, chunks = _bm25_state()
    scores = bm25.get_scores(tokenize(query))
    bm25_hits = sorted(
        ((f"c{i}", float(s)) for i, s in enumerate(scores)),
        key=lambda x: -x[1],
    )[:pool]

    col = _chroma_collection()
    res = col.query(query_texts=[query], n_results=pool)
    ids = res["ids"][0]
    dists = res["distances"][0] if res["distances"] else [0.0] * len(ids)
    dense_hits = [(id_, 1.0 - float(d)) for id_, d in zip(ids, dists)]

    merged = merge_hybrid(bm25_hits, dense_hits)[: pool + 10]

    id_to_chunk = {f"c{i}": c for i, c in enumerate(chunks)}
    candidates = [id_to_chunk[id_] for id_, _ in merged if id_ in id_to_chunk]
    if not candidates:
        return []

    ce = _cross_encoder()
    pairs = [[query, c.text[:2000]] for c in candidates]
    scores = ce.predict(pairs)
    ranked = sorted(zip(candidates, scores), key=lambda x: -float(x[1]))[:top_k]
    return [c for c, _ in ranked]
