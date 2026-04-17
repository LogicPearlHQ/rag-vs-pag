from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from rag_vs_pag.jsonio import read_json


def rule_map(ruleset: dict) -> dict[str, dict]:
    return {rule["id"]: rule for rule in ruleset.get("rules", [])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("old")
    parser.add_argument("new")
    args = parser.parse_args()

    old = rule_map(read_json(args.old))
    new = rule_map(read_json(args.new))
    old_ids = set(old)
    new_ids = set(new)
    for rule_id in sorted(new_ids - old_ids):
        rule = new[rule_id]
        print(f"ADDED {rule_id}: {rule.get('label')} -> {rule.get('verdict')}")
    for rule_id in sorted(old_ids - new_ids):
        rule = old[rule_id]
        print(f"REMOVED {rule_id}: {rule.get('label')} -> {rule.get('verdict')}")
    for rule_id in sorted(old_ids & new_ids):
        if old[rule_id] != new[rule_id]:
            print(f"CHANGED {rule_id}")
            for key in ("priority", "label", "all", "any", "none", "verdict", "authority_ids"):
                if old[rule_id].get(key) != new[rule_id].get(key):
                    print(f"  {key}: {old[rule_id].get(key)} -> {new[rule_id].get(key)}")


if __name__ == "__main__":
    main()
