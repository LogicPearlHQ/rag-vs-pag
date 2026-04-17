from __future__ import annotations

from pathlib import Path
from typing import Any

from benchmark.metrics import citation_metrics, correctness
from extraction.shared_extractor import extract_one
from pipelines import logicpearl, rag, rag_chunklookup
from rag_vs_pag.hashutil import canonical_hash
from rag_vs_pag.jsonio import read_json
from rag_vs_pag.schema import Scenario


PIPELINES = {
    "rag": rag.run,
    "rag_chunklookup": rag_chunklookup.run,
    "logicpearl": logicpearl.run,
}


def load_split(path: str, scenarios: list[Scenario]) -> dict[str, list[int]]:
    if Path(path).exists():
        return read_json(path)
    ids = [scenario.id for scenario in scenarios]
    pivot = max(1, len(ids) // 2)
    return {"dev": ids[:pivot], "test": ids[pivot:]}


def load_shared_features(path: str | None) -> tuple[dict[int, dict[str, Any]], list[dict[str, Any]]]:
    if not path:
        return {}, []
    payload = read_json(path)
    rows = payload.get("rows", [])
    by_id = {
        int(row["scenario_id"]): row["feature_payload"]
        for row in rows
    }
    extraction_rows = [
        {
            "kind": "shared_extraction",
            "scenario_id": int(row["scenario_id"]),
            "feature_hash": row["feature_hash"],
            "payload": row["feature_payload"],
            "extractor_provider": row.get("extractor_provider"),
            "extractor_model": row.get("extractor_model"),
        }
        for row in rows
    ]
    return by_id, extraction_rows


def load_adjudication(path: str | None) -> dict[int, dict[str, Any]]:
    if not path:
        return {}
    payload = read_json(path)
    rows = payload.get("rows", payload if isinstance(payload, list) else [])
    return {int(row["scenario_id"]): row for row in rows}


def run_all(
    scenarios: list[Scenario],
    repeats: int,
    precomputed_shared: dict[int, dict[str, Any]] | None = None,
    precomputed_rows: list[dict[str, Any]] | None = None,
    adjudication_by_id: dict[int, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    shared_by_id: dict[int, dict[str, Any]] = dict(precomputed_shared or {})
    rows.extend(precomputed_rows or [])
    for scenario in scenarios:
        if scenario.id in shared_by_id:
            continue
        payload = extract_one(scenario.request_text, scenario.agency_name)
        shared_by_id[scenario.id] = payload
        rows.append(
            {
                "kind": "shared_extraction",
                "scenario_id": scenario.id,
                "feature_hash": canonical_hash(payload["features"]),
                "payload": payload,
            }
        )
    for track in ("A", "B"):
        for runner in PIPELINES.values():
            for scenario in scenarios:
                for repeat in range(repeats):
                    shared_payload = shared_by_id.get(scenario.id)
                    if track == "B" and not shared_payload:
                        raise RuntimeError(f"missing shared features for scenario {scenario.id}")
                    shared_features = shared_payload["features"] if track == "B" else None
                    result = runner(scenario, track=track, shared_features=shared_features)
                    comparable = dict(result)
                    adjudication = (adjudication_by_id or {}).get(scenario.id)
                    result["repeat"] = repeat
                    result["gold_primary"] = scenario.primary_exemption
                    result["gold_all"] = list(scenario.all_cited_exemptions)
                    if adjudication:
                        gold = adjudication.get("gold", {})
                        result["adjudicated_gold_primary"] = gold.get("primary")
                        result["adjudicated_gold_acceptable"] = gold.get("acceptable", [])
                        result["benchmark_bucket"] = adjudication.get("benchmark_bucket")
                        result["adjudication_confidence"] = adjudication.get("adjudication_confidence")
                        result["ambiguity_flags"] = adjudication.get("ambiguity_flags", [])
                    result["correctness"] = correctness(result, scenario, adjudication)
                    result["citation_metrics"] = citation_metrics(result)
                    result["output_hash"] = canonical_hash(comparable)
                    rows.append({"kind": "pipeline_result", **result})
    return rows
