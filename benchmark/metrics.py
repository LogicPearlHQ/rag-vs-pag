from __future__ import annotations

from typing import Any

from rag_vs_pag.schema import Scenario


def correctness(
    result: dict[str, Any],
    scenario: Scenario,
    adjudication: dict[str, Any] | None = None,
) -> dict[str, bool]:
    verdict = result["verdict"]
    gold_primary = scenario.primary_exemption
    acceptable = set(scenario.all_cited_exemptions)
    if adjudication:
        gold = adjudication.get("gold", {})
        gold_primary = gold.get("primary", gold_primary)
        acceptable = set(gold.get("acceptable", acceptable))
    return {
        "strict": verdict == gold_primary,
        "lenient": verdict == scenario.primary_exemption or verdict in scenario.all_cited_exemptions,
        "acceptable": verdict == gold_primary or verdict in acceptable,
        "raw_strict": verdict == scenario.primary_exemption,
    }


def citation_metrics(result: dict[str, Any]) -> dict[str, int]:
    verdict = result["verdict"]
    if result["pipeline"] == "rag":
        chunks = result.get("retrieved_chunks", [])
        corpus_text = "\n".join(chunk["text"] for chunk in chunks)
        faithful = 0
        fabricated = 0
        supports = 0
        for citation in result.get("cited_authorities", []):
            if citation.get("excerpt", "") in corpus_text:
                faithful += 1
            else:
                fabricated += 1
            if citation.get("source_id", "").endswith(verdict):
                supports += 1
        return {
            "faithful": faithful,
            "fabricated": fabricated,
            "supports_verdict": supports,
            "cited": len(result.get("cited_authorities", [])),
        }
    if result["pipeline"] == "rag_chunklookup":
        resolved = result.get("resolved_citations", [])
        return {
            "faithful": len(resolved),
            "fabricated": len(result.get("invalid_chunk_ids", [])),
            "supports_verdict": sum(1 for chunk in resolved if chunk.get("source_id", "").endswith(verdict)),
            "cited": len(result.get("cited_chunk_ids", [])),
        }
    if result["pipeline"] == "logicpearl":
        authority_ids = result.get("authority_ids", [])
        return {
            "faithful": len(authority_ids),
            "fabricated": 0,
            "supports_verdict": sum(1 for authority_id in authority_ids if str(authority_id).endswith(verdict)),
            "cited": len(authority_ids),
        }
    return {"faithful": 0, "fabricated": 0, "supports_verdict": 0, "cited": 0}
