from __future__ import annotations

import argparse
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag_vs_pag.jsonio import read_json, write_json
from rag_vs_pag.text import normalize_space


EXEMPTIONS = [f"b{i}" for i in range(1, 10)]

CITATION_PATTERNS = [
    re.compile(r"(?:FOIA\s+)?exemptions?\s*(?:\(?b\)?\s*)?\(?([1-9])\)?", re.I),
    re.compile(r"(?:FOIA\s+)?exemptions?\s+b([1-9])", re.I),
    re.compile(r"(?:5\s*)?u\.?s\.?c\.?\s*§?\s*552\s*\(b\)\(([1-9])\)", re.I),
    re.compile(r"§\s*552\s*\(b\)\(([1-9])\)", re.I),
    re.compile(r"\(b\)\(([1-9])\)", re.I),
]

APPLIED_CONTEXT = re.compile(
    r"\b(?:withheld|withhold|withholding|redacted|redact|denied|deny|"
    r"exempt|pursuant to|under exemption|confidential|proprietary|"
    r"personal privacy|privacy|deliberative|attorney-client|work product|"
    r"classified|national security|law enforcement|investigat(?:e|ion|ive)|"
    r"protected by statute|prohibited from disclosure)\b",
    re.I,
)
BOILERPLATE_CONTEXT = re.compile(
    r"\b(?:appendix|standard language|general information|may be withheld|"
    r"could reasonably be expected|foreseeable harm standard|administrative appeal)\b",
    re.I,
)
PROCEDURAL_CONTEXT = re.compile(
    r"\b(?:you may file a response|will issue a decision|after we receive all responses|"
    r"submitter|consultation|third party notification|perfected request|fee category|"
    r"commercial use request|not a final agency decision)\b",
    re.I,
)
PRIVACY_CONTEXT = re.compile(r"\b(?:privacy|personal|personnel|named individual|names?|identifying)\b", re.I)
LAW_ENFORCEMENT_CONTEXT = re.compile(
    r"\b(?:fbi|dea|atf|criminal|law enforcement|investigat(?:e|ion|ive)|arrest|prosecution|case file)\b",
    re.I,
)
GENERIC_TEMPLATE_CONTEXT = re.compile(
    r"(?:all records described by 5\s*u\.?s\.?c\.?\s*§?\s*552\(a\)|"
    r"all records relating to the fulfillment of this request|"
    r"a detailed index of all claims of exemption|"
    r"for all responsive records, I also request)",
    re.I,
)


def context_window(text: str, start: int, end: int, before: int = 360, after: int = 360) -> str:
    return normalize_space(text[max(0, start - before): min(len(text), end + after)])


def find_evidence_spans(text: str) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for pattern in CITATION_PATTERNS:
        for match in pattern.finditer(text):
            exemption = f"b{match.group(1)}"
            key = (match.start(), exemption)
            if key in seen:
                continue
            seen.add(key)
            context = context_window(text, match.start(), match.end())
            spans.append(
                {
                    "exemption": exemption,
                    "start": match.start(),
                    "end": match.end(),
                    "match": match.group(0),
                    "context": context,
                    "applied_context": bool(APPLIED_CONTEXT.search(context)),
                    "boilerplate_context": bool(BOILERPLATE_CONTEXT.search(context)),
                    "procedural_context": bool(PROCEDURAL_CONTEXT.search(context)),
                }
            )
    return sorted(spans, key=lambda row: (row["start"], row["exemption"]))


