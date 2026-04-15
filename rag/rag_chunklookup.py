"""RAG with chunk-ID citation indirection (Anthropic Citations pattern).

Same retrieval + reasoning as rag/rag.py, but the LLM emits chunk IDs
instead of writing excerpt text. The backend looks up each referenced
chunk in the retrieval store and fills the excerpt from the real chunk
bytes. If the LLM references a chunk ID that isn't in the retrieval
result, that citation is dropped rather than trusted.

This pipeline does NOT use LogicPearl. Its purpose is to isolate the
effect of the citation-lookup architecture from the pearl's
contribution — to answer "does the citation-integrity win come from
the architecture alone, or from LogicPearl specifically?"
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from ragdemo.corpus import Chunk
from ragdemo.llm import LLMConfig, make_llm
from ragdemo.scenarios import load_scenario

from .retrieve import retrieve

ANSWER_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "exemption": {
            "type": "string",
            "enum": [
                "b1", "b2", "b3", "b4", "b5", "b6", "b7", "b8", "b9",
                "releasable", "insufficient_context", "not_applicable",
            ],
        },
        "releasable": {"type": "boolean"},
        "rationale": {"type": "string"},
        "cited_chunk_ids": {
            "type": "array",
            "items": {"type": "string"},
            "description": "IDs of retrieved chunks that support this answer. Do not invent IDs not shown in the retrieved context.",
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["exemption", "releasable", "rationale", "cited_chunk_ids", "confidence"],
}

SYSTEM_PROMPT = """You are a FOIA analyst. Given the retrieved statutory, regulatory, and guidance excerpts below — each prefixed with an ID like [c17] — determine whether the described record is exempt under 5 U.S.C. § 552(b), and under which subsection. If the record is releasable, use "releasable". If the request is an open-ended synthesis task, use "not_applicable".

You MUST cite supporting chunks by ID ONLY. Reference them as strings in `cited_chunk_ids` (e.g., ["c17", "c42"]). DO NOT write excerpt text — the backend will look up each chunk by ID and fill in the real text. DO NOT invent chunk IDs that were not in the retrieved context.

If the retrieved context does not clearly support a confident answer, respond with exemption="insufficient_context", cited_chunk_ids=[], and confidence="low"."""


def answer(scenario_path: Path, llm_cfg: LLMConfig) -> dict:
    s = load_scenario(scenario_path)
    t0 = time.time()
    chunks = retrieve(s.description, top_k=8)
    t_retrieve = time.time() - t0

    # Assign stable IDs to each retrieved chunk for this scenario.
    id_to_chunk: dict[str, Chunk] = {f"c{i+1}": c for i, c in enumerate(chunks)}
    blob = "\n\n".join(
        f"[{cid}] cite={c.metadata.get('cite', '(unknown)')}\n{c.text[:1200]}"
        for cid, c in id_to_chunk.items()
    )

    llm = make_llm(llm_cfg)
    user = f"RECORD DESCRIPTION:\n{s.description}\n\nRETRIEVED EXCERPTS (each prefixed with a chunk ID):\n{blob}"

    t1 = time.time()
    result = llm.chat_json(
        system=SYSTEM_PROMPT, user=user, schema=ANSWER_SCHEMA, temperature=0.0
    )
    t_llm = time.time() - t1

    # Resolve chunk IDs → real cite+excerpt from retrieval. Drop any ID the
    # LLM made up (not in id_to_chunk).
    cited_authorities: list[dict] = []
    invalid_ids: list[str] = []
    for cid in result.get("cited_chunk_ids", []):
        chunk = id_to_chunk.get(cid)
        if chunk is None:
            invalid_ids.append(cid)
            continue
        cited_authorities.append({
            "cite": chunk.metadata.get("cite", "(unknown)"),
            "excerpt": chunk.text[:400],  # first 400 chars — real bytes
            "chunk_id": cid,
        })

    out = {
        "exemption": result["exemption"],
        "releasable": result["releasable"],
        "rationale": result["rationale"],
        "cited_authorities": cited_authorities,
        "confidence": result["confidence"],
        "_latency_s": {"retrieve": round(t_retrieve, 3), "llm": round(t_llm, 3)},
        "_retrieved_cites": [c.metadata.get("cite") for c in chunks],
        "_invalid_cite_ids": invalid_ids,
        # All cites are lookups, so they're faithful by construction.
        # Matching rag/rag.py's shape for compare.py:
        "_citation_faithfulness": [
            {"cite": a["cite"], "excerpt_first_60": a["excerpt"][:60], "ok": True}
            for a in cited_authorities
        ],
    }
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("scenario", type=Path)
    p.add_argument("--provider", default=os.environ.get("LP_LLM_PROVIDER", "openai"))
    p.add_argument("--model", default=os.environ.get("LP_LLM_MODEL", "gpt-4o"))
    args = p.parse_args()
    cfg = LLMConfig(provider=args.provider, model=args.model)
    print(json.dumps(answer(args.scenario, cfg), indent=2))


if __name__ == "__main__":
    main()
