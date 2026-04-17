from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def json_read(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def extract_accuracy_table(summary_text: str) -> str:
    match = re.search(r"## Accuracy\n\n(?P<table>\| Track \|[\s\S]*?)(?:\n\n##|\Z)", summary_text)
    if not match:
        raise ValueError("could not find accuracy table")
    return match.group("table").strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/qa/final-benchmark-report.md")
    parser.add_argument("--adjudication", default="scenarios/adjudication.100.live.json")
    parser.add_argument("--manual-review", default="scenarios/manual_review.100.live.clean.json")
    parser.add_argument("--approved-clean", default="scenarios/muckrock_snapshot.100.live.clean.approved.json")
    parser.add_argument("--approved-split", default="scenarios/split.100.live.clean.approved.json")
    parser.add_argument("--full-summary", default="transcripts/live-100-openai-adjudicated-summary.md")
    parser.add_argument("--approved-summary", default="transcripts/live-100-openai-clean-approved-summary.md")
    args = parser.parse_args()

    adjudication = json_read(args.adjudication)
    review = json_read(args.manual_review)
    approved_rows = json_read(args.approved_clean)
    approved_split = json_read(args.approved_split)
    full_table = extract_accuracy_table(read(args.full_summary))
    approved_table = extract_accuracy_table(read(args.approved_summary))

    bucket_counts = Counter(row["benchmark_bucket"] for row in adjudication["rows"])
    review_counts = Counter(row["manual_status"] for row in review["rows"])
    approved_exemptions = Counter(row["primary_exemption"] for row in approved_rows)

    lines = [
        "# Final Benchmark Report",
        "",
        "Date: 2026-04-17",
        "",
        "## Claim Boundary",
        "",
        "This benchmark evaluates a governance-oriented claim, not a broad legal-classification claim. The strongest defensible result is that a versioned decision artifact can turn shared extracted facts into stable, inspectable, trace-valid decisions, and explicitly abstain when request text lacks exemption-shaped facts.",
        "",
        "Track A is end-to-end. Track B uses one shared OpenAI structured extractor for every pipeline and isolates the decision layer. The reported RAG and RAG-ChunkLookup baselines are real OpenAI calls. There is no heuristic benchmark path.",
        "",
        "## Corpus Construction",
        "",
        "- Source: public MuckRock FOIA requests and response text/PDF text already downloaded into the repo workspace.",
        "- Live benchmark source: `scenarios/muckrock_snapshot.100.live.json`.",
        "- Raw response-derived labels are agency-cited exemptions, not judicial determinations of legal correctness.",
        "- The OpenAI extractor produces feature vectors only; it does not choose exemption labels.",
        "- The RAG baseline asks OpenAI for verdict, rationale, and quoted excerpts.",
        "- The RAG-ChunkLookup baseline asks OpenAI for verdict, rationale, and retrieved chunk IDs; server code resolves citation text.",
        "",
        "## Gold-Label Cleanup",
        "",
        "The gold-label extractor was tightened before this report. Bare `(b)(N)` citations are counted only near FOIA/exemption/withholding context, and fee-regulation contexts such as `28 C.F.R. 16.10(b)(1)` are rejected.",
        "",
        "## Deterministic Adjudication",
        "",
        "| Bucket | Count |",
        "|---|---:|",
    ]
    for bucket in ("clean", "ambiguous", "invalid"):
        lines.append(f"| {bucket} | {bucket_counts.get(bucket, 0)} |")

    lines.extend(
        [
            "",
            "Adjudication is deterministic and prediction-independent. It inspects request/response text and records flags such as `multi_exemption_letter`, `privacy_law_enforcement_overlap`, `procedural_or_nonfinal_response`, and `boilerplate_only_or_appendix`.",
            "",
            "## Manual Clean Review",
            "",
            "| Manual status | Count |",
            "|---|---:|",
        ]
    )
    for status, count in sorted(review_counts.items()):
        lines.append(f"| {status} | {count} |")

    lines.extend(
        [
            "",
            f"Approved clean records: {len(approved_rows)}",
            f"Approved clean dev records: {len(approved_split.get('dev', []))}",
            f"Approved clean test records: {len(approved_split.get('test', []))}",
            "",
            "| Approved primary exemption | Count |",
            "|---|---:|",
        ]
    )
    for exemption, count in sorted(approved_exemptions.items()):
        lines.append(f"| {exemption} | {count} |")

    lines.extend(
        [
            "",
            "Manual review excluded three mechanically clean records from the approved-clean benchmark: `14161`, `33143`, and `118656`. The reasons are recorded in `docs/qa/manual-clean-review.md`.",
            "",
            "## Full Live, Ambiguity-Aware Results",
            "",
            full_table,
            "",
            "## Approved-Clean Results",
            "",
            approved_table,
            "",
            "## Interpretation",
            "",
            "- Full live acceptable-label scoring is the right view for noisy real-world FOIA responses with overlapping exemptions.",
            "- Approved-clean scoring is the conservative view; the approved clean held-out test set is small, so it should not be overclaimed.",
            "- `insufficient_facts` is an abstention, not a correct exemption label. It separates underdetermined request text from truly releasable records.",
            "- The LogicPearl row's trace-valid column requires an acceptable verdict from a non-default rule with cited authority IDs.",
            "- RAG-ChunkLookup prevents freeform quote fabrication by resolving chunk IDs server-side, but real model-selected chunk IDs are not always support-valid.",
            "- Plain RAG did not fabricate excerpt bytes in this run, but its quote text is still model-authored rather than server-resolved.",
            "",
            "## Trace Viewer",
            "",
            "A write-up-friendly trace view is generated at `docs/demo/trace-viewer.md`. It includes one clean rule-match case and one clean agency-withholding case where request text alone produces `insufficient_facts`.",
            "",
            "## Write-Up Language",
            "",
            "Use: This benchmark tests whether a versioned decision artifact makes FOIA-style classifications easier to audit under shared extracted facts.",
            "",
            "Avoid: LogicPearl broadly outperforms RAG on legal exemption classification.",
            "",
        ]
    )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
