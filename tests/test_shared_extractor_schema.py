from __future__ import annotations

import pytest

from extraction import shared_extractor
from extraction.shared_extractor import extract_one
from rag_vs_pag.features import empty_features, validate_feature_payload


def test_shared_extractor_returns_boolean_features(monkeypatch, tmp_path) -> None:
    features = empty_features()
    features["request_for_law_enforcement_investigation_records"] = True
    features["request_targets_specific_named_individual"] = True

    def fake_responses_json_schema(**kwargs):
        return {
            "parsed": {
                "features": features,
                "evidence": [
                    {
                        "feature": "request_for_law_enforcement_investigation_records",
                        "quote": "investigative records",
                    }
                ],
                "uncertain_features": [],
            },
            "raw_response_id": "resp_test",
            "usage": {},
            "model": kwargs["model"],
        }

    monkeypatch.setattr(shared_extractor, "responses_json_schema", fake_responses_json_schema)
    payload = extract_one(
        "FBI investigative records about John Doe",
        "Federal Bureau of Investigation",
        cache_dir=tmp_path,
    )
    assert payload["features"]["request_for_law_enforcement_investigation_records"] is True
    assert payload["features"]["request_targets_specific_named_individual"] is True


def test_validate_rejects_unknown_feature() -> None:
    with pytest.raises(ValueError):
        validate_feature_payload({"features": {"unknown": True}})
