from pathlib import Path

from ragdemo.scenarios import load_scenarios

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


def test_curated_scenarios_count():
    """Fifteen curated diagnostic scenarios at the top level."""
    paths = [
        p for p in SCENARIOS_DIR.glob("*.json")
        if p.name != "cases.json" and not p.name.startswith("_")
    ]
    assert len(paths) == 15


def test_all_scenarios_load_cleanly():
    """Curated + generated-from-cases together."""
    scs = load_scenarios(SCENARIOS_DIR)
    assert len(scs) >= 15  # curated + however many case scenarios exist


def test_scenarios_cover_expected_categories():
    """Categories across curated + case-derived scenarios.

    `out-of-distribution` was dropped (couldn't test 'insufficient_context'
    honestly without reintroducing an LLM judgment layer upstream of the
    pearl). `case-law` was added for scenarios derived from real cases
    via scenarios/cases.json.
    """
    scs = load_scenarios(SCENARIOS_DIR)
    cats = {s.category for s in scs}
    assert "clear-cut" in cats
    assert "borderline" in cats
    assert "rag-favored" in cats


def test_clearcut_scenarios_cover_every_exemption_plus_releasable():
    scs = load_scenarios(SCENARIOS_DIR)
    clearcut = [s for s in scs if s.category == "clear-cut"]
    expected = {f"b{i}" for i in range(1, 10)} | {"releasable"}
    got = {s.expected.exemption for s in clearcut}
    assert got == expected, (got - expected, expected - got)


def test_every_scenario_has_nontrivial_description():
    scs = load_scenarios(SCENARIOS_DIR)
    for s in scs:
        assert len(s.description.split()) >= 10, s.id
