from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag_vs_pag.features import empty_features
from rag_vs_pag.jsonio import read_json, read_jsonl
from rag_vs_pag.ruleset import evaluate_ruleset


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ruleset", required=True)
    parser.add_argument("--cases", required=True)
    args = parser.parse_args()

    ruleset = read_json(args.ruleset)
    failures = []
    for case in read_jsonl(args.cases):
        features = empty_features()
        features.update(case.get("features", {}))
        decision = evaluate_ruleset(ruleset, features)
        if decision["verdict"] != case["expected_verdict"] or decision["rule_id"] != case["expected_rule_id"]:
            failures.append(
                {
                    "id": case["id"],
                    "expected": (case["expected_verdict"], case["expected_rule_id"]),
                    "actual": (decision["verdict"], decision["rule_id"]),
                }
            )
    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        raise SystemExit(1)
    print(f"passed {len(read_jsonl(args.cases))} ruleset regression cases")


if __name__ == "__main__":
    main()
