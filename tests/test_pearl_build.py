"""End-to-end pearl build tests.

Run `bash pearl/build.sh` first (or `make build`). These tests verify that
the artifact exists, training parity is 100%, and the artifact verifies.
"""
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
ARTIFACT = ROOT / "pearl" / "artifact"


@pytest.mark.skipif(not ARTIFACT.exists(), reason="artifact not built — run `make build`")
def test_artifact_verifies():
    subprocess.run(
        ["logicpearl", "artifact", "verify", str(ARTIFACT)],
        check=True,
        capture_output=True,
    )


@pytest.mark.skipif(not ARTIFACT.exists(), reason="artifact not built — run `make build`")
def test_training_parity_is_100_percent():
    out = subprocess.run(
        ["logicpearl", "inspect", str(ARTIFACT), "--json"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    data = json.loads(out)
    # Parity lives under inspection metadata; accept any plausible location.
    def find_parity(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if "parity" in k.lower():
                    return v
                r = find_parity(v)
                if r is not None:
                    return r
        elif isinstance(obj, list):
            for v in obj:
                r = find_parity(v)
                if r is not None:
                    return r
        return None

    parity = find_parity(data)
    assert parity in (1.0, "100.0%", "100%"), f"parity={parity}"


@pytest.mark.skipif(not ARTIFACT.exists(), reason="artifact not built — run `make build`")
def test_b1_scenario_routes_to_b1():
    """Given b1 features, the pearl must output action=b1."""
    import tempfile

    features = {
        "classified_under_executive_order": True,
        "classification_still_in_force": True,
        "purely_internal_personnel_rule": False,
        "exempt_by_other_statute": False,
        "trade_secret_or_commercial_confidential": False,
        "commercial_info_voluntarily_submitted": False,
        "inter_or_intra_agency_memo": False,
        "pre_decisional_deliberative": False,
        "attorney_work_product_or_privileged": False,
        "personnel_medical_or_similar_file": False,
        "unwarranted_privacy_invasion": False,
        "law_enforcement_record": False,
        "law_enforcement_harm_proceedings": False,
        "law_enforcement_harm_privacy": False,
        "law_enforcement_harm_source": False,
        "law_enforcement_harm_techniques": False,
        "law_enforcement_harm_life_safety": False,
        "financial_institution_examination_report": False,
        "geological_well_data": False,
        "record_is_otherwise_public": False,
        "other_party_is_federal_agency_or_consultant": False,
    }
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(features, f)
        path = f.name
    out = subprocess.run(
        ["logicpearl", "run", str(ARTIFACT), path, "--explain", "--json"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    data = json.loads(out)
    action = data.get("action") or data.get("decision")
    assert action == "b1", f"expected b1, got {action}; full output: {data}"


@pytest.mark.skipif(not ARTIFACT.exists(), reason="artifact not built — run `make build`")
def test_all_false_scenario_is_releasable():
    import tempfile

    from pearl.generate_traces import _load_statute_text  # noqa: F401  (ensure import path)
    import json as _json

    features = {k: False for k in _json.loads((ROOT / "pearl" / "feature_dictionary.json").read_text())}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        _json.dump(features, f)
        path = f.name
    out = subprocess.run(
        ["logicpearl", "run", str(ARTIFACT), path, "--explain", "--json"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    data = _json.loads(out)
    action = data.get("action") or data.get("decision")
    assert action == "releasable", f"got {action}; {data}"