def unique(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def acceptable_exemptions(row: dict[str, Any], spans: list[dict[str, Any]]) -> tuple[list[str], list[str]]:
    accepted = unique([row["primary_exemption"], *row.get("all_cited_exemptions", [])])
    sources = ["agency_cited"]
    combined_text = "\n".join(
        [
            row.get("agency_name", ""),
            row.get("request_text", ""),
            row.get("response_text", ""),
            "\n".join(span["context"] for span in spans[:8]),
        ]
    )
    privacy = bool(PRIVACY_CONTEXT.search(combined_text))
    law_enforcement = bool(LAW_ENFORCEMENT_CONTEXT.search(combined_text))
    if privacy and law_enforcement and ("b6" in accepted or "b7" in accepted):
        accepted = unique([*accepted, "b6", "b7"])
        sources.append("privacy_law_enforcement_overlap")
    return accepted, sources


def flags_for(row: dict[str, Any], spans: list[dict[str, Any]], accepted: list[str]) -> list[str]:
    flags: list[str] = []
    response_text = row.get("response_text", "")
    request_text = row.get("request_text", "")
    all_cited = row.get("all_cited_exemptions", [])

    if len(all_cited) > 1:
        flags.append("multi_exemption_letter")
    if set(accepted) & {"b6", "b7"} and "b6" in accepted and "b7" in accepted:
        flags.append("privacy_law_enforcement_overlap")
    if len(normalize_space(request_text)) < 120:
        flags.append("thin_request_text")
    if len(request_text) > 4000 and GENERIC_TEMPLATE_CONTEXT.search(request_text):
        flags.append("generic_foia_template_request")
    if not spans:
        flags.append("no_exemption_evidence_span")
    if spans and not any(span["applied_context"] for span in spans):
        flags.append("no_applied_withholding_context")
    if spans and all(span["boilerplate_context"] for span in spans):
        flags.append("boilerplate_only_or_appendix")
    if PROCEDURAL_CONTEXT.search(response_text):
        flags.append("procedural_or_nonfinal_response")
    return flags


def bucket_for(flags: list[str], spans: list[dict[str, Any]]) -> str:
    if "no_exemption_evidence_span" in flags:
        return "invalid"
    if "boilerplate_only_or_appendix" in flags and "no_applied_withholding_context" in flags:
        return "invalid"
    ambiguous_flags = {
        "boilerplate_only_or_appendix",
        "multi_exemption_letter",
        "privacy_law_enforcement_overlap",
        "generic_foia_template_request",
        "no_applied_withholding_context",
        "procedural_or_nonfinal_response",
    }
    if ambiguous_flags.intersection(flags):
        return "ambiguous"
    if not any(span["applied_context"] for span in spans):
        return "ambiguous"
    return "clean"


def confidence_for(bucket: str, flags: list[str]) -> str:
    if bucket == "clean":
        return "high"
    if bucket == "invalid":
        return "low"
    if "multi_exemption_letter" in flags or "privacy_law_enforcement_overlap" in flags:
        return "medium"
    return "low"


def rationale_for(bucket: str, flags: list[str], accepted: list[str]) -> str:
    if bucket == "clean":
        return "Single-exemption response with exemption evidence in applied withholding context."
    if bucket == "invalid":
        return "The saved response text does not provide a reliable applied FOIA exemption label."
    return (
        "The response supports an exemption label, but the case is not clean because "
        f"{', '.join(flags) or 'the label requires review'}. Acceptable labels: {', '.join(accepted)}."
    )


def adjudicate_row(row: dict[str, Any]) -> dict[str, Any]:
    spans = find_evidence_spans(row.get("response_text", ""))
    accepted, accepted_sources = acceptable_exemptions(row, spans)
    flags = flags_for(row, spans, accepted)
    bucket = bucket_for(flags, spans)
    primary_span = next((span for span in spans if span["exemption"] == row["primary_exemption"]), spans[0] if spans else None)
    primary = row["primary_exemption"]
    return {
        "scenario_id": int(row["id"]),
        "source_url": row.get("muckrock_url", ""),
        "agency_name": row.get("agency_name", ""),
        "original_primary": row["primary_exemption"],
        "original_all_cited": row.get("all_cited_exemptions", []),
        "benchmark_bucket": bucket,
        "adjudication_confidence": confidence_for(bucket, flags),
        "gold": {
            "primary": primary,
            "acceptable": accepted,
            "unacceptable": [exemption for exemption in EXEMPTIONS if exemption not in accepted],
            "acceptable_sources": accepted_sources,
        },
        "evidence": {
            "primary_span": primary_span,
            "all_spans": spans,
        },
        "ambiguity_flags": flags,
        "rationale": rationale_for(bucket, flags, accepted),
        "review_required": bucket != "clean",
    }


def filter_scenarios(rows: list[dict[str, Any]], adjudications: dict[int, dict[str, Any]], bucket: str) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows:
        adjudication = adjudications[int(row["id"])]
        if adjudication["benchmark_bucket"] != bucket:
            continue
        copy = dict(row)
        copy["benchmark_bucket"] = bucket
        copy["adjudication_confidence"] = adjudication["adjudication_confidence"]
        copy["ambiguity_flags"] = adjudication["ambiguity_flags"]
        copy["primary_exemption"] = adjudication["gold"]["primary"]
        copy["all_cited_exemptions"] = adjudication["gold"]["acceptable"]
        filtered.append(copy)
    return filtered


def filter_split(split: dict[str, list[int]], keep_ids: set[int]) -> dict[str, list[int]]:
    return {
        "dev": [scenario_id for scenario_id in split.get("dev", []) if scenario_id in keep_ids],
        "test": [scenario_id for scenario_id in split.get("test", []) if scenario_id in keep_ids],
    }


def count_by_split(adjudications: list[dict[str, Any]], split: dict[str, list[int]]) -> dict[str, dict[str, int]]:
    split_name_by_id = {scenario_id: "dev" for scenario_id in split.get("dev", [])}
    split_name_by_id.update({scenario_id: "test" for scenario_id in split.get("test", [])})
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for adjudication in adjudications:
        split_name = split_name_by_id.get(adjudication["scenario_id"], "unassigned")
        counts[split_name][adjudication["benchmark_bucket"]] += 1
    return {split_name: dict(counter) for split_name, counter in sorted(counts.items())}


def report_markdown(
    *,
    scenarios_path: str,
    split_path: str,
    adjudication_path: str,
    clean_path: str,
    clean_split_path: str,
    adjudications: list[dict[str, Any]],
    split: dict[str, list[int]],
) -> str:
    bucket_counts = Counter(row["benchmark_bucket"] for row in adjudications)
    confidence_counts = Counter(row["adjudication_confidence"] for row in adjudications)
    exemption_counts = Counter(row["gold"]["primary"] for row in adjudications)
    split_counts = count_by_split(adjudications, split)

    lines = [
        "# Live Benchmark Adjudication",
        "",
        "Date: 2026-04-17",
        "",
        "This file records the benchmark-quality pass used to separate the live MuckRock corpus into a clean adjudicated layer and a messy live layer. The pass is deterministic and does not inspect any model or LogicPearl predictions.",
        "",
        "## Inputs and Outputs",
        "",
        f"- Source scenarios: `{scenarios_path}`",
        f"- Source split: `{split_path}`",
        f"- Adjudication sidecar: `{adjudication_path}`",
        f"- Clean scenarios: `{clean_path}`",
        f"- Clean split: `{clean_split_path}`",
        "",
        "## Criteria",
        "",
        "- `clean`: one cited exemption, with a nearby response-text span that looks like applied withholding or redaction reasoning.",
        "- `ambiguous`: a reliable exemption citation exists, but the case has multi-exemption, privacy/law-enforcement overlap, generic request-template, weak applied-context, or nonfinal/procedural-response flags.",
        "- `invalid`: the saved response text does not provide a reliable applied FOIA exemption label.",
        "",
        "Acceptable labels start with all agency-cited exemptions. The only automatic expansion is the common `b6`/`b7` privacy-law-enforcement overlap when both privacy and law-enforcement context are present.",
        "",
        "## Counts",
        "",
        "| Bucket | Count |",
        "|---|---:|",
    ]
    for bucket in ("clean", "ambiguous", "invalid"):
        lines.append(f"| {bucket} | {bucket_counts.get(bucket, 0)} |")

    lines.extend(["", "| Confidence | Count |", "|---|---:|"])
    for confidence, count in sorted(confidence_counts.items()):
        lines.append(f"| {confidence} | {count} |")

    lines.extend(["", "| Primary exemption | Count |", "|---|---:|"])
    for exemption, count in sorted(exemption_counts.items()):
        lines.append(f"| {exemption} | {count} |")

    lines.extend(["", "## Counts by Split", "", "| Split | Clean | Ambiguous | Invalid |", "|---|---:|---:|---:|"])
    for split_name in ("dev", "test", "unassigned"):
        if split_name not in split_counts:
            continue
        counts = split_counts[split_name]
        lines.append(
            f"| {split_name} | {counts.get('clean', 0)} | {counts.get('ambiguous', 0)} | {counts.get('invalid', 0)} |"
        )

    lines.extend(["", "## Review Queue", "", "| ID | Bucket | Primary | Acceptable | Flags | Evidence excerpt |", "|---:|---|---|---|---|---|"])
    for row in adjudications:
        if row["benchmark_bucket"] == "clean":
            continue
        span = row["evidence"].get("primary_span") or {}
        evidence = normalize_space(str(span.get("context", "")))[:220]
        flags = ", ".join(row["ambiguity_flags"])
        acceptable = ", ".join(row["gold"]["acceptable"])
        lines.append(
            f"| {row['scenario_id']} | {row['benchmark_bucket']} | {row['gold']['primary']} | {acceptable} | {flags} | {evidence} |"
        )

    lines.extend(
        [
            "",
            "## Fairness Notes",
            "",
            "- The adjudication sidecar is independent of RAG, RAG-ChunkLookup, and LogicPearl predictions.",
            "- The clean benchmark is a filtered subset, not a relabelled performance target tuned against model mistakes.",
            "- The messy live benchmark remains available and should be reported separately from the clean layer.",
            "- Ambiguous cases are retained with `acceptable` labels so that overlap such as `b6`/`b7` privacy is not treated as a simple single-label error.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default="scenarios/muckrock_snapshot.100.live.json")
    parser.add_argument("--split", default="scenarios/split.100.live.json")
    parser.add_argument("--adjudication-output", default="scenarios/adjudication.100.live.json")
    parser.add_argument("--clean-output", default="scenarios/muckrock_snapshot.100.live.clean.json")
    parser.add_argument("--clean-split-output", default="scenarios/split.100.live.clean.json")
    parser.add_argument("--report-output", default="docs/qa/live-benchmark-adjudication.md")
    args = parser.parse_args()

    rows = read_json(args.scenarios)
    split = read_json(args.split)
    adjudications = [adjudicate_row(row) for row in rows]
    adjudication_by_id = {row["scenario_id"]: row for row in adjudications}
    clean_rows = filter_scenarios(rows, adjudication_by_id, "clean")
    clean_ids = {int(row["id"]) for row in clean_rows}
    clean_split = filter_split(split, clean_ids)

    payload = {
        "method": "deterministic_response_text_adjudication_v1",
        "source_scenarios": args.scenarios,
        "source_split": args.split,
        "criteria": {
            "clean": "single cited exemption with applied withholding/redaction context",
            "ambiguous": "valid citation with overlap, multi-exemption, generic request, weak context, or procedural/nonfinal flags",
            "invalid": "no reliable applied FOIA exemption label in saved response text",
        },
        "rows": adjudications,
    }
    write_json(args.adjudication_output, payload)
    write_json(args.clean_output, clean_rows)
    write_json(args.clean_split_output, clean_split)

    report = report_markdown(
        scenarios_path=args.scenarios,
        split_path=args.split,
        adjudication_path=args.adjudication_output,
        clean_path=args.clean_output,
        clean_split_path=args.clean_split_output,
        adjudications=adjudications,
        split=split,
    )
    report_path = Path(args.report_output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report + "\n", encoding="utf-8")

    bucket_counts = Counter(row["benchmark_bucket"] for row in adjudications)
    print(f"wrote {args.adjudication_output}")
    print(f"wrote {args.clean_output} ({len(clean_rows)} clean records)")
    print(f"wrote {args.clean_split_output}")
    print(f"wrote {args.report_output}")
    print(dict(bucket_counts))


if __name__ == "__main__":
    main()
