"""PAG-R: RAG reasoning + pearl feature dictionary for citations.

The LLM reasons normally (retrieval-augmented) and produces a decision.
Instead of writing citation excerpts, the LLM identifies which pearl
features apply. Each feature is looked up in pearl/feature_dictionary.json
and its cite + label are emitted as the citation authority.

If the LLM identifies zero features (e.g., on a synthesis task), no
citations are returned. The LLM cannot write a cite; it can only
reference features from a whitelisted set.

This pipeline does NOT run the pearl's rule engine. The feature
dictionary is used purely as a lookup table for citation authorities.
Its purpose is to isolate LogicPearl's cite-library contribution from
the chunk-indirection pattern used in rag_chunklookup.py.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from ragdemo.llm import LLMConfig, make_llm
from ragdemo.scenarios import load_scenario
from rag.retrieve import retrieve

ROOT = Path(__file__).parent
FD_PATH = ROOT / "feature_dictionary.json"
FD = json.loads(FD_PATH.read_text())

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
        "features_that_apply": {
            "type": "array",
            "items": {"type": "string", "enum": list(FD.keys())},
            "description": "Feature names from the reviewed pearl dictionary whose statute elements are present in this record.",
        },
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["exemption", "releasable", "rationale", "features_that_apply", "confidence"],
}


def _system_prompt() -> str:
    features_block = "\n".join(
        f"- `{k}` — {v['label']} ({v['cite']})"
        for k, v in FD.items()
    )
    return f"""You are a FOIA analyst. Given the retrieved excerpts below, determine whether the described record is exempt under 5 U.S.C. § 552(b), and under which subsection. If the record is releasable, use "releasable". If the request is an open-ended synthesis task, use "not_applicable".

Citations must be made by naming features from this reviewed pearl dictionary. List the features whose statute-defined elements are supported by the description in `features_that_apply`:

{features_block}

The backend will look up each named feature's cite and label from the reviewed dictionary. DO NOT write excerpt text directly — you cannot cite anything outside this whitelisted feature list. If no feature applies, return features_that_apply=[] (no cite is better than a fabricated one)."""


def answer(scenario_path: Path, llm_cfg: LLMConfig) -> dict:
    s = load_scenario(scenario_path)
    t0 = time.time()
    chunks = retrieve(s.description, top_k=8)
    t_retrieve = time.time() - t0

    blob = "\n\n".join(
        f"[{c.metadata.get('cite', '(unknown)')}]\n{c.text[:1200]}" for c in chunks
    )

    llm = make_llm(llm_cfg)
    user = f"RECORD DESCRIPTION:\n{s.description}\n\nRETRIEVED EXCERPTS:\n{blob}"

    t1 = time.time()
    result = llm.chat_json(
        system=_system_prompt(), user=user, schema=ANSWER_SCHEMA, temperature=0.0
    )
    t_llm = time.time() - t1

    # Resolve features → cite authorities from the pearl's dictionary.
    cited_authorities: list[dict] = []
    for feat in result.get("features_that_apply", []):
        meta = FD.get(feat)
        if meta is None:
            continue
        cited_authorities.append({
            "cite": meta["cite"],
            "excerpt": meta["label"],
            "feature": feat,
        })

    return {
        "exemption": result["exemption"],
        "releasable": result["releasable"],
        "rationale": result["rationale"],
        "cited_authorities": cited_authorities,
        "confidence": result["confidence"],
        "_latency_s": {"retrieve": round(t_retrieve, 3), "llm": round(t_llm, 3)},
        "_retrieved_cites": [c.metadata.get("cite") for c in chunks],
        "_features_named": result.get("features_that_apply", []),
        # Cites are pearl-dict lookups, 100% faithful by construction.
        "_citation_faithfulness": [
            {"cite": a["cite"], "excerpt_first_60": a["excerpt"][:60], "ok": True}
            for a in cited_authorities
        ],
    }


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
