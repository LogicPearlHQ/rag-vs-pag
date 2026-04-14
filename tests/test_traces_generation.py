"""Tests for the trace generation pipeline.

The pipeline's integrity rests on three properties:

  1. Idempotence — running the generator twice produces byte-identical CSV.
  2. Quote verification — every statute_structure quote is a substring of
     the real fetched statute text (after whitespace normalization).
  3. Schema — every column is either a known feature or a metadata column;
     labels are in the allowed set.
"""
import csv
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FD_PATH = ROOT / "pearl" / "feature_dictionary.json"
STRUCTURE_PATH = ROOT / "pearl" / "statute_structure.json"
TRACES = ROOT / "pearl" / "traces.csv"

META = {"exemption", "source", "note"}
ALLOWED = {f"b{i}" for i in range(1, 10)} | {"releasable"}


def test_generator_is_idempotent():
    h1 = hashlib.sha256(TRACES.read_bytes()).hexdigest()
    subprocess.run(
        ["uv", "run", "python", "-m", "pearl.generate_traces"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    h2 = hashlib.sha256(TRACES.read_bytes()).hexdigest()
    assert h1 == h2, "running generate_traces twice changed traces.csv"


def test_statute_structure_quotes_appear_in_statute():
    from pearl.generate_traces import (
        _load_statute_text,
        verify_structure_against_statute,
    )

    fd = json.loads(FD_PATH.read_text())
    structure = json.loads(STRUCTURE_PATH.read_text())
    errors = verify_structure_against_statute(structure, _load_statute_text(), fd)
    assert errors == [], f"quote verification failed:\n  - " + "\n  - ".join(errors)


def test_every_structure_feature_is_known():
    fd = json.loads(FD_PATH.read_text())
    structure = json.loads(STRUCTURE_PATH.read_text())
    for key, entry in structure.items():
        if key.startswith("_"):
            continue
        for g in entry.get("groups", []):
            for f in g["features"]:
                assert f in fd, f"{key}: unknown feature {f}"


def test_every_exemption_has_at_least_one_group():
    structure = json.loads(STRUCTURE_PATH.read_text())
    for n in range(1, 10):
        key = f"b{n}"
        assert key in structure, f"statute_structure missing {key}"
        assert structure[key].get("groups"), f"{key} has no groups"


def test_traces_columns_all_known_or_meta():
    fd = json.loads(FD_PATH.read_text())
    with TRACES.open() as f:
        headers = next(csv.reader(f))
    for h in headers:
        assert h in META or h in fd, f"unknown column: {h}"


def test_traces_labels_in_allowed_set():
    with TRACES.open() as f:
        for row in csv.DictReader(f):
            assert row["exemption"] in ALLOWED, row["exemption"]


def test_traces_feature_values_are_boolean_strings():
    fd = json.loads(FD_PATH.read_text())
    with TRACES.open() as f:
        for row in csv.DictReader(f):
            for k in fd:
                assert row[k].strip().lower() in {"true", "false"}, (row, k)


def test_traces_cover_every_exemption():
    with TRACES.open() as f:
        labels = {r["exemption"] for r in csv.DictReader(f)}
    assert labels >= {f"b{i}" for i in range(1, 10)}
    assert "releasable" in labels


def test_traces_every_row_cites_a_source():
    with TRACES.open() as f:
        for r in csv.DictReader(f):
            assert r["source"].strip(), r
            assert r["note"].strip(), r


def test_no_row_is_hand_typed_marker():
    # Defensive check: rows whose `note` matches the statute quote pattern
    # confirm the row came from the generator, not by hand. At minimum, at
    # least one (b)(N) row has a `note` that is also a literal substring of
    # the raw statute text (post-normalization).
    from pearl.generate_traces import _load_statute_text, _norm

    statute_norm = _norm(_load_statute_text())
    matched = 0
    with TRACES.open() as f:
        for r in csv.DictReader(f):
            if r["exemption"].startswith("b") and _norm(r["note"]) in statute_norm:
                matched += 1
    assert matched >= 5, f"expected ≥5 rows whose note appears verbatim in statute; got {matched}"
