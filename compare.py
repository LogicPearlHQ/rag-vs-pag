from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from benchmark.run import load_adjudication, load_shared_features, load_split, run_all
from benchmark.summary import summarize
from rag_vs_pag.jsonio import read_json, write_jsonl
from rag_vs_pag.schema import load_scenarios


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", default="scenarios/muckrock_snapshot.100.live.json")
    parser.add_argument("--split", default="scenarios/split.100.live.json")
    parser.add_argument("--out", default="transcripts/final-run.jsonl")
    parser.add_argument("--summary", default="transcripts/final-summary.md")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--include-dev", action="store_true")
    parser.add_argument("--shared-features")
    parser.add_argument("--adjudication")
    args = parser.parse_args()

    scenarios = load_scenarios(read_json(args.scenarios))
    split = load_split(args.split, scenarios)
    wanted = set(split["test"])
    if args.include_dev:
        wanted.update(split.get("dev", []))
    selected = [scenario for scenario in scenarios if scenario.id in wanted]
    shared, extraction_rows = load_shared_features(args.shared_features)
    adjudication_by_id = load_adjudication(args.adjudication)
    selected_ids = {scenario.id for scenario in selected}
    extraction_rows = [row for row in extraction_rows if row["scenario_id"] in selected_ids]
    rows = run_all(selected, args.repeats, shared, extraction_rows, adjudication_by_id)
    write_jsonl(args.out, rows)
    summary = summarize(rows)
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary + "\n", encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    main()
