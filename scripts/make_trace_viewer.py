from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from pipelines import logicpearl, rag, rag_chunklookup
from rag_vs_pag.jsonio import read_json
from rag_vs_pag.schema import Scenario
from rag_vs_pag.text import normalize_space


def load_shared_features(path: str) -> dict[int, dict[str, Any]]:
    payload = read_json(path)
    return {int(row["scenario_id"]): row["feature_payload"] for row in payload.get("rows", [])}


def load_adjudication(path: str) -> dict[int, dict[str, Any]]:
    payload = read_json(path)
    return {int(row["scenario_id"]): row for row in payload.get("rows", [])}


def load_manual_review(path: str | None) -> dict[int, dict[str, Any]]:
    if not path:
        return {}
    payload = read_json(path)
    return {int(row["scenario_id"]): row for row in payload.get("rows", [])}


def compact(text: str, limit: int = 900) -> str:
    text = normalize_space(text)
    return text[:limit] + ("..." if len(text) > limit else "")


def bool_table(features: dict[str, bool]) -> list[str]:
    enabled = [name for name, value in sorted(features.items()) if value]
    if not enabled:
        return ["- No extracted features were true."]
    return [f"- `{name}`" for name in enabled]


def result_table(results: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| Pipeline | Verdict | Rationale / Rule | Citation behavior |",
        "|---|---|---|---|",
    ]
    for result in results:
        if result["pipeline"] == "logicpearl":
            decision = result["ruleset_decision"]
            rationale = f"{decision['rule_label']} (`{decision['rule_id']}`)"
            citation = ", ".join(result.get("authority_ids", [])) or "none"
        elif result["pipeline"] == "rag_chunklookup":
            rationale = result["rationale"]
            citation = f"{len(result.get('resolved_citations', []))} resolved chunk(s)"
        else:
            rationale = result["rationale"]
            citation = f"{len(result.get('cited_authorities', []))} freeform excerpt(s)"
        lines.append(f"| {result['pipeline']} | `{result['verdict']}` | {rationale} | {citation} |")
    return lines


def render_case(
    scenario: Scenario,
    shared_payload: dict[str, Any],
    adjudication: dict[str, Any] | None,
    manual_review: dict[str, Any] | None,
) -> list[str]:
    features = shared_payload["features"]
    results = [
        logicpearl.run(scenario, track="B", shared_features=features),
        rag.run(scenario, track="B", shared_features=features),
        rag_chunklookup.run(scenario, track="B", shared_features=features),
    ]
    lines = [
        f"## Scenario {scenario.id}",
        "",
        f"- Agency: {scenario.agency_name}",
        f"- MuckRock URL: {scenario.muckrock_url}",
        f"- Raw primary label: `{scenario.primary_exemption}`",
        f"- Raw cited labels: `{', '.join(scenario.all_cited_exemptions)}`",
    ]
    if adjudication:
        lines.extend(
            [
                f"- Adjudication bucket: `{adjudication['benchmark_bucket']}`",
                f"- Acceptable labels: `{', '.join(adjudication['gold']['acceptable'])}`",
                f"- Ambiguity flags: `{', '.join(adjudication['ambiguity_flags']) or 'none'}`",
            ]
        )
    if manual_review:
        lines.extend(
            [
                f"- Manual review: `{manual_review['manual_status']}`",
                f"- Manual rationale: {manual_review['rationale']}",
            ]
        )
    lines.extend(
        [
            "",
            "### Request",
            "",
            compact(scenario.request_text),
            "",
            "### Shared Extracted Facts",
            "",
            *bool_table(features),
            "",
            "### Decisions",
            "",
            *result_table(results),
            "",
        ]
    )
    if adjudication:
        span = adjudication.get("evidence", {}).get("primary_span") or {}
        if span:
            lines.extend(["### Gold Evidence Span", "", compact(span.get("context", ""), 1200), ""])
    return lines


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default="scenarios/muckrock_snapshot.100.live.json")
    parser.add_argument("--shared-features", default="extraction/outputs/shared_features.100.live.openai.json")
    parser.add_argument("--adjudication", default="scenarios/adjudication.100.live.json")
    parser.add_argument("--manual-review", default="scenarios/manual_review.100.live.clean.json")
    parser.add_argument("--output", default="docs/demo/trace-viewer.md")
    parser.add_argument("--ids", nargs="+", type=int, default=[63644, 118656])
    args = parser.parse_args()

    scenarios = {int(row["id"]): Scenario.from_dict(row) for row in read_json(args.scenarios)}
    shared = load_shared_features(args.shared_features)
    adjudication = load_adjudication(args.adjudication)
    manual_review = load_manual_review(args.manual_review)

    lines = [
        "# LogicPearl Trace Viewer",
        "",
        "This demo view shows the same shared extracted facts flowing through the LogicPearl decision artifact, baseline RAG, and RAG-ChunkLookup. It is generated from the local benchmark artifacts and does not call an LLM.",
        "",
    ]
    for scenario_id in args.ids:
        lines.extend(
            render_case(
                scenarios[scenario_id],
                shared[scenario_id],
                adjudication.get(scenario_id),
                manual_review.get(scenario_id),
            )
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
