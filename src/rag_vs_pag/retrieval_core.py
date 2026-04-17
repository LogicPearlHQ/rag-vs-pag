from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from rag_vs_pag.text import words


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_id: str
    title: str
    text: str

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "Chunk":
        return cls(
            chunk_id=str(row["chunk_id"]),
            source_id=str(row["source_id"]),
            title=str(row["title"]),
            text=str(row["text"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "source_id": self.source_id,
            "title": self.title,
            "text": self.text,
        }


def parse_authority_text(text: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    source_id = ""
    title = ""
    body: list[str] = []

    def flush() -> None:
        if source_id and body:
            chunks.append(
                Chunk(
                    chunk_id=f"c{len(chunks) + 1}",
                    source_id=source_id,
                    title=title,
                    text="\n".join(body).strip(),
                )
            )

    for line in text.splitlines():
        if line.startswith("SOURCE "):
            flush()
            source_id = line.removeprefix("SOURCE ").strip()
            title = ""
            body = []
        elif line.startswith("TITLE "):
            title = line.removeprefix("TITLE ").strip()
        elif line.strip():
            body.append(line.strip())
    flush()
    return chunks


def retrieve(query: str, chunks: list[Chunk], k: int = 4) -> list[dict[str, Any]]:
    query_terms = words(query)
    if not query_terms:
        return []
    doc_terms = [words(chunk.text + " " + chunk.title) for chunk in chunks]
    document_frequency: dict[str, int] = {}
    for terms in doc_terms:
        for term in set(terms):
            document_frequency[term] = document_frequency.get(term, 0) + 1
    total_docs = max(len(chunks), 1)
    scored: list[tuple[float, Chunk]] = []
    for chunk, terms in zip(chunks, doc_terms):
        term_counts: dict[str, int] = {}
        for term in terms:
            term_counts[term] = term_counts.get(term, 0) + 1
        score = 0.0
        for term in query_terms:
            tf = term_counts.get(term, 0)
            if not tf:
                continue
            df = document_frequency.get(term, 1)
            score += (1.0 + math.log(tf)) * math.log((total_docs + 1) / df)
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
    return [
        {
            **chunk.to_dict(),
            "score": round(score, 6),
        }
        for score, chunk in scored[:k]
    ]
