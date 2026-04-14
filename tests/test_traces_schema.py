import csv
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
FD = json.loads((ROOT / "pearl" / "feature_dictionary.json").read_text())
TRACES = ROOT / "pearl" / "traces.csv"
META = {"exemption", "source", "note"}
ALLOWED_LABELS = {f"b{i}" for i in range(1, 10)} | {"releasable"}


def _rows():
    with TRACES.open() as f:
        return list(csv.DictReader(f))


def test_every_column_is_known_or_meta():
    with TRACES.open() as f:
        headers = next(csv.reader(f))
    for h in headers:
        assert h in META or h in FD, f"unknown column: {h}"


def test_labels_in_allowed_set():
    for r in _rows():
        assert r["exemption"] in ALLOWED_LABELS, r["exemption"]


def test_every_row_cites_a_source():
    for r in _rows():
        assert r["source"].strip(), r


def test_every_row_has_note():
    for r in _rows():
        assert r["note"].strip(), r


def test_coverage_includes_every_exemption_label():
    labels = {r["exemption"] for r in _rows()}
    assert labels >= {f"b{i}" for i in range(1, 10)}
    assert "releasable" in labels


def test_feature_values_are_boolean_strings():
    for r in _rows():
        for k in FD:
            assert r.get(k, "").strip().lower() in {"true", "false"}, (r, k)
