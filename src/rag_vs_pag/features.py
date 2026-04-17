from __future__ import annotations

from typing import Any


FEATURE_IDS: tuple[str, ...] = (
    "request_for_attorney_client_or_work_product_records",
    "request_for_classified_or_national_security_records",
    "request_for_confidential_commercial_or_financial_records",
    "request_for_confidential_source_records",
    "request_for_contracts_bids_or_procurement_records",
    "request_for_emails_or_correspondence_about_named_people",
    "request_for_financial_regulatory_records",
    "request_for_geological_or_geophysical_well_data",
    "request_for_grant_application_or_research_proposal",
    "request_for_internal_deliberative_email_chain",
    "request_for_internal_personnel_rules",
    "request_for_investigative_techniques",
    "request_for_law_enforcement_investigation_records",
    "request_for_statutorily_protected_records",
    "request_for_suspicious_activity_reports_or_bsa_records",
    "request_for_tax_return_or_irs_return_information",
    "request_targets_personnel_roster_or_file",
    "request_targets_specific_named_individual",
)


def empty_features() -> dict[str, bool]:
    return {name: False for name in FEATURE_IDS}


def validate_feature_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload.get("features"), dict):
        raise ValueError("extractor output must contain a features object")
    features = empty_features()
    for key, value in payload["features"].items():
        if key not in features:
            raise ValueError(f"unknown feature {key!r}")
        if not isinstance(value, bool):
            raise ValueError(f"feature {key!r} must be boolean")
        features[key] = value
    evidence = payload.get("evidence", {})
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")
    uncertain = payload.get("uncertain_features", [])
    if not isinstance(uncertain, list):
        raise ValueError("uncertain_features must be a list")
    return {
        "features": features,
        "evidence": {str(k): str(v) for k, v in evidence.items()},
        "uncertain_features": [str(item) for item in uncertain],
    }
