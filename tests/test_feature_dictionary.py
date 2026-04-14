import json
from pathlib import Path

FD_PATH = Path(__file__).parent.parent / "pearl" / "feature_dictionary.json"


def test_every_feature_has_label_and_cite():
    data = json.loads(FD_PATH.read_text())
    assert len(data) >= 18
    for key, value in data.items():
        assert "label" in value, f"{key} missing label"
        assert "cite" in value, f"{key} missing cite"
        assert value["label"], key
        assert value["cite"], key


def test_covers_all_nine_exemptions():
    data = json.loads(FD_PATH.read_text())
    combined = " ".join(v["cite"] for v in data.values())
    for n in range(1, 10):
        assert f"(b)({n})" in combined, f"no feature cites (b)({n})"


def test_feature_keys_are_snake_case():
    data = json.loads(FD_PATH.read_text())
    for k in data:
        assert k == k.lower()
        assert " " not in k
        assert "-" not in k
