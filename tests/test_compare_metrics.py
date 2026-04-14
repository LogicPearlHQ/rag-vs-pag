from compare import (
    _strip_meta,
    avg_latency,
    citation_faithfulness_ratio,
    correctness,
    determinism_score,
)


def test_determinism_5_of_5_identical():
    runs = [{"exemption": "b5", "rationale": "x"}] * 5
    assert determinism_score(runs) == (5, 5)


def test_determinism_3_of_5_most_common():
    runs = (
        [{"exemption": "b5"}] * 3
        + [{"exemption": "b7"}, {"exemption": "b6"}]
    )
    assert determinism_score(runs) == (3, 5)


def test_determinism_strips_latency_noise():
    a = {"exemption": "b5", "_latency_s": {"retrieve": 1.0}}
    b = {"exemption": "b5", "_latency_s": {"retrieve": 2.0}}
    assert determinism_score([a, b]) == (2, 2)


def test_decision_determinism_ignores_rationale_drift():
    """Decision-level determinism should measure the exemption, not the
    rationale text that LLMs vary across reruns even at temperature=0."""
    a = {"exemption": "b5", "rationale": "The record is pre-decisional..."}
    b = {"exemption": "b5", "rationale": "Given that this is a draft memo..."}
    c = {"exemption": "b5", "rationale": "Exemption 5 applies because..."}
    assert determinism_score([a, b, c]) == (3, 3)


def test_full_determinism_catches_rationale_drift():
    from compare import full_determinism_score

    a = {"exemption": "b5", "rationale": "r1"}
    b = {"exemption": "b5", "rationale": "r2"}
    # Same decision, different rationales → full-det splits them.
    assert full_determinism_score([a, b]) == (1, 2)


def test_correctness_direct_match():
    assert correctness({"exemption": "b5"}, "b5") is True
    assert correctness({"exemption": "b5"}, "b6") is False


def test_correctness_accepts_refusal_when_expected_none():
    assert correctness({"exemption": "insufficient_context"}, None) is True
    assert correctness({"exemption": "releasable"}, "not_applicable") is True
    assert correctness({"exemption": "not_applicable"}, "not_applicable") is True


def test_citation_faithfulness_ratio_from_check_list():
    r = {"_citation_faithfulness": [{"ok": True}, {"ok": False}, {"ok": True}]}
    assert citation_faithfulness_ratio(r) == (2, 3)


def test_citation_faithfulness_pearl_side_is_all_ok():
    r = {"cited_authorities": [{"cite": "x", "excerpt": "y"}, {"cite": "z", "excerpt": "w"}]}
    assert citation_faithfulness_ratio(r) == (2, 2)


def test_avg_latency_rag():
    runs = [
        {"_latency_s": {"retrieve": 5.0, "llm": 3.0}},
        {"_latency_s": {"retrieve": 6.0, "llm": 2.0}},
    ]
    assert avg_latency(runs, "rag") == 8.0


def test_avg_latency_pearl():
    runs = [{"_latency_s": {"extract": 1.0, "pearl": 0.01, "explain": 1.5}}]
    assert avg_latency(runs, "pearl") == 2.51


def test_strip_meta_keeps_only_public_keys():
    stripped = _strip_meta({"exemption": "b5", "_latency_s": {"a": 1}, "_retrieved": []})
    assert stripped == {"exemption": "b5"}
