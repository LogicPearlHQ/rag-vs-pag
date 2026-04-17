from __future__ import annotations

from extraction.shared_extractor import normalize_structured_payload, structured_schema
from rag_vs_pag.features import empty_features


def test_structured_schema_requires_every_feature() -> None:
    schema = structured_schema()
    feature_names = sorted(empty_features())
    assert schema["properties"]["features"]["required"] == feature_names
    assert set(schema["properties"]["features"]["properties"]) == set(feature_names)


def test_normalize_structured_payload_accepts_evidence_array() -> None:
    features = empty_features()
    features["request_for_law_enforcement_investigation_records"] = True
    payload = normalize_structured_payload(
        {
            "features": features,
            "evidence": [
                {
                    "feature": "request_for_law_enforcement_investigation_records",
                    "quote": "investigative records",
                }
            ],
            "uncertain_features": [],
        }
    )
    assert payload["features"]["request_for_law_enforcement_investigation_records"] is True
    assert payload["evidence"]["request_for_law_enforcement_investigation_records"] == "investigative records"
