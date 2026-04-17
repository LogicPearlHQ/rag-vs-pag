from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag_vs_pag.jsonio import read_json, write_json


APPROVED = "approved_clean"


def load_review(path: str) -> dict[int, dict[str, Any]]:
    payload = read_json(path)
    return {int(row["scenario_id"]): row for row in payload["rows"]}


def filter_split(split: dict[str, list[int]], keep_ids: set[int]) -> dict[str, list[int]]:
    return {
        "dev": [scenario_id for scenario_id in split.get("dev", []) if scenario_id in keep_ids],
        "test": [scenario_id for scenario_id in split.get("test", []) if scenario_id in keep_ids],
    }


def markdown_report(review_payload: dict[str, Any], approved_rows: list[dict[str, Any]], split: dict[str, list[int]]) -> str:
    rows = review_payload["rows"]
    statuses = Counter(row["manual_status"] for row in rows)
    approved_ids = {int(row["id"]) for row in approved_rows}
    approved_split = filter_split(split, approved_ids)

    lines = [
        "# Manual Clean Benchmark Review",
        "",
        "Date: 2026-04-17",
        "",
        "This file records a manual review of the deterministic clean subset. The review checked whether each response evidence span supports a single-label clean gold answer. The review did not inspect RAG, RAG-ChunkLookup, LogicPearl, or OpenAI extractor predictions.",
        "",
        "## Summary",
        "",
        "| Status | Count |",
        "|---|---:|",
    ]
    for status, count in sorted(statuses.items()):
        lines.append(f"| {status} | {count} |")
    lines.extend(
        [
            "",
            f"Approved clean records: {len(approved_rows)}",
            f"Approved clean dev records: {len(approved_split['dev'])}",
            f"Approved clean test records: {len(approved_split['test'])}",
            "",
            "## Decisions",
            "",
            "| ID | Status | Approved primary | Acceptable | Rationale |",
            "|---:|---|---|---|---|",
        ]
    )
    for row in rows:
        acceptable = ", ".join(row["acceptable_labels"])
        lines.append(
            f"| {row['scenario_id']} | {row['manual_status']} | {row['approved_primary']} | {acceptable} | {row['rationale']} |"
        )
    lines.extend(
        [
            "",
            "## Fairness Notes",
            "",
            "- The deterministic clean subset is preserved separately from the manually approved clean subset.",
            "- Manual exclusions are recorded with status and rationale instead of silently deleting cases.",
            "- Approved primary labels and acceptable-label sets are stored in the manual review sidecar.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default="scenarios/muckrock_snapshot.100.live.clean.json")
    parser.add_argument("--split", default="scenarios/split.100.live.clean.json")
    parser.add_argument("--review", default="scenarios/manual_review.100.live.clean.json")
    parser.add_argument("--output", default="scenarios/muckrock_snapshot.100.live.clean.approved.json")
    parser.add_argument("--split-output", default="scenarios/split.100.live.clean.approved.json")
    parser.add_argument("--report-output", default="docs/qa/manual-clean-review.md")
    args = parser.parse_args()

    rows = read_json(args.scenarios)
    split = read_json(args.split)
    review_payload = read_json(args.review)
    review_by_id = load_review(args.review)

    approved_rows: list[dict[str, Any]] = []
    for row in rows:
        review = review_by_id[int(row["id"])]
        if review["manual_status"] != APPROVED:
            continue
        copy = dict(row)
        copy["primary_exemption"] = review["approved_primary"]
        copy["all_cited_exemptions"] = review["acceptable_labels"]
        copy["manual_review_status"] = review["manual_status"]
        copy["manual_review_rationale"] = review["rationale"]
        approved_rows.append(copy)

    approved_ids = {int(row["id"]) for row in approved_rows}
    approved_split = filter_split(split, approved_ids)
    write_json(args.output, approved_rows)
    write_json(args.split_output, approved_split)

    report_path = Path(args.report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown_report(review_payload, approved_rows, split) + "\n", encoding="utf-8")

    print(f"wrote {args.output} ({len(approved_rows)} approved records)")
    print(f"wrote {args.split_output}")
    print(f"wrote {args.report_output}")


if __name__ == "__main__":
    main()
