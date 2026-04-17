from __future__ import annotations

from collections import defaultdict
from typing import Any


def summarize(rows: list[dict[str, Any]]) -> str:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("kind") == "pipeline_result":
            grouped[(row["track"], row["pipeline"])].append(row)

    lines = [
        "# rag-vs-pag Final Summary",
        "",
        "## Accuracy",
        "",
        "| Track | Pipeline | Strict | Lenient | Acceptable | Trace-valid | Excerpt Fabricated | Citation Supports | Verdict Stable | Byte Identical |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for (track, pipeline), items in sorted(grouped.items()):
        first_repeats = [item for item in items if item["repeat"] == 0]
        strict = sum(1 for item in first_repeats if item["correctness"]["strict"])
        lenient = sum(1 for item in first_repeats if item["correctness"]["lenient"])
        acceptable = sum(1 for item in first_repeats if item["correctness"].get("acceptable", item["correctness"]["lenient"]))
        trace_valid = "-"
        if pipeline == "logicpearl":
            trace_valid_count = sum(
                1
                for item in first_repeats
                if item["correctness"].get("acceptable", item["correctness"]["lenient"])
                and not item.get("ruleset_decision", {}).get("defaulted", True)
                and bool(item.get("authority_ids"))
            )
            trace_valid = f"{trace_valid_count}/{len(first_repeats) or 1}"
        fabricated = sum(item["citation_metrics"]["fabricated"] for item in first_repeats)
        supports = sum(item["citation_metrics"].get("supports_verdict", 0) for item in first_repeats)
        cited = sum(item["citation_metrics"].get("cited", 0) for item in first_repeats)
        support_cell = f"{supports}/{cited}" if cited else "-"
        scenario_groups: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for item in items:
            scenario_groups[item["scenario_id"]].append(item)
        verdict_stable = sum(1 for repeats in scenario_groups.values() if len({row["verdict"] for row in repeats}) == 1)
        byte_identical = sum(1 for repeats in scenario_groups.values() if len({row["output_hash"] for row in repeats}) == 1)
        total = len(first_repeats) or 1
        scenario_total = len(scenario_groups) or 1
        lines.append(
            f"| {track} | {pipeline} | {strict}/{total} | {lenient}/{total} | {acceptable}/{total} | "
            f"{trace_valid} | {fabricated} | {support_cell} | {verdict_stable}/{scenario_total} | {byte_identical}/{scenario_total} |"
        )

    if any(row.get("llm_provider") for row in rows if row.get("kind") == "pipeline_result"):
        lines.extend(
            [
                "",
                "Note: real LLM baseline rows are cached. Stability columns measure replay stability for this artifact, not uncached sampling variance.",
            ]
        )

    bucket_scenario_ids: dict[str, set[int]] = defaultdict(set)
    logicpearl_abstentions_by_bucket: dict[str, int] = defaultdict(int)
    logicpearl_totals_by_bucket: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.get("kind") != "pipeline_result" or row.get("repeat") != 0:
            continue
        bucket = row.get("benchmark_bucket")
        if bucket:
            bucket_scenario_ids[bucket].add(int(row["scenario_id"]))
        if row.get("pipeline") == "logicpearl" and bucket:
            logicpearl_totals_by_bucket[bucket] += 1
            if row.get("ruleset_decision", {}).get("defaulted") or row.get("verdict") == "insufficient_facts":
                logicpearl_abstentions_by_bucket[bucket] += 1

    if bucket_scenario_ids:
        lines.extend(
            [
                "",
                "## Adjudication Layer",
                "",
                "LogicPearl abstentions/defaults are counted on first-repeat LogicPearl rows across evaluated tracks.",
                "",
                "| Bucket | Evaluated scenarios | LogicPearl abstentions/defaults |",
                "|---|---:|---:|",
            ]
        )
        for bucket in sorted(bucket_scenario_ids):
            total = len(bucket_scenario_ids[bucket])
            logicpearl_total = logicpearl_totals_by_bucket.get(bucket, 0)
            abstentions = logicpearl_abstentions_by_bucket.get(bucket, 0)
            abstention_cell = f"{abstentions}/{logicpearl_total}" if logicpearl_total else "-"
            lines.append(f"| {bucket} | {total} | {abstention_cell} |")

    lines.extend(
        [
            "",
            "## Capability Table",
            "",
            "| Capability | RAG | ChunkLookup | LogicPearl |",
            "|---|---:|---:|---:|",
            "| Freeform excerpt fabrication prevented | no | yes | yes |",
            "| Same fixed facts produce same verdict | no | no | yes |",
            "| Decision rule inspectable | no | no | yes |",
            "| Ruleset changes diffable | weak | weak | yes |",
            "| Regression-test ruleset changes | weak | weak | yes |",
            "",
        ]
    )
    return "\n".join(lines)
