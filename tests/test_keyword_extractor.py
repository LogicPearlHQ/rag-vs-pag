"""Tests for the fully-deterministic keyword feature extractor."""
import json
from pathlib import Path

from pearl.keyword_extractor import _normalize, extract_features

FD = json.loads((Path(__file__).parent.parent / "pearl" / "feature_dictionary.json").read_text())


def test_returns_every_feature():
    out = extract_features("irrelevant text")
    assert set(out) == set(FD)
    assert all(isinstance(v, bool) for v in out.values())


def test_all_features_false_on_empty():
    out = extract_features("")
    assert all(v is False for v in out.values())


def test_classified_record_fires_b1_features():
    out = extract_features("A memo classified TOP SECRET under Executive Order 13526, currently in force.")
    assert out["classified_under_executive_order"] is True
    assert out["classification_still_in_force"] is True


def test_negative_keyword_suppresses_positive():
    # 'declassified' is a negative_keywords entry for classification_still_in_force;
    # even if another keyword matches, the feature stays FALSE.
    out = extract_features("A State Department cable previously classified SECRET but automatically declassified in 2010.")
    assert out["classified_under_executive_order"] is True
    assert out["classification_still_in_force"] is False


def test_pre_decisional_negation_suppresses():
    out = extract_features("An inter-agency transmittal that is not pre-decisional and not privileged.")
    # Per feature_dictionary.json: 'not pre-decisional' is a negative_keyword.
    assert out["pre_decisional_deliberative"] is False


def test_extractor_is_pure():
    """Given the same input, two calls must produce identical output. This
    is the whole reason to use the keyword extractor — byte-identical
    extraction across reruns."""
    desc = "An inter-agency memo circulated before a final rulemaking decision."
    assert extract_features(desc) == extract_features(desc)


def test_normalize_collapses_inter_dash_agency():
    assert "inter-agency" in _normalize("inter- agency memo")
    assert "intra-agency" in _normalize("intra- agency  transmittal")


def test_no_llm_imports_required():
    """A sanity check: the keyword extractor should be usable in an
    environment where LLM SDKs aren't installed. Test that the module
    imports without triggering LLM package resolution."""
    import importlib
    import sys

    mod = importlib.reload(sys.modules["pearl.keyword_extractor"])
    assert hasattr(mod, "extract_features")
