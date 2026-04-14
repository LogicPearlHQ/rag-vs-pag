from pathlib import Path

import pytest

from pearl.pearl import FD, build_extract_tool, run_pearl


def test_extract_tool_covers_every_feature():
    tool = build_extract_tool()
    schema = tool["input_schema"]
    assert schema["type"] == "object"
    assert set(schema["properties"]) == set(FD)
    for k, prop in schema["properties"].items():
        assert prop["type"] == "boolean"
        assert FD[k]["label"] in prop["description"]


@pytest.mark.skipif(
    not (Path(__file__).parent.parent / "pearl" / "artifact").exists(),
    reason="artifact not built — run `make build`",
)
def test_run_pearl_routes_b5_scenario():
    features = {k: False for k in FD}
    features["inter_or_intra_agency_memo"] = True
    features["pre_decisional_deliberative"] = True
    out = run_pearl(features)
    action = out.get("action") or out.get("decision")
    assert action == "b5", out


@pytest.mark.skipif(
    not (Path(__file__).parent.parent / "pearl" / "artifact").exists(),
    reason="artifact not built — run `make build`",
)
def test_run_pearl_routes_releasable_when_all_false():
    features = {k: False for k in FD}
    out = run_pearl(features)
    action = out.get("action") or out.get("decision")
    assert action == "releasable", out


@pytest.mark.skipif(
    not (Path(__file__).parent.parent / "pearl" / "artifact").exists(),
    reason="artifact not built — run `make build`",
)
def test_engine_reports_defaulted_when_no_rule_fires():
    """The refusal pathway relies on the engine's `defaulted` flag."""
    features = {k: False for k in FD}
    out = run_pearl(features)
    assert out.get("defaulted") is True, out
    assert out.get("selected_rules") == [], out


@pytest.mark.skipif(
    not (Path(__file__).parent.parent / "pearl" / "artifact").exists(),
    reason="artifact not built — run `make build`",
)
def test_engine_reports_not_defaulted_when_rule_fires():
    features = {k: False for k in FD}
    features["inter_or_intra_agency_memo"] = True
    features["pre_decisional_deliberative"] = True
    out = run_pearl(features)
    assert out.get("defaulted") is False, out
    assert out.get("selected_rules"), out
