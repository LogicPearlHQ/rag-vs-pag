"""Generate scenario .json files from scenarios/cases.json.

Each case entry produces one scenario. The scenario's `description` is
the record_description_quote (i.e., verbatim DOJ Guide text describing
the records at issue); the `expected` fields are derived from the case's
gold label.

The pearl and the RAG pipelines have no idea these came from cases — to
them, they're just 15 additional scenario JSON files. The provenance
lives only in cases.json and is auto-verified by tests/test_cases_grounded.py.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CASES = ROOT / "scenarios" / "cases.json"
OUT_DIR = ROOT / "scenarios" / "cases"


def _slug(case_id: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", case_id.lower()).strip("_")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = json.loads(CASES.read_text()).get("cases", [])

    # Remove stale generated files so the generator is idempotent w.r.t.
    # case removals in cases.json.
    for stale in OUT_DIR.glob("*.json"):
        stale.unlink()

    for case in cases:
        desc = case["record_description_quote"].strip()
        # Frame the description so the LLM treats it as a record description,
        # not as an excerpt from a law-review article.
        description = f"A FOIA request seeks the following records: {desc}."
        scenario = {
            "id": f"case_{_slug(case['case_id'])}",
            "description": description,
            "expected": {
                "exemption": case["gold_exemption"],
                "releasable": bool(case["gold_releasable"]),
                "rationale_keywords": [],
                "expected_authority": None,
            },
            "category": case.get("category", "case-law"),
            "_provenance": {
                "case_name": case["case_name"],
                "source_doc": case["source_doc"],
                "source_page": case["source_page"],
                "record_description_quote": case["record_description_quote"],
                "outcome_quote": case["outcome_quote"],
                "note": case.get("note"),
            },
        }
        out = OUT_DIR / f"{scenario['id']}.json"
        out.write_text(json.dumps(scenario, indent=2) + "\n")

    print(f"wrote {len(cases)} scenarios to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
