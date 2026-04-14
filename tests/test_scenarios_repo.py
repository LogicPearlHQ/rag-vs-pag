from pathlib import Path

from ragdemo.scenarios import load_scenarios

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"


def test_fifteen_scenarios_load_cleanly():
    scs = load_scenarios(SCENARIOS_DIR)
    assert len(scs) == 15


def test_scenarios_cover_expected_categories():
    """Categories that remain after the refusal-pathway pass.

    `out-of-distribution` was dropped: we couldn't test 'insufficient_context'
    honestly without reintroducing an LLM judgment layer upstream of the
    pearl (which would undermine the demo's own thesis). Scenarios that
    exercise partial-elements edges live under `borderline`; scenarios that
    RAG is supposed to win live under `rag-favored`.
    """
    scs = load_scenarios(SCENARIOS_DIR)
    cats = {s.category for s in scs}
    assert cats == {"clear-cut", "borderline", "rag-favored"}


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
