from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag.retrieve import retrieve_for_text
from rag_vs_pag.jsonio import read_json, write_json
from rag_vs_pag.llm_baselines import call_openai_baseline
from rag_vs_pag.schema import Scenario


def run(
    scenario: Scenario,
    *,
    track: str,
    shared_features: dict[str, bool] | None = None,
    k: int = 4,
) -> dict[str, Any]:
    retrieved = retrieve_for_text(scenario.request_text, k=k)
    model = os.getenv("LP_RAG_MODEL", os.getenv("LP_LLM_MODEL", "gpt-4o-mini"))
    cache_dir = os.getenv("LP_RAG_CACHE_DIR", "extraction/cache/rag_baselines")
    payload = call_openai_baseline(
        pipeline="rag",
        track=track,
        request_text=scenario.request_text,
        agency_name=scenario.agency_name,
        retrieved=retrieved,
        shared_features=shared_features if track == "B" else None,
        model=model,
        cache_dir=cache_dir,
    )
    input_mode = "request_text+shared_features+retrieval+openai" if track == "B" else "request_text+retrieval+openai"
    return {
        "pipeline": "rag",
        "track": track,
        "scenario_id": scenario.id,
        "input_mode": input_mode,
        "verdict": payload["verdict"],
        "rationale": payload["rationale"],
        "retrieved_chunks": retrieved,
        "cited_authorities": payload.get("cited_authorities", []),
        "llm_provider": "openai",
        "llm_model": model,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_json")
    parser.add_argument("--track", choices=["A", "B"], default="A")
    parser.add_argument("--output")
    args = parser.parse_args()
    scenario = Scenario.from_dict(read_json(args.scenario_json))
    result = run(scenario, track=args.track)
    if args.output:
        write_json(args.output, result)
    else:
        print(result)


if __name__ == "__main__":
    main()
