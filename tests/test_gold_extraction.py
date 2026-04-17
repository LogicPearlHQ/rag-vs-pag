from __future__ import annotations

from scripts.corpus_build.extract_gold_labels import extract_exemptions, label_record


def test_extract_exemptions_common_forms() -> None:
    text = "Denied under Exemption 7 and 5 U.S.C. 552(b)(6), also exemption b4."
    assert extract_exemptions(text) == ["b7", "b6", "b4"]


def test_label_record_primary_is_first_seen() -> None:
    row = label_record({"response_text": "Withheld pursuant to Exemption 5 and Exemption 6."})
    assert row["primary_exemption"] == "b5"
    assert row["all_cited_exemptions"] == ["b5", "b6"]
