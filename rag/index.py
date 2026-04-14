"""One-time RAG indexing: chunk the corpus, build Chroma + BM25."""
from __future__ import annotations

import os
import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi

from ragdemo.corpus import Chunk, load_corpus

ROOT = Path(__file__).parent
PROJECT = ROOT.parent
INDEX = ROOT / "index"
BM25_PATH = INDEX / "bm25.pkl"
CHROMA_DIR = INDEX / "chroma"


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in text.split() if len(t) > 1 and t.isalnum()]


def build_bm25(chunks: list[Chunk]) -> tuple[BM25Okapi, list[str]]:
    tokens = [tokenize(c.text) for c in chunks]
    ids = [c.metadata.get("cite", f"chunk_{i}") for i, c in enumerate(chunks)]
    return BM25Okapi(tokens), ids


def _embedding_function():
    provider = os.environ.get("LP_EMBEDDING_PROVIDER", "openai")
    from chromadb.utils import embedding_functions

    if provider == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set; set LP_EMBEDDING_PROVIDER=sentence_transformers for offline")
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=key,
            model_name=os.environ.get("LP_EMBEDDING_MODEL", "text-embedding-3-small"),
        )
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=os.environ.get("LP_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    )


def build_chroma(chunks: list[Chunk]):
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    # Drop any existing collection to rebuild cleanly.
    try:
        client.delete_collection("foia")
    except Exception:
        pass
    col = client.create_collection("foia", embedding_function=_embedding_function())

    # Chroma accepts only primitive metadata values.
    def flatten_meta(m: dict) -> dict:
        return {k: v for k, v in m.items() if isinstance(v, (str, int, float, bool))}

    # Batch to stay under provider request limits.
    BATCH = 96
    for i in range(0, len(chunks), BATCH):
        batch = chunks[i : i + BATCH]
        col.add(
            ids=[f"c{i+j}" for j in range(len(batch))],
            documents=[c.text[:8000] for c in batch],  # embedding input cap
            metadatas=[flatten_meta(c.metadata) for c in batch],
        )
    return col


def main() -> int:
    raw = PROJECT / "corpus" / "raw"
    chunks = load_corpus(raw)
    print(f"loaded {len(chunks)} chunks from {raw}")
    INDEX.mkdir(exist_ok=True)

    bm25, ids = build_bm25(chunks)
    with BM25_PATH.open("wb") as f:
        pickle.dump({"bm25": bm25, "chunks": chunks}, f)
    print(f"bm25 index written: {BM25_PATH}")

    build_chroma(chunks)
    print(f"chroma index written: {CHROMA_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
