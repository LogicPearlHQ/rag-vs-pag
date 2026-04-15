"""Scenario loader + schema shared by both runners."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Category = Literal["clear-cut", "borderline", "out-of-distribution", "rag-favored"]


@dataclass
class Expected:
    exemption: str | None  # "b1".."b9", "releasable", or None (rag-favored)
    releasable: bool
    rationale_keywords: list[str]
    expected_authority: str | None


@dataclass
class Scenario:
    id: str
    description: str
    expected: Expected
    category: Category


def load_scenario(path: Path | str) -> Scenario:
    path = Path(path)
    data = json.loads(path.read_text())
    required = {"id", "description", "expected", "category"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"scenario {path.name} missing keys: {sorted(missing)}")
    e = data["expected"]
    return Scenario(
        id=data["id"],
        description=data["description"],
        expected=Expected(
            exemption=e.get("exemption"),
            releasable=bool(e.get("releasable", True)),
            rationale_keywords=list(e.get("rationale_keywords", [])),
            expected_authority=e.get("expected_authority"),
        ),
        category=data["category"],
    )


def load_scenarios(dir_: Path | str) -> list[Scenario]:
    """Load all .json scenarios in `dir_`, recursing one level.

    The top level holds curated diagnostic scenarios; the `cases/`
    subdirectory holds scenarios generated from real FOIA case
    records (see scenarios/generate_scenarios.py). Top-level files
    prefixed with an underscore or named `cases.json` are data
    files, not scenarios, and are skipped.
    """
    dir_ = Path(dir_)
    paths: list[Path] = [
        p for p in sorted(dir_.glob("*.json"))
        if p.name != "cases.json" and not p.name.startswith("_")
    ]
    paths.extend(sorted(dir_.glob("*/*.json")))
    return [load_scenario(p) for p in paths]
