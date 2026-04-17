from __future__ import annotations

from scripts.adjudicate_benchmark import adjudicate_row


def base_row(response_text: str, *, cited: list[str] | None = None) -> dict:
    cited = cited or ["b5"]
    return {
        "id": 1,
        "agency_name": "Test Agency",
        "muckrock_url": "https://example.test/request/1",
        "request_text": "Please provide internal deliberative memoranda about this agency guidance.",
        "response_text": response_text,
        "primary_exemption": cited[0],
        "all_cited_exemptions": cited,
    }


def test_single_applied_exemption_is_clean() -> None:
    row = base_row("We located responsive records and withheld portions pursuant to FOIA Exemption 5.")
    adjudication = adjudicate_row(row)
    assert adjudication["benchmark_bucket"] == "clean"
    assert adjudication["gold"]["acceptable"] == ["b5"]
    assert adjudication["review_required"] is False


def test_multi_exemption_letter_is_ambiguous() -> None:
    row = base_row(
        "We withheld portions pursuant to FOIA Exemption 6 and FOIA Exemption 7.",
        cited=["b6", "b7"],
    )
    adjudication = adjudicate_row(row)
    assert adjudication["benchmark_bucket"] == "ambiguous"
    assert "multi_exemption_letter" in adjudication["ambiguity_flags"]
    assert adjudication["review_required"] is True


def test_nonfinal_submitter_notice_is_ambiguous() -> None:
    row = base_row(
        "You may file a response explaining why confidential commercial information "
        "should be withheld pursuant to FOIA Exemption 4.",
        cited=["b4"],
    )
    adjudication = adjudicate_row(row)
    assert adjudication["benchmark_bucket"] == "ambiguous"
    assert "procedural_or_nonfinal_response" in adjudication["ambiguity_flags"]
