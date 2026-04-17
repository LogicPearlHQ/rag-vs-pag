from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag_vs_pag.jsonio import read_json
from rag_vs_pag.text import normalize_space


def excerpt(text: str, limit: int = 1200) -> str:
    text = normalize_space(text)
    return text[:limit] + ("..." if len(text) > limit else "")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default="scenarios/muckrock_snapshot.100.live.json")
    parser.add_argument("--output", default="docs/qa/archive/live-gold-label-review.md")
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    rows = read_json(args.scenarios)
    rng = random.Random(args.seed)
    sample = rng.sample(rows, min(args.n, len(rows)))
    lines = [
        "# Live Gold Label QA Review",
        "",
        f"Source: `{args.scenarios}`",
        f"Sample size: {len(sample)}",
        "",
        "For each item, verify that the primary exemption appears in the actual denial or withholding reasoning, not only in boilerplate or an exemption appendix.",
        "",
    ]
    for idx, row in enumerate(sample, start=1):
        lines.extend(
            [
                f"## {idx}. Request {row['id']} - {row['primary_exemption']}",
                "",
                f"- URL: {row.get('muckrock_url', '')}",
                f"- Agency: {row.get('agency_name', '')}",
                f"- Status: {row.get('status', '')}",
                f"- Source: {row.get('response_source', 'communication_text')}",
                f"- File ID: {row.get('response_file_id')}",
                f"- All cited: {', '.join(row.get('all_cited_exemptions', []))}",
                "",
                "**Request excerpt**",
                "",
                excerpt(row.get("request_text", "")),
                "",
                "**Response excerpt**",
                "",
                excerpt(row.get("response_text", "")),
                "",
                "**QA**",
                "",
                "- [ ] Label is correct",
                "- [ ] Label is suspect",
                "- Notes:",
                "",
            ]
        )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
