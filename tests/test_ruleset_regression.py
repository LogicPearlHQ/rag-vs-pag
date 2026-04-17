from __future__ import annotations

from rag_vs_pag.features import empty_features
from rag_vs_pag.jsonio import read_json
from rag_vs_pag.ruleset import evaluate_ruleset


def test_ruleset_selects_specific_b7_confidential_source_rule() -> None:
    ruleset = read_json("pearl/rulesets/v2/rules.json")
    features = empty_features()
    features["request_for_law_enforcement_investigation_records"] = True
    features["request_for_confidential_source_records"] = True
    decision = evaluate_ruleset(ruleset, features)
    assert decision["verdict"] == "b7"
    assert decision["rule_id"] == "b7d_confidential_source"


def test_ruleset_defaults_to_insufficient_facts() -> None:
    ruleset = read_json("pearl/rulesets/v2/rules.json")
    decision = evaluate_ruleset(ruleset, empty_features())
    assert decision["verdict"] == "insufficient_facts"
    assert decision["defaulted"] is True
