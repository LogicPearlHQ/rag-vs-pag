from pathlib import Path

import pytest

from ragdemo.scenarios import Scenario, load_scenario, load_scenarios

FIX = Path(__file__).parent / "fixtures" / "scenarios"


def test_load_valid_scenario():
    s = load_scenario(FIX / "ok.json")
    assert isinstance(s, Scenario)
    assert s.id == "test01"
    assert s.category == "clear-cut"
    assert s.expected.exemption == "b5"
    assert s.expected.releasable is False
    assert "pre-decisional" in s.expected.rationale_keywords
    assert s.expected.expected_authority == "5 U.S.C. § 552(b)(5)"


def test_bad_scenario_raises():
    with pytest.raises(ValueError, match="missing keys"):
        load_scenario(FIX / "bad.json")


def test_load_scenarios_raises_when_any_scenario_malformed():
    # bad.json in the fixtures dir is missing required keys; load_scenarios
    # should surface that as ValueError rather than silently skipping.
    with pytest.raises(ValueError):
        load_scenarios(FIX)


def test_load_scenarios_returns_sorted_by_filename(tmp_path):
    (tmp_path / "02_later.json").write_text(
        '{"id":"b","description":"x","expected":{"exemption":"b5","releasable":false},"category":"clear-cut"}'
    )
    (tmp_path / "01_first.json").write_text(
        '{"id":"a","description":"x","expected":{"exemption":"b1","releasable":false},"category":"clear-cut"}'
    )
    scs = load_scenarios(tmp_path)
    assert [s.id for s in scs] == ["a", "b"]
