from __future__ import annotations

from pathlib import Path
from typing import Any

from rag_vs_pag.hashutil import canonical_hash, sha256_text
from rag_vs_pag.jsonio import read_json, write_json
from rag_vs_pag.openai_structured import responses_json_schema
from rag_vs_pag.schema import VERDICTS


BASELINE_PROMPT_VERSION = "rag_vs_pag.real_llm_baselines.v1"


def feature_text(shared_features: dict[str, bool] | None) -> str:
    if shared_features is None:
        return "No shared feature vector was provided. Classify from request text and retrieved authority only."
    enabled = [name for name, value in sorted(shared_features.items()) if value]
    if not enabled:
        return "Shared feature vector: no features are true."
    return "Shared true features:\n" + "\n".join(f"- {name}" for name in enabled)


def chunks_text(retrieved: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for chunk in retrieved:
        lines.extend(
            [
                f"CHUNK_ID: {chunk['chunk_id']}",
                f"SOURCE_ID: {chunk['source_id']}",
                f"TITLE: {chunk['title']}",
                f"TEXT: {chunk['text']}",
                "",
            ]
        )
    return "\n".join(lines).strip()


def cache_key(
    *,
    pipeline: str,
    track: str,
    request_text: str,
    agency_name: str,
    model: str,
    retrieved: list[dict[str, Any]],
    shared_features: dict[str, bool] | None,
) -> str:
    return canonical_hash(
        {
            "schema_version": BASELINE_PROMPT_VERSION,
            "pipeline": pipeline,
            "track": track,
            "request_text_hash": sha256_text(request_text),
            "agency_name": agency_name,
            "model": model,
            "retrieved": [
                {
                    "chunk_id": chunk["chunk_id"],
                    "source_id": chunk["source_id"],
                    "text_hash": sha256_text(chunk["text"]),
                }
                for chunk in retrieved
            ],
            "shared_features": shared_features,
        }
    ).removeprefix("sha256:")


def verdict_enum() -> list[str]:
    return sorted(VERDICTS)


def rag_schema(retrieved: list[dict[str, Any]]) -> dict[str, Any]:
    chunk_ids = [chunk["chunk_id"] for chunk in retrieved]
    source_ids = sorted({chunk["source_id"] for chunk in retrieved})
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "verdict": {"type": "string", "enum": verdict_enum()},
            "rationale": {"type": "string"},
            "cited_authorities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "chunk_id": {"type": "string", "enum": chunk_ids},
                        "source_id": {"type": "string", "enum": source_ids},
                        "cite": {"type": "string"},
                        "excerpt": {"type": "string"},
                    },
                    "required": ["chunk_id", "source_id", "cite", "excerpt"],
                },
            },
        },
        "required": ["verdict", "rationale", "cited_authorities"],
    }


def chunklookup_schema(retrieved: list[dict[str, Any]]) -> dict[str, Any]:
    chunk_ids = [chunk["chunk_id"] for chunk in retrieved]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "verdict": {"type": "string", "enum": verdict_enum()},
            "rationale": {"type": "string"},
            "cited_chunk_ids": {
                "type": "array",
                "items": {"type": "string", "enum": chunk_ids},
            },
        },
        "required": ["verdict", "rationale", "cited_chunk_ids"],
    }


def rag_messages(
    *,
    request_text: str,
    agency_name: str,
    retrieved: list[dict[str, Any]],
    shared_features: dict[str, bool] | None,
) -> tuple[str, str]:
    system = (
        "You are a FOIA exemption classification baseline. Choose the most likely "
        "FOIA exemption verdict from the allowed enum using the request, optional "
        "shared facts, and retrieved authority chunks. If the request text and "
        "facts do not support an exemption-shaped classification, return "
        "`insufficient_facts`. For plain RAG, you may write short cited excerpts, "
        "but excerpts must be copied exactly from one retrieved chunk."
    )
    user = (
        f"Agency: {agency_name}\n\n"
        f"Request text:\n{request_text}\n\n"
        f"{feature_text(shared_features)}\n\n"
        "Retrieved authority chunks:\n"
        f"{chunks_text(retrieved)}\n\n"
        "Return JSON only."
    )
    return system, user


def chunklookup_messages(
    *,
    request_text: str,
    agency_name: str,
    retrieved: list[dict[str, Any]],
    shared_features: dict[str, bool] | None,
) -> tuple[str, str]:
    system = (
        "You are a FOIA exemption classification baseline using chunk lookup. "
        "Choose the most likely FOIA exemption verdict from the allowed enum using "
        "the request, optional shared facts, and retrieved authority chunks. If the "
        "request text and facts do not support an exemption-shaped classification, "
        "return `insufficient_facts`. Do not write quote text. Cite only chunk IDs "
        "from the retrieved chunks; the application will resolve citation text."
    )
    user = (
        f"Agency: {agency_name}\n\n"
        f"Request text:\n{request_text}\n\n"
        f"{feature_text(shared_features)}\n\n"
        "Retrieved authority chunks:\n"
        f"{chunks_text(retrieved)}\n\n"
        "Return JSON only."
    )
    return system, user


def call_openai_baseline(
    *,
    pipeline: str,
    track: str,
    request_text: str,
    agency_name: str,
    retrieved: list[dict[str, Any]],
    shared_features: dict[str, bool] | None,
    model: str,
    cache_dir: str | Path,
    force: bool = False,
) -> dict[str, Any]:
    key = cache_key(
        pipeline=pipeline,
        track=track,
        request_text=request_text,
        agency_name=agency_name,
        model=model,
        retrieved=retrieved,
        shared_features=shared_features,
    )
    cache_path = Path(cache_dir) / f"{key}.json"
    if cache_path.exists() and not force:
        return read_json(cache_path)["payload"]

    if pipeline == "rag":
        system, user = rag_messages(
            request_text=request_text,
            agency_name=agency_name,
            retrieved=retrieved,
            shared_features=shared_features,
        )
        schema = rag_schema(retrieved)
        schema_name = "foia_real_rag_baseline"
    elif pipeline == "rag_chunklookup":
        system, user = chunklookup_messages(
            request_text=request_text,
            agency_name=agency_name,
            retrieved=retrieved,
            shared_features=shared_features,
        )
        schema = chunklookup_schema(retrieved)
        schema_name = "foia_real_chunklookup_baseline"
    else:
        raise ValueError(f"unsupported LLM baseline pipeline {pipeline!r}")

    result = responses_json_schema(
        model=model,
        system=system,
        user=user,
        schema=schema,
        schema_name=schema_name,
        temperature=0.0,
    )
    payload = result["parsed"]
    write_json(
        cache_path,
        {
            "schema_version": "rag_vs_pag.real_llm_baseline_cache.v1",
            "prompt_version": BASELINE_PROMPT_VERSION,
            "pipeline": pipeline,
            "track": track,
            "requested_model": model,
            "model": result["model"],
            "raw_response_id": result["raw_response_id"],
            "usage": result["usage"],
            "cache_key": key,
            "payload": payload,
        },
    )
    return payload
