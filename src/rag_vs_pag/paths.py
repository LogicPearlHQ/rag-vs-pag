from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def root_path(*parts: str) -> Path:
    return ROOT.joinpath(*parts)
