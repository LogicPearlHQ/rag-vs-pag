from __future__ import annotations

from dataclasses import dataclass
from typing import Any


EXEMPTIONS = {f"b{i}" for i in range(1, 10)}
VERDICTS = EXEMPTIONS | {"releasable", "insufficient_facts"}


@dataclass(frozen=True)
class Scenario:
    id: int
    muckrock_url: str
    agency_name: str
    agency_id: int
    filed_date: str
    status: str
    request_text: str
    response_text: str
    primary_exemption: str
    all_cited_exemptions: tuple[str, ...]
    extraction_confidence: str
    retrieved_at: str

    @classmethod
    def from_dict(cls, row: dict[str, Any]) -> "Scenario":
        primary = row["primary_exemption"]
        if primary not in VERDICTS:
            raise ValueError(f"invalid primary exemption {primary!r}")
        cited = tuple(row.get("all_cited_exemptions", []))
        for exemption in cited:
            if exemption not in EXEMPTIONS:
                raise ValueError(f"invalid cited exemption {exemption!r}")
        return cls(
            id=int(row["id"]),
            muckrock_url=str(row.get("muckrock_url", "")),
            agency_name=str(row["agency_name"]),
            agency_id=int(row.get("agency_id", 0)),
            filed_date=str(row.get("filed_date", "")),
            status=str(row.get("status", "")),
            request_text=str(row["request_text"]),
            response_text=str(row.get("response_text", "")),
            primary_exemption=primary,
            all_cited_exemptions=cited,
            extraction_confidence=str(row.get("extraction_confidence", "")),
            retrieved_at=str(row.get("retrieved_at", "")),
        )

    def public_input(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agency_name": self.agency_name,
            "request_text": self.request_text,
        }


def load_scenarios(rows: list[dict[str, Any]]) -> list[Scenario]:
    return [Scenario.from_dict(row) for row in rows]
