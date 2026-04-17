from __future__ import annotations

from rag_vs_pag.jsonio import read_json
from rag_vs_pag.schema import load_scenarios


def test_live_scenarios_validate() -> None:
    scenarios = load_scenarios(read_json("scenarios/muckrock_snapshot.100.live.json"))
    assert len(scenarios) >= 10
    for scenario in scenarios:
        assert scenario.request_text
        assert scenario.agency_name
        assert scenario.primary_exemption in scenario.all_cited_exemptions


def test_public_input_excludes_gold_fields() -> None:
    scenario = load_scenarios(read_json("scenarios/muckrock_snapshot.100.live.json"))[0]
    public = scenario.public_input()
    assert "request_text" in public
    assert "agency_name" in public
    assert "primary_exemption" not in public
    assert "response_text" not in public
