from __future__ import annotations

import subprocess
import sys

from pipelines import logicpearl, rag, rag_chunklookup
from rag_vs_pag.features import empty_features
from rag_vs_pag.jsonio import read_json
from rag_vs_pag.schema import load_scenarios


def setup_module() -> None:
    subprocess.run([sys.executable, "corpus/fetch.py"], check=True)
    subprocess.run([sys.executable, "rag/index.py"], check=True)


def fake_rag_payload(*, pipeline: str, retrieved: list[dict], **kwargs) -> dict:
    chunk = retrieved[0]
    if pipeline == "rag_chunklookup":
        return {
            "verdict": "b7",
            "rationale": "The request targets law enforcement records.",
            "cited_chunk_ids": [chunk["chunk_id"]],
        }
    return {
        "verdict": "b7",
        "rationale": "The request targets law enforcement records.",
        "cited_authorities": [
            {
                "chunk_id": chunk["chunk_id"],
                "source_id": chunk["source_id"],
                "cite": chunk["title"],
                "excerpt": chunk["text"],
            }
        ],
    }


def test_all_pipelines_smoke_track_a(monkeypatch) -> None:
    scenario = load_scenarios(read_json("scenarios/muckrock_snapshot.100.live.json"))[0]
    features = empty_features()
    features["request_for_law_enforcement_investigation_records"] = True
    monkeypatch.setattr(rag, "call_openai_baseline", fake_rag_payload)
    monkeypatch.setattr(rag_chunklookup, "call_openai_baseline", fake_rag_payload)
    monkeypatch.setattr(
        logicpearl,
        "extract_one",
        lambda request_text, agency_name: {"features": features, "evidence": {}, "uncertain_features": []},
    )
    for runner in (rag.run, rag_chunklookup.run, logicpearl.run):
        result = runner(scenario, track="A")
        assert result["verdict"]
        assert result["scenario_id"] == scenario.id


def test_all_pipelines_smoke_track_b_shared_features(monkeypatch) -> None:
    scenario = load_scenarios(read_json("scenarios/muckrock_snapshot.100.live.json"))[0]
    features = empty_features()
    features["request_for_law_enforcement_investigation_records"] = True
    monkeypatch.setattr(rag, "call_openai_baseline", fake_rag_payload)
    monkeypatch.setattr(rag_chunklookup, "call_openai_baseline", fake_rag_payload)
    for runner in (rag.run, rag_chunklookup.run, logicpearl.run):
        result = runner(scenario, track="B", shared_features=features)
        assert result["verdict"]
        assert result["scenario_id"] == scenario.id


def test_insufficient_facts_does_not_force_citations(monkeypatch) -> None:
    scenario = load_scenarios(read_json("scenarios/muckrock_snapshot.100.live.json"))[0]
    features = empty_features()

    def fake_insufficient_payload(*, pipeline: str, **kwargs) -> dict:
        if pipeline == "rag_chunklookup":
            return {
                "verdict": "insufficient_facts",
                "rationale": "The request text does not contain enough facts.",
                "cited_chunk_ids": [],
            }
        return {
            "verdict": "insufficient_facts",
            "rationale": "The request text does not contain enough facts.",
            "cited_authorities": [],
        }

    monkeypatch.setattr(rag, "call_openai_baseline", fake_insufficient_payload)
    monkeypatch.setattr(rag_chunklookup, "call_openai_baseline", fake_insufficient_payload)

    rag_result = rag.run(scenario, track="B", shared_features=features)
    chunklookup_result = rag_chunklookup.run(scenario, track="B", shared_features=features)
    logicpearl_result = logicpearl.run(scenario, track="B", shared_features=features)

    assert rag_result["verdict"] == "insufficient_facts"
    assert rag_result["cited_authorities"] == []
    assert chunklookup_result["verdict"] == "insufficient_facts"
    assert chunklookup_result["resolved_citations"] == []
    assert logicpearl_result["verdict"] == "insufficient_facts"
    assert logicpearl_result["ruleset_decision"]["defaulted"] is True
